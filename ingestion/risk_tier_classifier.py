"""
Heuristic classifier for GitHub-mined repos: guesses an EU AI Act-style
risk_tier (prohibited / high_risk / limited_risk / minimal_risk) from a
repo's name/description/topics, loosely following the Annex III high-risk
categories most relevant to financial services (creditworthiness, insurance
pricing/claims, AML/KYC, employment screening, biometric ID) plus the
Article 50 transparency-obligation categories (chatbots, generative content)
for limited_risk.

Same honesty caveat as usecase_classifier.py: keyword overlap, not legal
analysis. This is a starting classification for a human (or a real legal
review) to correct, not a certified Annex III determination. Repos that
match nothing stay 'unclassified' -- the schema default -- rather than
being guessed into a tier with no supporting signal.
"""
from __future__ import annotations

import re

# Dict order doubles as severity priority: _score() below keeps the first
# tier it finds a strictly-higher hit count for, so a repo tripping both
# "prohibited" and "high_risk" keywords (e.g. a social-scoring critique
# that also mentions credit) is classified toward the more serious tier.
_RISK_KEYWORDS_RAW = {
    "prohibited": {
        "social scoring", "social credit", "subliminal", "manipulative technique",
        "emotion recognition", "biometric categorization", "predictive policing",
        "mass surveillance", "real-time biometric identification",
    },
    "high_risk": {
        "credit scoring", "creditworthiness", "credit risk", "credit risk model",
        "credit card risk", "underwriting",
        "loan approval", "loan decision", "insurance pricing", "insurance underwriting",
        "claims automation", "biometric identification", "biometric verification",
        "kyc", "aml", "anti-money laundering", "sanctions screening",
        "transaction monitoring", "fraud detection", "hiring", "recruitment",
        "video interview", "employee screening", "credit decision",
    },
    "limited_risk": {
        "chatbot", "conversational agent", "voice assistant", "virtual assistant",
        "customer service bot", "generative", "content generation", "copilot",
        "recommendation engine", "robo-advisor",
    },
    "minimal_risk": {
        "backtest", "backtesting", "market data", "data feed", "sdk", "api wrapper",
        "dashboard", "visualization", "research tool", "terminal", "charting",
    },
}


def _normalize_keyword_map(keyword_map: dict[str, set[str]]) -> dict[str, set[str]]:
    # Same fix as usecase_classifier.py: keywords are written with natural
    # hyphens (e.g. "robo-advisor"), but classify_risk_tier() normalizes
    # text_lower's hyphens to spaces before matching, so a hyphenated
    # keyword literal would silently never match. Found via validation
    # review: "anti-money laundering", "robo-advisor", and "real-time
    # biometric identification" had all gone dead this way.
    return {label: {kw.replace("-", " ") for kw in kws} for label, kws in keyword_map.items()}


RISK_KEYWORDS = _normalize_keyword_map(_RISK_KEYWORDS_RAW)


# Mirrors usecase_classifier._BOUNDARY_KEYWORDS -- longer keywords known
# to collide inside common words ("vision" in "division"). Keep the two
# sets identical.
_BOUNDARY_KEYWORDS = {"vision"}


def _keyword_matches(kw: str, text_lower: str) -> bool:
    # Same short-keyword collision risk as usecase_classifier.py -- "aml"
    # (anti-money-laundering) matched inside "seamless" as a real false
    # positive found via hand-validation (jpmorganchase/dataquery-sdk).
    if len(kw) <= 4 or kw in _BOUNDARY_KEYWORDS:
        return re.search(r"\b" + re.escape(kw) + r"\b", text_lower) is not None
    return kw in text_lower


def _score(text_lower: str, keyword_map: dict[str, set[str]]) -> tuple[str, int]:
    best_label, best_score = None, 0
    for label, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if _keyword_matches(kw, text_lower))
        if hits > best_score:
            best_label, best_score = label, hits
    return best_label, best_score


# Why each keyword lands in its tier -- the legal hook, stated once and
# shown to the user next to the phrase that tripped it. Written to be
# honest about the tier, not to flatter it: several "high_risk" keywords
# are NOT EU AI Act Annex III categories at all. Fraud detection is the
# clearest case -- Annex III point 5(b) expressly excludes "AI systems used
# for the purpose of detecting financial fraud" -- and it is kept in the
# tier because AML/CFT and sanctions obligations attach directly to what
# such a system outputs, which is the exposure this app exists to track.
# Keys are the normalized keywords (hyphens as spaces); every keyword in
# _RISK_KEYWORDS_RAW must have an entry, which _check_basis_coverage()
# enforces at import time.
_BASIS = {
    "annex_iii_1": ("EU AI Act, Annex III point 1", "Remote biometric identification systems are listed high-risk."),
    "annex_iii_4": ("EU AI Act, Annex III point 4", "AI used for recruitment, selection or evaluation of candidates and workers is listed high-risk."),
    "annex_iii_5b": ("EU AI Act, Annex III point 5(b)", "AI intended to evaluate the creditworthiness of natural persons or establish their credit score is listed high-risk."),
    "annex_iii_5c": ("EU AI Act, Annex III point 5(c)", "AI used for risk assessment and pricing of natural persons in life and health insurance is listed high-risk. Other insurance lines are not in Annex III; the phrase alone cannot tell them apart."),
    "aml_cft": ("EU AMLD / AMLR; US Bank Secrecy Act", "Not an Annex III category -- Annex III point 5(b) expressly excludes AI used to detect financial fraud. Treated as high-risk here because AML/CFT, sanctions and suspicious-activity reporting duties attach directly to the system's output."),
    "article_5": ("EU AI Act, Article 5", "A practice the Act prohibits outright (social scoring, manipulative or subliminal techniques, certain biometric categorisation and emotion recognition, untargeted surveillance)."),
    "article_50": ("EU AI Act, Article 50", "Transparency duties: people must be told they are interacting with an AI system, and AI-generated content must be marked as such."),
    "mifid_advice": ("MiFID II, Articles 24-25", "Investment advice and recommendations carry conduct-of-business and suitability duties. Not an Annex III category; no EU AI Act tier of its own."),
    "tooling": (None, "Tooling, data access or research infrastructure. No Annex III category or Article 50 obligation identified from this phrase; the tier reflects the absence of a signal, not a finding."),
}

