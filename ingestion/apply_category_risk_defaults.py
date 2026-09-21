"""
Tier every still-unclassified, categorised use case. The row's own text
is tried first (explain_risk_tier, so a keyword added later is picked up
on the next run); only when no phrase matches does the category default
(risk_tier_classifier.CATEGORY_DEFAULT_TIER) apply, stored with a basis
that says it is a default and not a phrase match. Rows already tiered
are never touched. Re-run after resetting category-default rows when the
defaults change.

    python apply_category_risk_defaults.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter

import db
from backfill_risk_basis import evidence_for
from risk_tier_classifier import default_risk_for_categories, explain_risk_tier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.category_risk_defaults")


def recompute_phrase_tiers(dry_run: bool) -> None:
    """After the keyword list changes: rows whose tier came from a phrase
    (or a category default) are re-derived from text; a row whose text now
    matches a different tier moves. Hand-set tiers (no risk_basis) are
    left alone (curated and user-submitted rows without a stored basis)."""
    outcomes: Counter[str] = Counter()
    with db.get_conn() as conn:
        for row in db.fetch_use_cases_for_risk_basis(conn):
            # Hand-set means a person set it: curated and user-submitted
            # rows without a stored basis. A mined row's tier is always
            # the classifier's, so it is always fair to re-derive.
            if not row.get("risk_basis") and row["source"] in ("curated", "user_submitted"):
                continue
            explained = explain_risk_tier(row["name"], evidence_for(row), [])
            if not explained:
                continue
            if explained["tier"] != row["risk_tier"]:
                outcomes[f"{row['risk_tier']}->{explained['tier']}"] += 1
                if not dry_run:
                    db.update_risk_tier(conn, row["id"], explained["tier"])
                    db.set_risk_basis(conn, row["id"], explained)
            elif (row["risk_basis"] or {}).get("from") == "category_default":
                # text now supports the same tier: record the phrase basis
                outcomes["basis_upgraded"] += 1
                if not dry_run:
                    db.set_risk_basis(conn, row["id"], explained)
    logger.info("Recompute: %s", dict(outcomes))


def run(dry_run: bool) -> None:
    outcomes: Counter[str] = Counter()
    with db.get_conn() as conn:
        rows = db.fetch_unclassified_categorised_use_cases(conn)
        logger.info("%d unclassified use case(s) with categories", len(rows))
        for row in rows:
            explained = explain_risk_tier(row["name"], evidence_for(row), [])
            how = "phrase"
            if not explained:
                explained = default_risk_for_categories(row["categories"])
                how = "default"
            if not explained:
                outcomes["no_default"] += 1
                continue
            outcomes[f"{explained['tier']}:{how}"] += 1
            if not dry_run:
                db.update_risk_tier(conn, row["id"], explained["tier"])
                db.set_risk_basis(conn, row["id"], explained)
    logger.info("Outcomes: %s", dict(outcomes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recompute", action="store_true", help="re-derive phrase-based tiers after a keyword change")
    args = parser.parse_args()
    if args.recompute:
        recompute_phrase_tiers(args.dry_run)
    run(args.dry_run)
