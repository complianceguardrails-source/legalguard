"""
Which of this app's granular risks (risk_taxonomy.py) each FINOS AI
Governance Framework risk covers.

The two catalogues were built for different purposes and neither is a
subset of the other:

  * ours is bottom-up and broad -- 59 risks including macroprudential and
    environmental ones a bank cannot control alone (herding, flash
    crashes, data-centre water use);
  * theirs is 23 risks a bank's own control function owns, every one
    cross-referenced to EU AI Act articles, ISO 42001, NIST SP 800-53 and
    the FFIEC booklets.

So this is a mapping, not an equivalence. A FINOS risk may cover several
of ours; some of ours have no FINOS counterpart, and the seven FINOS
risks about agent infrastructure (tool chains, MCP servers, agent state)
have no counterpart here because our taxonomy predates agentic
deployment patterns -- UNMAPPED_FINOS records those rather than forcing
them onto a risk they do not describe.

Each entry says why, because a reader should be able to disagree with one
mapping without discarding the rest.
"""
from __future__ import annotations

from risk_taxonomy import SLUGS

# FINOS risk id -> (our risk slugs it covers, why)
CROSSWALK: dict[str, tuple[list[str], str]] = {
    "ri-1": (
        ["proprietary_data_leakage", "ip_exposure"],
        "Information sent to a hosted model leaves the firm's boundary: the same exposure as staff pasting balance sheets into an external tool.",
    ),
    "ri-2": (
        ["proprietary_data_leakage", "ip_exposure"],
        "A vector store holds the same confidential material as the prompts that filled it, under weaker access control.",
    ),
    "ri-4": (
        ["hallucinations", "confident_misinformation"],
        "Directly the same risk: a model stating financial facts it invented.",
    ),
    "ri-5": (
        ["data_drift", "concept_drift", "operational_blind_spots"],
        "A foundation model version changing under a deployed system is drift the firm did not cause and cannot see.",
    ),
    "ri-6": (
        ["auditing_barriers", "lack_of_explainability"],
        "Output that differs run to run cannot be reproduced for a reviewer, which is what defeats validation.",
    ),
    "ri-7": (
        ["single_point_of_failure", "provider_concentration", "operational_blind_spots"],
        "Availability of the foundation model is third-party concentration risk in its most literal form.",
    ),
    "ri-8": (
        ["adversarial_manipulation", "supply_chain_breach"],
        "Tampering with the model itself, whether in the supply chain or after deployment.",
    ),
    "ri-9": (["data_poisoning"], "The same risk under the same name."),
    "ri-10": (
        ["adversarial_manipulation", "proprietary_data_leakage"],
        "Prompt injection is the adversarial input path for language models, and the usual route to exfiltration.",
    ),
    "ri-14": (
        ["artificial_environment", "operational_blind_spots"],
        "A system optimising for something other than the intended objective -- misalignment between what was asked and what is rewarded.",
    ),
    "ri-16": (
        ["lending_bias", "automated_redlining", "predatory_targeting"],
        "Bias and discrimination, which in finance lands on lending and pricing decisions.",
    ),
    "ri-17": (
        ["lack_of_explainability", "black_box", "auditing_barriers"],
        "Explainability, its cause (opaque architectures) and its consequence (nothing to show an auditor).",
    ),
    "ri-18": (
        ["model_convergence", "skills_atrophy", "professional_accountability"],
        "A model used beyond what it was validated for: reliance grows past the evidence, and the accountable person is still accountable.",
    ),
    "ri-19": (
        ["data_drift", "concept_drift", "regulatory_reporting_errors"],
        "Data quality and drift, including the reporting errors bad inputs produce downstream.",
    ),
    "ri-20": (
        ["consumer_alienation", "credit_limit_cuts", "greenwashing_allegations"],
        "Reputational damage, which in this catalogue shows up as customer backlash and unsupportable public claims.",
    ),
    "ri-22": (
        ["high_risk_designation", "human_oversight_audit_failure", "insurance_underwriting_penalties", "regulatory_reporting_errors"],
        "Regulatory compliance and oversight: the designation, the oversight evidence, and the penalties for failing either.",
    ),
    "ri-23": (
        ["copyright_infringement", "dataset_lawsuits"],
        "Intellectual property and copyright, on both the training data and the output.",
    ),
    "ri-24": (
        ["adversarial_manipulation", "social_engineering"],
        "An agent induced to act beyond its authority -- the closest this catalogue has to an agent authorisation bypass.",
    ),
    "ri-26": (
        ["supply_chain_breach", "open_source_vulnerabilities"],
        "A compromised MCP server is a third-party component with lateral access, which is what these two risks describe.",
    ),
    "ri-29": (
        ["proprietary_data_leakage", "spear_phishing"],
        "Credential harvesting through an agent: the credentials leak, and what follows is an automated campaign.",
    ),
}

# FINOS risks with no counterpart here, and why. Left unmapped rather than
# attached to something that does not describe them.
UNMAPPED_FINOS = {
    "ri-25": "Tool chain manipulation and injection -- agent tooling has no counterpart in this taxonomy.",
    "ri-27": "Agent state persistence poisoning -- concerns agent memory, which this taxonomy does not model.",
    "ri-28": "Multi-agent trust boundary violations -- multi-agent topology is not a risk category here.",
}

# Ours with no FINOS counterpart: everything the framework does not reach.
# Computed, not listed, so it cannot go stale.
def unmapped_ours() -> list[str]:
    covered = {slug for slugs, _ in CROSSWALK.values() for slug in slugs}
    return sorted(SLUGS - covered)


def _check() -> None:
    unknown = {s for slugs, _ in CROSSWALK.values() for s in slugs} - SLUGS
    if unknown:
        raise RuntimeError(f"crosswalk names risks that do not exist: {sorted(unknown)}")
    overlap = set(CROSSWALK) & set(UNMAPPED_FINOS)
    if overlap:
        raise RuntimeError(f"FINOS risk both mapped and unmapped: {sorted(overlap)}")


_check()
