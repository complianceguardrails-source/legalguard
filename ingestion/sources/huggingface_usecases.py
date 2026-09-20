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

Three discovery channels, each with a different blind spot:

  1. NAME SEARCH (?search=): matches the query against the model ID only.
     Finds "FinBERT"/"FinGPT" fine-tunes by the hundreds and nothing whose
     name is a brand -- InvestLM, FinTral, Fin-LLaMA, FinMA were all absent
     from the database after 19 queries, because no query string appears
     in their IDs. Before the other channels existed, only 6 of 150 mined
     HF models were decoder-only: the corpus was BERT-era classifiers, and
     the generative finance LLMs that actually carry hallucination and
     disclosure risk were almost entirely missing.
  2. TAG FILTER (?filter=<tag>): matches uploader-applied tags regardless
     of name. This is what surfaces Llama-3-SEC-Base, finance-Llama3-8B,
     Ling-Fin, FinR1 -- models a name search can never reach.
  3. ORG LISTING (?author=<org>): everything published by an organisation
     dedicated to finance models. TheFinAI alone has 40 (FinMA, FinLLaMA,
     FinLLaVA, OpenFinLLM); the database held 2 of them.

Each query, tag and org below was tested in isolation for precision
before being kept, by sampling results at random and judging on-topic
rate by hand. Dropped:

  Queries -- "financial risk" (AI-safety-research fine-tunes about giving
  risky financial advice: adjacent research artifacts, not production use
  cases), "financial named entity recognition", "insurance claim
  classification", "money laundering detection", "algorithmic trading
  model" (all zero results).

  Tags -- "sec" (10 results, mostly an unrelated "SeC" model family),
  "credit" (2 results), "economics" (Llama2-7b-economist and similar:
  adjacent research, not financial services -- same reasoning as
  "financial risk"). The "finance" tag is kept but is a special case:
  raw, it is ~15% on-topic (Gothica, idkai, Hackathon, Uncensored, xxxx --
  junk uploads with copied tag lists), which would repeat the
  awesome-list contamination documented in reclassify_awesome_list.py at
  eight times the scale. With a downloads floor of 100 it is ~60% on-topic,
  in line with the specific tags, so it carries one. (The likes floor is
  still 0 for name search -- see mine_hf_use_cases -- because those hits
  are on-topic by construction and popularity would only remove real
  ones. Different channel, different purpose.)

  Orgs -- "arcee-ai" (1 finance model in 200; the tag channel finds it),
  "instruction-pretrain" (1 in 5, same), "FinancialSupport" (medical QA
  and NanoGPT despite the name), "AI4Finance-Foundation" and "adaptllm"
  (no models). Only organisations that publish finance models exclusively
  are listed, because an org channel has no per-model filter.

Quantisation re-uploads are skipped on every channel. Bulk quantisers
(mradermacher, TheBloke, tensorblock, bartowski ...) republish upstream
models as -GGUF/-GPTQ/-AWQ/-i1 variants with the upstream tags copied
verbatim; in the "finance" tag with the downloads floor applied, 280 of
446 results were such re-uploads. They are the same use case as the
upstream model, which is found through its own listing.

