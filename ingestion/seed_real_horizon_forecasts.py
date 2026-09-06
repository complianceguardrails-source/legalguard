"""
Adds real, currently-pending or recently-signed-but-not-yet-effective AI
regulations to regulatory_horizon_forecast, replacing/supplementing the 2
illustrative hand-seeded examples in database/seed.sql with entries backed
by actual bill numbers and verified legislative status (checked against
official state legislature sites -- malegislature.gov, app.leg.wa.gov,
nysenate.gov -- as of this pass; legislative status moves fast, so treat
the citations in each description as the thing to re-verify, not this
script's probability_percentage).

probability_percentage is a documented, stage-based heuristic, not a
guess: a bill already SIGNED into law but not yet effective gets ~99% (all
that's left is the calendar); a bill that passed initial committee with a
favorable vote gets ~50-55%; a bill newly introduced or stalled would get
lower still. This mirrors the same "coarse but real, not certified" caveat
this project already applies to origin_driver_category classifications.

Run manually:
    DATABASE_URL=postgres://... python ingestion/seed_real_horizon_forecasts.py
"""
from __future__ import annotations

import logging
import sys

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.seed_real_horizon_forecasts")

FORECASTS = [
    {
        "projected_bill_name": "Massachusetts S.264 -- AI Chatbot Consumer Protections",
        "target_jurisdiction": "US-MA",
        "estimated_arrival_window": "H2 2026",
        "probability_percentage": 55,
        "upstream_catalyst_drivers": ["capability_leap"],
        "underlying_driver_description": (
            "Real, currently-pending bill (malegislature.gov Bill S.264, 194th General "
            "Court, 2025-2026 session): favorably reported by the Consumer Protection and "
            "Professional Licensure Committee and referred to Senate Ways and Means as of "
            "2025-12-18 -- has cleared its first committee hurdle but still needs a full "
            "Senate vote, House passage, and the Governor's signature before becoming law. "
            "Would require operators of consumer-facing AI chatbots to disclose that users "
            "are interacting with AI. Probability reflects favorable-committee-report stage, "
            "not a certified forecast -- re-check malegislature.gov before relying on it."
        ),
        "impact_text": "Voice agent and chatbot customer-support use cases",
        "tag_text": "consumer-facing artificial intelligence chatbot disclosure customer service voice agent conversational",
    },
    {
        "projected_bill_name": "Washington HB 2225 -- AI Companion Chatbot Safeguards (Chapter 168, 2026 Laws)",
        "target_jurisdiction": "US-WA",
        "estimated_arrival_window": "Q1 2027",
        "probability_percentage": 99,
        "upstream_catalyst_drivers": ["market_scandal"],
        "underlying_driver_description": (
            "Real, already-signed law (app.leg.wa.gov: signed by Governor Ferguson "
            "2026-03-24, Chapter 168 of 2026 Laws, passed 69-28 House / 43-5 Senate) with "
            "an effective date of 2027-01-01 that hasn't arrived yet -- listed here rather "
            "than in the regulation inventory because it isn't in force yet, not because "
            "its passage is in doubt. Requires AI companion chatbot operators to disclose "
            "the AI is artificial at the start of interaction and periodically thereafter, "
            "bars manipulative engagement techniques and claiming to be human, and mandates "
            "crisis-response protocols for self-harm signals, with a private right of action."
        ),
        "impact_text": "Voice agent and conversational customer-support use cases",
        "tag_text": "AI companion chatbot conversational voice agent customer service disclosure manipulative engagement",
    },
    {
        "projected_bill_name": "New York S.8115C -- Automated Lending Decision-Tool Oversight",
        "target_jurisdiction": "US-NY",
        "estimated_arrival_window": "H2 2026",
        "probability_percentage": 50,
        "upstream_catalyst_drivers": ["market_scandal"],
        "underlying_driver_description": (
            "Real, currently-pending bill (nysenate.gov Bill S.8115C): passed the Senate "
            "Banks Committee 5-2 and was reported to the Internet and Technology Committee "
            "as of 2026-05-12 -- still needs to clear that committee, pass both chambers, "
            "and be signed. Would require banks using automated lending decision tools to "
            "run annual third-party-involved disparate-impact assessments, publish summaries, "
            "give applicants 24-hour advance notice and an opt-out, explain denials within "
            "24 hours, and report discriminatory findings to regulators within 30 days."
        ),
        "impact_text": "Consumer lending and credit-scoring use cases",
        "tag_text": "automated lending decision tool bank credit underwriting scoring loan denial disparate impact",
    },
]


def run() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        logger.info("Loaded %d use case(s) for tagging", len(use_cases))

        for forecast in FORECASTS:
            matches = tag_regulation(forecast["tag_text"], use_cases)
            use_case_ids = [m.use_case_id for m in matches]

            with conn.cursor() as cur:
                # No DB-level unique constraint on projected_bill_name (this
                # table has none besides its primary key), so guard against
                # duplicate rows on a re-run explicitly rather than relying
                # on ON CONFLICT.
                cur.execute(
                    "SELECT id FROM regulatory_horizon_forecast WHERE projected_bill_name = %s",
                    (forecast["projected_bill_name"],),
                )
                existing = cur.fetchone()
                if existing:
                    row = existing
                    cur.execute(
                        """
                        UPDATE regulatory_horizon_forecast SET
                            target_jurisdiction = %s, estimated_arrival_window = %s,
                            probability_percentage = %s, upstream_catalyst_drivers = %s,
                            underlying_driver_description = %s, impact_blast_radius_summary = %s,
                            affected_use_case_ids = %s, updated_at = now()
                        WHERE id = %s
                        """,
                        (
                            forecast["target_jurisdiction"], forecast["estimated_arrival_window"],
                            forecast["probability_percentage"], forecast["upstream_catalyst_drivers"],
                            forecast["underlying_driver_description"], forecast["impact_text"],
                            use_case_ids, existing[0],
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO regulatory_horizon_forecast
                            (projected_bill_name, target_jurisdiction, estimated_arrival_window,
                             probability_percentage, upstream_catalyst_drivers,
                             underlying_driver_description, impact_blast_radius_summary,
                             affected_use_case_ids, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'watching')
                        RETURNING id
                        """,
                        (
                            forecast["projected_bill_name"],
                            forecast["target_jurisdiction"],
                            forecast["estimated_arrival_window"],
                            forecast["probability_percentage"],
                            forecast["upstream_catalyst_drivers"],
                            forecast["underlying_driver_description"],
                            forecast["impact_text"],
                            use_case_ids,
                        ),
                    )
                    row = cur.fetchone()

            logger.info(
                "%s -> id=%s, tagged %d use case(s): %s",
                forecast["projected_bill_name"],
                row[0] if row else "already existed",
                len(use_case_ids),
                ", ".join(m.use_case_name for m in matches) or "(none matched)",
            )

        logger.info("Done: %d real horizon forecast(s) seeded", len(FORECASTS))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
