"""
Derives a real architecture/framework signal for a single GitHub repo --
never a guessed one (see database/migrations/001_add_architecture_signal.sql
and ingestion/enrich_architecture.py, the entrypoint that reads/writes the
DB using these functions).

Calls the real single-repo endpoint (GET /repos/{owner}/{repo}, documented at
https://docs.github.com/en/rest/repos/repos#get-a-repository) and derives a
label two ways, in order:

  1. A recognized agent/AI framework name if any of the repo's own GitHub
     topics (tags the repo's maintainer applied) match a known framework --
     these are literal, maintainer-supplied labels, not inferred.
  2. Otherwise, the repo's primary language as GitHub's own linguist
     detected it (the `language` field) -- also a real, API-reported value.

Returns None when neither is available (no language, no matching topic, repo
gone/renamed) -- the caller leaves architecture_signal NULL rather than
writing a guess.
"""
from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

REPO_URL = "https://api.github.com/repos/{owner}/{repo}"

# Maps a substring that might appear in a repo's GitHub topics to the display
# label shown in the app. Ordered roughly by specificity; first match wins.
# Every key here is something a repo maintainer would plausibly tag their
# own repo with on GitHub -- not a guess about what the repo "probably" uses.
FRAMEWORK_TOPIC_MAP = [
    ("langgraph", "LangGraph"),
    ("langchain", "LangChain"),
    ("llamaindex", "LlamaIndex"),
    ("llama-index", "LlamaIndex"),
    ("autogen", "AutoGen"),
    ("crewai", "CrewAI"),
    ("crew-ai", "CrewAI"),
    ("semantic-kernel", "Semantic Kernel"),
    ("haystack", "Haystack"),
    ("google-adk", "Google ADK"),
    ("agent-development-kit", "Google ADK"),
    ("dspy", "DSPy"),
    ("openai-agents", "OpenAI Agents SDK"),
    ("agents-sdk", "OpenAI Agents SDK"),
    ("vertex-ai", "Vertex AI"),
    ("vertexai", "Vertex AI"),
    ("bedrock", "AWS Bedrock"),
    ("transformers", "Hugging Face Transformers"),
    ("huggingface", "Hugging Face Transformers"),
]


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LegalGuard-ArchitectureEnricher/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _as_str(value) -> str | None:
    """This DB connection returns some TEXT columns as bytes rather than
    str (a psycopg/driver-config quirk unrelated to this script) -- decode
    defensively rather than assuming either representation."""
    if value is None:
        return None
    return value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else value


def parse_owner_repo(github_reference_url, name) -> tuple[str, str] | None:
    github_reference_url = _as_str(github_reference_url)
    name = _as_str(name) or ""
    if github_reference_url:
        parts = github_reference_url.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
    if "/" in name:
        owner, repo = name.split("/", 1)
        return owner, repo
    return None


def derive_architecture_signal(language: str | None, topics: list[str]) -> str | None:
    lower_topics = [t.lower() for t in (topics or [])]
    for needle, label in FRAMEWORK_TOPIC_MAP:
        if any(needle in t for t in lower_topics):
            return label
    return language or None


class RateLimited(Exception):
    pass


def fetch_architecture_signal(owner: str, repo: str) -> str | None:
    """Returns a real architecture_signal for owner/repo, or None if nothing
    usable was found. Raises RateLimited if the run should stop early."""
    resp = requests.get(REPO_URL.format(owner=owner, repo=repo), headers=_headers(), timeout=20)
    if resp.status_code == 404:
        logger.warning("Repo not found (renamed/deleted?): %s/%s", owner, repo)
        return None
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RateLimited(f"Rate-limited fetching {owner}/{repo}")
    resp.raise_for_status()
    data = resp.json()
    return derive_architecture_signal(data.get("language"), data.get("topics", []))
