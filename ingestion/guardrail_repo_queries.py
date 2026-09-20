"""
Where to look for a technical control for each granular risk
(risk_taxonomy.py). Two kinds of pointer per risk:

  seeds   -- repositories known to implement a control for it: "owner/name"
             on GitHub, or "hf:owner/name" for a Hugging Face model. Every
             seed is fetched live; its stars, description, licence and last
             push come from the platform's API, never from here. A seed that
             no longer exists is reported and skipped.
  queries -- GitHub search queries for discovery, taken by stars.

Some risks have no tooling at all -- herding, model convergence, skills
atrophy are institutional or market-structure problems, not something a
library fixes. They are listed with nothing, so the gap is stated rather
than papered over, and ingest_guardrail_repos.py reports them.
"""
from __future__ import annotations

from risk_taxonomy import SLUGS

# Shared seed groups: the same tool controls several risks.
_DRIFT = ["evidentlyai/evidently", "NannyML/nannyml", "whylabs/whylogs", "SeldonIO/alibi-detect", "deepchecks/deepchecks", "Arize-ai/phoenix"]
_EXPLAIN = ["shap/shap", "marcotcr/lime", "interpretml/interpret", "pytorch/captum", "SeldonIO/alibi", "Trusted-AI/AIX360", "MAIF/shapash", "oegedijk/explainerdashboard"]
_LLM_OUTPUT = ["guardrails-ai/guardrails", "NVIDIA/NeMo-Guardrails", "explodinggradients/ragas", "confident-ai/deepeval", "truera/trulens", "Giskard-AI/giskard", "promptfoo/promptfoo", "uptrain-ai/uptrain"]
_LLM_ATTACK = ["protectai/llm-guard", "protectai/rebuff", "NVIDIA/garak", "Azure/PyRIT", "hf:protectai/deberta-v3-base-prompt-injection-v2", "hf:meta-llama/Llama-Guard-3-8B", "hf:google/shieldgemma-2b"]
_ADVERSARIAL = ["Trusted-AI/adversarial-robustness-toolbox", "cleverhans-lab/cleverhans", "bethgelab/foolbox", "QData/TextAttack"]
_PII = ["microsoft/presidio", "protectai/llm-guard", "hf:protectai/deberta-v3-base-prompt-injection-v2"]
_FAIRNESS = ["fairlearn/fairlearn", "Trusted-AI/AIF360", "dssg/aequitas", "holistic-ai/holisticai", "Giskard-AI/giskard"]
_DATA_QUALITY = ["great-expectations/great_expectations", "unionai-oss/pandera", "deepchecks/deepchecks", "whylabs/whylogs"]
_CARBON = ["mlco2/codecarbon", "lfwa/carbontracker", "Breakend/experiment-impact-tracker", "sb-ai-lab/eco2ai"]
_CLIMATE_NLP = ["hf:climatebert/environmental-claims", "hf:climatebert/distilroberta-base-climate-detector", "hf:climatebert/distilroberta-base-climate-commitment", "hf:climatebert/distilroberta-base-climate-sentiment", "hf:ESGBERT/EnvironmentalBERT-environmental", "hf:nbroad/ESG-BERT"]
_DEEPFAKE_VISION = ["selimsef/dfdc_deepfake_challenge", "ondyari/FaceForensics", "ZhendongWang6/DIRE", "SCLBD/DeepfakeBench", "hf:prithivMLmods/Deep-Fake-Detector-Model"]
_DEEPFAKE_AUDIO = ["clovaai/aasist", "asvspoof-challenge/2021", "TakHemlata/SSL_Anti-spoofing", "hf:MelodyMachine/Deepfake-audio-detection-V2"]
_SUPPLY_CHAIN = ["protectai/modelscan", "sigstore/cosign", "anchore/syft", "anchore/grype", "aquasecurity/trivy", "pypa/pip-audit"]
_RESILIENCE = ["BerriAI/litellm", "Netflix/chaosmonkey", "resilience4j/resilience4j"]
_HUMAN_OVERSIGHT = ["humanlayer/humanlayer", "langchain-ai/langgraph", "guardrails-ai/guardrails"]
_MARKET_SIM = ["abides-sim/abides", "jpmorganchase/abides-jpmc-public"]

