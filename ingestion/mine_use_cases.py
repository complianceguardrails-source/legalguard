"""
LegalGuard use-case discovery entrypoint.

Separate from main.py (the nightly regulation crawler) because this runs on
a different, slower cadence -- new financial-AI open-source repos don't
appear nearly as often as regulatory text changes, and GitHub Search API
rate limits make running this nightly wasteful. See
.github/workflows/mine_use_cases.yml for the weekly schedule.

Run manually:
    DATABASE_URL=postgres://... GITHUB_TOKEN=ghp_... python ingestion/mine_use_cases.py
"""
from __future__ import annotations

import logging
import sys

import db
from sources.github_usecases import mine_use_cases
from sources.bank_org_use_cases import mine_bank_use_cases

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.mine_use_cases")


def run() -> None:
    # Two complementary strategies: broad keyword search across all of
    # GitHub (finds independent/community projects), and a direct pull from
    # verified top-30-global-bank GitHub orgs (finds what the banks
    # themselves have actually published). Deduped by repo URL in case a
    # bank-org repo also happens to match a keyword query.
    candidates = mine_use_cases()
    bank_candidates = mine_bank_use_cases()
    seen_urls = {c["github_reference_url"] for c in candidates}
    for c in bank_candidates:
        if c["github_reference_url"] not in seen_urls:
            candidates.append(c)
            seen_urls.add(c["github_reference_url"])

    if not candidates:
        logger.warning("No candidate use cases found this run.")
        return

    with db.get_conn() as conn:
        inserted = 0
        skipped = 0
        for candidate in candidates:
            use_case_id = db.upsert_mined_use_case(
                conn,
                name=candidate["name"],
                parent_sector=candidate["parent_sector"],
                modality=candidate["modality"],
                description=candidate["description"],
                github_reference_url=candidate["github_reference_url"],
                risk_tier=candidate.get("risk_tier"),
            )
            if use_case_id:
                inserted += 1
                logger.info(
                    "Added use case: %s (%s / %s, %d stars) via query \"%s\"",
                    candidate["name"],
                    candidate["parent_sector"],
                    candidate["modality"],
                    candidate["stars"],
                    candidate["matched_query"],
                )
            else:
                skipped += 1

        logger.info("Use-case mining complete: %d added, %d already known/skipped", inserted, skipped)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
