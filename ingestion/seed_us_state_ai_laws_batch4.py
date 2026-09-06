"""
Fourth US state AI-law batch. Three real, individually-verified additions,
each in a state with zero prior coverage in this inventory (checked against
the current specific_regulations table before writing this):

1. Hawaii -- NAIC Model Bulletin on Insurers' Use of AI adoption, via
   Insurance Commissioner Memorandum No. 2025-13A (effective 2025-12-10).
   Completes the NAIC cluster for a state explicitly named as an adopter.
   Source: same Quarles & Brady tracking already cited in
   seed_naic_ai_bulletin_states.py, cross-checked against reporting
   specifically naming Hawaii's memorandum number and effective date.

2. Florida -- Florida Digital Bill of Rights (SB 262), profiling opt-out
   provision. Completes the comprehensive-privacy-law cluster (the 20th
   state) alongside seed_state_privacy_profiling_cluster.py's 18 entries.
   Narrower in practice than its peers: applies only to "controllers" that
   process data of 100,000+ Florida consumers AND meet a >=$1B global gross
   revenue threshold (not a general-applicability law like most peer
   states), and the statute's own defined term "profiling" is scoped to
   children specifically, even though the opt-out right for automated
   decisions with legal/similarly significant effects is written more
   generally -- flagged explicitly below rather than presented as identical
   in scope to the VCDPA-model laws.

3. Missouri -- SB 1019, prohibits advertising an AI chatbot as a licensed
   therapy/mental-health-diagnosis provider (effective 2026-08-28). A real,
   distinct, non-cluster state AI law -- reactive to documented AI-therapy-
   chatbot harm reporting (market_scandal), not a shared template. Enforced
   as an unlawful practice under the Missouri Merchandising Practices Act.

Not included despite research: Georgia, Louisiana, Arizona, and Kansas were
checked and found to have NOT adopted the NAIC bulletin as of this batch;
several are reported to have chatbot-safety-style bills in progress but
without a specific, individually verifiable bill citation found -- left for
a future batch once one is confirmed rather than cited from a vague
secondary summary.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_us_state_ai_laws_batch4.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_us_state_ai_laws_batch4")

NAIC_SOURCE_URL = "https://www.quarles.com/newsroom/publications/nearly-half-of-states-have-now-adopted-naic-model-bulletin-on-insurers-use-of-ai"
NAIC_STATUTORY_TEXT = (
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

FLORIDA_STATUTORY_TEXT = (
    "Grants Florida consumers the right to opt out of the processing of their personal "
    "data for purposes of profiling in furtherance of a decision that produces a legal or "
    "similarly significant effect concerning the consumer. Notably narrower in "
    "applicability than most peer state privacy laws: only binds 'controllers' that both "
    "process the personal data of 100,000 or more Florida consumers AND derive 50% or "
    "more of global gross annual revenue from the sale of advertisements online, operate a "
    "consumer smart speaker/voice assistant service, or operate an app store/digital "
    "distribution platform with at least 250,000 software applications for consumers to "
    "download -- alongside a separate revenue-threshold path requiring >=$1 billion in "
    "global gross annual revenue. The statute's own defined term 'profiling' is scoped "
    "specifically to processing that evaluates a child's characteristics; the general "
    "consumer opt-out right for automated decisions is written more broadly. Treat this as "
    "a materially narrower law than the VCDPA-model cluster it otherwise resembles, not an "
    "equivalent one."
)

MISSOURI_STATUTORY_TEXT = (
    "Prohibits advertising an AI chatbot or similar automated system as capable of "
    "providing therapy, mental health treatment, or a mental health diagnosis, or as being "
    "a licensed mental health professional. A violation constitutes an unlawful practice "
    "under the Missouri Merchandising Practices Act (the state's consumer-fraud statute), "
    "carrying a $10,000 fine for a first offense and $20,000 for each subsequent offense. "
    "Enacted as part of an omnibus health care bill (HCS SB 1019), passed by the Missouri "
    "General Assembly 2026-05-15 and delivered to the Governor 2026-05-28."
)


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))

        # -- Hawaii: NAIC Model Bulletin adoption --------------------------
        naic_matches = tag_regulation(NAIC_STATUTORY_TEXT, use_cases)
        naic_use_case_ids = [m.use_case_id for m in naic_matches]
        reg_id = db.upsert_regulation(
            conn,
            jurisdiction="US-HI",
            issuing_body="Hawaii Department of Commerce and Consumer Affairs, Insurance Division",
            clause_identifier="NAIC-MODELBULLETIN-AI-INSURERS",
            official_title="Hawaii -- Adoption of NAIC Model Bulletin on Insurers' Use of AI",
            source_url=NAIC_SOURCE_URL,
            statutory_text=NAIC_STATUTORY_TEXT,
            version_label="v1",
            publication_date=date(2025, 12, 10).isoformat(),
            effective_date=date(2025, 12, 10).isoformat(),
            risk_level="high_risk",
            ingestion_source="manual",
            origin_driver_category="standards_harmonization",
            origin_driver_description=(
                "Adopts a shared NAIC-drafted template (via Insurance Commissioner "
                "Memorandum No. 2025-13A) rather than a bespoke state law -- a coordinated "
                "standards-harmonization move, not a reaction to a single incident."
            ),
            title="Hawaii -- NAIC AI Model Bulletin Adoption",
            impact_level="Brand New Guardrail Required",
        )
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE specific_regulations SET source_url_classification = 'primary' WHERE reg_id = %s",
                (reg_id,),
            )
        db.set_affected_use_cases(conn, reg_id, naic_use_case_ids)
        logger.info("Hawaii (NAIC) -> reg_id=%s, %d use case(s)", reg_id, len(naic_use_case_ids))

        # -- Florida: Digital Bill of Rights profiling opt-out -------------
        fl_matches = tag_regulation(FLORIDA_STATUTORY_TEXT, use_cases)
        fl_use_case_ids = [m.use_case_id for m in fl_matches]
        reg_id = db.upsert_regulation(
            conn,
            jurisdiction="US-FL",
            issuing_body="Florida Attorney General, Department of Legal Affairs",
            clause_identifier="FDBR-PROFILING-OPTOUT",
            official_title="Florida Digital Bill of Rights (SB 262) -- Profiling Opt-Out Provision",
            source_url="https://www.whitecase.com/insight-alert/florida-enacts-digital-bill-rights-joining-growing-privacy-landscape",
            statutory_text=FLORIDA_STATUTORY_TEXT,
            version_label="v1",
            publication_date=date(2023, 6, 6).isoformat(),
            effective_date=date(2024, 7, 1).isoformat(),
            risk_level="limited_risk",
            ingestion_source="manual",
            origin_driver_category="standards_harmonization",
            origin_driver_description=(
                "Follows the same profiling-opt-out pattern as the VCDPA-model cluster, "
                "though scoped narrower via large-company applicability thresholds -- see "
                "statutory_text for the specific carve-outs."
            ),
            title="Florida Digital Bill of Rights -- Profiling Opt-Out",
            impact_level="Version Revision Trigger",
        )
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE specific_regulations SET source_url_classification = 'secondary' WHERE reg_id = %s",
                (reg_id,),
            )
        db.set_affected_use_cases(conn, reg_id, fl_use_case_ids)
        logger.info("Florida (FDBR) -> reg_id=%s, %d use case(s)", reg_id, len(fl_use_case_ids))

        # -- Missouri: AI therapy chatbot advertising ban -------------------
        mo_matches = tag_regulation(MISSOURI_STATUTORY_TEXT, use_cases)
        mo_use_case_ids = [m.use_case_id for m in mo_matches]
        reg_id = db.upsert_regulation(
            conn,
            jurisdiction="US-MO",
            issuing_body="Missouri Attorney General (Merchandising Practices Act enforcement)",
            clause_identifier="MO-SB1019-AI-THERAPY-CHATBOT-BAN",
            official_title="Missouri SB 1019 -- AI Therapy Chatbot Advertising Prohibition",
            source_url="https://www.metonym.news/p/the-quietest-therapy-bot-ban-in-america",
            statutory_text=MISSOURI_STATUTORY_TEXT,
            version_label="v1",
            publication_date=date(2026, 5, 15).isoformat(),
            effective_date=date(2026, 8, 28).isoformat(),
            risk_level="high_risk",
            ingestion_source="manual",
            origin_driver_category="market_scandal",
            origin_driver_description=(
                "Reactive to documented harm reports from AI chatbots giving unlicensed "
                "mental-health advice/diagnoses -- a distinct, bespoke state response, not "
                "a shared template like the NAIC or VCDPA-model clusters."
            ),
            title="Missouri -- AI Therapy Chatbot Advertising Ban",
            impact_level="Brand New Guardrail Required",
        )
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE specific_regulations SET source_url_classification = 'secondary' WHERE reg_id = %s",
                (reg_id,),
            )
        db.set_affected_use_cases(conn, reg_id, mo_use_case_ids)
        logger.info("Missouri (SB 1019) -> reg_id=%s, %d use case(s)", reg_id, len(mo_use_case_ids))

        logger.info("Done: 3 real state AI law(s) seeded (Hawaii, Florida, Missouri)")


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
