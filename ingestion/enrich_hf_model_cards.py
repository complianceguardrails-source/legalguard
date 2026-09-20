"""
Fetches the model card for every HF-mined use case that hasn't had one
fetched yet, and re-runs the sector/modality/risk classifiers on it.

Why this exists: the Hub's list endpoint returns no card text, so HF rows
were mined with the placeholder description "Hugging Face model
(<pipeline_tag>)" and classified on the model ID and tags alone. After the
tag/org discovery expansion that left 43% of HF rows Uncategorized and
94% at unclassified risk -- an AML sanctions screener among them. The
card README is the evidence those classifiers were missing.

Per model, two requests: the metadata endpoint (tags, pipeline_tag,
library_name, gated flag, and cardData -- the parsed frontmatter, which
carries base_model) and the raw README. A gated model answers the first
and 401s the second; it is classified on its tags and frontmatter, and
its model_modality can still be derived from base_model. Every attempt
stamps model_card_fetched_at so nothing is refetched next run.

Labels are recomputed for every row regardless of current value, not
only rows at the fallback default -- the awesome-list contamination
(reclassify_awesome_list.py) showed a plausible-but-wrong non-default
label is invisible to a default-only safety net. HF-mined rows are
automated, so the classifier's output is authoritative for them; curated
and user-submitted rows are excluded by the fetcher.

Run manually:
    DATABASE_URL=postgres://... python ingestion/enrich_hf_model_cards.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import collections
import logging
import sys
import time

import requests

import db
from risk_tier_classifier import classify_risk_tier
from sources.huggingface_usecases import (
    card_excerpt,
    card_prose_head,
    declared_base_model,
    derive_model_modality,
    fetch_model_card,
    fetch_model_metadata,
)
from usecase_classifier import classify_use_case

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.enrich_hf_model_cards")

REQUEST_PACING_S = 0.5


def enrich_one(row: dict) -> dict | None:
    """Everything derived for one row, or None if the metadata endpoint
    itself failed (nothing to record -- leave the row for a later run)."""
    model_id = row["hf_model_id"]
    try:
        meta = fetch_model_metadata(model_id)
    except requests.RequestException:
        logger.exception("%s: metadata fetch failed", model_id)
        return None

    tags = list(meta.get("tags") or [])
    card_data = meta.get("cardData") or {}
    tags.extend(t for t in (card_data.get("tags") or []) if isinstance(t, str))

    time.sleep(REQUEST_PACING_S)
    try:
        card_text, status = fetch_model_card(model_id)
    except requests.RequestException:
        logger.exception("%s: card fetch failed", model_id)
        return None

    # The classifiers get the card's opening prose -- not the whole card,
    # see card_prose_head -- or, without a card, the same placeholder they
    # saw at mining time.
    classify_text = card_prose_head(card_text) if card_text else row["description"]
    sector, modality = classify_use_case(row["name"], classify_text, tags)
    risk_tier = classify_risk_tier(row["name"], classify_text, tags)
    model_modality = derive_model_modality(
        meta.get("pipeline_tag"), meta.get("library_name"), tags, declared_base_model(card_data)
    )

    return {
        "card_text": card_text,
        "card_status": status,
        "gated": bool(meta.get("gated")),
        "description": card_excerpt(card_text) if card_text else None,
        "parent_sector": sector,
        "modality": modality,
        "risk_tier": risk_tier,
        "model_modality": model_modality,
    }


def run(dry_run: bool, limit: int | None) -> None:
    outcomes: collections.Counter = collections.Counter()
    changes: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)

    with db.get_conn() as conn:
        rows = db.fetch_hf_use_cases_needing_model_card(conn, limit)
        logger.info("%d HF use case(s) without a fetched model card%s", len(rows), " (dry run)" if dry_run else "")

        for row in rows:
            result = enrich_one(row)
            if result is None:
                outcomes["fetch_failed"] += 1
                continue

            if result["card_text"]:
                outcomes["card"] += 1
            elif result["card_status"] in (401, 403):
                outcomes["gated"] += 1
            else:
                outcomes["no_card"] += 1

            for field in ("parent_sector", "modality", "risk_tier", "model_modality"):
                before, after = row[field], result[field]
                if before != after:
                    changes[field] += 1
                    if len(examples[field]) < 6:
                        examples[field].append(f"{row['hf_model_id']}: {before} -> {after}")
            if result["description"]:
                changes["description"] += 1

            if not dry_run:
                db.set_hf_model_card_enrichment(
                    conn, row["id"],
                    card_text=result["card_text"], description=result["description"],
                    parent_sector=result["parent_sector"], modality=result["modality"],
                    risk_tier=result["risk_tier"], model_modality=result["model_modality"],
                )
            time.sleep(REQUEST_PACING_S)

    logger.info("Outcomes: %s", dict(outcomes))
    logger.info("Fields changed: %s", dict(changes))
    for field, lines in examples.items():
        logger.info("  %s examples:\n    %s", field, "\n    ".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="fetch and classify, write nothing")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(args.dry_run, args.limit)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
