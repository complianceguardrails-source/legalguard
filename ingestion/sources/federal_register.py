"""
Federal Register API ingestion source.

Why this instead of scraping CFPB/Fed/OCC HTML directly: the Federal
Register (federalregister.gov) is the US government's own structured,
documented, stable, auth-free JSON API for every rule, proposed rule, and
notice published by federal agencies -- including CFPB, the Federal
Reserve, the OCC, FinCEN, SEC and CFTC. Scraping agency press-release pages
is brittle (markup changes silently); this API is a public contract with a
changelog, so it is the right long-term ingestion source for US financial
regulation.

Docs: https://www.federalregister.gov/developers/documentation/api/v1
No API key required.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Agency slugs relevant to consumer/investment banking AI oversight.
# Full list of valid slugs: https://www.federalregister.gov/api/v1/agencies
#
# SEC and CFTC are deliberately excluded from the default list: verified via
# direct API testing that these agencies' filings are dominated by generic
# "Self-Regulatory Organizations; <Exchange>; Notice of..." procedural
# filings that loosely match broad AI-related terms (e.g. "algorithmic")
# without being substantively about AI regulation -- one test query against
# just these two agencies returned 749 matches, nearly all irrelevant
# exchange rule-change notices. If you need CIB/trading-specific coverage,
# add them back with SEC_CFTC_AGENCIES below and expect to filter harder.
DEFAULT_AGENCIES = [
    "consumer-financial-protection-bureau",
    "federal-reserve-system",
    "comptroller-of-the-currency",
    "federal-deposit-insurance-corporation",
    "financial-crimes-enforcement-network",
]
SEC_CFTC_AGENCIES = ["securities-and-exchange-commission", "commodity-futures-trading-commission"]

# Search terms narrowing results to AI/automated-decisioning relevant
# filings. Each is wrapped in quotes at request time to force exact-phrase
# matching -- verified via direct API testing that unquoted multi-word terms
# are scored as loose relevance across the individual words (not a phrase
# match), which is what let "algorithmic discrimination" match 749 unrelated
# SEC/CFTC filings above. Quoting "artificial intelligence" against the
# agencies above narrowed that same style of query to 62 results, most of
# them genuinely on-topic (e.g. actual CFPB Circulars about algorithmic
# adverse-action scoring).
DEFAULT_TERMS = [
    "artificial intelligence",
    "automated underwriting",
    "algorithmic discrimination",
    "algorithmic bias",
    "automated decision-making",
    "machine learning model risk",
]

# Titles matching this prefix are near-universally generic exchange
# rule-change procedure notices, not substantive AI regulation, regardless
# of which search term matched them -- confirmed via live testing above.
_NOISE_TITLE_PREFIXES = ("Self-Regulatory Organizations;",)


def fetch_documents(
    agencies: Iterable[str] = DEFAULT_AGENCIES,
    terms: Iterable[str] = DEFAULT_TERMS,
    published_after: Optional[str] = None,
    per_page: int = 40,
) -> list[dict]:
    """Queries the Federal Register API and returns normalized regulation dicts.

    published_after: ISO date string (e.g. "2026-01-01"). If omitted, the API
    default ordering (newest first) still bounds result volume via per_page.
    """
    results: list[dict] = []
    for term in terms:
        # Quote to force exact-phrase matching -- see DEFAULT_TERMS comment.
        quoted_term = term if term.startswith('"') else f'"{term}"'
        params = {
            "conditions[term]": quoted_term,
            "conditions[agencies][]": list(agencies),
            "order": "newest",
            "per_page": per_page,
            "fields[]": [
                "document_number",
                "title",
                "abstract",
                "html_url",
                "publication_date",
                "effective_on",
                "agencies",
                "type",
            ],
        }
        if published_after:
            params["conditions[publication_date][gte]"] = published_after

        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        for doc in payload.get("results", []):
            title = doc.get("title", "")
            if title.startswith(_NOISE_TITLE_PREFIXES):
                continue
            agency_names = ", ".join(a.get("name", "") for a in doc.get("agencies", [])) or "Unknown Agency"
            results.append(
                {
                    "jurisdiction": "US",
                    "issuing_body": agency_names,
                    "clause_identifier": doc["document_number"],
                    "official_title": doc.get("title", ""),
                    "source_url": doc.get("html_url", ""),
                    # abstract is the closest structured "statutory text" summary
                    # the API exposes without fetching + parsing the full XML body.
                    "statutory_text": doc.get("abstract") or doc.get("title", ""),
                    "version_label": "v1",
                    "publication_date": doc.get("publication_date"),
                    "effective_date": doc.get("effective_on"),
                    "risk_level": None,  # classified downstream by the tagger
                    "ingestion_source": "federal_register",
                    "matched_term": term,
                    "document_type": doc.get("type"),
                }
            )
    # De-dupe across overlapping search terms by document_number within this batch.
    seen = set()
    deduped = []
    for r in results:
        if r["clause_identifier"] in seen:
            continue
        seen.add(r["clause_identifier"])
        deduped.append(r)
    logger.info("Federal Register: fetched %d unique documents", len(deduped))
    return deduped
