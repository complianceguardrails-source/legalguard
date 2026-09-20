"""
Derive every visible use case's granular risks (risk_taxonomy.py) and
store them as risk_factors. Recomputes all rows each run; a rule change
is reflected on the next run. Prints coverage per family so a family no
rule reaches for most systems is visible.

    DATABASE_URL=postgres://... python tag_risk_factors.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter

import db
from risk_taxonomy import BY_SLUG, FAMILIES, assign_risk_factors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.tag_risk_factors")


def run(dry_run: bool) -> None:
    per_risk: Counter[str] = Counter()
    per_family_any: Counter[str] = Counter()
    counts: list[int] = []
    changed = 0
    with db.get_conn() as conn:
        rows = db.fetch_visible_use_cases_for_risk_factors(conn)
        for uc in rows:
            factors = assign_risk_factors(uc)
            counts.append(len(factors))
            per_risk.update(factors)
            for fam in {BY_SLUG[f]["family"] for f in factors}:
                per_family_any[fam] += 1
            if factors != (uc.get("risk_factors") or []):
                changed += 1
                if not dry_run:
                    db.set_risk_factors(conn, uc["id"], factors)
    n = len(rows)
    logger.info("%d use case(s); risks per use case: min %d, median %d, max %d; %d with none",
                n, min(counts), sorted(counts)[n // 2], max(counts), sum(1 for c in counts if c == 0))
    for fam, label in FAMILIES.items():
        logger.info("  %-40s reaches %4d (%d%%)", label, per_family_any[fam], 100 * per_family_any[fam] // n)
    logger.info("least assigned: %s", per_risk.most_common()[-8:])
    logger.info("%d row(s) %s", changed, "would change" if dry_run else "updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
