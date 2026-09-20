"""
Fetch today's AI-risk headlines from the allowlisted outlets and
regulators (sources/risk_news.py) and store the ones that map onto the
risk taxonomy. Meant to run on a schedule; re-running is safe (URL is
the key).

    DATABASE_URL=postgres://... python ingest_risk_news.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter

import db
from sources.risk_news import mine_risk_news

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_risk_news")


def run(dry_run: bool) -> None:
    stories = mine_risk_news()
    fam: Counter[str] = Counter(f for s in stories for f in s["families"])
    logger.info("%d matching stor%s; by family: %s", len(stories), "y" if len(stories) == 1 else "ies", dict(fam.most_common()))
    if dry_run:
        for s in stories[:40]:
            logger.info("  [%s] %s -> %s (%s)", s["outlet"], s["title"][:90], ",".join(s["risk_slugs"]), ",".join(s["matched_terms"]))
        return
    new = 0
    with db.get_conn() as conn:
        for s in stories:
            new += db.upsert_risk_news_story(conn, s)
    logger.info("Done: %d new, %d already stored", new, len(stories) - new)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
