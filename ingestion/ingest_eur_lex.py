"""
Ingests the EUR-Lex financial-services articles (sources/eur_lex.py) into
specific_regulations. The scheduled run (main.py) does the same thing on
its cadence; this exists for the first run and for manual re-runs, and it
has a --dry-run that fetches and parses everything but writes nothing.

Same cache and upsert path as main.py: an article whose text is unchanged
since the last run is skipped; one whose text changed (a newer
consolidation) is upserted under its new version_label, which is part of
the conflict key, so the previous version's row -- and any guardrail
mapped to it -- is left intact.

Run manually:
    DATABASE_URL=postgres://... python ingestion/ingest_eur_lex.py [--dry-run]
"""
from __future__ import annotations

import argparse
import collections
import logging
import sys

import db
from sources.eur_lex import mine_eur_lex_regulations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_eur_lex")


def run(dry_run: bool) -> None:
    docs = mine_eur_lex_regulations()
    logger.info("%d article(s) fetched%s", len(docs), " (dry run)" if dry_run else "")

    by_act: collections.Counter = collections.Counter(d["official_title"].split(" Article ")[0] for d in docs)
    for act, n in by_act.items():
        logger.info("  %s: %d", act, n)

    if dry_run:
        for d in docs:
            logger.info("  %-44s %-9s pub=%s eff=%s %6d chars  %s",
                        d["clause_identifier"], d["version_label"], d["publication_date"],
                        d["effective_date"], len(d["statutory_text"]), d["source_url"])
        return

    with db.get_conn() as conn:
        new = unchanged = 0
        for doc in docs:
            cache_key = f"{doc['ingestion_source']}:{doc['jurisdiction']}:{doc['issuing_body']}:{doc['clause_identifier']}"
            content_hash = db.sha256_of(doc["statutory_text"])
            if db.is_unchanged(conn, cache_key, content_hash):
                unchanged += 1
                continue
            db.upsert_regulation(conn, **doc)
            db.upsert_cache(conn, cache_key, content_hash)
            new += 1
            logger.info("Upserted %s (%s)", doc["clause_identifier"], doc["version_label"])
        logger.info("Done: %d new/changed, %d unchanged", new, unchanged)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
