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
    # Added on request: fraud detection and green/sustainable finance were
    # already covered above (see "fraud detection banking machine learning"
    # and the sustainable/climate finance axis). Tested and DROPPED after
    # checking real results: decarbonization/decarbonisation, carbon
    # accounting, carbon credit, energy transition, energy systems, energy
    # infrastructure, energy grid, and consumer/customer profiling all
    # returned mostly generic "awesome-X" aggregator lists and unrelated
    # mega-star repos regardless of phrasing (the same "OR"+bare "AI"
    # precedence issue documented above for basis-risk/retrofit-finance,
    # but here even single-phrase-only variants stayed noisy) -- consumer/
    # customer profiling specifically returned zero relevant hits in either
    # phrasing. Consistent with "customer support" being dropped earlier
    # for the same reason: not worth keeping a noisy recurring query.
    #
    # "biodiversity credit" is the one that worked -- best signal of
    # everything tested, extending the existing "nature finance
    # biodiversity risk" query to biodiversity *credits* specifically. Not
    # perfectly precise though: first real run returned 7 non-obviously-
    # noise candidates, of which 2 (a generic org "program" repo, a
    # wildlife-tracking app with no financial content) turned out on
    # inspection to not actually be finance-related despite matching the
    # phrase -- manually removed after checking each repo's real
    # description/topics via the GitHub API, not just checking for
    # "specific system vs. generic list" noise. Future runs of this query
    # should get the same finance-relevance check, not just a noise check.
    '"biodiversity credit" in:name,description,readme',
    # Spatial finance: geospatial evidence behind a financial decision.
    # Scoped to name+description rather than readme -- the readme scope
    # returns the big "awesome" lists, which mention everything and
    # implement nothing.
    "satellite imagery insurance in:name,description",
    '"crop yield" commodity OR trading OR insurance in:name,description',
    '"deforestation" "due diligence" OR "supply chain" in:name,description',
    "property valuation satellite OR aerial imagery in:name,description",
    "flood risk mapping machine learning in:name,description",
    "catastrophe risk model in:name,description",
    "vessel tracking AIS analytics in:name,description",
    '"climate risk" finance in:name,description',
    '"remote sensing" mortgage OR lending in:name,description',
    '"satellite" "real estate" in:name,description',
    '"supply chain" satellite monitoring in:name,description',
    "parametric insurance in:name,description",
    "crop insurance remote sensing in:name,description",
    "physical climate risk in:name,description",
    "carbon credit verification satellite in:name,description",
    # Generative market models: diffusion / GAN / flow models that produce
    # synthetic financial time series or simulate order books. They are
    # AI systems whose output is a market, so they carry the systemic and
    # synthetic-data risks the taxonomy names.
    "diffusion model financial time series in:name,description,readme",
    "synthetic financial time series generation in:name,description,readme",
    "limit order book simulation deep learning in:name,description,readme",
    # Decision-model ("jev") systems applied to trading or credit.
    "jev trading OR jev finance OR jev credit in:name,description,readme",
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


# Repositories that must be in the knowledge base whether or not a search
# surfaces them: the finance-AI platforms, agent skill packs, benchmarks
# and reference collections the product owner named. Fetched by name on
# every run so stars and description stay the platform's; a repository
# that disappears is logged and skipped, never invented.
PINNED_REPOS = [
    "OpenBB-finance/OpenBB",
    "OpenBB-finance/agents-for-openbb",
    "dgunning/edgartools",
    "financial-datasets/mcp-server",
    "juanjuandog/FinSight-AI",
    "RUC-NLPIR/FinSight",
    "quant-sentiment-ai/claude-equity-research",
    "himself65/finance-skills",
    "RKiding/Awesome-finance-skills",
    "anthropics/claude-cookbooks",
    "openai/openai-cookbook",
    "The-FinAI/PIXIU",
    "The-FinAI/FinBen",
    "patronus-ai/financebench",
    "georgezouq/awesome-ai-in-finance",
    "hananedupouy/LLMs-in-Finance",
    # Spatial finance: OS-Climate is the Linux Foundation's climate-risk
    # effort, the same kind of consortium artefact as FINOS, and physrisk
    # is the engine banks actually cite for physical risk.
    "os-climate/physrisk",
    "os-climate/hazard",
    "os-climate/ITR",
    "etherisc-legacy/HurricaneGuard",
    # generative market models and the finance decision-model system
    "EmmanuelleB985/FinDiffusion",
    "LeonardoBerti00/DeepMarket",
    "seantanger/diffusion-financial-timeseries-generation",
    "CallmeQuant/financial_ts_generation_hackathon",
    "eddisonpham/StonkBench",
    "OpenByteInc/QuantDinger",
]


def fetch_repository(full_name: str) -> Optional[dict]:
    resp = requests.get(f"https://api.github.com/repos/{full_name}", headers=_headers(), timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _candidate(repo: dict, matched: str) -> dict:
    name = repo.get("full_name", repo.get("name", "unknown/unknown"))
    description = repo.get("description") or ""
    topics = repo.get("topics", [])
    sector, modality = classify_use_case(name, description, topics)
    risk_tier = classify_risk_tier(name, description, topics)
    return {
        "name": name,
        "parent_sector": sector,
        "modality": modality,
        "risk_tier": risk_tier,
        "description": description[:500],
        "github_reference_url": repo.get("html_url"),
        "matched_query": matched,
        "stars": repo.get("stargazers_count", 0),
    }


def mine_pinned_repos() -> list[dict]:
    out: list[dict] = []
    for full_name in PINNED_REPOS:
        try:
            repo = fetch_repository(full_name)
        except requests.RequestException:
            logger.exception("pinned repo fetch failed: %s", full_name)
            continue
        if not repo:
            logger.warning("pinned repo no longer exists: %s", full_name)
            continue
        out.append(_candidate(repo, "pinned"))
        time.sleep(0.5 if os.environ.get("GITHUB_TOKEN") else 1.5)
    logger.info("GitHub pinned repos: %d of %d resolved", len(out), len(PINNED_REPOS))
    return out


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
