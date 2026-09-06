"""
One-time data migration: copies every row from the local dev Postgres
instance into the new Neon production database, table by table, using
psycopg directly (pg_dump/pg_restore weren't usable here -- the only
locally available pg_dump binary was version-mismatched against the
local server, and a cached libpq bottle was missing symbols). schema.sql
must already be applied to the target (Neon) database before running this.

Run manually:
    LOCAL_DATABASE_URL=postgresql://legalguard_admin@localhost:5434/legalguard \
    NEON_DATABASE_URL=postgresql://... \
    python ingestion/migrate_to_neon.py
"""
from __future__ import annotations

import logging
import os
import sys

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.migrate_to_neon")

# Dependency order matters for the two junction/FK tables at the end.
TABLES = [
    "banking_use_cases",
    "specific_regulations",
    "guardrail_packages",
    "guardrail_regulatory_mapping",
    "regulatory_horizon_forecast",
    "ingestion_cache",
    "user_subscriptions",
]


def _decode_value(v):
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8")
    if isinstance(v, list):
        # TEXT[] columns (e.g. upstream_catalyst_drivers) hit the same
        # bytes-vs-str quirk on their individual elements, not just at the
        # top level -- missing this recursive case is exactly what let
        # every regulatory_horizon_forecast row's array elements get
        # migrated as bytea-hex-literal garbage (\x6d61726b...) instead of
        # plain text, since the outer value is a list, not bytes itself,
        # so a shallow isinstance check on the row tuple never touched it.
        return [_decode_value(item) for item in v]
    return v


def _decode_row(row):
    # This local connection returns some TEXT/VARCHAR columns (and, as
    # above, array elements) as raw bytes rather than str (a driver/libpq
    # quirk seen throughout this project's scripts) -- no column in this
    # schema is meant to hold real binary data, so decoding any stray bytes
    # as utf-8 is always safe here.
    return tuple(_decode_value(v) for v in row)


def copy_table(local_conn, neon_conn, table: str) -> int:
    with local_conn.cursor() as local_cur:
        local_cur.execute(f"SELECT * FROM {table}")
        rows = [_decode_row(row) for row in local_cur.fetchall()]
        columns = [d.name for d in local_cur.description]

    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    with neon_conn.cursor() as neon_cur:
        neon_cur.executemany(insert_sql, rows)

    return len(rows)


def run() -> None:
    local_url = os.environ.get("LOCAL_DATABASE_URL")
    neon_url = os.environ.get("NEON_DATABASE_URL")
    if not local_url or not neon_url:
        raise RuntimeError("Both LOCAL_DATABASE_URL and NEON_DATABASE_URL must be set")

    with psycopg.connect(local_url, autocommit=True) as local_conn, \
         psycopg.connect(neon_url, autocommit=True) as neon_conn:
        for table in TABLES:
            count = copy_table(local_conn, neon_conn, table)
            logger.info("%s: copied %d row(s)", table, count)

    logger.info("Migration complete.")


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
