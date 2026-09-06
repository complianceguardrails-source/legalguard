"""
Breaks the EU AI Act (Regulation (EU) 2024/1689) down into individual
article-level specific_regulations rows, instead of the single Article 10
row that existed before this pass. Real statutory content for each article,
verified against https://artificialintelligenceact.eu (a reference tracker
widely cited by EU Commission communications, law firms, and academics for
this exact regulation) -- summarized/paraphrased in this project's own
words with short quoted fragments, not full verbatim reproduction of the
legislative text.

Covers the operative obligations most relevant to a compliance-guardrail
tool: Article 5 (prohibited practices), Article 6 (high-risk
classification), the Chapter III "requirements for high-risk AI systems"
core (9, 13, 14, 15), Article 26 (deployer obligations), Article 50
(transparency for chatbots/deepfakes -- directly relevant to this app's
voice-agent use cases), and Article 99 (penalties). Not all ~113 articles --
procedural/administrative ones (notified bodies, governance structure, etc.)
are out of scope for what a guardrail-generation tool needs to reference.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_eu_ai_act_articles.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_eu_ai_act_articles")

# Same official Commission policy page the existing Article 10 row already
# cites as its primary source (this project doesn't yet have per-article
# eur-lex anchor links) -- see docs/POSTGREST.md's precedent.
COMMISSION_SOURCE_URL = "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"
PUBLICATION_DATE = date(2024, 7, 12)  # Official Journal publication of Regulation (EU) 2024/1689

ARTICLES = [
    {
        "clause_identifier": "AIACT-ART5-ProhibitedPractices",
        "official_title": "EU AI Act Article 5 -- Prohibited AI Practices",
        "statutory_text": (
            "Prohibits placing on the market or using AI systems that: (a) deploy subliminal, "
            "manipulative or deceptive techniques materially distorting behaviour and causing "
            "significant harm; (b) exploit vulnerabilities of age, disability or socioeconomic "
            "situation to the same effect; (c) perform social scoring causing unjustified "
            "detrimental treatment; (d) predict an individual's risk of committing a criminal "
            "offence based solely on profiling; (e) build facial recognition databases through "
            "untargeted scraping of images from the internet or CCTV; (f) infer emotions in the "
            "workplace or education without a medical/safety justification; (g) biometrically "
            "categorise people by race, political views, religion, or sexual orientation; and "
            "(h) use real-time remote biometric identification in public spaces for law "
            "enforcement, subject to narrow, judicially-authorised exceptions."
        ),
        "effective_date": date(2025, 2, 2),
        "risk_level": "prohibited",
    },
    {
        "clause_identifier": "AIACT-ART6-HighRiskClassification",
        "official_title": "EU AI Act Article 6 -- Classification Rules for High-Risk AI Systems",
        "statutory_text": (
            "Establishes two paths to high-risk classification: (1) the system is a safety "
            "component of, or is itself, a product already subject to third-party conformity "
            "assessment under EU harmonisation legislation (Annex I); or (2) the system falls "
            "within one of the use-case categories listed in Annex III (e.g. employment, credit "
            "scoring, essential services access). A carve-out in paragraph 3 excludes an Annex "
            "III system from high-risk status if it performs only a narrow procedural task, "
            "improves the result of a prior human activity, detects decision-making patterns "
            "without replacing human review, or performs preparatory assessment work -- unless "
            "it profiles natural persons, in which case high-risk status always applies."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART9-RiskManagementSystem",
        "official_title": "EU AI Act Article 9 -- Risk Management System",
        "statutory_text": (
            "Requires providers of high-risk AI systems to establish, implement, document and "
            "maintain a risk management system as 'a continuous iterative process planned and "
            "run throughout the entire lifecycle' of the system, covering: identification of "
            "known and reasonably foreseeable risks; estimation of risks under both intended use "
            "and reasonably foreseeable misuse; analysis of post-market monitoring data; and "
            "adoption of targeted mitigation measures. Systems must be tested against "
            "pre-defined metrics and thresholds before market placement, and residual risk must "
            "be judged acceptable."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART13-TransparencyToDeployers",
        "official_title": "EU AI Act Article 13 -- Transparency and Provision of Information to Deployers",
        "statutory_text": (
            "Requires high-risk AI systems to be 'designed and developed in such a way as to "
            "ensure that their operation is sufficiently transparent to enable deployers to "
            "interpret a system's output and use it appropriately.' Providers must supply "
            "instructions covering: the provider's identity, the system's intended purpose, "
            "accuracy/robustness/cybersecurity levels, known risks under foreseeable misuse, "
            "performance across relevant population groups, input data specifications, and any "
            "log-collection mechanisms."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART14-HumanOversight",
        "official_title": "EU AI Act Article 14 -- Human Oversight",
        "statutory_text": (
            "High-risk AI systems must be 'designed and developed in such a way ... that they "
            "can be effectively overseen by natural persons during the period in which they are "
            "in use,' to prevent or minimize risks to health, safety, and fundamental rights. "
            "Overseeing personnel must be able to understand the system's capacities and "
            "limitations, recognize automation bias, correctly interpret outputs, and refuse, "
            "override or reverse a system's decision, including via a 'stop' button or "
            "equivalent procedure. For certain biometric identification systems, no action may "
            "be taken based on the system's output unless separately verified by at least two "
            "competent individuals."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART15-AccuracyRobustnessCybersecurity",
        "official_title": "EU AI Act Article 15 -- Accuracy, Robustness and Cybersecurity",
        "statutory_text": (
            "High-risk AI systems must 'achieve an appropriate level of accuracy, robustness, "
            "and cybersecurity, and perform consistently' across their lifecycle, with accuracy "
            "metrics declared in the instructions for use. Systems must resist errors and "
            "inconsistencies through technical redundancy or fail-safe measures, and for systems "
            "that continue learning after deployment, providers must reduce the risk of biased "
            "outputs feeding back into future operation. Cybersecurity measures must address "
            "AI-specific attack vectors including data poisoning, model poisoning, and "
            "adversarial examples."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART26-DeployerObligations",
        "official_title": "EU AI Act Article 26 -- Obligations of Deployers of High-Risk AI Systems",
        "statutory_text": (
            "Deployers must use high-risk AI systems per the provider's instructions, assign "
            "human oversight to personnel with 'the necessary competence, training and "
            "authority,' ensure input data they control is relevant and sufficiently "
            "representative, monitor operation and report risks or serious incidents to the "
            "provider, retain automatically-generated logs for at least six months, inform "
            "workers before deploying a system at the workplace, and notify individuals when a "
            "system's output affects a decision about them."
        ),
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
    },
    {
        "clause_identifier": "AIACT-ART50-TransparencyDisclosure",
        "official_title": "EU AI Act Article 50 -- Transparency Obligations for Providers and Deployers of Certain AI Systems",
        "statutory_text": (
            "Providers of systems intended to interact directly with individuals (e.g. "
            "chatbots) must ensure people are informed they are interacting with AI, 'unless "
            "this is obvious.' Providers of systems generating synthetic audio, image, video or "
            "text must mark outputs as artificially generated in a machine-readable format. "
            "Deployers of emotion-recognition or biometric-categorisation systems must inform "
            "affected individuals. Deployers of deepfake-generating systems, and of systems "
            "generating AI-authored news-relevant text, must disclose that the content is "
            "artificially generated, unless it has undergone human editorial review."
        ),
        "effective_date": date(2026, 8, 2),
        "risk_level": "limited_risk",
    },
    {
        "clause_identifier": "AIACT-ART99-Penalties",
        "official_title": "EU AI Act Article 99 -- Penalties",
        "statutory_text": (
            "Sets three fine tiers for non-compliance: up to EUR 35 million or 7% of worldwide "
            "annual turnover (whichever is higher) for violating the Article 5 prohibited "
            "practices; up to EUR 15 million or 3% of turnover for violating provider/deployer "
            "obligations elsewhere in the Act; and up to EUR 7.5 million or 1% of turnover for "
            "supplying false information to authorities. Member States must set penalty "
            "frameworks that are 'effective, proportionate and dissuasive,' accounting for SME "
            "and start-up viability."
        ),
        "effective_date": date(2025, 8, 2),
        "risk_level": None,
    },
]


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))

        for article in ARTICLES:
            reg_id = db.upsert_regulation(
                conn,
                jurisdiction="EU",
                issuing_body="European AI Office",
                clause_identifier=article["clause_identifier"],
                official_title=article["official_title"],
                source_url=COMMISSION_SOURCE_URL,
                statutory_text=article["statutory_text"],
                version_label="v1",
                publication_date=PUBLICATION_DATE.isoformat(),
                effective_date=article["effective_date"].isoformat(),
                risk_level=article["risk_level"],
                ingestion_source="manual",
                origin_driver_category="standards_harmonization",
                origin_driver_description=(
                    "Codifies the EU's binding AI governance standard -- not reactive to a "
                    "specific scandal or capability leap, but the harmonized legal framework "
                    "itself entering into force on its own staggered timeline."
                ),
                title=article["official_title"],
                impact_level="Brand New Guardrail Required",
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE specific_regulations SET source_url_classification = 'primary' WHERE reg_id = %s",
                    (reg_id,),
                )

            matches = tag_regulation(article["statutory_text"], use_cases)
            use_case_ids = [m.use_case_id for m in matches]
            db.set_affected_use_cases(conn, reg_id, use_case_ids)

            logger.info(
                "%s -> reg_id=%s, tagged %d use case(s): %s",
                article["clause_identifier"],
                reg_id,
                len(use_case_ids),
                ", ".join(m.use_case_name for m in matches) or "(none matched)",
            )

        logger.info("Done: %d EU AI Act article(s) seeded", len(ARTICLES))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
