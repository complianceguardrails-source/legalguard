"""
The granular risks an AI system in finance can carry, and which of them
each use case carries. Seven families, fifty-nine risks. A use case's
risk_tier says how serious; its risk_factors say what of -- this is the
list the tier is composed of, shown when the tier is tapped in the app.

Assignment is by rule, from the same facts the rest of classification
uses: categories (what it does), model_modality and source (what it is),
modality/interface (how it is deployed) and risk_basis (why it was
tiered). Every rule is written as the claim it makes, so a reviewer can
disagree with one rule without distrusting the rest. A risk that no rule
reaches for a use case is not listed for it: absence means "no rule says
so", never "safe".

The labels and descriptions are the product owner's own wording. The app's
copy, app/lib/riskTaxonomy.js, is generated from this file (see
scripts: `python -c "import risk_taxonomy; risk_taxonomy.write_app_module()"`)
so the two cannot drift; slugs are the stored values.
"""
from __future__ import annotations

from typing import Callable

FAMILIES = {
    "systemic": "Macroprudential & systemic market",
    "model": "Operational, quantitative & model",
    "cyber": "Cybersecurity, data security & fraud",
    "legal": "Legal, regulatory & compliance",
    "vendor": "Vendor & third-party reliance",
    "ethical": "Ethical, social & reputational",
    "environmental": "Environmental & climate sustainability",
}

