"""
Earth-observation systems that were not built for finance, stored with
the financial decision each could feed (spatial_translation.py).

They are marked 'translatable', never 'deployed': the catalogue's promise
is that a card is a real system, and these are -- but they are not
financial systems, and the app keeps them in their own section for that
reason. A repository that matches no capability is skipped rather than
guessed at.

    [GITHUB_TOKEN=...] DATABASE_URL=postgres://... python ingest_spatial_translatable.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter

import db
from sources.github_usecases import mine_use_cases
from sources.huggingface_usecases import mine_hf_use_cases
from spatial_translation import all_queries, hf_queries, translate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.spatial_translatable")

MIN_STARS = 5  # above the general floor: these are adaptations, not finds


def run(dry_run: bool) -> None:
    candidates = mine_use_cases(queries=all_queries(), min_stars=MIN_STARS)
    candidates += mine_hf_use_cases(queries=hf_queries(), tags=[])
    by_capability: Counter[str] = Counter()
    rows = []
    for c in candidates:
        t = translate(c["name"], c.get("description"))
        if not t:
            continue
        by_capability[t.id] += 1
        rows.append((c, t))

    logger.info("%d candidate(s) -> %d with a stated translation", len(candidates), len(rows))
    for cap, n in by_capability.most_common():
        logger.info("   %-20s %d", cap, n)

    if dry_run:
        for c, t in rows[:25]:
            logger.info("  %-46s %-16s -> %s", c["name"][:46], t.id, t.application[:60])
        return

    new = 0
    with db.get_conn() as conn:
        for c, t in rows:
            new += db.upsert_translatable_use_case(
                conn,
                name=c["name"], parent_sector=c["parent_sector"], modality=c["modality"],
                description=c["description"], github_reference_url=c.get("github_reference_url"),
                hf_model_id=c.get("hf_model_id"), risk_tier=c.get("risk_tier"),
                categories=["spatial_finance"] + t.categories,
                translation={"rule": t.id, "capability": t.capability, "application": t.application,
                             "application_short": t.application_short, "prerequisite": t.prerequisite,
                             # spatial_finance included: these rows are the
                             # category, and the keyword tagger cannot see
                             # it from a description that says only
                             # "semantic segmentation".
                             "categories": ["spatial_finance"] + t.categories},
            )
    logger.info("Done: %d new, %d already stored", new, len(rows) - new)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
