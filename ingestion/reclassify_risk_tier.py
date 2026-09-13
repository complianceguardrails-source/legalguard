"""
Re-runs risk_tier_classifier.py against every use case still sitting at the
'unclassified' schema default -- many predate the hyphen/underscore
normalization fix in risk_tier_classifier.py, which meant a real,
obviously-matching name like "credit-scoring-model" never matched the
keyword phrase "credit scoring" at all (only a literal space would match).

Only ever touches rows currently at 'unclassified' -- never overwrites a
row that already has a real tier, whether hand-curated or previously
classified successfully.

Run manually:
    DATABASE_URL=postgres://... python ingestion/reclassify_risk_tier.py
"""
from __future__ import annotations

import logging
import sys

import db
from risk_tier_classifier import classify_risk_tier
from reclassify_use_cases import clean_description

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.reclassify_risk_tier")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_unclassified_risk_tier_use_cases(conn)
        logger.info("Found %d use case(s) still at 'unclassified' risk_tier", len(rows))

        reclassified = 0
        still_unclassified = 0
        for row in rows:
            tier = classify_risk_tier(row["name"], clean_description(row["description"]), [])
            if tier != "unclassified":
                db.update_risk_tier(conn, row["id"], tier)
                reclassified += 1
                logger.info("%s -> %s", row["name"], tier)
            else:
                still_unclassified += 1

        logger.info(
            "Done: %d reclassified out of %d, %d still genuinely unclassified",
            reclassified, len(rows), still_unclassified,
        )


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
