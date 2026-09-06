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

# Dict order doubles as severity priority: _score() below keeps the first
# tier it finds a strictly-higher hit count for, so a repo tripping both
# "prohibited" and "high_risk" keywords (e.g. a social-scoring critique
# that also mentions credit) is classified toward the more serious tier.
RISK_KEYWORDS = {
    "prohibited": {
        "social scoring", "social credit", "subliminal", "manipulative technique",
        "emotion recognition", "biometric categorization", "predictive policing",
        "mass surveillance", "real-time biometric identification",
    },
    "high_risk": {
        "credit scoring", "creditworthiness", "credit risk model", "underwriting",
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


def _score(text_lower: str, keyword_map: dict[str, set[str]]) -> tuple[str, int]:
    best_label, best_score = None, 0
    for label, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > best_score:
            best_label, best_score = label, hits
    return best_label, best_score


def classify_risk_tier(name: str, description: str, topics: list[str]) -> str:
    """Returns one of prohibited/high_risk/limited_risk/minimal_risk, or
    'unclassified' (the schema default) when nothing matches."""
    text_lower = " ".join([name, description or "", " ".join(topics or [])]).lower()
    label, score = _score(text_lower, RISK_KEYWORDS)
    return label if score > 0 else "unclassified"
