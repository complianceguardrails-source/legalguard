"""
Backfills banking_use_cases.system_interface_type and
.agent_operational_tools for every GitHub-mined use case that doesn't have
them yet -- real values read from the repo's own dependency manifest
(requirements.txt, pyproject.toml, or package.json, whichever exists
first), never guessed from the repo's name/description. See
database/migrations/005_add_model_system_taxonomy.sql and
sources/architecture_enricher.py::fetch_manifest_signals for exactly what
counts as evidence.

A repo with no recognized manifest file, or a manifest with no recognized
dependency, is left with both fields NULL -- that's the correct, honest
outcome for real evidence not found, not something this script tries to
compensate for by guessing.

Run manually:
    DATABASE_URL=postgres://... GITHUB_TOKEN=ghp_... python ingestion/enrich_system_signals.py
"""
from __future__ import annotations

import logging
import os
import sys
import time

import requests

import db
from sources.architecture_enricher import RateLimited, fetch_manifest_signals, parse_owner_repo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.enrich_system_signals")


def run() -> None:
    with db.get_conn() as conn:
        rows = db.fetch_use_cases_missing_system_signals(conn)
        logger.info("Found %d use case(s) needing a system-signal backfill", len(rows))

        updated = 0
        skipped = 0
        for row in rows:
            owner_repo = parse_owner_repo(row["github_reference_url"], row["name"])
            if not owner_repo:
                skipped += 1
                continue
            owner, repo = owner_repo
            try:
                system_interface_type, tools = fetch_manifest_signals(owner, repo)
            except RateLimited as exc:
                logger.warning("%s -- stopping this run", exc)
                break
            except requests.RequestException:
                logger.exception("Failed fetching manifest for %s/%s", owner, repo)
                skipped += 1
                continue

            if system_interface_type:
                db.set_system_interface_type(conn, row["id"], system_interface_type)
            if tools:
                db.set_agent_operational_tools(conn, row["id"], tools)

            if system_interface_type or tools:
                updated += 1
                logger.info("%s -> interface=%s tools=%s", row["name"], system_interface_type, tools)
            else:
                skipped += 1
                logger.info("%s -> no manifest file or no recognized dependency", row["name"])

            # Two manifest fetch attempts possible per repo (tries up to 3
            # filenames, most stop at the first hit or first 404 chain) --
            # pace a little more conservatively than the single-call
            # architecture enricher.
            time.sleep(0.3 if os.environ.get("GITHUB_TOKEN") else 1.5)

        logger.info("Done: %d updated, %d skipped (no repo, no manifest, or no usable signal)", updated, skipped)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
