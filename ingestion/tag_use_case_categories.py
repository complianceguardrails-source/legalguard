"""
Assigns use-case categories (usecase_categories.py) to every row of
banking_use_cases from its real evidence -- name, description, and the
model-card or README prose the enrichment steps store -- and writes the
untagged rows to a review file.

Recomputes every row, not just those without categories: keyword lists
change, and a row tagged under an older list should follow the current
one. Rows that match nothing are stored as NULL, which the app hides.
Tagging the corpus showed that set is mostly not financial AI at all
(see usecase_categories.py), but not entirely -- a real finance model
whose card is gated or missing can land there too -- so the review file
exists to rescue those by hand rather than lose them.

Run after enrich_hf_model_cards.py, since that is where most of the
evidence comes from.

Run manually:
    DATABASE_URL=postgres://... python ingestion/tag_use_case_categories.py [--dry-run] [--review-file untagged.tsv]
"""
from __future__ import annotations

import argparse
import collections
import logging
import sys
from pathlib import Path

import db
from sources.huggingface_usecases import card_prose_head
from usecase_categories import CATEGORIES, CATEGORY_LABELS, assign_categories

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.tag_use_case_categories")


def evidence_for(row: dict) -> str:
    if row.get("model_card_text"):
        return card_prose_head(row["model_card_text"])
    return (row.get("llm_evidence_text") or "")[:1500]


def run(dry_run: bool, review_file: Path) -> None:
    sizes: collections.Counter = collections.Counter()
    per_row: collections.Counter = collections.Counter()
    changed = 0
    untagged: list[dict] = []

    with db.get_conn() as conn:
        rows = db.fetch_use_cases_for_categorisation(conn)
        logger.info("%d use case(s)%s", len(rows), " (dry run)" if dry_run else "")

        for row in rows:
            cats = assign_categories(row["name"], row.get("description"), evidence_for(row))
            per_row[len(cats)] += 1
            for c in cats:
                sizes[c] += 1
            if not cats:
                untagged.append(row)
            if cats != (row.get("categories") or []):
                changed += 1
                if not dry_run:
                    db.set_use_case_categories(conn, row["id"], cats)

    covered = len(rows) - len(untagged)
    logger.info("Covered %d/%d (%.0f%%); %d row(s) changed", covered, len(rows), 100 * covered / len(rows), changed)
    logger.info("Categories per use case: %s", dict(sorted(per_row.items())))
    for c in CATEGORIES:
        logger.info("  %-22s %5d", CATEGORY_LABELS[c], sizes[c])

    with review_file.open("w", encoding="utf-8") as sink:
        sink.write("name\tsource\tdescription\n")
        for row in untagged:
            sink.write(f"{row['name']}\t{row['source']}\t{(row.get('description') or '')[:120].replace(chr(9), ' ')}\n")
    logger.info("%d untagged row(s) written to %s for review", len(untagged), review_file)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--review-file", type=Path, default=Path("untagged_use_cases.tsv"))
    args = parser.parse_args()
    run(args.dry_run, args.review_file)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
