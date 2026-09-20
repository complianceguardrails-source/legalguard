"""
Ingests the legislation.gov.uk provisions (sources/legislation_gov_uk.py)
into specific_regulations. Same shape as ingest_eur_lex.py.

    DATABASE_URL=postgres://... python ingest_uk_legislation.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging

import db
from sources.legislation_gov_uk import mine_uk_legislation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_uk_legislation")


def run(dry_run: bool) -> None:
    docs = mine_uk_legislation()
    logger.info("%d provision(s) fetched%s", len(docs), " (dry run)" if dry_run else "")
    if dry_run:
        for d in docs:
            logger.info("  %-40s %s eff=%s  %s", d["clause_identifier"], d["version_label"], d["effective_date"], d["statutory_text"][:160])
        return
    with db.get_conn() as conn:
        for d in docs:
            db.upsert_regulation(conn, **d)
            logger.info("Upserted %s (%s)", d["clause_identifier"], d["version_label"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
