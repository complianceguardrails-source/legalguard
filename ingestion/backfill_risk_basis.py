"""
Backfill risk_basis (migrations/009): re-derive each classified use case's
risk tier from its stored text with explain_risk_tier() and, where that
reproduces the stored tier, record the matched phrases and their legal
basis. Where it does not -- the tier was set with signals that were never
persisted (repo topics, Hub tags), or by a later hand correction -- the
tier is left alone and risk_basis stays NULL: a basis that doesn't explain
the stored tier would be worse than none.

    python backfill_risk_basis.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter

import db
from reclassify_use_cases import clean_description
from risk_tier_classifier import explain_risk_tier
from sources.huggingface_usecases import card_prose_head

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.backfill_risk_basis")


def evidence_for(row: dict) -> str:
    # The same text enrich_hf_model_cards.py classified on: the card's
    # opening prose when there is a card, else the description.
    if row["source"] == "huggingface_mined" and row.get("model_card_text"):
        return card_prose_head(row["model_card_text"])
    return clean_description(row.get("description") or "")


def run(dry_run: bool) -> None:
    outcomes: Counter[str] = Counter()
    mismatches: list[str] = []
    with db.get_conn() as conn:
        rows = db.fetch_use_cases_for_risk_basis(conn)
        logger.info("%d classified use case(s)", len(rows))
        for row in rows:
            explained = explain_risk_tier(row["name"], evidence_for(row), [])
            if explained and explained["tier"] == row["risk_tier"]:
                outcomes["reproduced"] += 1
                if not dry_run:
                    db.set_risk_basis(conn, row["id"], explained)
            else:
                got = explained["tier"] if explained else "unclassified"
                outcomes[f"not_reproduced:{row['risk_tier']}->{got}"] += 1
                mismatches.append(f"{row['name']}: stored {row['risk_tier']}, text gives {got}")
                if not dry_run:
                    db.set_risk_basis(conn, row["id"], None)
    logger.info("Outcomes: %s", dict(outcomes))
    for line in mismatches[:40]:
        logger.info("  %s", line)
    if len(mismatches) > 40:
        logger.info("  ... %d more", len(mismatches) - 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