# (slug, family, label, description)
RISKS: list[tuple[str, str, str, str]] = [
    # --- Macroprudential & systemic market -------------------------------
    ("herding_behavior", "systemic", "Herding behavior", "Multiple financial institutions deploy identical off-the-shelf base models, leading to synchronized market movements."),
    ("model_convergence", "systemic", "Model convergence", "Algorithms train on the same public data pools, causing identical automated reactions during market stress."),
    ("liquidity_dry_ups", "systemic", "Sudden liquidity dry-ups", "Synchronized algorithmic selling completely exhausts market buyers in seconds."),
    ("flash_crashes", "systemic", "Automated flash crashes", "High-speed, identical model responses trigger rapid, cascading asset price collapses."),
    ("procyclicality", "systemic", "Procyclicality", "AI systems optimized on real-time variables accidentally amplify current market trends."),
    ("market_spirals", "systemic", "Algorithmic acceleration of market spirals", "Trading models accelerate a downward market trajectory during panic selling."),
    ("asset_bubbles", "systemic", "Artificial asset bubble generation", "Momentum-driven analytics tools overheat specific asset classes during market booms."),
    ("hidden_interconnectedness", "systemic", "Invisible data-driven interconnectedness", "The widespread use of alternative data creates hidden correlations between unrelated asset classes."),
    ("synthetic_correlation", "systemic", "Synthetic portfolio correlation", "Analytics engines incorrectly treat diverse portfolios as diversified when they actually share underlying data dependencies."),
    ("geopolitical_brittleness", "systemic", "Geopolitical model brittleness", "AI systems fail because they lack a conceptual understanding of black swan world events."),
    ("regime_shift_failure", "systemic", "Macroeconomic regime shift failures", "Models degrade unexpectedly when historical training patterns are broken by structural shifts like sudden inflation."),
    # --- Operational, quantitative & model ---------------------------------
    ("black_box", "model", "The black box problem", "Complex deep learning architectures prevent humans from tracing the exact path to a decision."),
    ("lack_of_explainability", "model", "Lack of explainability", "Risk managers cannot isolate the precise cause-and-effect rationale behind a model's output."),
    ("auditing_barriers", "model", "Auditing barriers", "Internal compliance teams cannot validate opaque credit models for regulatory review."),
    ("hallucinations", "model", "Generative hallucinations", "Large language models confidently manufacture false financial statistics."),
    ("confident_misinformation", "model", "Confident misinformation", "AI assistants invent fictitious historical interest rates or corporate performance metrics."),
    ("data_drift", "model", "Data drift", "A model's predictive accuracy degrades because real-world economic conditions diverge from its training baseline."),
    ("concept_drift", "model", "Concept drift", "The underlying statistical properties of the target variable change over time, rendering static models obsolete."),
    ("feedback_loops", "model", "Self-fulfilling feedback loops", "High-frequency trading bots alter the very market dynamics they observe, corrupting future training data."),
    ("artificial_environment", "model", "Artificial environment optimization", "Algorithms optimize for a distorted market environment that they created themselves."),
    ("skills_atrophy", "model", "Human skills atrophy", "Complete reliance on automated analytics degrades the fundamental qualitative judgment of human analyst teams."),
    ("operational_blind_spots", "model", "Operational blind spots", "Institutions face catastrophic failure if automated software goes offline and staff lack the skills to take over manually."),
    # --- Cybersecurity, data security & fraud -----------------------------
    ("biometric_spoofing", "cyber", "Biometric identity verification spoofing", "Bad actors use high-fidelity AI video cloning to bypass visual KYC checks."),
    ("voice_clone_bypass", "cyber", "Voice clone authorization bypassing", "Fraudsters use AI voice synthesis to defeat telephone banking security protocols."),
    ("synthetic_accounts", "cyber", "Synthetic bank account creation", "Criminals combine deepfakes with stolen credentials to open un-trackable fraudulent accounts."),
    ("data_poisoning", "cyber", "Data poisoning", "Malicious actors deliberately inject malformed data points into public feeds to corrupt financial models."),
    ("adversarial_manipulation", "cyber", "Adversarial manipulation", "Attackers manipulate input data to trick underwriting bots into miscalculating risk."),
    ("proprietary_data_leakage", "cyber", "Proprietary data leakage", "Employees feed corporate balance sheets into external generative tools, exposing trade secrets."),
    ("ip_exposure", "cyber", "Intellectual property exposure", "Sensitive customer financial histories enter shared public model spaces through unencrypted prompts."),
    ("spear_phishing", "cyber", "Hyper-targeted spear-phishing", "AI automates the creation of highly convincing, personalized emails that mimic executive leadership."),
    ("social_engineering", "cyber", "Automated corporate social engineering", "AI bots systematically target vendor communication channels to trigger unauthorized wire transfers."),
    # --- Legal, regulatory & compliance -----------------------------------
    ("high_risk_designation", "legal", "High-risk designation liabilities", "Credit-scoring systems trigger strict compliance burdens under global frameworks like the EU AI Act."),
    ("insurance_underwriting_penalties", "legal", "Insurance underwriting penalties", "Automated insurance platforms face heavy fines if they fail to log conformity data."),
    ("human_oversight_audit_failure", "legal", "Human conformity audit failures", "Firms penalised because they cannot prove active human oversight over autonomous pipelines."),
    ("professional_accountability", "legal", "Professional accountability gaps", "Licensed professionals face personal legal liability when an AI assistant generates erroneous tax returns."),
    ("regulatory_reporting_errors", "legal", "Regulatory reporting errors", "Automated compliance software submits incorrect financial data to oversight bodies, leading to censures."),
    ("copyright_infringement", "legal", "Copyright infringement", "Finetuning localized models on paywalled market research documents triggers intellectual property lawsuits."),
    ("dataset_lawsuits", "legal", "Proprietary dataset lawsuits", "Training models on scraping-restricted financial data pools results in breach-of-contract litigation."),
    # --- Vendor & third-party reliance ------------------------------------
    ("provider_concentration", "vendor", "Service provider concentration", "Financial institutions consolidate their heavy analytics workloads onto a tiny handful of cloud giants."),
    ("single_point_of_failure", "vendor", "Single-point-of-failure fragility", "A single regional server outage at a dominant cloud provider disables critical live financial functions globally."),
    ("supply_chain_breach", "vendor", "Supply chain cyber breaches", "Hackers exploit a vulnerability in a third-party AI vendor to gain lateral access to a bank's core infrastructure."),
    ("open_source_vulnerabilities", "vendor", "Hidden open-source vulnerabilities", "Developers insert undocumented open-source AI libraries into workflows, introducing unmonitored backdoors."),
    # --- Ethical, social & reputational -----------------------------------
    ("lending_bias", "ethical", "Algorithmic lending bias", "Financial AI models quietly reinforce historical, systemic discrimination against marginalized groups."),
    ("automated_redlining", "ethical", "Automated redlining", "Credit scoring models reject loan applications from specific postcodes without an auditable reason."),
    ("predatory_targeting", "ethical", "Predatory micro-targeting", "Behavioral analytics identify financially vulnerable consumers to pitch high-interest payday loans."),
    ("opportunistic_placement", "ethical", "Opportunistic product placement", "Algorithms serve high-fee financial products to users at their moment of maximum economic distress."),
    ("consumer_alienation", "ethical", "Automated consumer alienation", "Robotic financial advisors cause mass customer churn due to a lack of empathy or nuance."),
    ("credit_limit_cuts", "ethical", "Unjustified credit limit cuts", "Abrupt, algorithmically driven reductions in credit lines trigger intense public and reputational backlash."),
    # --- Environmental & climate sustainability ---------------------------
    ("training_carbon", "environmental", "Carbon-intensive computational training", "Training large language models requires millions of kilowatt-hours of fossil-fuel-powered electricity."),
    ("inference_energy", "environmental", "Continuous inference energy demands", "Running 24/7 high-frequency trading simulations expands an institution's carbon footprint continuously."),
    ("scope2_inflation", "environmental", "Scope 2 emissions inflation", "Massive data center power consumption directly prevents firms from meeting corporate Net-Zero targets."),
    ("greenwashing_allegations", "environmental", "Greenwashing allegations", "High energy consumption patterns contradict public corporate sustainability marketing."),
    ("water_scarcity", "environmental", "Evaporative water scarcity", "AI data centers consume millions of gallons of water daily for cooling, straining local reservoirs."),
    ("data_center_downtime", "environmental", "Data center operational downtime", "Drought-prone regions enforce regulatory water restrictions, shutting down active financial pipelines."),
    ("e_waste", "environmental", "Accelerated e-waste cycles", "Specialized AI graphics processing units become obsolete every 2 to 3 years, generating massive hazardous waste."),
    ("circular_economy_failures", "environmental", "Circular economy compliance failures", "Rapid hardware replacement cycles undermine institutional waste management goals."),
    ("green_bleaching", "environmental", "AI-driven green-bleaching", "Flawed ESG analytics tools misinterpret corporate disclosures and misclassify carbon-heavy assets as sustainable."),
    ("transition_portfolio_risk", "environmental", "Climate transition portfolio risk", "Financial models exposed to severe losses when sudden carbon taxes hit misclassified \"green\" assets."),
    ("high_emission_optimization", "environmental", "High-emission algorithmic optimization", "Asset allocation models route capital into fossil fuels because they optimize strictly for short-term yield."),
]

