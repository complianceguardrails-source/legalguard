"""
Batch runner for the real, general-purpose LLM extraction step
(llm_compiler.py): fetches each candidate use case's actual GitHub README
and asks an LLM whether it implies a concrete, specific compliance-relevant
guardrail obligation, grounded in a verbatim quote from that real text.

Costs real money per use case (one real Anthropic API call each) --
deliberately run in small batches (default 25) rather than against the
whole use-case table at once, unlike the free, no-external-cost
reclassification scripts elsewhere in this directory.

Every attempt is recorded via db.store_llm_extraction() regardless of
outcome, so this script is naturally idempotent: re-running it only ever
processes use cases that have never been attempted
(db.fetch_use_cases_needing_llm_extraction), never re-spends on one
that already has an answer (including a "nothing found" answer).

Run manually:
    ANTHROPIC_API_KEY=... DATABASE_URL=postgres://... python ingestion/compile_llm_requirements.py [batch_size]
"""
from __future__ import annotations

import logging
import sys

import db
from llm_compiler import extract_compiled_requirement, ExtractionError
from sources.awesome_list_use_cases import fetch_readme_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.compile_llm_requirements")


def _owner_repo(github_reference_url: str) -> tuple[str, str] | None:
    parts = github_reference_url.rstrip("/").replace("https://github.com/", "").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def run(batch_size: int = 25) -> None:
    with db.get_conn() as conn:
        rows = db.fetch_use_cases_needing_llm_extraction(conn, limit=batch_size)
        logger.info("Found %d use case(s) not yet attempted (batch size %d)", len(rows), batch_size)

        hits = 0
        attempted = 0
        fetch_failed = 0

        for row in rows:
            owner_repo = _owner_repo(row["github_reference_url"])
            if not owner_repo:
                logger.warning("%s: could not parse owner/repo from %s, skipping", row["name"], row["github_reference_url"])
                continue

            try:
                evidence_text = fetch_readme_markdown(*owner_repo)
            except Exception:
                logger.exception("%s: README fetch failed", row["name"])
                fetch_failed += 1
                continue

            try:
                extraction = extract_compiled_requirement(row["name"], evidence_text)
            except ExtractionError as exc:
                logger.error("Stopping batch: %s", exc)
                return

            attempted += 1
            db.store_llm_extraction(conn, row["id"], extraction, evidence_text)
            if extraction:
                hits += 1
                logger.info("%s: HIT -- %s (%s requires %s)", row["name"], extraction["requirement_id"], extraction["action_type"], extraction["approval_flag"])
            else:
                logger.info("%s: no applicable requirement", row["name"])

        logger.info(
            "Done: %d attempted, %d hit (%.1f%%), %d README fetch failures, out of %d candidates",
            attempted, hits, (100.0 * hits / attempted) if attempted else 0.0, fetch_failed, len(rows),
        )


if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    try:
        run(batch_size)
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
