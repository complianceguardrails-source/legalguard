"""
Whole-database reclassification for every automated (github_mined /
huggingface_mined) use case, regardless of its current parent_sector /
modality / risk_tier -- not just rows sitting at the schema default.

Why this exists: reclassify_use_cases.py and reclassify_risk_tier.py only
ever touch rows still at the 'Uncategorized' / 'unclassified' fallback, by
design, so a classifier fix never overwrites a row that already has a real
label. A 100-row hand-validation pass found this is also the fix's blind
spot: a row classified before a bug was fixed can be left holding a
plausible-but-wrong non-default label forever, since nothing ever revisits
it. (Concretely: devonfire/Financial-Fraud-Detection-Model-Qwen-1.5b was
stored as 'Front Office' from before the current keyword set existed;
re-running today's classifier on it gives 'Operations & Risk'.)

This script recomputes sector/modality/risk_tier for every mined row using
the current classifier code and overwrites any that differ -- deliberately
excluding 'curated' and 'user_submitted' rows, which are human-authored
labels a heuristic classifier must never override.

Run manually:
    DATABASE_URL=postgres://... python ingestion/reclassify_all_mined.py
"""
from __future__ import annotations

import logging
import sys

import db
from usecase_classifier import classify_use_case
from risk_tier_classifier import classify_risk_tier
from reclassify_use_cases import clean_description

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.reclassify_all_mined")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_all_mined_use_cases(conn)
        logger.info("Found %d mined use case(s) to check", len(rows))

        sector_changed = 0
        risk_changed = 0
        unchanged = 0

        for row in rows:
            clean = clean_description(row["description"])
            true_sector, true_modality = classify_use_case(row["name"], clean, [])
            true_risk = classify_risk_tier(row["name"], clean, [])

            changed = False
            if true_sector != row["parent_sector"] or true_modality != row["modality"]:
                db.update_use_case_classification(conn, row["id"], true_sector, true_modality)
                logger.info(
                    "%s: sector/modality %s/%s -> %s/%s",
                    row["name"], row["parent_sector"], row["modality"], true_sector, true_modality,
                )
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
            "Done: %d sector/modality correction(s), %d risk_tier correction(s), "
            "%d row(s) already correct, out of %d total",
            sector_changed, risk_changed, unchanged, len(rows),
        )


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
