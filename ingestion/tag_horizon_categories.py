"""
Place every horizon forecast against the use-case categories it would
reach, using the same matcher that categorises use cases (bill name,
driver description and the suggested guardrail logic are the text).

    DATABASE_URL=postgres://... python tag_horizon_categories.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging

import db
from usecase_categories import CATEGORY_LABELS, categorise_with_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.tag_horizon_categories")


def run(dry_run: bool) -> None:
    changed = uncategorised = 0
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, projected_bill_name, underlying_driver_description, "
                "suggested_proactive_guardrail_logic, affected_categories FROM regulatory_horizon_forecast"
            )
            rows = cur.fetchall()
        for forecast_id, name, description, logic, stored in rows:
            matches = categorise_with_evidence(name, description, logic)
            cats = sorted(matches) or None
            if not cats:
                uncategorised += 1
            logger.info("%-52s -> %s", name[:52], ", ".join(CATEGORY_LABELS[c] for c in cats or []) or "no category matched")
            if cats == (stored or None):
                continue
            changed += 1
            if not dry_run:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE regulatory_horizon_forecast SET affected_categories = %s, category_evidence = %s, "
                        "updated_at = now() WHERE id = %s",
                        (cats, json.dumps(matches) if matches else None, forecast_id),
                    )
                conn.commit()
    logger.info("%d forecast(s) %s; %d matched no category", changed, "would change" if dry_run else "updated", uncategorised)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