_KEYWORD_BASIS_RAW = {
    "social scoring": "article_5", "social credit": "article_5", "subliminal": "article_5",
    "manipulative technique": "article_5", "emotion recognition": "article_5",
    "biometric categorization": "article_5", "predictive policing": "article_5",
    "mass surveillance": "article_5", "real-time biometric identification": "article_5",
    "credit scoring": "annex_iii_5b", "creditworthiness": "annex_iii_5b", "credit risk": "annex_iii_5b",
    "credit risk model": "annex_iii_5b", "credit card risk": "annex_iii_5b", "underwriting": "annex_iii_5b",
    "loan approval": "annex_iii_5b", "loan decision": "annex_iii_5b", "credit decision": "annex_iii_5b",
    "insurance pricing": "annex_iii_5c", "insurance underwriting": "annex_iii_5c", "claims automation": "annex_iii_5c",
    "biometric identification": "annex_iii_1", "biometric verification": "annex_iii_1",
    "kyc": "aml_cft", "aml": "aml_cft", "anti-money laundering": "aml_cft", "sanctions screening": "aml_cft",
    "transaction monitoring": "aml_cft", "fraud detection": "aml_cft",
    "hiring": "annex_iii_4", "recruitment": "annex_iii_4", "video interview": "annex_iii_4", "employee screening": "annex_iii_4",
    "chatbot": "article_50", "conversational agent": "article_50", "voice assistant": "article_50",
    "virtual assistant": "article_50", "customer service bot": "article_50", "generative": "article_50",
    "content generation": "article_50", "copilot": "article_50",
    "recommendation engine": "mifid_advice", "robo-advisor": "mifid_advice",
    "backtest": "tooling", "backtesting": "tooling", "market data": "tooling", "data feed": "tooling",
    "sdk": "tooling", "api wrapper": "tooling", "dashboard": "tooling", "visualization": "tooling",
    "research tool": "tooling", "terminal": "tooling", "charting": "tooling",
}
KEYWORD_BASIS = {kw.replace("-", " "): basis for kw, basis in _KEYWORD_BASIS_RAW.items()}


def _check_basis_coverage() -> None:
    missing = {kw for kws in RISK_KEYWORDS.values() for kw in kws if kw not in KEYWORD_BASIS}
    if missing:
        raise RuntimeError(f"risk keywords without a stated basis: {sorted(missing)}")


_check_basis_coverage()


def _normalize_text(name: str, description: str, topics: list[str]) -> str:
    text_lower = " ".join([name, description or "", " ".join(topics or [])]).lower()
    # Same fix as usecase_classifier.py: "credit-scoring-model" wouldn't
    # otherwise match the keyword phrase "credit scoring" at all.
    return text_lower.replace("-", " ").replace("_", " ")


def classify_risk_tier(name: str, description: str, topics: list[str]) -> str:
    """Returns one of prohibited/high_risk/limited_risk/minimal_risk, or
    'unclassified' (the schema default) when nothing matches."""
    label, score = _score(_normalize_text(name, description, topics), RISK_KEYWORDS)
    return label if score > 0 else "unclassified"


def explain_risk_tier(name: str, description: str, topics: list[str]) -> dict | None:
    """The same classification, with its working: which phrases of the
    winning tier were found in the text, and the legal basis for each.
    None when nothing matched (the row stays 'unclassified')."""
    text_lower = _normalize_text(name, description, topics)
    label, score = _score(text_lower, RISK_KEYWORDS)
    if score == 0:
        return None
    matched = sorted(kw for kw in RISK_KEYWORDS[label] if _keyword_matches(kw, text_lower))
    bases = []
    for key in dict.fromkeys(KEYWORD_BASIS[kw] for kw in matched):
        reference, summary = _BASIS[key]
        bases.append({"reference": reference, "summary": summary, "phrases": [kw for kw in matched if KEYWORD_BASIS[kw] == key]})
    return {"tier": label, "matched": matched, "basis": bases}
