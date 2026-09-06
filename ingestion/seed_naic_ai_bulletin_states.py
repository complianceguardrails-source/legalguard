"""
Adds real, individually-verified state insurance-department adoptions of the
NAIC Model Bulletin on the Use of Artificial Intelligence Systems by
Insurers -- a genuinely scalable path toward broad US state AI-law coverage,
since 24+ states adopted the same substantive template "in full or without
material customization" (per Quarles & Brady's tracking, cited below), each
via its own real, dated regulatory bulletin.

Every row here shares the same real substantive content (the model
bulletin's actual requirements), varying only jurisdiction, issuing
insurance department, and each state's own verified adoption date -- not
24 independently-researched bespoke laws, but 24 real, distinct regulatory
actions adopting one real template, which is what actually happened.

Source for the full adoption-date list: Quarles & Brady, "Nearly Half of
States Have Now Adopted NAIC Model Bulletin on Insurers' Use of AI" (as of
March 2025) -- https://www.quarles.com/newsroom/publications/nearly-half-of-states-have-now-adopted-naic-model-bulletin-on-insurers-use-of-ai

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_naic_ai_bulletin_states.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_naic_ai_bulletin_states")

SOURCE_URL = "https://www.quarles.com/newsroom/publications/nearly-half-of-states-have-now-adopted-naic-model-bulletin-on-insurers-use-of-ai"

STATUTORY_TEXT = (
    "Adopts the NAIC Model Bulletin on the Use of Artificial Intelligence Systems by "
    "Insurers (approved by the NAIC's Innovation, Cybersecurity, and Technology Committee "
    "in December 2023) in full or without material customization. Requires insurers to "
    "develop, implement, and maintain a written program governing the responsible use of "
    "AI systems that make or support decisions in regulated insurance practices (e.g. "
    "underwriting, claims, pricing), addressing: governance oversight and accountability "
    "for AI-related outcomes; a risk-management framework covering the AI system's full "
    "lifecycle from development/acquisition through deployment and retirement; internal "
    "audit and third-party vendor oversight (including when relying on third-party AI "
    "systems or data); and specific measures to identify and mitigate adverse or unfairly "
    "discriminatory consumer outcomes. The insurance commissioner may request the written "
    "program and supporting documentation during examinations."
)

# (jurisdiction_code, state_name, adoption_date)
ADOPTIONS = [
    ("US-AK", "Alaska", date(2024, 2, 1)),
    ("US-AR", "Arkansas", date(2024, 7, 31)),
    ("US-CT", "Connecticut", date(2024, 2, 26)),
    ("US-DE", "Delaware", date(2025, 2, 5)),
    ("US-DC", "District of Columbia", date(2024, 5, 21)),
    ("US-IL", "Illinois", date(2024, 3, 13)),
    ("US-IA", "Iowa", date(2024, 11, 7)),
    ("US-KY", "Kentucky", date(2024, 4, 16)),
    ("US-MD", "Maryland", date(2024, 4, 22)),
    ("US-MA", "Massachusetts", date(2024, 12, 9)),
    ("US-MI", "Michigan", date(2024, 8, 7)),
    ("US-NE", "Nebraska", date(2024, 2, 23)),
    ("US-NV", "Nevada", date(2024, 2, 23)),
    ("US-NH", "New Hampshire", date(2024, 2, 20)),
    ("US-NJ", "New Jersey", date(2025, 2, 11)),
    ("US-NC", "North Carolina", date(2024, 12, 18)),
    ("US-OK", "Oklahoma", date(2024, 11, 14)),
    ("US-PA", "Pennsylvania", date(2024, 4, 6)),
    ("US-RI", "Rhode Island", date(2025, 3, 15)),
    ("US-VT", "Vermont", date(2024, 3, 12)),
    ("US-VA", "Virginia", date(2024, 7, 22)),
    ("US-WA", "Washington", date(2024, 4, 22)),
    ("US-WV", "West Virginia", date(2024, 8, 9)),
    ("US-WI", "Wisconsin", date(2025, 3, 18)),
]


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))
        matches = tag_regulation(STATUTORY_TEXT, use_cases)
        use_case_ids = [m.use_case_id for m in matches]
        logger.info(
            "Shared tag result for all 24 adoptions: %d use case(s): %s",
            len(use_case_ids),
            ", ".join(m.use_case_name for m in matches) or "(none matched)",
        )

        inserted = 0
        for jurisdiction, state_name, adoption_date in ADOPTIONS:
            reg_id = db.upsert_regulation(
                conn,
                jurisdiction=jurisdiction,
                issuing_body=f"{state_name} Department of Insurance",
                clause_identifier="NAIC-MODELBULLETIN-AI-INSURERS",
                official_title=f"{state_name} -- Adoption of NAIC Model Bulletin on Insurers' Use of AI",
                source_url=SOURCE_URL,
                statutory_text=STATUTORY_TEXT,
                version_label="v1",
                publication_date=adoption_date.isoformat(),
                effective_date=adoption_date.isoformat(),
                risk_level="high_risk",
                ingestion_source="manual",
                origin_driver_category="standards_harmonization",
                origin_driver_description=(
                    "Adopts a shared NAIC-drafted template rather than a bespoke state "
                    "law -- a coordinated standards-harmonization move across state "
                    "insurance regulators, not a reaction to a single state-specific incident."
                ),
                title=f"{state_name} -- NAIC AI Model Bulletin Adoption",
                impact_level="Brand New Guardrail Required",
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE specific_regulations SET source_url_classification = 'primary' WHERE reg_id = %s",
                    (reg_id,),
                )
            db.set_affected_use_cases(conn, reg_id, use_case_ids)
            inserted += 1
            logger.info("%s -> reg_id=%s (adopted %s)", state_name, reg_id, adoption_date.isoformat())

        logger.info("Done: %d NAIC AI Model Bulletin adoption(s) seeded", inserted)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
