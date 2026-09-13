"""
Hugging Face Hub use-case miner: searches the real Hugging Face Hub model
search API for open financial-AI models and returns them as candidate
banking_use_cases rows, source='huggingface_mined'.

Uses the real, public model search endpoint
(https://huggingface.co/api/models?search=...), verified live -- no
authentication required for basic search. Returns real fields per model:
id, pipeline_tag, library_name, tags, likes, downloads, createdAt.

Real, significant gap worth knowing up front: many genuinely relevant
finance models (most FinGPT LoRA fine-tunes, most stock-price predictors,
many "credit scoring"/"fraud detection" hits) have pipeline_tag = None --
HF metadata is often incomplete for community uploads. model_modality will
legitimately end up NULL for a real fraction of mined rows; that is a
correct reflection of missing evidence, not a bug to "fix" by guessing.

Queries below were each tested in isolation for precision before being
kept. Dropped: "financial risk" (surfaced AI-safety-research fine-tunes
about giving risky financial advice -- adjacent research artifacts, not
production use cases, not what this taxonomy is for) and "financial named
entity recognition" (zero results).

This is a discovery aid, not a technical audit -- every result should be
treated as an unverified candidate for a human to confirm, same as
github_usecases.py.
"""
from __future__ import annotations

import logging
import time
from typing import Iterable

import requests

from usecase_classifier import classify_use_case
from risk_tier_classifier import classify_risk_tier

logger = logging.getLogger(__name__)

SEARCH_URL = "https://huggingface.co/api/models"

DEFAULT_QUERIES = [
    "financial sentiment",
    "FinBERT",
    "credit scoring",
    "FinGPT",
    "financial fraud detection",
    "trading signal",
    "ESG classification",
    "loan default prediction",
]

# Real, documented Hugging Face pipeline_tag values
# (https://huggingface.co/docs/hub/models-tasks) mapped to the three model-
# modality labels. Anything not covered here (image/audio pipeline tags,
# or no pipeline_tag at all) falls through to the library_name fallback,
# then to NULL -- never guessed from the model name alone.
_DECODER_TAGS = {"text-generation", "text2text-generation", "conversational"}
_ENCODER_TAGS = {"text-classification", "feature-extraction", "sentence-similarity", "fill-mask"}
_TABULAR_TAGS = {"tabular-classification", "tabular-regression"}
_TABULAR_LIBRARIES = {"sklearn", "xgboost", "lightgbm", "catboost"}


def derive_model_modality(pipeline_tag: str | None, library_name: str | None) -> str | None:
    if pipeline_tag in _DECODER_TAGS:
        return "decoder-only"
    if pipeline_tag in _ENCODER_TAGS:
        return "encoder-only"
    if pipeline_tag in _TABULAR_TAGS:
        return "tabular-regressor"
    if library_name in _TABULAR_LIBRARIES:
        return "tabular-regressor"
    return None


def search_models(query: str, limit: int = 15) -> list[dict]:
    resp = requests.get(
        SEARCH_URL,
        params={"search": query, "limit": limit},
        headers={"User-Agent": "LegalGuard-UseCaseMiner/1.0"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def mine_hf_use_cases(queries: Iterable[str] = DEFAULT_QUERIES, min_likes: int = 0) -> list[dict]:
    """Returns a deduped list of candidate use-case dicts ready for
    db.upsert_mined_use_case(), classified by usecase_classifier.

    min_likes defaults to 0 (unlike github_usecases.py's min_stars=3) --
    most real, on-topic finance models on HF have very few likes (see
    module docstring); a star-style popularity filter here would exclude
    most genuinely relevant hits rather than just noise.
    """
    seen_ids: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        try:
            models = search_models(query)
        except requests.RequestException:
            logger.exception("HF search failed for query: %s", query)
            continue

        for model in models:
            model_id = model.get("id")
            if not model_id or model_id in seen_ids:
                continue
            if model.get("likes", 0) < min_likes:
                continue
            seen_ids.add(model_id)

            tags = model.get("tags", [])
            description = f"Hugging Face model ({model.get('pipeline_tag') or 'no pipeline_tag'})"
            sector, modality = classify_use_case(model_id, description, tags)
            risk_tier = classify_risk_tier(model_id, description, tags)
            model_modality = derive_model_modality(model.get("pipeline_tag"), model.get("library_name"))

            candidates.append(
                {
                    "name": model_id,
                    "parent_sector": sector,
                    "modality": modality,
                    "risk_tier": risk_tier,
                    "description": description,
                    "hf_model_id": model_id,
                    "model_modality": model_modality,
                    "matched_query": query,
                    "likes": model.get("likes", 0),
                }
            )

        # HF's public API has no documented per-minute cap as strict as
        # GitHub's, but pace requests conservatively regardless.
        time.sleep(1.0)

    logger.info(
        "HF use-case miner: found %d unique candidate model(s), %d with a derivable model_modality",
        len(candidates),
        sum(1 for c in candidates if c["model_modality"]),
    )
    return candidates
