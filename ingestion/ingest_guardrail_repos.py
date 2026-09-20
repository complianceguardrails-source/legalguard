"""
Resolve the guardrail repositories for every granular risk
(guardrail_repo_queries.py via sources/guardrail_repos.py) and store
them. Reports the risks that end up with no control at all and the seeds
that no longer resolve, so both stay visible.

    [GITHUB_TOKEN=...] DATABASE_URL=postgres://... python ingest_guardrail_repos.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging

import db
from risk_taxonomy import BY_SLUG
from sources.guardrail_repos import mine_guardrail_repos

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_guardrail_repos")


def run(dry_run: bool) -> None:
    rows, empty, missing = mine_guardrail_repos()
    logger.info("%d repositor%s resolved (%d GitHub, %d Hugging Face)", len(rows), "y" if len(rows) == 1 else "ies",
                sum(r["platform"] == "github" for r in rows), sum(r["platform"] == "huggingface" for r in rows))
    for seed in missing:
        logger.warning("seed did not resolve: %s", seed)
    if empty:
        logger.warning("risks with no guardrail repository: %s", ", ".join(BY_SLUG[r]["label"] for r in empty))
    if dry_run:
        for r in sorted(rows, key=lambda r: -(r["stars"] or 0))[:30]:
            logger.info("  %-45s %6s  %s", r["external_id"], r["stars"], ",".join(r["risk_slugs"])[:80])
        return
    with db.get_conn() as conn:
        for r in rows:
            db.upsert_guardrail_repo(conn, r)
    logger.info("Done: %d stored", len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
