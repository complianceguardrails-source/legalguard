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

SECTOR_KEYWORDS = {
    # Checked before Consumer Finance so an insurance-underwriting repo (which
    # also matches Consumer Finance's "underwrit") doesn't lose a tie to it --
    # dict iteration order is insertion order, and _score() only overrides
    # its best match on a strictly higher count, so whichever sector is
    # tried first keeps a tie. Insurance's own keyword ("insurance") almost
    # always co-occurs, giving it 2+ hits vs. Consumer Finance's 1.
    "Insurance": {
        "insurance", "insurtech", "insurer", "reinsurance", "claims",
        "actuarial", "parametric insurance", "policyholder", "basis risk",
    },
    "Climate & Sustainable Finance": {
        "climate finance", "green finance", "nature finance", "sustainable finance",
        "transition finance", "retrofit finance", "esg", "biodiversity risk",
        "green bond", "carbon", "climate risk",
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

MODALITY_KEYWORDS = {
    "voice_agentic": {"voice", "speech", "ivr", "gemini live", "vertex ai agent", "audio"},
    "vision": {"vision", "ocr", "image", "satellite", "computer vision", "cv "},
    "rag_document": {"rag", "retrieval", "document", "pdf", "contract analysis", "llm"},
    "multi_agent": {"multi-agent", "agentic", "agent framework", "autonomous agent"},
    # 'structured' is the fallback default, not matched explicitly.
}


def _score(text_lower: str, keyword_map: dict[str, set[str]]) -> tuple[str, int]:
    best_label, best_score = None, 0
    for label, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > best_score:
            best_label, best_score = label, hits
    return best_label, best_score


def classify_use_case(name: str, description: str, topics: list[str]) -> tuple[str, str]:
    """Returns (parent_sector, modality), both with safe fallbacks."""
    text_lower = " ".join([name, description or "", " ".join(topics or [])]).lower()

    sector, sector_score = _score(text_lower, SECTOR_KEYWORDS)
    modality, modality_score = _score(text_lower, MODALITY_KEYWORDS)

    return (
        sector if sector_score > 0 else "Uncategorized",
        modality if modality_score > 0 else "structured",
    )
