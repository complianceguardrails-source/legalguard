"""
How a headline maps onto the risk taxonomy (risk_taxonomy.py).

A story is kept only if it clears the AI gate (it is about AI, models,
algorithms or automation in the first place) and then matches at least
one risk's phrases in its title or summary. Phrases are matched on the
lower-cased text with hyphens as spaces; short ones on word boundaries.
Every risk has phrases; a risk with none would be silently unreachable,
which _check_coverage() refuses at import.

Deliberately literal: a story about "flash crash" maps to flash_crashes,
a story about "greenwashing" to greenwashing_allegations. It does not try
to infer -- a headline that only implies a risk is left out rather than
guessed in, and matched_terms is stored so a reviewer can see why a story
is where it is.
"""
from __future__ import annotations

import re

from risk_taxonomy import SLUGS

AI_GATE = [
    "ai ", " ai", "artificial intelligence", "machine learning", "deep learning", "algorithm",
    "algorithmic", "automated", "automation", "chatbot", "chat bot", "large language model", "llm",
    "generative", "genai", "gen ai", "openai", "chatgpt", "gemini", "claude", "anthropic", "copilot",
    "neural network", "model risk", "deepfake*", "deep fake", "voice clone", "robo", "agentic", "ai agent",
    "foundation model", "gpu", "data cent*", "nvidia",
]

