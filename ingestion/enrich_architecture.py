"""
Backfills banking_use_cases.architecture_signal for every GitHub-mined use
case that doesn't have one yet -- a real value read from its repo (a known
agent/AI framework detected in the repo's own topics, or failing that its
primary language), never a guessed one. See
database/migrations/001_add_architecture_signal.sql and
sources/architecture_enricher.py for how the signal is derived.

Run manually:
    DATABASE_URL=postgres://... GITHUB_TOKEN=ghp_... python ingestion/enrich_architecture.py
"""
from __future__ import annotations

import logging
import os
import sys
import time

import requests

import db
from sources.architecture_enricher import RateLimited, fetch_architecture_signal, parse_owner_repo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.enrich_architecture")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_use_cases_missing_architecture_signal(conn)
        logger.info("Found %d use case(s) needing an architecture_signal backfill", len(rows))

        updated = 0
        skipped = 0
        for row in rows:
            owner_repo = parse_owner_repo(row["github_reference_url"], row["name"])
            if not owner_repo:
                skipped += 1
                continue
            owner, repo = owner_repo
            try:
                signal = fetch_architecture_signal(owner, repo)
            except RateLimited as exc:
                logger.warning("%s -- stopping this run", exc)
                break
            except requests.RequestException:
                logger.exception("Failed fetching %s/%s", owner, repo)
                skipped += 1
                continue

            if signal:
                db.set_architecture_signal(conn, row["id"], signal)
                updated += 1
                logger.info("%s -> %s", row["name"], signal)
            else:
                skipped += 1
                logger.info("%s -> no language/topic signal available", row["name"])

            time.sleep(0.15 if os.environ.get("GITHUB_TOKEN") else 1.0)

        logger.info("Done: %d updated, %d skipped (no repo, 404, or no usable signal)", updated, skipped)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
