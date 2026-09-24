"""
Derives real, trend-based Horizon forecasts from actual ingested regulation
data -- the wiring docs/ARCHITECTURE.md describes as the natural next step
once origin_driver_trend_summary has enough history to mean anything:
"if capability_leap-labeled regulations from the UK have been climbing
quarter over quarter, that's a concrete reason to expect the next one."

This module is pure logic, DB-agnostic (see
ingestion/generate_horizon_forecasts.py for the entrypoint that reads/writes
via db.py), so it's testable without a live connection.

Definition of "accelerating", deliberately conservative and literal: a
(jurisdiction, origin_driver_category) pair with regulations in at least two
distinct quarters, where the most recent quarter with data has a STRICTLY
HIGHER count than the quarter immediately before it. A single data point, or
a flat/declining count, does not qualify -- this project's standing rule is
to omit a forecast rather than manufacture one from a weak or absent signal
(see guardrailThresholds.js/architecture_signal for the same principle
elsewhere). With this project's current, early ingestion history, that
conservative bar may currently yield zero qualifying pairs -- that's the
correct, honest output, not a bug.

Two further conditions, both about time rather than counts, because a
sparse corpus makes it easy to read a trend that isn't there:

  * The two quarters compared must be CONSECUTIVE. Taking the last two
    quarters that merely happen to contain data lets a gap masquerade as
    growth -- a jurisdiction with three instruments in 2023 Q4, nothing at
    all for two quarters, then fourteen in 2024 Q3 is not accelerating in
    any sense a reader would accept.
  * The run must still be CURRENT: the latest quarter with data has to be
    this quarter or the one before it. A series that stopped moving two
    years ago is history, not a forecast, and a probability attached to it
    reads as a claim about now.

The arrival window is therefore the quarter after the current one, not the
quarter after the last one with data -- an "estimated arrival" that has
already been and gone is worse than no forecast at all.

Every generated forecast is traceable back to the specific real regulations
that produced it (via reg_id/title), and every numeric field is computed
from real counts -- probability_percentage is a documented, deterministic
function of the quarter-over-quarter growth ratio, not a guess.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

ORIGIN_DRIVER_LABELS = {
    "market_scandal": "Market Scandal",
    "capability_leap": "Capability Leap",
    "geopolitical_sovereignty": "Geopolitical Sovereignty",
    "standards_harmonization": "Standards Harmonization",
}


def quarter_start(d: date) -> date:
    q_month = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, q_month, 1)


def quarter_label(d: date) -> str:
    quarter_num = (d.month - 1) // 3 + 1
    return f"Q{quarter_num} {d.year}"


def prev_quarter(d: date) -> date:
    """The start of the quarter immediately before the one d starts."""
    month, year = d.month - 3, d.year
    if month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


def next_quarter_label(d: date) -> str:
    next_month = d.month + 3
    next_year = d.year
    if next_month > 12:
        next_month -= 12
        next_year += 1
    return quarter_label(date(next_year, next_month, 1))


def probability_from_ratio(latest_count: int, previous_count: int) -> int:
    """Deterministic, documented mapping from growth ratio to a confidence
    score -- not an arbitrary pick. A ratio of 1.0 (flat) would map to 50,
    but flat pairs never reach this function (they don't qualify as
    accelerating); a doubling (ratio 2.0) maps to 90. Clamped to [55, 95]
    so this never claims near-certainty from a small-sample heuristic."""
    ratio = latest_count / previous_count
    return max(55, min(95, round(50 + (ratio - 1) * 40)))


def compute_trend_forecasts(regulations: list[dict], today: date | None = None) -> list[dict]:
    """regulations: rows from db.fetch_regulations_for_trend_analysis, each
    with jurisdiction, origin_driver_category, publication_date,
    display_title, affected_use_case_ids. Returns a list of forecast dicts
    ready for db.upsert_trend_forecast, one per qualifying (jurisdiction,
    category) pair."""
    this_quarter = quarter_start(today or date.today())

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for reg in regulations:
        key = (reg["jurisdiction"], reg["origin_driver_category"])
        groups[key].append(reg)

    forecasts = []
    for (jurisdiction, category), regs in groups.items():
        by_quarter: dict[date, list[dict]] = defaultdict(list)
        for reg in regs:
            by_quarter[quarter_start(reg["publication_date"])].append(reg)

        quarters = sorted(by_quarter.keys())
        if len(quarters) < 2:
            continue  # not enough history to call this a trend either way

        latest_q, previous_q = quarters[-1], quarters[-2]
        if previous_q != prev_quarter(latest_q):
            continue  # a gap between them, not quarter-over-quarter growth
        if latest_q < prev_quarter(this_quarter):
            continue  # the run stopped more than a quarter ago -- history, not a trend

        latest_regs, previous_regs = by_quarter[latest_q], by_quarter[previous_q]
        latest_count, previous_count = len(latest_regs), len(previous_regs)

        if latest_count <= previous_count:
            continue  # flat or declining -- not accelerating, skip

        category_label = ORIGIN_DRIVER_LABELS.get(category, category.replace("_", " ").title())
        driving_titles = [r["display_title"] for r in latest_regs if r.get("display_title")][:5]
        all_use_case_ids = sorted({str(uid) for r in regs for uid in (r.get("affected_use_case_ids") or [])})

        forecasts.append(
            {
                "trend_key": f"trend:{jurisdiction}:{category}",
                "target_jurisdiction": jurisdiction,
                "projected_bill_name": f"Accelerating {category_label} Activity -- {jurisdiction}",
                "estimated_arrival_window": next_quarter_label(this_quarter),
                "probability_percentage": probability_from_ratio(latest_count, previous_count),
                "upstream_catalyst_drivers": [category],
                "underlying_driver_description": (
                    f"{latest_count} {category_label.lower()}-driven regulation(s) classified in "
                    f"{jurisdiction} in the most recent quarter with data ({quarter_label(latest_q)}), "
                    f"up from {previous_count} the quarter before ({quarter_label(previous_q)}). "
                    f"Derived from real ingested regulation counts, not a certified prediction -- "
                    f"origin_driver_category is itself a coarse heuristic classification "
                    f"(see ingestion/tagger.py)."
                ),
                "impact_blast_radius_summary": "; ".join(driving_titles) if driving_titles else "(untitled regulations)",
                "affected_use_case_ids": all_use_case_ids,
            }
        )

    return forecasts
