"""
Re-runs usecase_classifier.py against every use case still sitting at the
'Uncategorized' fallback -- most of them predate the Insurance and Climate &
Sustainable Finance sector keywords added to usecase_classifier.py, so a
large share (320 of 451 at last count) were never actually unclassifiable,
just missing a matching sector at classification time.

Only ever touches rows currently at 'Uncategorized' -- never overwrites a
row that already has a real sector, whether hand-curated or previously
classified successfully.

Run manually:
    DATABASE_URL=postgres://... python ingestion/reclassify_use_cases.py
"""
from __future__ import annotations

import logging
import re
import sys

import db
from usecase_classifier import classify_use_case

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.reclassify_use_cases")

# sources/awesome_list_use_cases.py appends "(curated in {owner}/{repo}'s
# awesome-list)" to the stored description for provenance -- strip it before
# reclassifying, or a list name like "awesome-systematic-trading" spuriously
# matches the CIB sector's "trading" keyword for every repo pulled from that
# list, regardless of what the repo itself actually is (numpy, pandas, and
# scikit-learn all got mis-tagged CIB this way before this fix).
PROVENANCE_SUFFIX_RE = re.compile(r"\s*\(curated in [^)]+'s awesome-list\)\s*$")


def clean_description(description: str) -> str:
    return PROVENANCE_SUFFIX_RE.sub("", description or "")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_uncategorized_use_cases(conn)
        logger.info("Found %d use case(s) still at 'Uncategorized'", len(rows))

        reclassified = 0
        still_uncategorized = 0
        for row in rows:
            sector, modality = classify_use_case(row["name"], clean_description(row["description"]), [])
            if sector != "Uncategorized":
                db.update_use_case_classification(conn, row["id"], sector, modality)
                reclassified += 1
                logger.info("%s -> %s / %s", row["name"], sector, modality)
            else:
                still_uncategorized += 1

        logger.info(
            "Done: %d reclassified out of %d, %d still genuinely uncategorized",
            reclassified, len(rows), still_uncategorized,
        )


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