SLUGS = {r[0] for r in RISKS}
assert len(SLUGS) == len(RISKS), "duplicate risk slug"
BY_SLUG = {r[0]: {"family": r[1], "label": r[2], "description": r[3]} for r in RISKS}


# --- Facts about a use case the rules read -----------------------------
def _cats(uc: dict) -> set[str]:
    return set(uc.get("categories") or [])


def _has(*slugs: str) -> Callable[[dict], bool]:
    return lambda uc: bool(_cats(uc) & set(slugs))


def _generative(uc: dict) -> bool:
    # A decoder-only model, an LLM/chatbot category, or a curated system
    # whose deployment modality is only built on generative models.
    return (
        uc.get("model_modality") == "decoder-only"
        or bool(_cats(uc) & {"finance_llm", "banking_support"})
        or uc.get("modality") in ("rag_document", "multi_agent", "voice_agentic")
    )


def _third_party(uc: dict) -> bool:
    return uc.get("source") == "huggingface_mined"


def _voice(uc: dict) -> bool:
    return uc.get("modality") == "voice_agentic" or "voice" in (uc.get("name") or "").lower()


def _structured_ml(uc: dict) -> bool:
    return uc.get("model_modality") in ("tabular-regressor", "encoder-only") or uc.get("modality") == "structured"


