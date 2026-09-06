"""
Second batch of individually-verified US state AI laws, continuing from
seed_us_state_ai_laws.py -- same verification standard (checked against
official bill text or authoritative law-firm/news coverage of the actual
legislative status).

Notably excludes Virginia's HB 2094 (High-Risk AI Developer and Deployer
Act): it passed the legislature in Feb 2025 but was VETOED by Governor
Youngkin on 2025-03-24, so it is not current law. Its expected narrower
2026 reintroduction has no confirmed bill number or text as of this pass,
so it isn't added anywhere (regulation inventory or Horizon) -- omission
over a fabricated placeholder for legislation that doesn't exist yet.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_us_state_ai_laws_batch2.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_us_state_ai_laws_batch2")

REGULATIONS = [
    {
        "jurisdiction": "US-MT",
        "issuing_body": "Montana State Legislature",
        "clause_identifier": "MT-SB212-RightToComputeAct",
        "official_title": "Montana Right to Compute Act (SB 212)",
        "source_url": "https://www.multistate.ai/updates/vol-59-montana-right-to-compute-law",
        "statutory_text": (
            "The first US state 'right to compute' law (signed by Governor Gianforte, "
            "April 2025, effective on passage). Establishes a fundamental right to privately "
            "own and use computational resources for lawful purposes, and applies strict "
            "scrutiny -- the highest constitutional standard -- to government restrictions "
            "on that right, requiring any limitation to be demonstrably necessary and "
            "narrowly tailored to a compelling government interest. Notably still imposes a "
            "real, targeted obligation: deployers of AI systems controlling critical "
            "infrastructure facilities (e.g. power plants, water systems) making "
            "consequential decisions must adopt a risk management policy based on a "
            "recognized framework such as NIST's AI Risk Management Framework."
        ),
        "publication_date": date(2025, 4, 23),
        "effective_date": date(2025, 4, 23),
        "risk_level": None,
        "origin_driver_category": "capability_leap",
        "origin_driver_description": (
            "A pro-innovation, rights-protective counter-example to the discrimination-"
            "focused state AI laws elsewhere in this inventory -- worth tracking precisely "
            "because it constrains what obligations OTHER Montana rules can impose on AI, "
            "not because it imposes new obligations itself (aside from the critical-"
            "infrastructure carve-out)."
        ),
    },
    {
        "jurisdiction": "US-TN",
        "issuing_body": "Tennessee General Assembly",
        "clause_identifier": "TN-ELVISACT-VoiceLikeness",
        "official_title": "Tennessee ELVIS Act (Ensuring Likeness Voice and Image Security Act)",
        "source_url": "https://en.wikipedia.org/wiki/ELVIS_Act",
        "statutory_text": (
            "Signed 2024-03-21, effective 2024-07-01. Amends Tennessee's existing right-of-"
            "publicity law to explicitly protect a person's voice -- both their actual voice "
            "and an AI-generated 'simulation' of it -- as a property right, alongside name, "
            "photograph, and likeness, across any medium. Prohibits unauthorized commercial "
            "use, enforceable via civil action and, unusually among state AI-adjacent laws, "
            "as a criminal Class A misdemeanor (up to 11 months 29 days jail and/or $2,500 "
            "fine). Directly relevant to voice-cloning/synthetic-voice AI use cases -- the "
            "first US state law to name AI voice cloning specifically."
        ),
        "publication_date": date(2024, 3, 21),
        "effective_date": date(2024, 7, 1),
        "risk_level": None,
        "origin_driver_category": "capability_leap",
    },
    {
        "jurisdiction": "US-NJ",
        "issuing_body": "New Jersey Division on Civil Rights",
        "clause_identifier": "NJ-LAD-DisparateImpactRules-AI",
        "official_title": "New Jersey Law Against Discrimination -- Disparate Impact Regulations (AI Guidance)",
        "source_url": "https://www.consumerfinancialserviceslawmonitor.com/2025/12/new-jersey-adopts-disparate-impact-rules-under-lad-with-broad-reach-across-housing-lending-employment-and-other-fields-with-specific-guidance-on-ai/",
        "statutory_text": (
            "Adopted by the NJ Division on Civil Rights, effective 2025-12-15 -- described "
            "by NJ Attorney General Matthew Platkin as 'the most comprehensive state-level "
            "disparate impact regulations in the country.' Establishes that facially-neutral "
            "practices (including automated tools: resume-screening algorithms, video-based "
            "assessments, scheduling filters) violate the Law Against Discrimination if they "
            "disproportionately harm a protected group, unless necessary to a legitimate "
            "objective with no less-discriminatory alternative available. Entities using "
            "third-party AI systems must take reasonable steps to ensure vendor compliance -- "
            "but doing so does NOT shield them from liability if the tool still produces an "
            "unlawful disparate impact. Lending-specific guidance was comparatively thin in "
            "this rulemaking; future clarification is expected."
        ),
        "publication_date": date(2025, 12, 15),
        "effective_date": date(2025, 12, 15),
        "risk_level": "high_risk",
        "origin_driver_category": "market_scandal",
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

        logger.info("Done: %d state AI law(s) seeded", len(REGULATIONS))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
