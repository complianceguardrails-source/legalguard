"""
Adds a real, individually-verified batch of US state/local AI laws to the
regulatory inventory -- a first installment toward comprehensive US state
coverage (there is no free, unauthenticated, bulk structured source for
this; see the conversation this script came out of for why -- OpenStates
and LegiScan both require an API key, IAPP's tracker is paywalled, and
NCSL's tracker blocks automated fetches). Each entry here was verified
against law-firm/news coverage citing the actual bill text or official
status, same standard as seed_eu_ai_act_articles.py and
seed_global_standards_and_laws.py.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_us_state_ai_laws.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_us_state_ai_laws")

REGULATIONS = [
    {
        "jurisdiction": "US-CO",
        "issuing_body": "Colorado General Assembly",
        "clause_identifier": "CO-SB24-205-ConsumerProtectionsAI",
        "official_title": "Colorado SB 24-205 -- Consumer Protections for Artificial Intelligence",
        "source_url": "https://leg.colorado.gov/bills/sb24-205",
        "statutory_text": (
            "Requires developers and deployers of 'high-risk' AI systems used in "
            "'consequential decisions' (employment, lending, housing, insurance, education, "
            "legal services, essential government services) to use reasonable care to "
            "prevent algorithmic discrimination. Developers must give deployers disclosure "
            "statements and impact-assessment documentation, publish a public statement on "
            "discrimination-risk management, and report known discrimination risks to the "
            "Attorney General within 90 days. Deployers must run risk-management programs, "
            "conduct impact assessments, review deployments annually, notify consumers of "
            "AI-driven consequential decisions, and provide correction/appeal rights. Any "
            "consumer-facing AI must disclose that users are interacting with AI."
        ),
        "publication_date": date(2024, 5, 17),
        "effective_date": date(2026, 6, 30),
        "risk_level": "high_risk",
        "origin_driver_category": "market_scandal",
        "origin_driver_description": (
            "Effective date originally set for 2026-02-01, delayed to 2026-06-30 via "
            "Colorado SB 25B-004 (signed August 2025) -- a real amendment, not this "
            "project's own estimate."
        ),
    },
    {
        "jurisdiction": "US-TX",
        "issuing_body": "Texas Legislature",
        "clause_identifier": "TX-HB149-TRAIGA",
        "official_title": "Texas Responsible Artificial Intelligence Governance Act (TRAIGA, HB 149)",
        "source_url": "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB149",
        "statutory_text": (
            "Texas's comprehensive state AI governance statute, signed by the Governor "
            "2025-06-22 during the 89th Legislature's Second Called Session. Regulates "
            "government use of AI, prohibits specific harmful AI uses (manipulation causing "
            "self-harm/violence, unlawful discrimination, social scoring by government "
            "entities, certain biometric identification without consent), and requires "
            "disclosure when consumers interact with AI systems in specified contexts. "
            "Enforcement runs through the Texas Attorney General rather than a private "
            "right of action."
        ),
        "publication_date": date(2025, 6, 22),
        "effective_date": date(2026, 1, 1),
        "risk_level": "high_risk",
        "origin_driver_category": "standards_harmonization",
    },
    {
        "jurisdiction": "US-IL",
        "issuing_body": "Illinois General Assembly",
        "clause_identifier": "IL-HB3773-AIEmploymentDiscrimination",
        "official_title": "Illinois HB 3773 -- AI Employment Discrimination Amendment to the Human Rights Act",
        "source_url": "https://natlawreview.com/article/illinois-anti-discrimination-law-address-ai-goes-effect-1-january-2026",
        "statutory_text": (
            "Amends the Illinois Human Rights Act to make it a civil rights violation to use "
            "AI in a way that subjects employees to discrimination, or to use zip codes as a "
            "proxy for protected classes, in recruitment, hiring, promotion, discharge, "
            "discipline, or other employment decisions. Employers must notify employees when "
            "AI is used for these purposes; the Illinois Department of Human Rights enforces "
            "the law, with civil penalties up to $5,000 per violation. Notice-timing rules "
            "were still pending IDHR rulemaking as of mid-2026."
        ),
        "publication_date": date(2024, 8, 9),
        "effective_date": date(2026, 1, 1),
        "risk_level": "high_risk",
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "US-IL",
        "issuing_body": "Illinois General Assembly",
        "clause_identifier": "IL-BIPA-Biometric",
        "official_title": "Illinois Biometric Information Privacy Act (BIPA)",
        "source_url": "https://www.aclu-il.org/campaigns-initiatives/biometric-information-privacy-act-bipa/",
        "statutory_text": (
            "Requires written notice and signed consent before collecting biometric "
            "identifiers (fingerprints, facial-geometry scans, etc.), a publicly available "
            "retention/destruction policy, and prohibits selling or profiting from biometric "
            "data. Directly relevant to voice/facial biometric liveness-detection AI use "
            "cases. A financial-institution exemption applies to biometric data collected "
            "under the Gramm-Leach-Bliley Act's privacy provisions -- a real, narrower carve-"
            "out than blanket exemption, not a general finance-sector pass. Amended in 2024 "
            "to cap damages at one violation per person per method, rather than per scan."
        ),
        "publication_date": date(2008, 10, 3),
        "effective_date": date(2008, 10, 3),
        "risk_level": None,
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "US-UT",
        "issuing_body": "Utah State Legislature",
        "clause_identifier": "UT-SB149-AIPolicyAct",
        "official_title": "Utah Artificial Intelligence Policy Act (SB 149)",
        "source_url": "https://en.wikipedia.org/wiki/Utah_Artificial_Intelligence_Policy_Act",
        "statutory_text": (
            "One of the first US state AI-specific consumer-protection statutes. Requires "
            "disclosure when a person is interacting with generative AI in a regulated "
            "occupation (verbally at conversation start, or via message before written "
            "exchange), and on request outside regulated occupations. Holds companies "
            "responsible for violations of statutes the Division of Consumer Protection "
            "administers even where the violation was carried out by generative AI. "
            "Established the Office of Artificial Intelligence Policy, an AI Learning "
            "Laboratory Program, and a process for temporary regulatory mitigation for "
            "businesses developing AI systems. Amended 2025-05-07 with stricter requirements "
            "for higher-risk interactions."
        ),
        "publication_date": date(2024, 3, 13),
        "effective_date": date(2024, 5, 1),
        "risk_level": None,
        "origin_driver_category": "capability_leap",
    },
    {
        "jurisdiction": "US-NY",
        "issuing_body": "New York City Department of Consumer and Worker Protection",
        "clause_identifier": "NYC-LL144-AutomatedEmploymentDecisionTools",
        "official_title": "NYC Local Law 144 -- Automated Employment Decision Tools",
        "source_url": "https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page",
        "statutory_text": (
            "Requires employers/employment agencies using an Automated Employment Decision "
            "Tool (AEDT -- any ML/statistical/AI process producing a score, classification, "
            "or recommendation substantially assisting or replacing employment decisions) to "
            "evaluate NYC-resident candidates to: commission an independent annual bias "
            "audit, publicly post a summary of results, and give candidates at least 10 "
            "business days' notice before use. Enforced by NYC DCWP with civil penalties of "
            "$500-1,500 per violation per day; a December 2025 NY State Comptroller audit "
            "found weak oversight and prompted a wave of 2026 enforcement actions."
        ),
        "publication_date": date(2021, 12, 11),
        "effective_date": date(2023, 7, 5),
        "risk_level": "high_risk",
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "US-CA",
        "issuing_body": "California State Legislature",
        "clause_identifier": "CA-SB942-AITransparencyAct",
        "official_title": "California AI Transparency Act (SB 942, as amended by AB 853)",
        "source_url": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942",
        "statutory_text": (
            "Requires large generative-AI providers (over 1 million monthly users) that "
            "produce image, video, or audio content to offer a free, publicly available "
            "detection tool letting users check whether content was created/altered by "
            "their system, and to watermark AI-generated content both visibly and via "
            "imperceptible embedded metadata (system used, timestamp). AB 853 (signed "
            "2025-10-13) pushed the operative date to 2026-08-02 and added transparency "
            "duties for GenAI hosting platforms, large online platforms, and capture-device "
            "manufacturers starting 2027-01-01."
        ),
        "publication_date": date(2024, 9, 19),
        "effective_date": date(2026, 8, 2),
        "risk_level": None,
        "origin_driver_category": "capability_leap",
    },
    # Not a US state law, but added alongside these on request: the most
    # comprehensive real watermarking/labeling-specific regulation found --
    # complements EU AI Act Article 50 and California SB 942 above, both of
    # which touch AI-content marking as part of a broader transparency
    # regime rather than as a dedicated labeling standard.
    {
        "jurisdiction": "CN",
        "issuing_body": "Cyberspace Administration of China (CAC)",
        "clause_identifier": "CN-GB45438-2025-AIContentLabeling",
        "official_title": "China Measures for Labeling AI-Generated Content (GB 45438-2025)",
        "source_url": "https://www.chinalawtranslate.com/en/ai-labeling/",
        "statutory_text": (
            "Mandatory national standard (released by the CAC 2025-03-14, effective "
            "2025-09-01) requiring AI-generated or AI-synthesized text, images, audio, "
            "video, and virtual assets distributed on Chinese platforms to carry two "
            "complementary labels: an explicit, visible label (e.g. 'AI-Generated') at the "
            "start, end, or another appropriate position in the content; and an implicit, "
            "machine-readable label embedded in file metadata (provider name, content "
            "reference number, and a digital watermark where feasible -- watermarks are "
            "encouraged but not strictly mandated). Applies to internet information service "
            "providers and online content distribution platforms; developers must build "
            "labeling in by design, ensure output traceability, and retain logs for at "
            "least six months."
        ),
        "publication_date": date(2025, 3, 14),
        "effective_date": date(2025, 9, 1),
        "risk_level": None,
        "origin_driver_category": "geopolitical_sovereignty",
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
                    "Reactive to documented algorithmic-discrimination/consumer-harm concerns "
                    "specific to this jurisdiction, per the cited source.",
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

        logger.info("Done: %d state/local AI law(s) seeded", len(REGULATIONS))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