RISK_PHRASES: dict[str, list[str]] = {
    # --- systemic ---
    "herding_behavior": ["herding", "herd behaviour", "herd behavior", "same model", "same models", "identical models", "crowded trade"],
    "model_convergence": ["model convergence", "same data", "same training data", "converge on", "monoculture"],
    "liquidity_dry_ups": ["liquidity dried*", "liquidity dries*", "liquidity dry*", "liquidity evaporat*", "liquidity crunch", "liquidity vanish*"],
    "flash_crashes": ["flash crash", "flash-crash", "sudden crash", "cascading sell", "cascade of sell"],
    "procyclicality": ["procyclical*", "pro-cyclical*", "amplif*", "amplifies", "amplifying"],
    "market_spirals": ["downward spiral", "selling spiral", "doom loop", "panic selling", "sell-off accelerat*", "selloff accelerat*"],
    "asset_bubbles": ["bubble", "overheat*", "frothy", "froth", "mania"],
    "hidden_interconnectedness": ["interconnected*", "interconnectedness", "hidden correlation", "alternative data", "contagion",
                                  "satellite data", "satellite imagery", "geospatial data", "alt data"],
    "synthetic_correlation": ["correlated", "correlation", "diversification", "diversified"],
    "geopolitical_brittleness": ["black swan", "geopolitical shock", "geopolitical risk", "tariff shock", "war shock"],
    "regime_shift_failure": ["regime shift", "regime change", "structural shift", "inflation shock", "rate shock", "stagflation"],
    # --- model ---
    "black_box": ["black box", "black-box", "opaque*", "opacity"],
    "lack_of_explainability": ["explainab*", "explainable", "interpretab*", "explain its decision", "explain the decision", "cannot explain"],
    "auditing_barriers": ["audit", "auditor", "validate the model", "model validation", "cannot validate"],
    "hallucinations": ["hallucinat*", "made up", "made-up", "fabricat*", "invented figures", "invented numbers", "fake citation*"],
    "confident_misinformation": ["misinformation", "wrong answer*", "inaccurate answer*", "incorrect advice", "false information", "gave wrong"],
    "data_drift": ["data drift", "drift", "degrad*", "stale data", "out of date data", "outdated data"],
    "concept_drift": ["concept drift", "no longer predictive", "stopped working", "broke down", "obsolete model"],
    "feedback_loops": ["feedback loop", "self-fulfilling", "self fulfilling", "reflexiv*"],
    "artificial_environment": ["distorted market", "distort the market", "distorting markets", "market distortion"],
    "skills_atrophy": ["deskilling", "de-skilling", "skills atrophy", "skill atrophy", "lose the skills", "over-reliance", "overreliance", "over reliance"],
    "operational_blind_spots": ["outage", "went down", "system failure", "systems failed", "downtime", "glitch", "it failure", "manual fallback", "manual workaround"],
    # --- cyber ---
    "biometric_spoofing": ["biometric*", "face id", "facial recognition", "liveness", "video cloning", "video deepfake", "face swap",
                            "deepfake*", "deep fake*", "spoof*", "kyc check", "identity verification"],
    "voice_clone_bypass": ["voice clon*", "voice-clon*", "cloned voice", "synthetic voice*", "voice deepfake", "voiceprint", "voice authentication", "voice id", "vishing"],
    # The family is "cybersecurity, data security and fraud": a story about
    # fraud in banking belongs here, whether the AI is committing it or
    # detecting it. "fraud" on its own is enough; it is not a word that
    # turns up in finance coverage by accident.
    "synthetic_accounts": ["synthetic identit*", "fake account*", "fraudulent account*", "mule account*", "account opening fraud",
                           "fraud", "frauds", "fraudster*", "scam*", "account takeover", "identity fraud", "identity theft",
                           "payment fraud", "fraud ring", "money launder*", "anti money laundering", "aml", "financial crime"],
    "data_poisoning": ["data poisoning", "poisoned data", "poisoning attack", "tainted data", "corrupt the training"],
    "adversarial_manipulation": ["adversarial*", "manipulate the model", "gaming the model", "game the algorithm", "trick the model",
                                 "prompt injection", "jailbreak*", "tricked into", "model guardrail*", "bypass*"],
    "proprietary_data_leakage": ["data leak", "leaked", "leak of", "trade secret", "confidential data", "shared confidential", "uploaded confidential", "pasted into"],
    "ip_exposure": ["customer data exposed", "customer data leak", "exposed customer", "privacy breach", "data breach*", "personal data exposed",
                     "data privacy", "privacy risk*", "customer data", "location data", "location tracking", "geolocation"],
    "spear_phishing": ["phishing*", "spear-phishing", "spear phishing", "impersonat*", "ceo fraud", "executive impersonation", "business email compromise", "smishing"],
    # AI used offensively against the firm: the taxonomy has no separate
    # "AI as attacker" risk, and this is the one it fits -- an automated
    # campaign against the firm's people and channels.
    "social_engineering": ["social engineering", "wire transfer fraud", "fraudulent transfer", "invoice fraud", "payment diversion", "vendor fraud",
                           "hacker*", "hacked", "malware", "ransomware", "cyberattack*", "cyber attack*", "cyber risk*", "cybersecurity", "cyber security"],
    # --- legal ---
    "high_risk_designation": ["high-risk", "high risk ai", "annex iii", "ai act", "eu ai act", "conformity assessment", "high-risk designation"],
    "insurance_underwriting_penalties": ["insurer fined", "insurance fine", "insurance regulator", "naic", "underwriting penalt*", "insurance ai"],
    "human_oversight_audit_failure": ["human oversight", "human in the loop", "human-in-the-loop", "human review", "oversight failure", "without human"],
    "professional_accountability": ["liable", "liability", "malpractice", "professional negligence", "accountant", "tax return", "tax advice", "auditor liab*"],
    "regulatory_reporting_errors": ["misreport*", "mis-report*", "reporting error", "reporting failure", "inaccurate filing", "incorrect filing", "regulatory reporting", "fined for reporting"],
    "copyright_infringement": ["copyright*", "infring*", "paywalled", "pirated", "licensing dispute", "sued for training"],
    "dataset_lawsuits": ["scraping*", "scraped*", "terms of service", "breach of contract", "data licensing", "unauthorised data", "unauthorized data", "dataset lawsuit"],
    # --- vendor ---
    "provider_concentration": ["concentration risk", "concentration", "dependence on", "reliance on", "dominant provider", "handful of providers", "cloud giants", "hyperscaler"],
    "single_point_of_failure": ["single point of failure", "outage", "aws outage", "azure outage", "cloud outage", "region outage", "went offline"],
    "supply_chain_breach": ["supply chain attack", "supply-chain attack", "third-party breach", "third party breach", "vendor breach", "vendor hack",
                             "supplier hack", "lateral movement", "vendor risk", "third party risk", "third-party risk", "ict risk*", "supplier risk"],
    "open_source_vulnerabilities": ["open source", "open-source", "vulnerabilit*", "backdoor", "malicious package", "cve-", "zero-day", "zero day"],
    # --- ethical ---
    "lending_bias": ["bias", "biased", "discriminat*", "disparate impact", "fair lending", "unfair", "unlawful discrimination"],
    "automated_redlining": ["redlining", "red-lining", "postcode", "zip code", "neighbourhood", "neighborhood", "geograph*"],
    "predatory_targeting": ["predatory*", "vulnerable customer", "vulnerable consumer", "payday", "high-interest", "high interest", "targeting vulnerable"],
    "opportunistic_placement": ["upsell", "cross-sell", "cross sell", "nudg*", "dark pattern", "pushed products", "mis-sold", "mis-selling", "misselling"],
    "consumer_alienation": ["churn*", "customers left", "customer complaints", "frustrat*", "cannot reach a human", "can't reach a human", "robo-advis*", "customer service bot"],
    "credit_limit_cuts": ["credit limit", "credit line", "limit cut", "limits cut", "reduced limits", "slashed limits"],
    # --- environmental ---
    "training_carbon": ["training emissions", "carbon footprint", "energy to train", "training run", "energy-hungry", "energy hungry", "power hungry", "power-hungry"],
    "inference_energy": ["electricity demand", "power demand", "energy demand", "energy consumption", "electricity consumption", "power consumption"],
    "scope2_inflation": ["scope 2", "net zero", "net-zero", "emissions target", "climate target", "emissions rose", "emissions jump", "emissions surge"],
    "greenwashing_allegations": ["greenwash*", "green-wash", "misleading sustainability", "misleading esg", "sustainability claim*", "green claim*", "esg claim*"],
    "water_scarcity": ["water", "cooling", "drought", "reservoir", "aquifer"],
    "data_center_downtime": ["data centre", "data center", "datacenter", "datacentre"],
    "e_waste": ["e-waste", "ewaste", "electronic waste", "gpu waste", "hardware waste", "obsolete hardware"],
    "circular_economy_failures": ["circular economy", "recycl*", "hardware refresh", "replacement cycle"],
    "green_bleaching": ["green-bleaching", "greenbleaching", "misclassif*", "esg rating", "esg score", "esg data", "sustainability rating",
                        "satellite monitoring", "remote sensing", "deforestation", "carbon credit*", "offset*"],
    "transition_portfolio_risk": ["transition risk", "stranded asset", "carbon tax", "carbon price", "carbon pricing", "climate stress test"],
    "high_emission_optimization": ["fossil fuel", "oil and gas", "coal", "capital into fossil", "high-emission", "high emission"],
}

