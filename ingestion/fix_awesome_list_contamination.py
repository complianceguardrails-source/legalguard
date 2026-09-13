"""
One-off decontamination for use cases mined via sources/awesome_list_use_cases.py.

The provenance suffix awesome_list_use_cases.py appends to the stored
description -- "(curated in {owner}/{repo}'s awesome-list)" -- can contain a
real classifier keyword purely as part of the owner/repo name, independent of
what the linked repo actually is. Confirmed live in this DB: every one of the
125 use cases sourced from paperswithbacktest/awesome-systematic-trading was
classified with that suffix already present in the text, so:
  - "trading" inside "awesome-systematic-trading" spuriously matches the CIB
    sector keyword for every single row from that list (pytorch, scipy,
    scikit-learn included, none of which are CIB-specific)
  - "backtest" inside "paperswithbacktest" spuriously matches the
    minimal_risk keyword the same way

reclassify_use_cases.py / reclassify_risk_tier.py already strip this same
suffix before reclassifying, but only ever touch rows still sitting at the
'Uncategorized'/'unclassified' fallback default -- by design, so they never
overwrite a real classification. That design is exactly why this bug went
unnoticed: a wrong-but-plausible non-default label (CIB, minimal_risk) never
gets revisited. This script is the deliberate exception: it recomputes and
overwrites sector/modality/risk_tier for every row carrying the provenance
suffix, regardless of current value, using the same clean_description() strip
reclassify_use_cases.py already established.

Run manually:
    DATABASE_URL=postgres://... python ingestion/fix_awesome_list_contamination.py
"""
from __future__ import annotations

import logging
import sys

import db
from usecase_classifier import classify_use_case
from risk_tier_classifier import classify_risk_tier
from reclassify_use_cases import clean_description

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.fix_awesome_list_contamination")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_use_cases_with_awesome_list_provenance(conn)
        logger.info("Found %d use case(s) with awesome-list provenance suffix", len(rows))

        sector_changed = 0
        risk_changed = 0
        unchanged = 0

        for row in rows:
            clean = clean_description(row["description"])
            true_sector, true_modality = classify_use_case(row["name"], clean, [])
            true_risk = classify_risk_tier(row["name"], clean, [])

            changed = False
            if true_sector != row["parent_sector"]:
                db.update_use_case_classification(conn, row["id"], true_sector, true_modality)
                logger.info("%s: sector %s -> %s", row["name"], row["parent_sector"], true_sector)
                sector_changed += 1
                changed = True
            if true_risk != row["risk_tier"]:
                db.update_risk_tier(conn, row["id"], true_risk)
                logger.info("%s: risk_tier %s -> %s", row["name"], row["risk_tier"], true_risk)
                risk_changed += 1
                changed = True
            if not changed:
                unchanged += 1

        logger.info(
            "Done: %d sector correction(s), %d risk_tier correction(s), %d row(s) already correct, out of %d total",
            sector_changed, risk_changed, unchanged, len(rows),
        )


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
