"""
Fetch the FINOS AI Governance Framework (sources/finos_aigf.py), attach
this app's crosswalk (finos_crosswalk.py) to each risk, and store both
collections. Reports what the crosswalk does not reach, in both
directions, so the gaps stay visible.

    [GITHUB_TOKEN=...] DATABASE_URL=postgres://... python ingest_finos_framework.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging

import db
from finos_crosswalk import CROSSWALK, UNMAPPED_FINOS, unmapped_ours
from risk_taxonomy import BY_SLUG
from sources.finos_aigf import mine_finos_framework

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_finos")


def run(dry_run: bool) -> None:
    risks, mitigations = mine_finos_framework()

    for risk in risks:
        mapped = CROSSWALK.get(risk["external_id"])
        risk["risk_slugs"] = mapped[0] if mapped else None
        risk["crosswalk_note"] = mapped[1] if mapped else UNMAPPED_FINOS.get(risk["external_id"])

    mapped_count = sum(1 for r in risks if r["risk_slugs"])
    logger.info("%d risk(s), %d mitigation(s); %d risk(s) mapped to this taxonomy", len(risks), len(mitigations), mapped_count)
    for r in risks:
        if not r["risk_slugs"]:
            logger.info("  unmapped FINOS risk %-6s %s", r["external_id"], r["title"])
    missing = unmapped_ours()
    logger.info("%d of our risks have no FINOS counterpart (mostly macroprudential and environmental)", len(missing))

    if dry_run:
        for r in risks[:5]:
            logger.info("  %-6s %-42s -> %s", r["external_id"], r["title"][:42],
                        ", ".join(BY_SLUG[s]["label"] for s in r["risk_slugs"] or []) or "-")
        return

    with db.get_conn() as conn:
        for row in risks + mitigations:
            db.upsert_finos_entry(conn, row)
    logger.info("Done: %d entries stored", len(risks) + len(mitigations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
