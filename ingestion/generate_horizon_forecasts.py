"""
Generates real, trend-based Horizon forecasts from actual ingested
regulation data, replacing/supplementing the hand-authored seed rows in
database/seed.sql with ones backed by an actual quarter-over-quarter signal.
See sources/horizon_forecaster.py for the (deliberately conservative)
definition of "accelerating" and why a sparse/early dataset may correctly
yield zero forecasts on a given run.

Idempotent: re-running upserts the same trend_key-tagged rows as the
underlying data changes, and removes any previously-generated forecast
whose signal no longer holds. Never touches the original hand-seeded rows
(trend_key IS NULL for those).

Run manually:
    DATABASE_URL=postgres://... python ingestion/generate_horizon_forecasts.py
"""
from __future__ import annotations

import logging
import sys

import db
from sources.horizon_forecaster import compute_trend_forecasts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.generate_horizon_forecasts")


def run() -> None:
    with db.get_conn() as conn:
        regulations = db.fetch_regulations_for_trend_analysis(conn)
        logger.info(
            "Found %d regulation(s) with both a publication date and a classified origin driver",
            len(regulations),
        )

        forecasts = compute_trend_forecasts(regulations)
        if not forecasts:
            logger.info(
                "No (jurisdiction, origin_driver_category) pair is currently accelerating "
                "(needs >=2 quarters of data with the most recent quarter's count higher than "
                "the one before it) -- leaving the horizon table as-is. This is expected with "
                "an early/sparse dataset, not an error."
            )
        for forecast in forecasts:
            db.upsert_trend_forecast(conn, **forecast)
            logger.info(
                "%s: %s -> %d%% probability, next window %s",
                forecast["trend_key"],
                forecast["projected_bill_name"],
                forecast["probability_percentage"],
                forecast["estimated_arrival_window"],
            )

        current_keys = [f["trend_key"] for f in forecasts]
        removed = db.delete_stale_trend_forecasts(conn, current_keys)
        if removed:
            logger.info("Removed %d previously-generated forecast(s) whose trend no longer holds", removed)

        logger.info("Done: %d real trend-based forecast(s) generated/updated", len(forecasts))


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