def _basis_keys(uc: dict) -> set[str]:
    from risk_tier_classifier import KEYWORD_BASIS
    rb = uc.get("risk_basis") or {}
    keys = {KEYWORD_BASIS.get(p) for p in rb.get("matched") or []}
    # category defaults carry the key by reference text; map back
    refs = {b.get("reference") for b in rb.get("basis") or []}
    if any(r and "Annex III point 1" in r for r in refs): keys.add("annex_iii_1")
    if any(r and "Annex III point 5(b)" in r for r in refs): keys.add("annex_iii_5b")
    if any(r and "Annex III point 5(c)" in r for r in refs): keys.add("annex_iii_5c")
    if any(r and "Annex III point 4" in r for r in refs): keys.add("annex_iii_4")
    return {k for k in keys if k}


def _annex_iii(uc: dict) -> bool:
    return bool(_basis_keys(uc) & {"annex_iii_1", "annex_iii_4", "annex_iii_5b", "annex_iii_5c"}) or bool(_cats(uc) & {"credit_lending", "insurance"})


def _any(*preds):
    return lambda uc: any(p(uc) for p in preds)


def _all(*preds):
    return lambda uc: all(p(uc) for p in preds)


# --- Rules: (risk slugs, applies) ----------------------------------------
_TRADING = _has("trading_markets", "stock_prediction")
_MARKET_FACING = _has("trading_markets", "stock_prediction", "portfolio_wealth", "crypto_defi")
_CONSUMER_DECISION = _has("credit_lending", "insurance")