SEEDS: dict[str, list[str]] = {
    # systemic
    "herding_behavior": _MARKET_SIM,
    "model_convergence": [],
    "liquidity_dry_ups": _MARKET_SIM,
    "flash_crashes": _MARKET_SIM,
    "procyclicality": _MARKET_SIM,
    "market_spirals": _MARKET_SIM,
    "asset_bubbles": [],
    "hidden_interconnectedness": [],
    "synthetic_correlation": [],
    "geopolitical_brittleness": _DRIFT,
    "regime_shift_failure": _DRIFT,
    # model
    "black_box": _EXPLAIN,
    "lack_of_explainability": _EXPLAIN,
    "auditing_barriers": _EXPLAIN + ["mlflow/mlflow", "IDSIA/sacred"],
    "hallucinations": _LLM_OUTPUT,
    "confident_misinformation": _LLM_OUTPUT,
    "data_drift": _DRIFT,
    "concept_drift": _DRIFT + ["online-ml/river"],
    "feedback_loops": _MARKET_SIM,
    "artificial_environment": _MARKET_SIM,
    "skills_atrophy": [],
    "operational_blind_spots": _RESILIENCE,
    # cyber
    "biometric_spoofing": _DEEPFAKE_VISION,
    "voice_clone_bypass": _DEEPFAKE_AUDIO,
    "synthetic_accounts": _DEEPFAKE_VISION + ["Fraud-Detection-Handbook/fraud-detection-handbook"],
    "data_poisoning": _ADVERSARIAL,
    "adversarial_manipulation": _ADVERSARIAL + _LLM_ATTACK,
    "proprietary_data_leakage": _PII,
    "ip_exposure": _PII,
    "spear_phishing": _LLM_ATTACK,
    "social_engineering": _LLM_ATTACK,
    # legal
    "high_risk_designation": ["mlflow/mlflow", "great-expectations/great_expectations", "fairlearn/fairlearn"],
    "insurance_underwriting_penalties": ["mlflow/mlflow", "fairlearn/fairlearn"],
    "human_oversight_audit_failure": _HUMAN_OVERSIGHT,
    "professional_accountability": _LLM_OUTPUT,
    "regulatory_reporting_errors": _DATA_QUALITY,
    "copyright_infringement": ["Data-Provenance-Initiative/Data-Provenance-Collection", "unitaryai/detoxify"],
    "dataset_lawsuits": ["Data-Provenance-Initiative/Data-Provenance-Collection"],
    # vendor
    "provider_concentration": _RESILIENCE,
    "single_point_of_failure": _RESILIENCE,
    "supply_chain_breach": _SUPPLY_CHAIN,
    "open_source_vulnerabilities": _SUPPLY_CHAIN,
    # ethical
    "lending_bias": _FAIRNESS,
    "automated_redlining": _FAIRNESS,
    "predatory_targeting": _FAIRNESS,
    "opportunistic_placement": [],
    "consumer_alienation": [],
    "credit_limit_cuts": _EXPLAIN,
    # environmental
    "training_carbon": _CARBON,
    "inference_energy": _CARBON,
    "scope2_inflation": _CARBON,
    "greenwashing_allegations": _CLIMATE_NLP,
    "water_scarcity": [],
    "data_center_downtime": [],
    "e_waste": [],
    "circular_economy_failures": [],
    "green_bleaching": _CLIMATE_NLP,
    "transition_portfolio_risk": _CLIMATE_NLP,
    "high_emission_optimization": [],
}

# GitHub search for discovery (top results by stars), only where a query
# is specific enough not to return generic ML tooling.
QUERIES: dict[str, list[str]] = {
    "data_drift": ["drift detection machine learning monitoring"],
    "concept_drift": ["concept drift detection"],
    "hallucinations": ["llm hallucination detection"],
    "lack_of_explainability": ["explainable ai toolkit"],
    "adversarial_manipulation": ["adversarial robustness toolbox machine learning"],
    "data_poisoning": ["data poisoning defense machine learning"],
    "biometric_spoofing": ["deepfake detection"],
    "voice_clone_bypass": ["audio deepfake detection anti-spoofing"],
    "spear_phishing": ["phishing detection machine learning"],
    "lending_bias": ["fairness toolkit machine learning bias"],
    "training_carbon": ["carbon emissions tracking machine learning"],
    "greenwashing_allegations": ["greenwashing detection nlp"],
    "supply_chain_breach": ["ml model supply chain security scanner"],
    "human_oversight_audit_failure": ["human in the loop approval ai agents"],
    "proprietary_data_leakage": ["pii redaction llm prompts"],
    "regulatory_reporting_errors": ["data validation pipeline quality checks"],
}

assert set(SEEDS) == SLUGS, "SEEDS must name every risk exactly once"
assert set(QUERIES) <= SLUGS
