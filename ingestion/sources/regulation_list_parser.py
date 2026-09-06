"""
Generic curated-list regulation parser.

Several high-quality, hand-maintained GitHub README lists organize real AI
regulations by jurisdiction as a simple markdown outline:

    ## <Jurisdiction heading>
    * [Title](https://...) - description text
    * [Title](https://...) - description text
    ## <Next jurisdiction>
    ...

This covers ethicalml/awesome-artificial-intelligence-regulation (##
headings are countries directly under "# Regulation and Policy") and
ModelOriented/MAIR (### headings are countries/regions nested under a
higher "# White papers" / "# Formal regulations" category split). Both are
parsed by the same walker: track the most recent heading at
`jurisdiction_level` as the jurisdiction, and the most recent heading
*above* that level as an optional category tag folded into the mandate
description.

This is a MUCH higher-precision source than keyword search or RSS: a human
curator already decided each entry is a real, relevant regulation, and
already wrote a real description -- not a generic auto-summary.
"""
from __future__ import annotations

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"

_ITEM_PATTERN = re.compile(r"^\s*[-*]\s*\[([^\]]+)\]\((https?://[^\s)]+)\)\s*-?\s*(.*)$")


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "LegalGuard-RegulationListParser/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_readme_markdown(owner: str, repo: str, path: str = "README.md") -> str:
    resp = requests.get(
        f"{API_ROOT}/repos/{owner}/{repo}/contents/{path}",
        headers={**_headers(), "Accept": "application/vnd.github.raw"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse_regulation_list(
    markdown_text: str,
    jurisdiction_heading_prefix: str = "## ",
    category_heading_prefix: str | None = "# ",
    section_start: str | None = None,
    section_end: str | None = None,
) -> list[dict]:
    """Returns [{jurisdiction, category, title, url, description}, ...]."""
    text = markdown_text
    if section_start:
        idx = text.find(section_start)
        if idx == -1:
            logger.warning("Section start heading not found: %r -- scanning whole document", section_start)
        else:
            text = text[idx:]
            if section_end:
                end_idx = text.find(section_end, len(section_start))
                if end_idx != -1:
                    text = text[:end_idx]

    entries: list[dict] = []
    current_jurisdiction: str | None = None
    current_category: str = ""

    for line in text.splitlines():
        if category_heading_prefix and line.startswith(category_heading_prefix) and not line.startswith(jurisdiction_heading_prefix):
            current_category = line[len(category_heading_prefix):].strip()
            continue
        if line.startswith(jurisdiction_heading_prefix):
            current_jurisdiction = line[len(jurisdiction_heading_prefix):].strip()
            continue
        match = _ITEM_PATTERN.match(line)
        if match and current_jurisdiction:
            title, url, description = match.groups()
            entries.append(
                {
                    "jurisdiction": current_jurisdiction,
                    "category": current_category,
                    "title": title.strip(),
                    "url": url.strip(),
                    "description": description.strip(),
                }
            )

    return entries


def mine_regulation_list(
    owner: str,
    repo: str,
    jurisdiction_heading_prefix: str = "## ",
    category_heading_prefix: str | None = "# ",
    section_start: str | None = None,
    section_end: str | None = None,
) -> list[dict]:
    """Fetches a README and returns candidate regulation dicts in the same
    shape ingestion/main.py's upsert loop already expects (see
    sources/federal_register.py for the reference shape)."""
    markdown_text = fetch_readme_markdown(owner, repo)
    entries = parse_regulation_list(
        markdown_text,
        jurisdiction_heading_prefix=jurisdiction_heading_prefix,
        category_heading_prefix=category_heading_prefix,
        section_start=section_start,
        section_end=section_end,
    )
    logger.info("Regulation list %s/%s: parsed %d entries", owner, repo, len(entries))

    results = []
    for e in entries:
        # clause_identifier must be stable across re-runs for dedup to work --
        # derive it from the URL rather than an incrementing counter.
        clause_id = re.sub(r"[^a-zA-Z0-9]+", "-", e["url"])[-140:].strip("-")
        title = f"[{e['category']}] {e['title']}" if e["category"] else e["title"]
        results.append(
            {
                "jurisdiction": e["jurisdiction"],
                "issuing_body": f"curated-list:{owner}/{repo}",
                "clause_identifier": clause_id,
                "official_title": title,
                "source_url": e["url"],
                "statutory_text": e["description"] or e["title"],
                "version_label": "v1",
                "publication_date": None,
                "effective_date": None,
                "risk_level": None,
                "ingestion_source": "curated_list",
            }
        )
    return results