# Phrases too generic to carry a story on their own: they count only
# alongside another phrase for the same risk, or alongside a family-mate.
WEAK_PHRASES = {
    "data centre", "data center", "datacenter", "datacentre", "robo-advis*", "ai act", "automated", "automation",
    "audit", "auditor", "drift", "degrad*", "bubble", "amplif*", "amplifies", "amplifying", "leaked", "leak of",
    "outage", "bias", "biased", "unfair", "water", "cooling", "coal", "correlated", "correlation", "diversified",
    "diversification", "concentration", "dependence on", "reliance on", "opaque*", "opacity", "glitch", "impersonat*",
    "geograph*", "nudg*", "frustrat*", "churn*", "recycl*", "liable", "liability", "accountant", "vulnerabilit*",
    "open source", "open-source", "contagion", "mania", "froth", "frothy",
}


def _check_coverage() -> None:
    missing = SLUGS - set(RISK_PHRASES)
    extra = set(RISK_PHRASES) - SLUGS
    if missing or extra:
        raise RuntimeError(f"risk_news_keywords out of step with taxonomy: missing={sorted(missing)} extra={sorted(extra)}")


_check_coverage()


def _norm(text: str) -> str:
    return " " + re.sub(r"[\-_/]+", " ", text.lower()) + " "


def _hit(phrase: str, text: str) -> bool:
    # Whole words, always: "ai act" must not match "AI action". A phrase
    # ending in "*" is a stem and matches any continuation of its last
    # word ("hallucinat*" -> hallucination, hallucinated).
    p = phrase.replace("-", " ").strip()
    if p.endswith("*"):
        return re.search(r"\b" + re.escape(p[:-1]) + r"\w*", text) is not None
    return re.search(r"\b" + re.escape(p) + r"\b", text) is not None


def is_about_ai(title: str, summary: str) -> bool:
    text = _norm(f"{title} {summary or ''}")
    return any(_hit(p, text) for p in AI_GATE)


def match_risks(title: str, summary: str) -> dict[str, list[str]]:
    """risk slug -> phrases that matched, for stories that clear the gate.
    A risk carried only by weak phrases is dropped unless it has two of
    them or a strong one."""
    text = _norm(f"{title} {summary or ''}")
    out: dict[str, list[str]] = {}
    for slug, phrases in RISK_PHRASES.items():
        hits = [p for p in phrases if _hit(p, text)]
        strong = [h for h in hits if h not in WEAK_PHRASES]
        if strong or len(hits) >= 2:
            out[slug] = hits
    return out
