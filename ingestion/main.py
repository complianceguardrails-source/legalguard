"""
LegalGuard ingestion entrypoint.

Run manually:
    DATABASE_URL=postgres://... python ingestion/main.py

Run nightly for free via .github/workflows/ingest.yml (GitHub-hosted runner,
scheduled cron, DATABASE_URL supplied as a repo secret).

Pipeline per run:
  1. Pull new/changed documents from Federal Register (US) + configured RSS
     feeds (UK/EU-style regulators).
  2. Skip anything whose content hash matches ingestion_cache (no-op for
     unchanged documents -- this is the Redis-cache idea from the design
     doc, implemented as a plain Postgres table so there's no second
     service to run for free).
  3. Upsert each genuinely new/changed document as its own row in
     specific_regulations -- regulations are never merged across
     jurisdictions or agencies, even when textually similar.
  4. Run the keyword tagger against banking_use_cases to produce candidate
     blast-radius matches, logged for the mobile app's Impact Diff screen
     to surface for human review.
"""
from __future__ import annotations

import logging
import sys
from datetime import date, timedelta

import db
from config import RSS_FEEDS
from sources import federal_register, rss_source
from tagger import classify_origin_driver, tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest")


def run() -> None:
    since = (date.today() - timedelta(days=14)).isoformat()

    documents: list[dict] = []
    try:
        documents.extend(federal_register.fetch_documents(published_after=since))
    except Exception:
        logger.exception("Federal Register ingestion failed; continuing with other sources")

    for jurisdiction, issuing_body, feed_url in RSS_FEEDS:
        try:
            documents.extend(rss_source.fetch_feed(feed_url, jurisdiction, issuing_body))
        except Exception:
            logger.exception("RSS ingestion failed for %s (%s); continuing", issuing_body, feed_url)

    if not documents:
        logger.warning("No documents fetched this run.")
        return

    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        new_count = 0
        skipped_count = 0

        for doc in documents:
            cache_key = f"{doc['ingestion_source']}:{doc['jurisdiction']}:{doc['issuing_body']}:{doc['clause_identifier']}"
            content_hash = db.sha256_of(doc["statutory_text"])

            if db.is_unchanged(conn, cache_key, content_hash):
                skipped_count += 1
                continue

            driver_category, driver_reason = classify_origin_driver(
                f"{doc['official_title']} {doc['statutory_text']}"
            )

            reg_id = db.upsert_regulation(
                conn,
                jurisdiction=doc["jurisdiction"],
                issuing_body=doc["issuing_body"],
                clause_identifier=doc["clause_identifier"],
                official_title=doc["official_title"],
                source_url=doc["source_url"],
                statutory_text=doc["statutory_text"],
                version_label=doc["version_label"],
                publication_date=doc["publication_date"],
                effective_date=doc["effective_date"],
                risk_level=doc["risk_level"],
                ingestion_source=doc["ingestion_source"],
                origin_driver_category=driver_category,
                origin_driver_description=driver_reason,
            )
            db.upsert_cache(conn, cache_key, content_hash)
            new_count += 1

            logger.info(
                "New/changed regulation %s (%s) -> origin driver: %s (%s)",
                doc["clause_identifier"],
                doc["official_title"][:80],
                driver_category or "unclassified",
                driver_reason,
            )

            matches = tag_regulation(doc["statutory_text"], use_cases)
            if matches:
                logger.info(
                    "New/changed regulation %s (%s) -> candidate blast radius: %s",
                    doc["clause_identifier"],
                    doc["official_title"][:80],
                    ", ".join(f"{m.use_case_name} ({m.score})" for m in matches),
                )
            else:
                logger.info(
                    "New/changed regulation %s (%s) -> no confident use-case match; needs manual tagging",
                    doc["clause_identifier"],
                    doc["official_title"][:80],
                )

        logger.info("Ingestion run complete: %d new/changed, %d unchanged (skipped)", new_count, skipped_count)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