This is a discovery aid, not a technical audit -- every result should be
treated as an unverified candidate for a human to confirm, same as
github_usecases.py.
"""
from __future__ import annotations

import logging
import re
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
    "ClimateBERT",
    "portfolio optimization",
    "earnings call sentiment",
    "credit risk",
    "insurance underwriting",
    "insurance fraud",
    "stock price prediction",
    "bankruptcy prediction",
    "financial question answering",
    "KYC verification",
    "anti money laundering",
]

# (tag, minimum downloads). See the module docstring for why "finance"
# alone carries a floor.
DEFAULT_TAGS: list[tuple[str, int]] = [
    ("financial", 0),
    ("banking", 0),
    ("trading", 0),
    ("insurance", 0),
    ("fintech", 0),
    ("stock-market", 0),
    ("finance", 100),
]

DEFAULT_AUTHORS = ["TheFinAI", "FinGPT", "ChanceFocus", "Duxiaoman-DI"]

# Largest single tag ("finance") is ~2,700 models at time of writing;
# this bounds runtime if a tag balloons rather than limiting real results.
MAX_MODELS_PER_CHANNEL = 4000

_QUANT_ID_RE = re.compile(r"[-_](gguf|gptq|awq|exl2|mlx|i1|imatrix|bnb|[48]bit)\b", re.IGNORECASE)
_QUANT_TAGS = {"gguf", "gptq", "awq", "exl2", "mlx"}

# Real, documented Hugging Face pipeline_tag values
# (https://huggingface.co/docs/hub/models-tasks) mapped to the three model-
# modality labels. Anything not covered here (image/audio pipeline tags,
# or no pipeline_tag at all) falls through the declared-metadata fallbacks
# below, then to NULL -- never guessed from the model name alone.
_DECODER_TAGS = {"text-generation", "text2text-generation", "conversational"}
_ENCODER_TAGS = {"text-classification", "feature-extraction", "sentence-similarity", "fill-mask"}
_TABULAR_TAGS = {"tabular-classification", "tabular-regression"}
_TABULAR_LIBRARIES = {"sklearn", "xgboost", "lightgbm", "catboost"}

# Architecture families, matched as substrings of an uploader-declared
# base_model id (card frontmatter, surfaced by the API as cardData.base_model).
# A fine-tune of Llama with no pipeline_tag is still a decoder-only model;
# the uploader has said so, just in a different field. Kept to families
# whose architecture is unambiguous.
_DECODER_FAMILIES = (
    "llama", "qwen", "mistral", "mixtral", "gemma", "phi-", "phi3", "phi2", "bloom", "falcon",
    "gpt2", "gpt-neo", "gptj", "gpt-j", "opt-", "deepseek", "granite", "smollm", "yi-", "internlm",
    "baichuan", "chatglm", "tinyllama", "olmo", "pythia", "stablelm", "starcoder", "codellama",
)
_ENCODER_FAMILIES = (
    "bert", "roberta", "deberta", "distilbert", "electra", "albert", "modernbert", "bge-", "e5-",
    "minilm", "mpnet", "xlm-r", "longformer", "bigbird",
)

MODEL_CARD_MAX_CHARS = 12000
MODEL_CARD_URL = "https://huggingface.co/{model_id}/raw/main/README.md"
MODEL_API_URL = "https://huggingface.co/api/models/{model_id}"


def _family_modality(base_model: str | None) -> str | None:
    if not base_model:
        return None
    lowered = base_model.lower()
    if any(f in lowered for f in _DECODER_FAMILIES):
        return "decoder-only"
    if any(f in lowered for f in _ENCODER_FAMILIES):
        return "encoder-only"
    return None


def derive_model_modality(
    pipeline_tag: str | None,
    library_name: str | None,
    tags: Iterable[str] = (),
    base_model: str | None = None,
) -> str | None:
    """Declared metadata only, in order of directness: the pipeline_tag
    field; a pipeline name present in the tag list when the field itself
    is unset (the Hub surfaces it both ways, not always consistently); the
    library; the declared base model's architecture family."""
    if pipeline_tag is None:
        pipeline_tag = next((t for t in tags if t in _DECODER_TAGS | _ENCODER_TAGS | _TABULAR_TAGS), None)
    if pipeline_tag in _DECODER_TAGS:
        return "decoder-only"
    if pipeline_tag in _ENCODER_TAGS:
        return "encoder-only"
    if pipeline_tag in _TABULAR_TAGS:
        return "tabular-regressor"
    if library_name in _TABULAR_LIBRARIES:
        return "tabular-regressor"
    return _family_modality(base_model)


_HEADERS = {"User-Agent": "LegalGuard-UseCaseMiner/1.0"}


def _list_models(params: dict, max_items: int = MAX_MODELS_PER_CHANNEL) -> list[dict]:
    """Follows the Hub's Link: rel="next" pagination. The next-page URL
    already carries the cursor, so params are sent on the first request
    only."""
    url: str | None = SEARCH_URL
    items: list[dict] = []
    while url and len(items) < max_items:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=60)
        resp.raise_for_status()
        items.extend(resp.json())
        links = requests.utils.parse_header_links(resp.headers.get("Link", ""))
        url = next((link["url"] for link in links if link.get("rel") == "next"), None)
        params = None
        # HF's public API has no documented per-minute cap as strict as
        # GitHub's, but pace requests conservatively regardless.
        time.sleep(1.0)
    return items[:max_items]


def search_models(query: str, limit: int = 15) -> list[dict]:
    return _list_models({"search": query, "limit": limit}, max_items=limit)


