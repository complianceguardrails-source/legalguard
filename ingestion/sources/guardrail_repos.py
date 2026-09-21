"""
Open-source guardrails for the risk taxonomy: repositories on GitHub and
models on the Hugging Face Hub that implement a technical control for a
granular risk, resolved from guardrail_repo_queries.py.

Everything stored about a repository comes from the platform's API at
fetch time -- name, description, stars or likes, downloads, language,
licence, last push. The only thing this side supplies is which risks the
repository is a control for, and how that was decided (a curated seed or
a search query), which is stored as evidence next to it.

GitHub: unauthenticated calls are limited to 60/hour and search to 10/min;
set GITHUB_TOKEN (any scope) to lift that to 5,000/hour. The run paces
itself either way.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict

import requests

from guardrail_repo_queries import QUERIES, SEEDS
from risk_taxonomy import BY_SLUG

logger = logging.getLogger(__name__)

_GH = "https://api.github.com"
_HF = "https://huggingface.co/api/models"
_UA = "legalguard-ingest/1.0 (+https://github.com/complianceguardrails-source/legalguard)"
SEARCH_TOP_N = 5
MIN_SEARCH_STARS = 200


def _gh_headers() -> dict:
    h = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _gh_get(path: str, params: dict | None = None) -> dict | None:
    for attempt in range(3):
        resp = requests.get(f"{_GH}{path}", headers=_gh_headers(), params=params, timeout=30)
        if resp.status_code == 404:
            return None
        if resp.status_code in (403, 429):
            reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait = max(5, min(reset - int(time.time()), 900)) if reset else 60
            logger.warning("GitHub rate limit; sleeping %ds", wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    return None


def _gh_repo_row(repo: dict) -> dict:
    return {
        "platform": "github",
        "created_at": repo.get("created_at"),
        "external_id": repo["full_name"],
        "url": repo["html_url"],
        "name": repo["name"],
        "description": (repo.get("description") or "")[:600] or None,
        "stars": repo.get("stargazers_count"),
        "downloads": None,
        "language": repo.get("language"),
        "license": (repo.get("license") or {}).get("spdx_id"),
        "last_pushed_at": repo.get("pushed_at"),
    }


def fetch_github_repo(full_name: str) -> dict | None:
    repo = _gh_get(f"/repos/{full_name}")
    if not repo or repo.get("archived") and repo.get("stargazers_count", 0) < 100:
        return None
    return _gh_repo_row(repo)


def search_github(query: str) -> list[dict]:
    data = _gh_get("/search/repositories", {"q": f"{query} stars:>={MIN_SEARCH_STARS}", "sort": "stars", "order": "desc", "per_page": SEARCH_TOP_N})
    time.sleep(6.5 if not os.environ.get("GITHUB_TOKEN") else 2.1)  # search: 10/min unauthenticated, 30/min with a token
    return [_gh_repo_row(r) for r in (data or {}).get("items", [])]


EMERGING_DAYS = 90
EMERGING_MIN_STARS = 20


def search_github_emerging(query: str) -> list[dict]:
    """The same query restricted to repositories created in the last
    EMERGING_DAYS days -- what the stars-sorted search cannot surface yet.
    A low star floor keeps out empty forks without waiting for adoption."""
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=EMERGING_DAYS)).isoformat()
    data = _gh_get("/search/repositories", {"q": f"{query} created:>={since} stars:>={EMERGING_MIN_STARS}", "sort": "stars", "order": "desc", "per_page": SEARCH_TOP_N})
    time.sleep(6.5 if not os.environ.get("GITHUB_TOKEN") else 2.1)
    rows = []
    for r in (data or {}).get("items", []):
        row = _gh_repo_row(r)
        row["created_at"] = r.get("created_at")
        rows.append(row)
    return rows


def fetch_hf_model(model_id: str) -> dict | None:
    resp = requests.get(f"{_HF}/{model_id}", headers={"User-Agent": _UA}, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    m = resp.json()
    card = m.get("cardData") or {}
    return {
        "platform": "huggingface",
        "created_at": m.get("createdAt"),
        "external_id": m.get("id") or model_id,
        "url": f"https://huggingface.co/{m.get('id') or model_id}",
        "name": (m.get("id") or model_id).split("/")[-1],
        "description": None,  # the Hub has no one-line description field; the card is the page
        "stars": m.get("likes"),
        "downloads": m.get("downloads"),
        "language": m.get("library_name"),
        "license": card.get("license") if isinstance(card.get("license"), str) else None,
        "last_pushed_at": m.get("lastModified"),
    }


def mine_guardrail_repos() -> tuple[list[dict], list[str], list[str]]:
    """(rows, risks with nothing, seeds that did not resolve)."""
    by_key: dict[tuple[str, str], dict] = {}
    evidence: dict[tuple[str, str], list[dict]] = defaultdict(list)
    missing_seeds: list[str] = []
    cache: dict[str, dict | None] = {}

    def resolve(seed: str) -> dict | None:
        if seed in cache:
            return cache[seed]
        if seed.startswith("hf:"):
            row = fetch_hf_model(seed[3:])
        else:
            row = fetch_github_repo(seed)
            time.sleep(1.0)
        cache[seed] = row
        return row

    for risk, seeds in SEEDS.items():
        for seed in seeds:
            row = resolve(seed)
            if not row:
                if seed not in missing_seeds:
                    missing_seeds.append(seed)
                continue
            key = (row["platform"], row["external_id"])
            by_key.setdefault(key, row)
            evidence[key].append({"risk": risk, "how": "curated seed"})

    for risk, queries in QUERIES.items():
        for q in queries:
            for row in search_github(q):
                key = (row["platform"], row["external_id"])
                by_key.setdefault(key, row)
                if not any(e["risk"] == risk for e in evidence[key]):
                    evidence[key].append({"risk": risk, "how": "search", "query": q})
            for row in search_github_emerging(q):
                key = (row["platform"], row["external_id"])
                by_key.setdefault(key, row)
                if not any(e["risk"] == risk for e in evidence[key]):
                    evidence[key].append({"risk": risk, "how": "emerging", "query": q, "created_at": row.get("created_at")})

    rows = []
    for key, row in by_key.items():
        risks = sorted({e["risk"] for e in evidence[key]})
        rows.append({**row, "risk_slugs": risks, "families": sorted({BY_SLUG[r]["family"] for r in risks}), "evidence": evidence[key]})
    covered = {r for row in rows for r in row["risk_slugs"]}
    empty = sorted(set(SEEDS) - covered)
    return rows, empty, missing_seeds
