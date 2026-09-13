"""
Real, general-purpose extraction step: reads a use case's actual evidence
text (its GitHub README, for now -- see fetch_evidence_text) and asks an
LLM to decide whether it implies a genuine, specific compliance-relevant
guardrail obligation, grounded in an exact quote from that real text.

This is deliberately split into two halves with very different trust
levels, matching this project's standing "never guess, verify what you can"
principle (see usecase_classifier.py's docstring for the same idea applied
to a different guess-vs-fact boundary):

  1. EXTRACTION (this module): the LLM reads arbitrary real evidence and
     decides *whether* a guardrail applies and *what* it should require --
     this is the genuinely general, arbitrary-evidence part. Its output is
     untrusted until validated.
  2. VALIDATION (validate_extraction, still this module): the extracted
     evidence_quote must be a real, verbatim substring of the text the LLM
     was given -- catches hallucinated justification outright, the same
     way assertRegulationProvenance() in guardrailTemplate.js refuses to
     emit a citation with no real source. Only a validated extraction is
     ever written to the database or reaches guardrailTemplate.js.

Deliberately NOT done here: letting the LLM freely author the Rego rule
text itself. The extracted {action_type, approval_flag} pair is rendered
through the exact same deterministic template already used for the five
hand-written COMPILED_REQUIREMENTS entries in guardrailTemplate.js, so an
LLM-derived rule gets the identical opa-test-verified rule *shape* as a
hand-written one -- only *which* action/flag pair applies is genuinely
LLM-derived from arbitrary text. Running arbitrary LLM-generated code
inside a policy-authorization engine is a real safety risk this project
is not taking on, even as a research prototype; constraining the output
schema is how that risk is avoided while still doing real, general
extraction from evidence no fixed keyword/field list could cover.
"""
from __future__ import annotations

import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")

EXTRACTION_PROMPT = """You are reviewing the real README of an open-source repository that was mined as a candidate financial-AI use case, to decide whether its own text implies a specific, concrete compliance-relevant obligation that should be enforced before a matching action is allowed to proceed.

Repository: {name}

--- README (verbatim, real text) ---
{evidence_text}
--- end README ---

Only extract a requirement if the README's OWN WORDS describe something concrete and specific enough to name an action type and an approval condition -- not a generic aspiration ("we care about compliance") and not something you infer from the repository's general subject matter alone. You must be able to quote the exact real sentence or phrase that justifies your answer.

Respond with ONLY a single JSON object, no other text, matching exactly one of these two shapes:

If no such concrete, specific obligation is stated in the text:
{{"applies": false}}

If one is:
{{
  "applies": true,
  "requirement_id": "<snake_case identifier, e.g. sar_filing>",
  "action_type": "<snake_case action name this gates, e.g. suspicious_activity_report>",
  "approval_flag": "<snake_case input flag name required before that action, e.g. compliance_officer_signed_off>",
  "evidence_quote": "<the EXACT literal substring from the README above that justifies this -- must be copyable verbatim from the text, not paraphrased>",
  "rationale": "<one sentence: why this quote implies this specific requirement>"
}}
"""


class ExtractionError(Exception):
    pass


def _call_anthropic(prompt: str, api_key: str) -> str:
    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def _parse_json_response(raw_text: str) -> dict:
    # Models sometimes wrap JSON in a code fence despite instructions --
    # strip that defensively rather than fail the whole extraction on it.
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def validate_extraction(extraction: dict, evidence_text: str) -> tuple[bool, str]:
    """Returns (is_valid, reason). A validated extraction is the only kind
    ever persisted or compiled into a guardrail -- this is the boundary
    between "the LLM said so" and "we verified it's grounded in real text"."""
    if not extraction.get("applies"):
        return False, "extraction reported no applicable requirement"

    for field in ("requirement_id", "action_type", "approval_flag", "evidence_quote", "rationale"):
        if not extraction.get(field):
            return False, f"missing required field: {field}"

    for field in ("requirement_id", "action_type", "approval_flag"):
        if not _SLUG_RE.match(extraction[field]):
            return False, f"{field} is not a valid snake_case identifier: {extraction[field]!r}"

    quote = extraction["evidence_quote"]
    if quote not in evidence_text:
        return False, "evidence_quote is not a verbatim substring of the real evidence text (likely hallucinated)"

    return True, "ok"


def extract_compiled_requirement(name: str, evidence_text: str, api_key: str | None = None) -> dict | None:
    """Real end-to-end call: sends the use case's actual evidence text to
    the Anthropic Messages API, parses and validates the response. Returns
    a validated extraction dict, or None if nothing applies or the
    response failed validation (logged either way, never silently
    swallowed)."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ExtractionError("ANTHROPIC_API_KEY not set -- cannot make a real extraction call")

    prompt = EXTRACTION_PROMPT.format(name=name, evidence_text=evidence_text[:8000])
    raw = _call_anthropic(prompt, api_key)

    try:
        extraction = _parse_json_response(raw)
    except json.JSONDecodeError:
        logger.warning("%s: extraction response was not valid JSON: %r", name, raw[:500])
        return None

    if not extraction.get("applies"):
        logger.info("%s: no applicable requirement extracted", name)
        return None

    valid, reason = validate_extraction(extraction, evidence_text)
    if not valid:
        logger.warning("%s: extraction REJECTED (%s): %r", name, reason, extraction)
        return None

    logger.info("%s: extraction validated -- %s", name, extraction["requirement_id"])
    return extraction
