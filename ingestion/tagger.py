"""
Impact tagger: maps a newly-ingested regulation to the banking_use_cases it
plausibly affects (the "blast radius").

Zero-budget default: keyword/phrase overlap scoring against each use case's
name + description. This has no external dependency and costs nothing to
run, but is deliberately coarse -- treat matches as candidates for a human
(or the mobile app's split-pane diff view) to confirm, not as an
auto-approved merge.

Optional upgrade: if ANTHROPIC_API_KEY is set in the environment, swap in a
real semantic classification call (left as a documented extension point
below) for materially better precision than keyword overlap.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
    "shall", "must", "is", "are", "be", "this", "that", "as", "by", "at",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


@dataclass
class TaggedMatch:
    use_case_id: str
    use_case_name: str
    score: float


def tag_regulation(regulation_text: str, use_cases: list[dict], top_k: int = 5, min_score: float = 0.06) -> list[TaggedMatch]:
    """Scores every known use case against the regulation text via Jaccard
    overlap of tokenized keywords, returns the top_k above min_score."""
    reg_tokens = _tokenize(regulation_text)
    if not reg_tokens:
        return []

    scored: list[TaggedMatch] = []
    for uc in use_cases:
        uc_text = f"{uc['name']} {uc.get('description') or ''} {uc.get('modality') or ''} {uc.get('parent_sector') or ''}"
        uc_tokens = _tokenize(uc_text)
        if not uc_tokens:
            continue
        overlap = reg_tokens & uc_tokens
        union = reg_tokens | uc_tokens
        score = len(overlap) / len(union) if union else 0.0
        if score >= min_score:
            scored.append(TaggedMatch(use_case_id=str(uc["id"]), use_case_name=uc["name"], score=round(score, 4)))

    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top_k]


# Keyword sets for the origin-driver heuristic below. Order matters: a
# document is scored against every category and the highest-scoring one
# wins, so put words here that are actually distinctive of that driver
# rather than generic finance/AI vocabulary.
_DRIVER_KEYWORDS = {
    "market_scandal": {
        "scandal", "fraud", "deceptive", "harm", "complaint", "complaints",
        "enforcement", "penalty", "violation", "misled", "denied", "discriminat",
        "bias", "unfair", "victim", "loss", "breach", "lawsuit", "settlement",
    },
    "capability_leap": {
        "generative", "agentic", "autonomous", "multimodal", "voice", "deepfake",
        "synthetic", "chatbot", "large language model", "foundation model",
        "real-time", "biometric", "liveness",
    },
    "geopolitical_sovereignty": {
        "sovereignty", "cross-border", "national security", "foreign", "sanctions",
        "export control", "data residency", "localization", "critical infrastructure",
        "adversary", "state actor",
    },
    "standards_harmonization": {
        "iso", "nist", "framework", "standard", "harmoniz", "codif", "guidance",
        "best practice", "voluntary", "risk management framework", "certification",
    },
}


def classify_origin_driver(regulation_text: str) -> tuple[Optional[str], str]:
    """Coarse keyword-overlap heuristic guessing which upstream force (market
    scandal, capability leap, geopolitics, or standards harmonization)
    plausibly produced this regulation. Returns (category_or_None, reason).

    This is intentionally simple and will misclassify plenty of documents --
    it's a starting hypothesis for a human to confirm/correct in the app, not
    a certified causal analysis. Swap for an LLM classification call (same
    upgrade path as tag_regulation_llm below) once you want higher precision.
    """
    text_lower = regulation_text.lower()
    scores: dict[str, int] = {}
    for category, keywords in _DRIVER_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text_lower]
        if hits:
            scores[category] = len(hits)

    if not scores:
        return None, "No driver keywords matched; needs manual classification."

    best_category = max(scores, key=scores.get)
    matched = [kw for kw in _DRIVER_KEYWORDS[best_category] if kw in text_lower]
    reason = f"Matched keyword(s): {', '.join(matched[:5])}"
    return best_category, reason


def tag_regulation_llm(regulation_text: str, use_cases: list[dict]) -> list[TaggedMatch]:
    """Extension point: replace the keyword tagger with a real LLM call for
    higher-precision blast-radius classification. Requires ANTHROPIC_API_KEY.

    Left unimplemented here deliberately -- wire this up to your preferred
    Claude API call (see the `claude-api` skill / Anthropic SDK docs) once
    you're ready to move past keyword matching. Until then, call
    tag_regulation() above.

    ANTI-HALLUCINATION CONSTRAINT for whoever implements this: unlike
    tag_regulation()'s Jaccard scoring, an LLM call can invent a plausible-
    sounding but nonexistent use case, or assert a match with no traceable
    basis in the regulation text. When implementing this:
      (1) constrain the model to select ONLY from the use_case_id values in
          the `use_cases` argument (e.g. structured output against that
          exact allowlist) -- never let it free-generate a new entity/id;
      (2) return a real `tagging_method` provenance value (e.g.
          'llm_assisted') distinct from tag_regulation()'s implicit
          'keyword_heuristic', so an LLM-sourced tag is never silently
          indistinguishable from a deterministic one in
          affected_use_case_ids -- a human reviewing audit_tagging.py's
          output needs to know which matcher produced a given tag.
    """
    raise NotImplementedError(
        "Set ANTHROPIC_API_KEY and implement this against the Messages API "
        "when you're ready to upgrade from keyword-based tagging."
    )
