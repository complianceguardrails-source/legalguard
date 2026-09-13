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


CONTENTS_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
MANIFEST_FILES = ["requirements.txt", "pyproject.toml", "package.json"]

# Each entry: a real dependency-name substring that would appear in a real
# manifest file, matched against actual file content -- never guessed from
# the repo's name/description the way a topic-based signal might be.
_INTERFACE_DEPS = [
    ("fastapi", "rest-api"),
    ("flask", "rest-api"),
    ("django", "rest-api"),
    ("express", "rest-api"),
    ("koa", "rest-api"),
    ("grpcio", "rpc-gateway"),
    ("grpc", "rpc-gateway"),
    ("websockets", "websocket-stream"),
    ("socket.io", "websocket-stream"),
    ("python-socketio", "websocket-stream"),
]
_TOOL_DEPS = [
    ("sqlalchemy", "database-tool"),
    ("psycopg2", "database-tool"),
    ("psycopg", "database-tool"),
    ("pymongo", "database-tool"),
    ("redis", "database-tool"),
    ("chromadb", "database-tool"),
    ("pinecone-client", "database-tool"),
    ("qdrant-client", "database-tool"),
    ("faiss", "database-tool"),
    ("ccxt", "execution-tool"),
    ("alpaca-trade-api", "execution-tool"),
    ("ib_insync", "execution-tool"),
]


def _fetch_manifest_text(owner: str, repo: str, path: str) -> str | None:
    """Returns the real, decoded text content of a single file, or None if
    it doesn't exist (404) or isn't a plain file. Raises RateLimited the
    same way fetch_architecture_signal does."""
    import base64

    resp = requests.get(CONTENTS_URL.format(owner=owner, repo=repo, path=path), headers=_headers(), timeout=20)
    if resp.status_code == 404:
        return None
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RateLimited(f"Rate-limited fetching {owner}/{repo}/{path}")
    resp.raise_for_status()
    data = resp.json()
    if data.get("encoding") != "base64" or not data.get("content"):
        return None
    return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")


def derive_system_signals(manifest_text: str) -> tuple[str | None, list[str]]:
    lower_text = manifest_text.lower()
    system_interface_type = None
    for needle, label in _INTERFACE_DEPS:
        if needle in lower_text:
            system_interface_type = label
            break
    tools = []
    for needle, label in _TOOL_DEPS:
        if needle in lower_text and label not in tools:
            tools.append(label)
    return system_interface_type, tools


def fetch_manifest_signals(owner: str, repo: str) -> tuple[str | None, list[str]]:
    """Tries each real manifest file in turn (a repo only has some subset of
    these; 404 on one just means try the next). Returns (None, []) if none
    of them exist or nothing recognized matched -- never a guess. Stops at
    the first manifest file found, matching a repo's actual primary
    language rather than merging signals across an unrelated stray file."""
    for path in MANIFEST_FILES:
        text = _fetch_manifest_text(owner, repo, path)
        if text is not None:
            return derive_system_signals(text)
    return None, []
