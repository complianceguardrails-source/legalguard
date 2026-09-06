"""
Second shared-template cluster, after the NAIC AI Model Bulletin: US state
comprehensive consumer privacy laws that share a near-identical "opt out of
profiling in furtherance of automated decisions producing legal or
similarly significant effects" provision -- most modeled directly on
Virginia's VCDPA (the "Virginia model"). Directly relevant here because the
model's own definition of "legal or similarly significant effects" is
explicitly enumerated across these laws as: denial or provision of
financial/lending services, housing, insurance, education enrollment/
opportunities, criminal justice, employment opportunities, health care
services, or access to basic necessities -- i.e. most of this app's use-case
taxonomy by name.

State list and enactment years verified via IAPP's state privacy law
overview (https://iapp.org/resources/article/us-state-privacy-laws-overview,
July 2025 snapshot); day-level effective dates are each state's
well-documented, widely-reported statutory effective date.

This is a distinct regulation from any state-specific AI/employment/
insurance law already in the inventory for the same state (different
clause_identifier, different subject matter -- general consumer profiling
rights, not sector- or context-specific AI rules).

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_state_privacy_profiling_cluster.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_state_privacy_profiling_cluster")

STATUTORY_TEXT_TEMPLATE = (
    "Grants consumers the right to opt out of the processing of their personal data for "
    "purposes of profiling in furtherance of decisions that produce legal or similarly "
    "significant effects -- defined (following the Virginia/Colorado model most of these "
    "laws share) as the denial or provision of financial or lending services, housing, "
    "insurance, education enrollment or opportunity, criminal justice outcomes, employment "
    "opportunities, health care services, or access to essential goods or services. "
    "Controllers must honor opt-out requests, and several of these laws (following "
    "Colorado's lead) additionally require a data protection assessment before processing "
    "personal data for profiling that presents a reasonably foreseeable risk of unfair or "
    "deceptive treatment, unlawful disparate impact, or other substantial injury to "
    "consumers. {state_note}"
)

# (jurisdiction, state_name, official_law_name, effective_date, extra_note)
LAWS = [
    ("US-CA", "California", "California Consumer Privacy Act (as amended by the CPRA)", date(2023, 1, 1), ""),
    ("US-VA", "Virginia", "Virginia Consumer Data Protection Act (VCDPA)", date(2023, 1, 1), "The original source of this model."),
    ("US-CO", "Colorado", "Colorado Privacy Act (CPA)", date(2023, 7, 1), "First to add the mandatory data protection assessment requirement for profiling."),
    ("US-CT", "Connecticut", "Connecticut Data Privacy Act (CTDPA)", date(2023, 7, 1), ""),
    ("US-UT", "Utah", "Utah Consumer Privacy Act (UCPA)", date(2023, 12, 31), "Notably lacks Colorado's data protection assessment requirement."),
    ("US-MT", "Montana", "Montana Consumer Data Privacy Act (MTCDPA)", date(2024, 10, 1), ""),
    ("US-OR", "Oregon", "Oregon Consumer Privacy Act (OCPA)", date(2024, 7, 1), ""),
    ("US-TX", "Texas", "Texas Data Privacy and Security Act (TDPSA)", date(2024, 7, 1), ""),
    ("US-DE", "Delaware", "Delaware Personal Data Privacy Act (DPDPA)", date(2025, 1, 1), ""),
    ("US-IA", "Iowa", "Iowa Consumer Data Protection Act (ICDPA)", date(2025, 1, 1), "One of the narrower versions -- no data protection assessment requirement."),
    ("US-NE", "Nebraska", "Nebraska Data Privacy Act (NDPA)", date(2025, 1, 1), ""),
    ("US-NH", "New Hampshire", "New Hampshire Privacy Act", date(2025, 1, 1), ""),
    ("US-NJ", "New Jersey", "New Jersey Data Privacy Act (NJDPA)", date(2025, 1, 15), ""),
    ("US-TN", "Tennessee", "Tennessee Information Protection Act (TIPA)", date(2025, 7, 1), ""),
    ("US-MN", "Minnesota", "Minnesota Consumer Data Privacy Act (MNCDPA)", date(2025, 7, 31), "Uniquely grants a right to question and receive an explanation for consequential automated-profiling decisions, not just opt out."),
    ("US-MD", "Maryland", "Maryland Online Data Privacy Act (MODPA)", date(2025, 10, 1), "Among the most protective versions -- narrows permissible data minimization further than most peer laws."),
    ("US-IN", "Indiana", "Indiana Consumer Data Protection Act", date(2026, 1, 1), ""),
    ("US-KY", "Kentucky", "Kentucky Consumer Data Protection Act (KCDPA)", date(2026, 1, 1), ""),
    ("US-RI", "Rhode Island", "Rhode Island Data Transparency and Privacy Protection Act (RIDTPPA)", date(2026, 1, 1), ""),
]


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))
        matches = tag_regulation(STATUTORY_TEXT_TEMPLATE.format(state_note=""), use_cases)
        use_case_ids = [m.use_case_id for m in matches]
        logger.info(
            "Shared tag result for all %d laws: %d use case(s): %s",
            len(LAWS), len(use_case_ids),
            ", ".join(m.use_case_name for m in matches) or "(none matched)",
        )

        inserted = 0
        for jurisdiction, state_name, law_name, effective_date, note in LAWS:
            statutory_text = STATUTORY_TEXT_TEMPLATE.format(state_note=note)
            reg_id = db.upsert_regulation(
                conn,
                jurisdiction=jurisdiction,
                issuing_body=f"{state_name} Legislature",
                clause_identifier=f"{jurisdiction}-PRIVACYACT-ProfilingOptOut",
                official_title=f"{law_name} -- Profiling Opt-Out Provision",
                source_url="https://iapp.org/resources/article/us-state-privacy-laws-overview",
                statutory_text=statutory_text,
                version_label="v1",
                publication_date=effective_date.isoformat(),
                effective_date=effective_date.isoformat(),
                risk_level="high_risk",
                ingestion_source="manual",
                origin_driver_category="standards_harmonization",
                origin_driver_description=(
                    "Part of a well-documented multi-state pattern of near-identical "
                    "privacy-law provisions modeled on Virginia's VCDPA, not an "
                    "independent, state-specific reaction."
                ),
                title=f"{law_name} -- Profiling Opt-Out",
                impact_level="Brand New Guardrail Required",
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE specific_regulations SET source_url_classification = 'secondary' WHERE reg_id = %s",
                    (reg_id,),
                )
            db.set_affected_use_cases(conn, reg_id, use_case_ids)
            inserted += 1
            logger.info("%s -> reg_id=%s (effective %s)", state_name, reg_id, effective_date.isoformat())

        logger.info("Done: %d state privacy-law profiling provision(s) seeded", inserted)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
