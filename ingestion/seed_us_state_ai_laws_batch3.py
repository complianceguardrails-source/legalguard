"""
Third batch of individually-verified US state AI laws.

Excludes Maryland's "Preventing Algorithmic Discrimination Act" (explicitly
described in coverage as "proposed," no confirmed bill number/current
status found) for the same reason Virginia's HB 2094 reintroduction was
excluded from batch 2 -- omission over a fabricated placeholder.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_us_state_ai_laws_batch3.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_us_state_ai_laws_batch3")

REGULATIONS = [
    {
        "jurisdiction": "US-MD",
        "issuing_body": "Maryland General Assembly",
        "clause_identifier": "MD-HB1106-AIEmploymentLaw",
        "official_title": "Maryland AI Employment Law (HB 1106)",
        "source_url": "https://aicompliant.ai/blog/maryland-ai-employment-law-compliance-update",
        "statutory_text": (
            "Effective 2025-10-01. Regulates AI-powered tools used in employment decisions, "
            "including hiring and ongoing worker monitoring. Requires employers to provide "
            "notice to affected individuals, obtain consent before using AI in a covered "
            "employment decision, conduct bias audits of the tools used, and retain related "
            "compliance records."
        ),
        "publication_date": date(2025, 5, 20),
        "effective_date": date(2025, 10, 1),
        "risk_level": "high_risk",
        "origin_driver_category": "market_scandal",
    },
    {
        "jurisdiction": "US-CA",
        "issuing_body": "California State Legislature",
        "clause_identifier": "CA-SB1120-PhysiciansMakeDecisionsAct",
        "official_title": "California SB 1120 -- Physicians Make Decisions Act (AI Utilization Review)",
        "source_url": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB1120",
        "statutory_text": (
            "Signed 2024-09-28, effective 2025-01-01. Regulates how health care service "
            "plans and disability insurers may use AI, algorithms, and other software tools "
            "in utilization review and utilization management. Prohibits denying, delaying, "
            "or modifying health care services based on medical necessity through AI alone -- "
            "any such denial, delay, or modification must be reviewed and decided by a "
            "licensed physician or other qualified health care provider with expertise in "
            "the specific clinical issues involved. Directly relevant to insurance-sector AI "
            "use cases involving claims/utilization decisions."
        ),
        "publication_date": date(2024, 9, 28),
        "effective_date": date(2025, 1, 1),
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
                origin_driver_description="Reactive to documented consumer-harm concerns specific to this jurisdiction, per the cited source.",
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
