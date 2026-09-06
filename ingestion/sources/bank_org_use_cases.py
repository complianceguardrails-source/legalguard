"""
Top-30-global-bank GitHub org miner.

Rather than guessing which repos are "associated with" a major bank via
loose text search (which pulls in generic "awesome-X" lists, as the
keyword-search miner in github_usecases.py does), this source queries
each bank's *own, verified* GitHub organization directly and filters to
AI/ML-relevant repos within it.

CONFIRMED_BANK_ORGS below was built by live-testing GET /orgs/{slug}
against a list of the world's largest banks by total assets, not by
guessing -- see the org-verification pass in project history. Several
plausible-looking slugs turned out to be squatted/unrelated accounts
(e.g. "deutsche-bank" resolves to an unrelated "Reset App" org; the real
one is "DeutscheBank") or genuine-but-empty orgs (0 public repos, e.g.
"wellsfargo", "bankofamerica") and are deliberately excluded. Many of the
largest banks by assets (ICBC, China Construction Bank, Bank of China,
MUFG, Sumitomo Mitsui, Standard Chartered, etc.) had no discoverable
public GitHub org under the names tried -- that's a real finding, not a
gap in this code, and worth re-checking periodically rather than assumed
permanent.
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"

# (display name, verified org slug, public_repos at verification time)
CONFIRMED_BANK_ORGS = [
    ("JPMorgan Chase", "jpmorganchase"),
    ("HSBC", "hsbc"),
    ("Citi", "citi"),
    ("Santander", "santander"),
    ("Societe Generale", "societe-generale"),
    ("Barclays", "Barclays"),
    ("Deutsche Bank", "DeutscheBank"),
    ("Goldman Sachs", "goldmansachs"),
    ("Morgan Stanley", "morganstanley"),
    ("UBS", "UBS-IB"),
    ("Royal Bank of Canada", "rbc"),
    ("TD Bank (Layer 6 AI)", "layer6ai"),
    ("ING", "ing-bank"),
    ("Groupe BPCE", "bpce"),
]

# Keeps this source scoped to *AI-relevant* repos within each bank's org,
# not every internal tooling/style-guide repo they've open-sourced.
_AI_RELEVANCE_KEYWORDS = {
    "ai", "ml", "machine-learning", "machine learning", "llm", "nlp",
    "deep-learning", "deep learning", "neural", "model", "predict",
    "forecasting", "anomaly", "recommender", "recommendation", "agent",
    "generative", "classifier", "classification", "risk-model", "gpt",
    "embedding", "computer-vision", "vision", "speech", "chatbot",
}


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LegalGuard-BankOrgMiner/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_ai_relevant(name: str, description: str, topics: list[str]) -> bool:
    text = " ".join([name, description or "", " ".join(topics or [])]).lower()
    return any(kw in text for kw in _AI_RELEVANCE_KEYWORDS)


def fetch_org_repos(org_slug: str, per_page: int = 100) -> list[dict]:
    resp = requests.get(
        f"{API_ROOT}/orgs/{org_slug}/repos",
        params={"per_page": per_page, "sort": "updated", "type": "public"},
        headers=_headers(),
        timeout=30,
    )
    if resp.status_code == 404:
        logger.warning("Bank org not found (may have been renamed/removed): %s", org_slug)
        return []
    resp.raise_for_status()
    return resp.json()


def mine_bank_use_cases(orgs: list[tuple[str, str]] = CONFIRMED_BANK_ORGS, min_stars: int = 0) -> list[dict]:
    """Returns candidate use-case dicts, same shape as github_usecases.mine_use_cases(),
    but sourced from verified bank-owned orgs and filtered to AI-relevant repos."""
    candidates: list[dict] = []

    for bank_name, org_slug in orgs:
        try:
            repos = fetch_org_repos(org_slug)
        except requests.RequestException:
            logger.exception("Failed to fetch repos for bank org %s (%s)", bank_name, org_slug)
            continue

        matched = 0
        for repo in repos:
            if repo.get("archived") or repo.get("fork"):
                continue
            if repo.get("stargazers_count", 0) < min_stars:
                continue
            name = repo.get("name", "")
            description = repo.get("description") or ""
            topics = repo.get("topics", [])
            if not _is_ai_relevant(name, description, topics):
                continue

            from usecase_classifier import classify_use_case  # local import avoids a cycle at module load
            from risk_tier_classifier import classify_risk_tier

            sector, modality = classify_use_case(name, description, topics)
            risk_tier = classify_risk_tier(name, description, topics)
            candidates.append(
                {
                    "name": repo.get("full_name", f"{org_slug}/{name}"),
                    "parent_sector": sector,
                    "modality": modality,
                    "risk_tier": risk_tier,
                    "description": f"{description} (published by {bank_name}'s open-source engineering org)".strip(),
                    "github_reference_url": repo.get("html_url"),
                    "matched_query": f"bank_org:{org_slug}",
                    "stars": repo.get("stargazers_count", 0),
                }
            )
            matched += 1

        logger.info("Bank org %s (%s): %d AI-relevant repos out of %d total", bank_name, org_slug, matched, len(repos))
        time.sleep(1.0 if os.environ.get("GITHUB_TOKEN") else 2.5)

    logger.info("Bank org miner: found %d AI-relevant candidate repos across %d banks", len(candidates), len(orgs))
    return candidates