def fetch_model_metadata(model_id: str) -> dict:
    """The single-model endpoint. Unlike the list endpoint it returns
    cardData (the card's parsed frontmatter) and the gated flag, and it
    still answers for gated models -- only the README body is withheld."""
    resp = requests.get(MODEL_API_URL.format(model_id=model_id), headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_model_card(model_id: str) -> tuple[str | None, int]:
    """(card text, HTTP status). None with 401/403 is a gated model, None
    with 404 is a model that has no card -- both are real, distinct
    outcomes the caller records rather than retries."""
    resp = requests.get(MODEL_CARD_URL.format(model_id=model_id), headers=_HEADERS, timeout=30)
    if resp.status_code in (401, 403, 404):
        return None, resp.status_code
    resp.raise_for_status()
    return resp.text[:MODEL_CARD_MAX_CHARS], resp.status_code


def declared_base_model(card_data: dict | None) -> str | None:
    value = (card_data or {}).get("base_model")
    if isinstance(value, list):
        value = value[0] if value else None
    return value if isinstance(value, str) else None


_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MARKUP_LINE_RE = re.compile(r"^\s*(#|\||---|\*\*\*|https?://)")

CARD_PROSE_CHARS = 800


def card_prose_paragraphs(card_text: str) -> list[str]:
    """Prose paragraphs of a model card, in order, with everything that is
    not a sentence about the model removed: frontmatter, fenced code (which
    is where usage and instruction-tuning examples live), HTML, images,
    badges, tables, headings, bare URLs. Markdown link text is kept."""
    body = _FRONTMATTER_RE.sub("", card_text, count=1)
    body = _CODE_BLOCK_RE.sub("", body)
    body = _MD_IMAGE_RE.sub("", body)
    body = _MD_LINK_RE.sub(r"\1", body)
    body = _HTML_TAG_RE.sub("", body)
    paragraphs = []
    for block in re.split(r"\n\s*\n", body):
        lines = [ln.strip() for ln in block.strip().splitlines()]
        prose = [ln for ln in lines if ln and not _MARKUP_LINE_RE.match(ln)]
        if prose:
            paragraphs.append(" ".join(prose))
    return paragraphs


def card_prose_head(card_text: str, max_chars: int = CARD_PROSE_CHARS) -> str:
    """The opening prose of a card, for classification. A card's first
    paragraphs say what the model is; what follows is training detail,
    usage examples and citations, and classifying on all of it tripped
    sector keywords from sample inputs (a LOAN AND SECURITY AGREEMENT used
    as an instruction-tuning example) and a modality keyword inside an
    unrelated longer word ("business division" -> "vision")."""
    out: list[str] = []
    total = 0
    for para in card_prose_paragraphs(card_text):
        out.append(para)
        total += len(para)
        if total >= max_chars:
            break
    return " ".join(out)[:max_chars]


def card_excerpt(card_text: str, max_chars: int = 300) -> str | None:
    """First substantial prose paragraph, for the app's use-case list.
    None if there isn't one, so the caller keeps its existing description."""
    for text in card_prose_paragraphs(card_text):
        if len(text) < 40:
            continue
        return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"
    return None


def is_quant_reupload(model: dict) -> bool:
    if _QUANT_ID_RE.search(model.get("id", "")):
        return True
    return any(tag.lower() in _QUANT_TAGS for tag in model.get("tags", []))


def _to_candidate(model: dict, matched_query: str) -> dict:
    model_id = model["id"]
    tags = model.get("tags", [])
    description = f"Hugging Face model ({model.get('pipeline_tag') or 'no pipeline_tag'})"
    sector, modality = classify_use_case(model_id, description, tags)
    return {
        "name": model_id,
        "parent_sector": sector,
        "modality": modality,
        "risk_tier": classify_risk_tier(model_id, description, tags),
        "description": description,
        "hf_model_id": model_id,
        "model_modality": derive_model_modality(model.get("pipeline_tag"), model.get("library_name"), tags),
        "matched_query": matched_query,
        "likes": model.get("likes", 0),
    }


def mine_hf_use_cases(
    queries: Iterable[str] = DEFAULT_QUERIES,
    tags: Iterable[tuple[str, int]] = DEFAULT_TAGS,
    authors: Iterable[str] = DEFAULT_AUTHORS,
    min_likes: int = 0,
) -> list[dict]:
    """Returns a deduped list of candidate use-case dicts ready for
    db.upsert_mined_use_case(), classified by usecase_classifier, from
    the three channels described in the module docstring. A model found
    by more than one channel is attributed to the first that saw it.

    min_likes applies to name search only and defaults to 0 (unlike
    github_usecases.py's min_stars=3) -- most real, on-topic finance
    models on HF have very few likes, and a name-search hit is on-topic
    by construction, so a popularity filter there removes real results
    rather than noise. The tag channel's per-tag downloads floor is the
    noise filter, applied where noise actually is.
    """
    seen_ids: set[str] = set()
    candidates: list[dict] = []
    per_channel: dict[str, int] = {}
    skipped_quant = 0

    def consider(models: list[dict], channel: str, min_downloads: int = 0) -> None:
        nonlocal skipped_quant
        added = 0
        for model in models:
            model_id = model.get("id")
            if not model_id or model_id in seen_ids:
                continue
            if model.get("downloads", 0) < min_downloads:
                continue
            if is_quant_reupload(model):
                skipped_quant += 1
                continue
            seen_ids.add(model_id)
            candidates.append(_to_candidate(model, channel))
            added += 1
        per_channel[channel] = added

    for query in queries:
        try:
            models = [m for m in search_models(query) if m.get("likes", 0) >= min_likes]
        except requests.RequestException:
            logger.exception("HF search failed for query: %s", query)
            continue
        consider(models, query)

    for tag, min_downloads in tags:
        try:
            models = _list_models({"filter": tag, "limit": 1000})
        except requests.RequestException:
            logger.exception("HF tag listing failed for tag: %s", tag)
            continue
        consider(models, f"tag:{tag}", min_downloads)

    for author in authors:
        try:
            models = _list_models({"author": author, "limit": 1000})
        except requests.RequestException:
            logger.exception("HF author listing failed for org: %s", author)
            continue
        consider(models, f"author:{author}")

    logger.info(
        "HF use-case miner: %d unique candidate model(s), %d with a derivable model_modality, "
        "%d quantisation re-uploads skipped; per channel: %s",
        len(candidates),
        sum(1 for c in candidates if c["model_modality"]),
        skipped_quant,
        per_channel,
    )
    return candidates
