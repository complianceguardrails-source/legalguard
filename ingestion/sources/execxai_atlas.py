"""
Exec x AI "Global AI Regulation Atlas" ingestion source.

execxai.com/robots.txt allows general crawling of the public page (`Allow:
/`) but explicitly disallows `/api/`. The full 62-row ledger visible in a
browser is populated client-side from that disallowed API, so this source
deliberately does NOT reach for it. What IS fair to use: the page embeds a
schema.org JSON-LD `ItemList` (their own structured-data block, published
specifically for machine consumption) listing their newest ~25 tracked
instruments -- real content, explicitly offered, not scraped past a
Disallow line.

If you want the full 62-item ledger, that requires reaching out to Exec x
AI for API access, the same outreach path recommended for OECD.AI
elsewhere in this project -- not scraping around their robots.txt.
"""
from __future__ import annotations

import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

ATLAS_URL = "https://www.execxai.com/atlas"
_JSONLD_PATTERN = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


def fetch_atlas_html() -> str:
    resp = requests.get(ATLAS_URL, headers={"User-Agent": "LegalGuard-Ingestion/1.0"}, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_atlas_itemlist(html: str) -> list[dict]:
    """Extracts the schema.org ItemList block and splits each entry's
    "Jurisdiction — Title" name into separate fields."""
    entries: list[dict] = []
    for block in _JSONLD_PATTERN.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        graph = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in graph:
            if not isinstance(node, dict) or node.get("@type") != "ItemList":
                continue
            for item in node.get("itemListElement", []):
                name = item.get("name", "")
                url = item.get("url", "")
                if "—" in name:
                    jurisdiction, title = name.split("—", 1)
                elif " - " in name:
                    jurisdiction, title = name.split(" - ", 1)
                else:
                    jurisdiction, title = "Unspecified", name
                entries.append({"jurisdiction": jurisdiction.strip(), "title": title.strip(), "url": url})
    return entries


def mine_atlas_regulations() -> list[dict]:
    html = fetch_atlas_html()
    entries = parse_atlas_itemlist(html)
    logger.info("Exec x AI Atlas: parsed %d entries from published JSON-LD (full ledger requires their disallowed /api/)", len(entries))

    results = []
    for e in entries:
        clause_id = re.sub(r"[^a-zA-Z0-9]+", "-", e["url"])[-140:].strip("-")
        results.append(
            {
                "jurisdiction": e["jurisdiction"],
                "issuing_body": "curated-list:execxai.com/atlas",
                "clause_identifier": clause_id,
                "official_title": e["title"],
                "source_url": e["url"],
                "statutory_text": e["title"],
                "version_label": "v1",
                "publication_date": None,
                "effective_date": None,
                "risk_level": None,
                "ingestion_source": "curated_list",
            }
        )
    return results
