"""
The FINOS AI Governance Framework: the risks and mitigations a group of
member banks agreed on, published as structured Markdown at
github.com/finos/ai-governance-framework.

Why it is here: our own taxonomy (risk_taxonomy.py) is bottom-up and
granular; this one is industry consensus, and every entry carries
cross-references to the control frameworks an auditor actually asks about
-- EU AI Act articles, ISO 42001, NIST SP 800-53, FFIEC booklets. Holding
both lets a risk in this app point at the framework entry that covers it,
and at the organisational control that addresses it rather than only at a
repository.

Each file is Jekyll front matter plus prose. Front matter carries the
title, a type code, the framework references, and -- on a mitigation --
the `mitigates` list naming the risks it addresses. Nothing here is
paraphrased: the title, references and links are the framework's own, and
the summary is its own opening prose.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
import yaml

logger = logging.getLogger(__name__)

_UA = "legalguard-ingest/1.0 (+https://github.com/complianceguardrails-source/legalguard)"
API = "https://api.github.com/repos/finos/ai-governance-framework/contents/docs/{collection}"
RAW = "https://raw.githubusercontent.com/finos/ai-governance-framework/main/docs/{collection}/{name}"
SITE = "https://air-governance-framework.finos.org/{kind}/{slug}.html"

# The framework's own type codes, spelled out.
RISK_TYPE = {"OP": "Operational", "SEC": "Security", "RC": "Regulatory & compliance"}
MITIGATION_TYPE = {"PREV": "Preventative", "DET": "Detective", "COR": "Corrective"}

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def _headers() -> dict:
    import os

    h = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _list_files(collection: str) -> list[str]:
    resp = requests.get(API.format(collection=collection), headers=_headers(), timeout=30)
    resp.raise_for_status()
    return sorted(e["name"] for e in resp.json() if e["type"] == "file" and e["name"].endswith(".md"))


def _first_paragraph(body: str) -> Optional[str]:
    """The entry's own opening prose, with headings and markdown stripped."""
    for block in re.split(r"\n\s*\n", body):
        text = block.strip()
        if not text or text.startswith(("#", ">", "|", "-", "*", "<")):
            continue
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links -> their text
        text = re.sub(r"(\*\*|__|`)", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 40:
            return text[:700]
    return None


def _references(front: dict) -> dict:
    """Every *_references block, keyed by the framework it points at."""
    out = {}
    for key, value in front.items():
        if not key.endswith("_references") or not value:
            continue
        name = key[: -len("_references")]
        out[name] = [str(v) for v in value if v is not None]
    return out


def _parse(collection: str, name: str, kind: str) -> Optional[dict]:
    resp = requests.get(RAW.format(collection=collection, name=name), headers={"User-Agent": _UA}, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    m = _FRONT_MATTER.match(resp.text)
    if not m:
        logger.warning("%s/%s: no front matter", collection, name)
        return None
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        logger.exception("%s/%s: front matter did not parse", collection, name)
        return None

    slug = name[:-3]  # drop .md
    prefix = "ri" if kind == "risk" else "mi"
    sequence = front.get("sequence")
    if sequence is None:
        logger.warning("%s: no sequence number", slug)
        return None
    type_map = RISK_TYPE if kind == "risk" else MITIGATION_TYPE
    return {
        "external_id": f"{prefix}-{sequence}",
        "kind": kind,
        "sequence": int(sequence),
        "title": front.get("title") or slug,
        "type_code": front.get("type"),
        "type_label": type_map.get(front.get("type")),
        "doc_status": front.get("doc-status"),
        "summary": _first_paragraph(m.group(2)),
        "references": _references(front),
        # Mitigations declare which risks they address, as "ri-7" etc.
        "mitigates": [str(r).strip() for r in (front.get("mitigates") or [])],
        "url": SITE.format(kind="risks" if kind == "risk" else "mitigations", slug=slug),
    }


def mine_finos_framework() -> tuple[list[dict], list[dict]]:
    """(risks, mitigations) as stored rows."""
    risks, mitigations = [], []
    for collection, kind, sink in (("_risks", "risk", risks), ("_mitigations", "mitigation", mitigations)):
        for name in _list_files(collection):
            row = _parse(collection, name, kind)
            if row:
                sink.append(row)
        logger.info("%s: %d entries", collection, len(sink))
    return risks, mitigations
