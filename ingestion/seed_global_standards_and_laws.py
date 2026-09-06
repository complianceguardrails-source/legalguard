"""
Expands the regulatory inventory with real content verified against primary
or authoritative secondary sources (same standard as seed_eu_ai_act_articles.py):

  - 4 more EU AI Act articles (8, 27, 53, 72), on top of the 9 already seeded,
    moving toward comprehensive coverage of the Act's distinct
    provider/deployer/GPAI/post-market obligations rather than chasing an
    exact external "40 obligations" count, which is a third-party compliance-
    tracker framing, not something the Act itself labels.
  - Vietnam's first standalone AI Law (passed 2025-12-10, effective
    2026-03-01), verified via Baker McKenzie/IAPP/Lexology coverage.
  - ISO/IEC 42001:2023 (AI management systems) and ISO/IEC 27001:2022
    (information security management) -- not government regulations, but
    real, formally published international standards this project's
    guardrail-generation use case already treats as first-class compliance
    references.
  - 4 real Australian regulations relevant to financial services: the SOCI
    Act 2018, APRA CPS 234, APRA CPS 230, and the Privacy Act 1988's 2024
    automated-decision-making amendments.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_global_standards_and_laws.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_global_standards_and_laws")

EU_SOURCE_URL = "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"
EU_PUBLICATION_DATE = date(2024, 7, 12)

REGULATIONS = [
    # -- 4 more EU AI Act articles --------------------------------------
    {
        "jurisdiction": "EU",
        "issuing_body": "European AI Office",
        "clause_identifier": "AIACT-ART8-ComplianceWithRequirements",
        "official_title": "EU AI Act Article 8 -- Compliance with the Requirements",
        "source_url": EU_SOURCE_URL,
        "statutory_text": (
            "Requires high-risk AI systems to comply with the Chapter III Section 2 "
            "requirements (Articles 9-15) taking into account the system's intended "
            "purpose, its specific context and conditions of use, the information in its "
            "instructions for use, and 'the generally acknowledged state of the art' in AI "
            "technology, alongside the risk management system required by Article 9. Where "
            "a system is also subject to Union harmonisation legislation (Annex I), providers "
            "must integrate testing, reporting and documentation processes across both "
            "frameworks to avoid duplication."
        ),
        "publication_date": EU_PUBLICATION_DATE,
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
        "origin_driver_category": "standards_harmonization",
    },
    {
        "jurisdiction": "EU",
        "issuing_body": "European AI Office",
        "clause_identifier": "AIACT-ART27-FundamentalRightsImpactAssessment",
        "official_title": "EU AI Act Article 27 -- Fundamental Rights Impact Assessment",
        "source_url": EU_SOURCE_URL,
        "statutory_text": (
            "Requires deployers that are public bodies or private entities providing public "
            "services to conduct a fundamental rights impact assessment before first "
            "deploying certain high-risk AI systems, documenting how the system fits their "
            "operational processes, its duration and frequency of use, the categories of "
            "affected individuals, specific harms to those groups, human oversight measures, "
            "and complaint mechanisms. The completed assessment must be submitted to market "
            "surveillance authorities, and may cross-reference an existing GDPR data "
            "protection impact assessment rather than duplicating overlapping sections."
        ),
        "publication_date": EU_PUBLICATION_DATE,
        "effective_date": date(2027, 12, 2),
        "risk_level": "high_risk",
        "origin_driver_category": "standards_harmonization",
    },
    {
        "jurisdiction": "EU",
        "issuing_body": "European AI Office",
        "clause_identifier": "AIACT-ART53-GPAIProviderObligations",
        "official_title": "EU AI Act Article 53 -- Obligations for Providers of General-Purpose AI Models",
        "source_url": EU_SOURCE_URL,
        "statutory_text": (
            "Requires providers of general-purpose AI models to maintain technical "
            "documentation of training/testing/evaluation results, supply downstream "
            "developers with documentation of the model's capabilities and limitations, "
            "establish a policy to respect copyright rights-reservations under Directive "
            "(EU) 2019/790, and publicly release a sufficiently detailed summary of training "
            "content per an AI Office template. The documentation and downstream-disclosure "
            "duties don't apply to freely licensed, publicly available models -- unless the "
            "model is designated as carrying systemic risk."
        ),
        "publication_date": EU_PUBLICATION_DATE,
        "effective_date": date(2025, 8, 2),
        "risk_level": None,
        "origin_driver_category": "standards_harmonization",
    },
    {
        "jurisdiction": "EU",
        "issuing_body": "European AI Office",
        "clause_identifier": "AIACT-ART72-PostMarketMonitoring",
        "official_title": "EU AI Act Article 72 -- Post-Market Monitoring by Providers",
        "source_url": EU_SOURCE_URL,
        "statutory_text": (
            "Requires providers of high-risk AI systems to establish a post-market "
            "monitoring system, proportionate to the technology's risks, that 'actively and "
            "systematically' collects and analyses data on the system's real-world "
            "performance throughout its lifetime to verify ongoing compliance with the "
            "Chapter III Section 2 requirements. The system must follow a documented plan "
            "integrated into the technical documentation; providers already covered by "
            "Annex I harmonisation legislation (including certain financial institution AI "
            "systems) may integrate this into their existing monitoring processes instead of "
            "running a separate one."
        ),
        "publication_date": EU_PUBLICATION_DATE,
        "effective_date": date(2026, 8, 2),
        "risk_level": "high_risk",
        "origin_driver_category": "standards_harmonization",
    },
    # -- Vietnam's first standalone AI Law ------------------------------
    {
        "jurisdiction": "VN",
        "issuing_body": "National Assembly of Vietnam",
        "clause_identifier": "VN-AILAW-2025-RiskTieredFramework",
        "official_title": "Vietnam Law on Artificial Intelligence (2025)",
        "source_url": "https://en.vneconomy.vn/national-assembly-approves-vietnams-first-ai-law.htm",
        "statutory_text": (
            "Vietnam's first standalone AI law (35 articles, passed 429-5 on 2025-12-10), "
            "heavily influenced by the EU AI Act. Uses a three-tier risk framework instead "
            "of an 'unacceptable risk' category: high-risk AI (periodic audits, pre-market "
            "conformity certification), medium-risk AI (reports and independent "
            "assessments), and low-risk AI (incident-based audits), alongside a list of "
            "prohibited acts (deceptive deepfakes, national-security-threatening synthetic "
            "content, obstruction of human oversight). High-risk providers must maintain a "
            "Vietnamese commercial presence or authorised representative and mark generated "
            "audio/video as machine-readable synthetic content; deployers must flag "
            "authenticity-confusion risk. Applies to domestic and foreign entities engaged "
            "in AI activity in Vietnam."
        ),
        "publication_date": date(2025, 12, 10),
        "effective_date": date(2026, 3, 1),
        "risk_level": "high_risk",
        "origin_driver_category": "standards_harmonization",
        "origin_driver_description": (
            "Explicitly modeled on the EU AI Act ('Brussels effect') -- a "
            "standards-harmonization move rather than a reaction to a specific domestic "
            "incident. Finance sector gets an 18-month grace period from the March 2026 "
            "effective date (to ~September 2027), longer than the general 12-month period, "
            "reflecting the sector's compliance complexity."
        ),
    },
    # -- ISO standards (not government law, but formally published --
    # -- international standards this app already treats as compliance --
    # -- references) -----------------------------------------------------
    {
        "jurisdiction": "International",
        "issuing_body": "International Organization for Standardization (ISO/IEC)",
        "clause_identifier": "ISO-42001-2023-AIManagementSystem",
        "official_title": "ISO/IEC 42001:2023 -- Artificial Intelligence Management System (AIMS)",
        "source_url": "https://www.iso.org/standard/42001",
        "statutory_text": (
            "The first international standard for an organizational AI management system, "
            "published December 2023. Clauses 4-10 (following a Plan-Do-Check-Act "
            "structure) require: establishing organizational context and leadership "
            "commitment (4-5); risk-based planning that identifies AI-specific risks, runs "
            "assessments, and sets measurable AI objectives (6); resourcing, competence and "
            "communication (7); operating documented controls across the AI lifecycle (8); "
            "measuring performance against defined indicators (9); and continual "
            "improvement (10). Annex A defines 38 controls across 9 areas (AI policy, "
            "impact assessment, AI lifecycle management, data governance) -- the AI system "
            "impact assessment control has no equivalent in ISO/IEC 27001."
        ),
        "publication_date": date(2023, 12, 18),
        "effective_date": date(2023, 12, 18),
        "risk_level": None,
        "origin_driver_category": "standards_harmonization",
    },
    {
        "jurisdiction": "International",
        "issuing_body": "International Organization for Standardization (ISO/IEC)",
        "clause_identifier": "ISO-27001-2022-InformationSecurityManagement",
        "official_title": "ISO/IEC 27001:2022 -- Information Security Management System (ISMS)",
        "source_url": "https://www.iso.org/standard/27001",
        "statutory_text": (
            "The current edition (2022, superseding 2013) of the leading international "
            "information security management standard. Requires an organization to "
            "establish, implement, maintain and continually improve an ISMS covering risk "
            "assessment and treatment, a Statement of Applicability, and management review, "
            "with Annex A's 93 controls (aligned to ISO/IEC 27002:2022) grouped into four "
            "themes: organizational, people, physical, and technological. Widely used "
            "alongside ISO/IEC 42001 for AI systems specifically, since 42001 assumes an "
            "underlying information-security baseline rather than duplicating it."
        ),
        "publication_date": date(2022, 10, 25),
        "effective_date": date(2022, 10, 25),
        "risk_level": None,
        "origin_driver_category": "standards_harmonization",
    },
    # -- Australia: 4 real regulations relevant to financial services ---
    {
        "jurisdiction": "AU",
        "issuing_body": "Australian Government",
        "clause_identifier": "AU-SOCI-2018-CriticalInfrastructure",
        "official_title": "Security of Critical Infrastructure Act 2018 (Cth)",
        "source_url": "https://www.cisc.gov.au/legislation-regulation-and-compliance/soci-act-2018",
        "statutory_text": (
            "Establishes a national framework to identify, manage and reduce national "
            "security risks to critical infrastructure across 11 sectors, including "
            "financial services and markets. Responsible entities for financial market "
            "infrastructure must register operational/ownership information on the Register "
            "of Critical Infrastructure Assets, adopt and comply with a written critical "
            "infrastructure risk management program, notify third-party data "
            "storage/processing providers when they hold business-critical data for a "
            "critical infrastructure asset, and report cyber incidents affecting essential-"
            "service delivery to the Australian Cyber Security Centre. Systems of National "
            "Significance face additional Enhanced Cyber Security Obligations."
        ),
        "publication_date": date(2018, 4, 11),
        "effective_date": date(2018, 4, 11),
        "risk_level": None,
        "origin_driver_category": "geopolitical_sovereignty",
    },
    {
        "jurisdiction": "AU",
        "issuing_body": "Australian Prudential Regulation Authority (APRA)",
        "clause_identifier": "AU-APRA-CPS234-InformationSecurity",
        "official_title": "APRA Prudential Standard CPS 234 -- Information Security",
        "source_url": "https://www.apra.gov.au/standards/cps-234",
        "statutory_text": (
            "Requires APRA-regulated entities to maintain information security capability "
            "commensurate with the size and extent of threats to their information assets, "
            "clearly define information security-related roles and responsibilities, "
            "maintain an information security capability that responds to and is resilient "
            "against incidents (including cyberattacks), test the effectiveness of controls "
            "through a systematic testing program, and notify APRA of material information "
            "security incidents. Applies to information assets managed directly and by "
            "related parties or third-party service providers."
        ),
        "publication_date": date(2019, 7, 1),
        "effective_date": date(2019, 7, 1),
        "risk_level": None,
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "AU",
        "issuing_body": "Australian Prudential Regulation Authority (APRA)",
        "clause_identifier": "AU-APRA-CPS230-OperationalRisk",
        "official_title": "APRA Prudential Standard CPS 230 -- Operational Risk Management",
        "source_url": "https://www.apra.gov.au/standards/cps-230",
        "statutory_text": (
            "Requires APRA-regulated entities to identify, assess and manage operational "
            "risk with effective internal controls, monitoring, and remediation; maintain "
            "the ability to deliver critical operations within tolerance levels through "
            "severe disruptions via a credible business continuity plan; and manage "
            "service-provider risk through a comprehensive service provider management "
            "policy, formal agreements, and robust monitoring -- explicitly including "
            "monitoring the age and health of information assets in coordination with CPS "
            "234's information security requirements."
        ),
        "publication_date": date(2023, 7, 17),
        "effective_date": date(2025, 7, 1),
        "risk_level": None,
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "AU",
        "issuing_body": "Australian Government (Office of the Australian Information Commissioner)",
        "clause_identifier": "AU-PRIVACYACT-2024-AutomatedDecisionMaking",
        "official_title": "Privacy Act 1988 (Cth) -- Automated Decision-Making Transparency Amendments",
        "source_url": "https://www.oaic.gov.au/privacy/australian-privacy-principles",
        "statutory_text": (
            "The Privacy and Other Legislation Amendment Act 2024 (Cth) inserts a new "
            "Australian Privacy Principle (APP 1.7) requiring APP entities that use "
            "computer systems or AI to make decisions -- wholly or partly without human "
            "intervention -- that could reasonably be expected to significantly affect an "
            "individual's rights or interests, to disclose this in their privacy policy, "
            "including the kinds of personal information used and the kinds of decisions "
            "made. Carries a two-year grace period from Royal Assent before enforcement."
        ),
        "publication_date": date(2024, 12, 10),
        "effective_date": date(2026, 12, 10),
        "risk_level": None,
        "origin_driver_category": "capability_leap",
    },
]


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))

        for reg in REGULATIONS:
            reg_id = db.upsert_regulation(
                conn,
                jurisdiction=reg["jurisdiction"],
                issuing_body=reg["issuing_body"],
                clause_identifier=reg["clause_identifier"],
                official_title=reg["official_title"],
                source_url=reg["source_url"],
                statutory_text=reg["statutory_text"],
                version_label="v1",
                publication_date=reg["publication_date"].isoformat(),
                effective_date=reg["effective_date"].isoformat(),
                risk_level=reg["risk_level"],
                ingestion_source="manual",
                origin_driver_category=reg.get("origin_driver_category"),
                origin_driver_description=reg.get(
                    "origin_driver_description",
                    "Codifies an existing/emerging governance standard rather than reacting to a "
                    "single incident.",
                ),
                title=reg["official_title"],
                impact_level="Brand New Guardrail Required",
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE specific_regulations SET source_url_classification = 'primary' WHERE reg_id = %s",
                    (reg_id,),
                )

            matches = tag_regulation(reg["statutory_text"], use_cases)
            use_case_ids = [m.use_case_id for m in matches]
            db.set_affected_use_cases(conn, reg_id, use_case_ids)

            logger.info(
                "%s -> reg_id=%s, tagged %d use case(s): %s",
                reg["clause_identifier"],
                reg_id,
                len(use_case_ids),
                ", ".join(m.use_case_name for m in matches) or "(none matched)",
            )

        logger.info("Done: %d regulation(s) seeded", len(REGULATIONS))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
