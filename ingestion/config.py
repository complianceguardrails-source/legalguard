"""
Ingestion source configuration.

RSS_FEEDS: deliberately EMPTY. It previously listed FCA's and EBA's general
news RSS feeds, but live testing showed these are press-release/enforcement
news feeds (personnel bans, email digests, market alerts), not regulation
feeds -- the resulting rows were things like "FCA bans senior manager for
lack of honesty and integrity", not actual rules. Those 30 rows were
purged from the database. rss_source.py is still available as a mechanism
if a genuinely regulation-specific RSS feed is found later (verify it
actually publishes rule text/citations, not news, before adding it here).
For real cross-jurisdiction regulation coverage right now, see
sources/regulation_list_parser.py (curated GitHub lists) and
sources/execxai_atlas.py instead.
"""

RSS_FEEDS: list[tuple[str, str, str]] = []

# Federal Register agency slugs + search terms are configured directly in
# sources/federal_register.py (DEFAULT_AGENCIES / DEFAULT_TERMS) since that
# API's parameters are more structured than a flat feed list.
