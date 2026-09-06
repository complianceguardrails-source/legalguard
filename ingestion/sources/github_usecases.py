"""
GitHub use-case miner: searches GitHub for open-source financial-AI repos
across the full tier taxonomy from the design session (consumer lending,
mortgages, green financing, front-office voice agents, CIB, AML/KYC, etc.)
and returns them as candidate banking_use_cases rows.

Uses the real GitHub REST Search API (api.github.com/search/repositories),
documented at https://docs.github.com/en/rest/search/search#search-repositories.
Unauthenticated requests are capped at 10/min; set GITHUB_TOKEN (a
fine-grained PAT with no special scopes needed for public search) to raise
that to 30/min via the Authorization header.

This is a discovery aid, not a legal/technical audit of the repos it finds --
every result should be treated as an unverified candidate for a human to
confirm before it's trusted as a real production pattern.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Iterable, Optional

import requests

from usecase_classifier import classify_use_case
from risk_tier_classifier import classify_risk_tier

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.github.com/search/repositories"

# One query per taxonomy tier discussed in the design session. Kept broad
# enough to surface real repos, narrow enough to stay finance-specific --
# GitHub's search operators (`in:name,description,readme`) restrict matches
# to where the term actually appears rather than anywhere in the repo.
DEFAULT_QUERIES = [
    "consumer credit scoring AI in:name,description,readme",
    "loan underwriting machine learning in:name,description,readme",
    "mortgage AI OR mortgage LLM in:name,description,readme",
    "buy-to-let OR rental yield model in:name,description,readme",
    "green finance ESG AI in:name,description,readme",
    "banking chatbot OR conversational banking agent in:name,description,readme",
    "voice agent banking OR financial voice assistant in:name,description,readme",
    "AML transaction monitoring machine learning in:name,description,readme",
    "KYC automation AI in:name,description,readme",
    "fraud detection banking machine learning in:name,description,readme",
    "algorithmic trading agent LLM in:name,description,readme",
    "M&A due diligence AI in:name,description,readme",
    "wealth management robo-advisor AI in:name,description,readme",
    "financial complaint classification NLP in:name,description,readme",
    "biometric liveness detection banking in:name,description,readme",
    # Sustainable / climate finance axes
    "sustainable finance risk AI in:name,description,readme",
    "transition finance climate AI in:name,description,readme",
    "nature finance biodiversity risk in:name,description,readme",
    "ESG portfolio optimization AI in:name,description,readme",
    "green bonds verification AI in:name,description,readme",
    "climate finance risk model in:name,description,readme",
    "ESG document chatbot OR ESG NLP in:name,description,readme",
    # Insurtech / adjacent fintech vertical axes
    "insurtech AI underwriting in:name,description,readme",
    "investech robo-advisor AI in:name,description,readme",
    "tradingtech algorithmic execution AI in:name,description,readme",
    "insurance claims AI agent in:name,description,readme",
    "parametric insurance AI in:name,description,readme",
    "insurance regulatory compliance AI in:name,description,readme",
    # Added on request: two verticals this taxonomy didn't cover at all yet.
    # Quoted exact phrases -- an earlier unquoted version of these ("basis
    # risk hedging model AI", "retrofit finance OR building retrofit
    # financing AI", multiple bare words with no phrase grouping) let
    # GitHub's search fall back to loose relevance ranking on common
    # individual words like "AI" and "model", surfacing dozens of unrelated
    # high-star repos (PHP/C# awesome-lists, hacking tools, football
    # analytics) instead of anything about basis risk or retrofit finance
    # specifically. A quoted exact phrase, appended with "AI" only for
    # basis risk (bare "retrofit finance" alone already returns precise,
    # if low-star, real hits -- adding "AI" to it returned nothing useful).
    # "customer support" as its own vertical was tried and dropped: neither
    # a quoted-phrase nor an AI-qualified version returned a single relevant
    # repo across two attempts, just the same generic high-star dev-tool
    # lists regardless of phrasing -- the existing "banking chatbot OR
    # conversational banking agent" query above already covers this ground.
    '"basis risk" AI in:name,description,readme',
    '"retrofit finance" in:name,description,readme',
    # AI-driven data classification (PII/sensitivity tagging, data
    # governance labeling) -- a distinct vertical from AML/KYC/fraud above.
    # Quoted exact phrases -- an unquoted version ("AI data classification
    # OR sensitive data classification machine learning") hit the same
    # loose-matching problem as the earlier customer-support/basis-risk
    # queries, surfacing only generic mega-star "awesome"/tutorial lists.
    '"PII detection" OR "sensitive data classification" in:name,description,readme',
]


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LegalGuard-UseCaseMiner/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_repositories(query: str, per_page: int = 15) -> list[dict]:
    resp = requests.get(
        SEARCH_URL,
        params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
        headers=_headers(),
        timeout=30,
    )
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        logger.warning("GitHub search rate-limited; skipping remaining queries this run: %s", query)
        return []
    resp.raise_for_status()
    return resp.json().get("items", [])


def mine_use_cases(queries: Iterable[str] = DEFAULT_QUERIES, min_stars: int = 3) -> list[dict]:
    """Returns a deduped list of candidate use-case dicts ready for
    db.upsert_mined_use_case(), classified by usecase_classifier."""
    seen_urls: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        try:
            repos = search_repositories(query)
        except requests.RequestException:
            logger.exception("Search failed for query: %s", query)
            continue

        for repo in repos:
            html_url = repo.get("html_url")
            if not html_url or html_url in seen_urls:
                continue
            if repo.get("stargazers_count", 0) < min_stars:
                continue
            seen_urls.add(html_url)

            name = repo.get("full_name", repo.get("name", "unknown/unknown"))
            description = repo.get("description") or ""
            topics = repo.get("topics", [])
            sector, modality = classify_use_case(name, description, topics)
            risk_tier = classify_risk_tier(name, description, topics)

            candidates.append(
                {
                    "name": name,
                    "parent_sector": sector,
                    "modality": modality,
                    "risk_tier": risk_tier,
                    "description": description[:500],
                    "github_reference_url": html_url,
                    "matched_query": query,
                    "stars": repo.get("stargazers_count", 0),
                }
            )

        # Respect the unauthenticated 10/min (or authenticated 30/min) search
        # rate limit rather than burning through it and getting 403'd mid-run.
        time.sleep(2.5 if os.environ.get("GITHUB_TOKEN") else 6.5)

    logger.info("GitHub use-case miner: found %d unique candidate repos", len(candidates))
    return candidates