RULES: list[tuple[list[str], Callable[[dict], bool]]] = [
    # Systemic: anything that trades or predicts prices can move with the herd.
    (["herding_behavior", "model_convergence", "procyclicality", "market_spirals", "asset_bubbles"], _TRADING),
    (["liquidity_dry_ups", "flash_crashes", "feedback_loops", "artificial_environment"], _has("trading_markets")),
    (["hidden_interconnectedness", "synthetic_correlation"], _any(_has("sentiment_news", "portfolio_wealth", "risk_management"), _all(_TRADING, _has("sentiment_news")))),
    (["geopolitical_brittleness", "regime_shift_failure"], _has("trading_markets", "stock_prediction", "economics_macro", "risk_management", "portfolio_wealth", "credit_lending")),
    # Model: opacity for learned models; hallucination for anything that writes.
    (["black_box", "lack_of_explainability"], _any(_structured_ml, _generative, _has("credit_lending", "insurance", "fraud_aml", "trading_markets", "stock_prediction", "risk_management"))),
    (["auditing_barriers"], _any(_CONSUMER_DECISION, _has("fraud_aml"))),
    (["hallucinations", "confident_misinformation"], _generative),
    (["data_drift", "concept_drift"], _any(_structured_ml, _has("credit_lending", "insurance", "fraud_aml", "trading_markets", "stock_prediction", "risk_management", "sentiment_news", "payments"))),
    (["skills_atrophy", "operational_blind_spots"], _has("trading_markets", "credit_lending", "fraud_aml", "banking_support", "payments", "compliance_legal", "risk_management")),
    # Cyber and fraud: by the attack surface the system opens.
    (["biometric_spoofing"], _any(lambda uc: "annex_iii_1" in _basis_keys(uc), lambda uc: "kyc" in ((uc.get("risk_basis") or {}).get("matched") or []))),
    (["voice_clone_bypass"], _any(_voice, _all(_has("banking_support"), _generative))),
    (["synthetic_accounts"], _has("fraud_aml", "payments", "banking_support")),
    (["data_poisoning"], _any(_third_party, _has("sentiment_news", "stock_prediction", "trading_markets"))),
    (["adversarial_manipulation"], _any(_CONSUMER_DECISION, _has("fraud_aml"))),
    (["proprietary_data_leakage", "ip_exposure"], _generative),
    (["spear_phishing", "social_engineering"], _has("payments", "banking_support", "fraud_aml")),
    # Legal: by regime.
    (["high_risk_designation"], _annex_iii),
    (["insurance_underwriting_penalties"], _has("insurance")),
    (["human_oversight_audit_failure"], _any(_annex_iii, _has("trading_markets", "fraud_aml"))),
    (["professional_accountability"], _any(_has("tax_accounting", "compliance_legal"), _all(_generative, _has("portfolio_wealth", "filings_reports")))),
    (["regulatory_reporting_errors"], _has("compliance_legal", "filings_reports", "tax_accounting", "fraud_aml", "esg_climate")),
    (["copyright_infringement", "dataset_lawsuits"], _any(_all(_third_party, _generative), _all(_generative, _has("sentiment_news", "filings_reports", "finance_llm")))),
    # Vendor: models you did not build, run on infrastructure you do not own.
    (["provider_concentration", "single_point_of_failure"], _any(_generative, _third_party)),
    (["supply_chain_breach", "open_source_vulnerabilities"], _third_party),
    # Ethical: consumer-facing decisions and nudges.
    (["lending_bias", "automated_redlining", "credit_limit_cuts"], _has("credit_lending")),
    (["lending_bias"], _has("insurance")),
    (["predatory_targeting", "opportunistic_placement"], _any(_has("payments", "banking_support"), _all(_has("credit_lending"), _has("banking_support", "sentiment_news")))),
    (["consumer_alienation"], _has("banking_support", "portfolio_wealth")),
    # Environmental: compute footprint for large models and always-on trading; classification error for ESG tooling.
    (["training_carbon", "scope2_inflation", "water_scarcity", "data_center_downtime", "e_waste", "circular_economy_failures"], _any(_generative, _third_party)),
    (["inference_energy"], _any(_has("trading_markets"), _generative)),
    (["greenwashing_allegations"], _any(_all(_generative, _has("esg_climate")), _all(_generative, _has("portfolio_wealth", "finance_llm", "banking_support")))),
    (["green_bleaching", "transition_portfolio_risk"], _has("esg_climate")),
    (["transition_portfolio_risk", "high_emission_optimization"], _has("portfolio_wealth", "risk_management")),
    (["high_emission_optimization"], _has("trading_markets")),
]

for slugs, _ in RULES:
    unknown = set(slugs) - SLUGS
    assert not unknown, f"rule names unknown risks: {unknown}"


def assign_risk_factors(uc: dict) -> list[str]:
    """Risk slugs for one use case, in taxonomy order, no duplicates."""
    found: set[str] = set()
    for slugs, applies in RULES:
        if applies(uc):
            found.update(slugs)
    return [r[0] for r in RISKS if r[0] in found]


def write_app_module(path: str = "../app/lib/riskTaxonomy.js") -> None:
    import json
    lines = [
        "// Generated from ingestion/risk_taxonomy.py -- do not edit by hand; regenerate",
        "// with the snippet in that file's docstring so labels and descriptions stay",
        "// identical to what the ingestion stores. Slugs are the stored values.",
        "",
        "export const RISK_FAMILIES = " + json.dumps([{"key": k, "label": v} for k, v in FAMILIES.items()], indent=2) + ";",
        "",
        "export const RISKS = " + json.dumps([{"slug": s, "family": f, "label": l, "description": d} for s, f, l, d in RISKS], indent=2, ensure_ascii=False) + ";",
        "",
        "export const RISK_BY_SLUG = Object.fromEntries(RISKS.map((r) => [r.slug, r]));",
        "",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
