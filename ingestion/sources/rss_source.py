"""
Generic RSS/Atom ingestion source.

Many non-US regulators (FCA, EBA, national data-protection authorities)
publish press releases and policy-statement feeds as RSS/Atom, even when
they don't offer a structured API like the US Federal Register. This module
is deliberately source-agnostic: you configure a list of (jurisdiction,
issuing_body, feed_url) tuples in config.py, and this ingests whatever
entries appear.

IMPORTANT: feed URLs go stale and regulators restructure sites without
notice. The URLs in config.py are starting points you must verify (open
them in a browser / curl them) before relying on this in production --
this module does not guarantee any specific feed is currently live.
"""
from __future__ import annotations

import logging
from typing import Optional

import feedparser

logger = logging.getLogger(__name__)


def fetch_feed(
    feed_url: str,
    jurisdiction: str,
    issuing_body: str,
    max_entries: int = 20,
) -> list[dict]:
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        logger.warning("Feed unreachable or malformed: %s (%s)", feed_url, parsed.bozo_exception)
        return []

    results: list[dict] = []
    for entry in parsed.entries[:max_entries]:
        clause_id = entry.get("id") or entry.get("link") or entry.get("title")
        published: Optional[str] = None
        if getattr(entry, "published_parsed", None):
            published = f"{entry.published_parsed.tm_year:04d}-{entry.published_parsed.tm_mon:02d}-{entry.published_parsed.tm_mday:02d}"

        results.append(
            {
                "jurisdiction": jurisdiction,
                "issuing_body": issuing_body,
                "clause_identifier": clause_id,
                "official_title": entry.get("title", ""),
                "source_url": entry.get("link", feed_url),
                "statutory_text": entry.get("summary", entry.get("title", "")),
                "version_label": "v1",
                "publication_date": published,
                "effective_date": None,
                "risk_level": None,
                "ingestion_source": "rss",
            }
        )
    logger.info("RSS %s: fetched %d entries", feed_url, len(results))
    return results
