"""
Heuristic classifier for GitHub-mined repos: guesses parent_sector and
modality from a repo's name/description/topics so it can be inserted into
banking_use_cases without a human filling in every field by hand.

Same honesty caveat as tagger.py's origin-driver classifier: keyword
overlap, not semantic understanding. Expect a meaningful error rate --
this is a starting classification for a human to correct in the app, not
a certified taxonomy assignment. Repos that match nothing are still
inserted (as 'Uncategorized' / 'structured') rather than dropped, so
nothing found by the miner is silently lost.
"""
from __future__ import annotations

import re

_SECTOR_KEYWORDS_RAW = {
    # Checked before Consumer Finance so an insurance-underwriting repo (which
    # also matches Consumer Finance's "underwrit") doesn't lose a tie to it --
    # dict iteration order is insertion order, and _score() only overrides
    # its best match on a strictly higher count, so whichever sector is
    # tried first keeps a tie. Insurance's own keyword ("insurance") almost
    # always co-occurs, giving it 2+ hits vs. Consumer Finance's 1.
    "Insurance": {
        "insurance", "insurtech", "insurer", "reinsurance",
        "insurance claims", "claims processing", "claims automation",
        "claims settlement", "claim validity",
        "actuarial", "parametric insurance", "policyholder", "basis risk",
        # Bare "claims" was here until a validation pass found it colliding
        # with "environmental-claims" (a ClimateBERT model, unrelated to
        # insurance) via a tie against Climate's bare "climate" keyword --
        # replaced with the compound phrases above, which don't collide.
    },
    "Climate & Sustainable Finance": {
        "climate finance", "green finance", "nature finance", "sustainable finance",
        "transition finance", "retrofit finance", "esg", "biodiversity risk",
        "green bond", "carbon", "climate risk",
        # Bare "climate"/"biodiversity" added after finding real HF models
        # (e.g. "climatebert/distilroberta-base-climate-commitment") whose
        # name/tags contain the bare word but never the compound phrases
        # above -- a hyphenated model name doesn't contain the two-word
        # substring "climate risk" even though it's obviously climate-
        # related. Same reasoning applies to "biodiversity" alone.
        "climate", "biodiversity",
    },
    "Consumer Finance": {
        "credit", "loan", "lending", "mortgage", "underwrit", "score", "scoring",
        "buy-to-let", "btl", "green loan", "esg loan", "student loan", "payday",
    },
    "Front Office": {
        "chatbot", "customer service", "customer support", "voice assistant", "ivr",
        "support agent", "complaint", "conversational", "helpdesk",
    },
    "CIB": {
        "trading", "algo trading", "m&a", "due diligence", "prospectus",
        "investment bank", "capital markets", "pitch deck", "proxy",
    },
    "Wealth Management": {
        "portfolio", "wealth", "robo-advisor", "asset allocation", "financial planning",
    },
    "Operations & Risk": {
        "aml", "kyc", "fraud", "sanctions", "compliance", "surveillance",
        "anti-money laundering", "transaction monitoring", "risk model",
        "data classification", "pii detection", "pii", "data governance",
        "anonymiz", "de-identification",
    },
}

_MODALITY_KEYWORDS_RAW = {
    "voice_agentic": {"voice", "speech", "ivr", "gemini live", "vertex ai agent", "audio"},
    "vision": {"vision", "ocr", "image", "satellite", "computer vision", "cv "},
    "rag_document": {"rag", "retrieval", "document", "pdf", "contract analysis", "llm"},
    "multi_agent": {"multi-agent", "agentic", "agent framework", "autonomous agent"},
    # 'structured' is the fallback default, not matched explicitly.
}


def _normalize_keyword_map(keyword_map: dict[str, set[str]]) -> dict[str, set[str]]:
    # Keywords are written with natural hyphens for readability (e.g.
    # "buy-to-let"), but classify_use_case() normalizes text_lower's hyphens
    # to spaces before matching -- so a hyphenated keyword literal would
    # silently never match again. Apply the identical transform here once,
    # so the two sides can never drift out of sync (found via validation
    # review: "multi-agent" had gone dead this way).
    return {label: {kw.replace("-", " ") for kw in kws} for label, kws in keyword_map.items()}


SECTOR_KEYWORDS = _normalize_keyword_map(_SECTOR_KEYWORDS_RAW)
MODALITY_KEYWORDS = _normalize_keyword_map(_MODALITY_KEYWORDS_RAW)


def _keyword_matches(kw: str, text_lower: str) -> bool:
    # Short keywords (<=4 chars, e.g. "aml", "kyc", "esg", "pii") risk
    # matching as a coincidental substring of an unrelated word -- "aml"
    # inside "seamless" is a real false positive found via hand-validation.
    # Longer phrases are vanishingly unlikely to collide this way, so only
    # short keywords pay the cost of a regex word-boundary check.
    if len(kw) <= 4:
        return re.search(r"\b" + re.escape(kw) + r"\b", text_lower) is not None
    return kw in text_lower


def _score(text_lower: str, keyword_map: dict[str, set[str]]) -> tuple[str, int]:
    best_label, best_score = None, 0
    for label, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if _keyword_matches(kw, text_lower))
        if hits > best_score:
            best_label, best_score = label, hits
    return best_label, best_score


def classify_use_case(name: str, description: str, topics: list[str]) -> tuple[str, str]:
    """Returns (parent_sector, modality), both with safe fallbacks."""
    text_lower = " ".join([name, description or "", " ".join(topics or [])]).lower()
    # Real repo/model names commonly use hyphens or underscores where a
    # human-written keyword phrase (e.g. "credit scoring") has a space --
    # "credit-scoring-model" would otherwise never match. Normalizing both
    # separators to spaces lets every existing multi-word keyword phrase
    # match hyphenated/underscored names too, without enumerating every
    # separator variant by hand.
    text_lower = text_lower.replace("-", " ").replace("_", " ")

    sector, sector_score = _score(text_lower, SECTOR_KEYWORDS)
    modality, modality_score = _score(text_lower, MODALITY_KEYWORDS)

    return (
        sector if sector_score > 0 else "Uncategorized",
        modality if modality_score > 0 else "structured",
    )
