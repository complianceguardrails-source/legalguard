"""
Curated "awesome list" README miner.

Raw keyword search (github_usecases.py) surfaces a lot of false positives
-- generic "awesome-X" meta-lists that happen to mention a search term
once in a huge README. This source instead mines the actual link list
*inside* a specific, hand-curated awesome-list README, which is much
higher precision: a human already vetted every entry as relevant to that
list's topic (e.g. paperswithbacktest/awesome-systematic-trading's
"Libraries and packages" section is a curated set of real quant/trading
tools, not a loose text match).

This is a generic capability, not a one-off script: point it at any
GitHub-hosted markdown list and an optional section heading range, and it
extracts every `[name](https://github.com/owner/repo)` link in that range,
fetches each repo's real metadata, and classifies it the same way every
other source does.
"""
from __future__ import annotations

import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https://github\.com/[^/\s)]+/[^/\s)]+)\)")


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LegalGuard-AwesomeListMiner/1.0",
    }
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


def extract_github_links(markdown_text: str, section_start: str | None = None, section_end: str | None = None) -> list[tuple[str, str]]:
    """Returns [(display_name, github_url), ...], deduped by URL.

    If section_start/section_end are given (exact heading line text, e.g.
    "# Libraries and packages"), only links between those two headings are
    returned -- otherwise the whole document is scanned.
    """
    text = markdown_text
    if section_start:
        start_idx = text.find(section_start)
        if start_idx == -1:
            logger.warning("Section start heading not found: %r -- scanning whole document instead", section_start)
        else:
            text = text[start_idx:]
            if section_end:
                end_idx = text.find(section_end, len(section_start))
                if end_idx != -1:
                    text = text[:end_idx]

    seen_urls: set[str] = set()
    results: list[tuple[str, str]] = []
    for name, url in _LINK_PATTERN.findall(text):
        # Normalize away trailing slashes / anchors so the same repo linked
        # twice with slightly different URL formatting only counts once.
        normalized = url.rstrip("/").split("#")[0]
        if normalized in seen_urls:
            continue
        # Skip links that are just to a user/org profile, not a specific repo.
        path_parts = normalized.replace("https://github.com/", "").split("/")
        if len(path_parts) < 2 or not path_parts[1]:
            continue
        seen_urls.add(normalized)
        results.append((name, normalized))
    return results


def mine_awesome_list(
    owner: str,
    repo: str,
    section_start: str | None = None,
    section_end: str | None = None,
    min_stars: int = 0,
) -> list[dict]:
    """Fetches a README, extracts linked repos in the given section, pulls
    real metadata for each, and returns candidate use-case dicts in the
    same shape as the other sources' mine_*() functions."""
    from usecase_classifier import classify_use_case  # local import avoids a cycle at module load
    from risk_tier_classifier import classify_risk_tier

    markdown_text = fetch_readme_markdown(owner, repo)
    links = extract_github_links(markdown_text, section_start, section_end)
    logger.info("Awesome-list %s/%s: found %d linked repos in target section", owner, repo, len(links))

    candidates: list[dict] = []
    for display_name, github_url in links:
        owner_repo = github_url.replace("https://github.com/", "")
        try:
            resp = requests.get(f"{API_ROOT}/repos/{owner_repo}", headers=_headers(), timeout=20)
            if resp.status_code == 404:
                logger.warning("Linked repo no longer exists: %s", github_url)
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            logger.exception("Failed to fetch metadata for %s", github_url)
            continue

        if data.get("archived") or data.get("stargazers_count", 0) < min_stars:
            continue

        full_name = data.get("full_name", owner_repo)
        description = data.get("description") or ""
        topics = data.get("topics", [])
        sector, modality = classify_use_case(display_name, description, topics)
        risk_tier = classify_risk_tier(display_name, description, topics)

        candidates.append(
            {
                "name": full_name,
                "parent_sector": sector,
                "modality": modality,
                "risk_tier": risk_tier,
                "description": f"{description} (curated in {owner}/{repo}'s awesome-list)".strip(),
                "github_reference_url": data.get("html_url", github_url),
                "matched_query": f"awesome_list:{owner}/{repo}",
                "stars": data.get("stargazers_count", 0),
            }
        )
        time.sleep(0.1 if os.environ.get("GITHUB_TOKEN") else 1.0)

    logger.info("Awesome-list %s/%s: %d repos passed metadata + relevance checks", owner, repo, len(candidates))
    return candidates
