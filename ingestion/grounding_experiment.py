"""Controlled experiment: does verbatim-quote grounding actually reduce
fabricated compliance obligations, and how much of any effect comes from
*asking* for a citation versus *checking* it?

The production pipeline (llm_compiler.py) conflates two separable effects:

  1. PROMPT EFFECT -- requiring a quote changes what the model generates.
  2. VERIFICATION EFFECT -- the substring check rejects what it does generate.

Because production only ever reports post-rejection results, a run where the
check catches nothing is equally consistent with "this model does not fabricate
here" and "demanding a citation is what stopped it". Separating them needs
arms that differ in exactly one variable:

  ungrounded       (arm A)  -- no quote requested, caution paragraph KEPT
  ungrounded_weak  (arm A') -- no quote requested, caution paragraph removed
  grounded         (arm B)  -- production prompt, verdict RECORDED not enforced
  grounded+verify  (arm C)  -- derived from arm B by applying validate_extraction

Arm C is not a separate API call: it is arm B with the production rejection
applied, so the B-vs-C comparison carries no sampling noise at all. That is the
number the paper currently lacks -- what fraction of claimed obligations the
grounding check actually rejects.

Every record is written to JSONL append-only and the run is resumable, because
a few thousand billed calls should not be lost to one interrupted process.
Human annotation columns are left null here and joined in later; nothing in
this module judges whether an extraction is *correct*, only whether it is
grounded. Using an LLM to adjudicate LLM hallucination would be circular.

Usage:
    python ingestion/grounding_experiment.py build-manifest --limit 500 --out manifest.jsonl
    ANTHROPIC_API_KEY=... python ingestion/grounding_experiment.py run \\
        --manifest manifest.jsonl --out results.jsonl \\
        --models claude-sonnet-5 --arms ungrounded,grounded --samples 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import db
import llm_compiler
from sources.awesome_list_use_cases import fetch_readme_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.grounding_experiment")

# Matches production: the model sees at most this much, but validation runs
# against the FULL text, exactly as extract_compiled_requirement() does.
EVIDENCE_CHAR_LIMIT = 8000

EXTRACTION_FIELDS = ("requirement_id", "action_type", "approval_flag", "rationale")


def _anthropic_caller(prompt, model, api_key, temperature, max_tokens):
    response = llm_compiler.call_anthropic(
        prompt, api_key, model=model, temperature=temperature, max_tokens=max_tokens
    )
    usage = response.get("usage", {})
    return llm_compiler.text_of(response), usage.get("input_tokens"), usage.get("output_tokens")


# To add a provider, implement a caller with this signature and register its
# model-id prefix here. Only Anthropic is wired up because it is the only
# provider this project holds a key for; the cross-model comparison the write-up
# calls for needs at least one more entry.
MODEL_PROVIDERS = {"claude-": _anthropic_caller}


def _provider_for(model: str):
    for prefix, caller in MODEL_PROVIDERS.items():
        if model.startswith(prefix):
            return caller
    raise ValueError(
        f"no provider registered for model {model!r} -- add its prefix to MODEL_PROVIDERS"
    )


def owner_repo(github_reference_url: str) -> tuple[str, str] | None:
    parts = github_reference_url.rstrip("/").replace("https://github.com/", "").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def load_readme(repo: str, cache_dir: Path) -> str:
    """Cached on disk because GitHub's rate limit, not model cost, is the
    binding constraint: one README is reused across every arm, model and
    sample, and survives an interrupted run."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / (repo.replace("/", "__") + ".md")
    if cached.exists():
        return cached.read_text(encoding="utf-8")

    parsed = owner_repo(f"https://github.com/{repo}")
    if not parsed:
        raise ValueError(f"could not parse owner/repo from {repo!r}")
    text = fetch_readme_markdown(*parsed)
    cached.write_text(text, encoding="utf-8")
    return text


def run_one(
    *,
    entry: dict,
    evidence_full: str,
    arm: str,
    model: str,
    sample_idx: int,
    api_key: str,
    run_id: str,
    temperature: float | None,
) -> dict:
    template = llm_compiler.ARM_PROMPTS[arm]
    evidence_sent = evidence_full[:EVIDENCE_CHAR_LIMIT]
    prompt = template.format(name=entry["repo"], evidence_text=evidence_sent)

    record = {
        "run_id": run_id,
        "use_case_id": entry.get("use_case_id"),
        "repo": entry["repo"],
        "model_id": model,
        "arm": arm,
        "sample_idx": sample_idx,
        "temperature": temperature,
        "prompt_variant_sha256": llm_compiler.prompt_sha256(template),
        "evidence_sha256": db.sha256_of(evidence_full),
        "evidence_chars_full": len(evidence_full),
        "evidence_chars_sent": len(evidence_sent),
        "truncated": len(evidence_full) > EVIDENCE_CHAR_LIMIT,
        "control_class": entry.get("control_class", "organic"),
        "injected_sentence": entry.get("injected_sentence"),
    }
    # Set up front so every exit path -- including a parse failure -- emits the
    # identical column set; a ragged JSONL would break the annotation join.
    for column in (
        "human_obligation_present", "human_supports_claim", "human_strength_in_text",
        "claimed_strength", "strength_inflated", "human_span", "annotator_id", "adjudicated",
    ):
        record[column] = None

    started = time.monotonic()
    raw, input_tokens, output_tokens = _provider_for(model)(
        prompt, model, api_key, temperature, 1024
    )
    record["latency_ms"] = int((time.monotonic() - started) * 1000)
    record["input_tokens"] = input_tokens
    record["output_tokens"] = output_tokens
    record["raw_response"] = raw

    try:
        extraction = llm_compiler._parse_json_response(raw)
        record["parse_ok"] = True
        record["parse_error"] = None
    except json.JSONDecodeError as exc:
        record.update(
            parse_ok=False, parse_error=str(exc), applies=None,
            **{field: None for field in EXTRACTION_FIELDS},
            evidence_quote=None, slug_fields_valid=None,
            quote_exact_match=None, quote_normalized_match=None,
            quote_fuzzy_score=None, quote_longest_run_chars=None, rejection_class=None,
            # Null, not False: parse_ok already carries the failure, and a False
            # here would pool "unparseable" with "hallucinated quote" in the
            # catch-rate denominator.
            validate_verdict=None, validate_reason=None,
            arm_c_accepted=False,
        )
        return record

    applies = bool(extraction.get("applies"))
    record["applies"] = applies
    for field in EXTRACTION_FIELDS:
        record[field] = extraction.get(field)
    record["evidence_quote"] = extraction.get("evidence_quote")

    record["slug_fields_valid"] = all(
        isinstance(extraction.get(f), str) and llm_compiler._SLUG_RE.match(extraction[f])
        for f in ("requirement_id", "action_type", "approval_flag")
    ) if applies else None

    # Recorded, never enforced: this is the whole point of arm B. Left null for
    # ungrounded arms, where production validation is meaningless by
    # construction (their schema has no quote to check) -- recording False there
    # would read as a 100% failure rate to anyone aggregating across arms.
    if arm in llm_compiler.GROUNDED_ARMS:
        valid, reason = llm_compiler.validate_extraction(extraction, evidence_full)
    else:
        valid, reason = None, None
    record["validate_verdict"] = valid
    record["validate_reason"] = reason

    if applies and arm in llm_compiler.GROUNDED_ARMS:
        record.update(
            llm_compiler.quote_match_report(extraction.get("evidence_quote") or "", evidence_full)
        )
    else:
        record.update(
            quote_exact_match=None, quote_normalized_match=None,
            quote_fuzzy_score=None, quote_longest_run_chars=None, rejection_class=None,
        )

    record["arm_c_accepted"] = bool(arm in llm_compiler.GROUNDED_ARMS and valid)
    return record


def done_keys(out_path: Path) -> set[tuple]:
    if not out_path.exists():
        return set()
    keys = set()
    with out_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            keys.add((row["repo"], row["model_id"], row["arm"], row["sample_idx"]))
    return keys


def run_experiment(
    manifest_path: Path, out_path: Path, cache_dir: Path,
    models: list[str], arms: list[str], samples: int,
    temperature: float | None, api_key: str, run_id: str,
) -> None:
    entries = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    already = done_keys(out_path)
    logger.info("%d manifest entries, %d records already present", len(entries), len(already))

    written = fetch_failed = call_failed = 0
    with out_path.open("a", encoding="utf-8") as sink:
        for entry in entries:
            pending = [
                (model, arm, idx)
                for model in models for arm in arms for idx in range(samples)
                if (entry["repo"], model, arm, idx) not in already
            ]
            if not pending:
                continue

            try:
                evidence = load_readme(entry["repo"], cache_dir)
            except Exception:
                logger.exception("%s: README fetch failed, skipping", entry["repo"])
                fetch_failed += 1
                continue

            if entry.get("injected_sentence"):
                evidence = f"{evidence}\n\n{entry['injected_sentence']}\n"

            for model, arm, idx in pending:
                try:
                    record = run_one(
                        entry=entry, evidence_full=evidence, arm=arm, model=model,
                        sample_idx=idx, api_key=api_key, run_id=run_id, temperature=temperature,
                    )
                except Exception:
                    logger.exception("%s [%s/%s/%d]: call failed", entry["repo"], model, arm, idx)
                    call_failed += 1
                    continue

                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                written += 1

    logger.info(
        "Done: %d records written, %d README fetch failures, %d call failures",
        written, fetch_failed, call_failed,
    )


def build_manifest(limit: int, out_path: Path) -> None:
    """Fixed, reproducible sample written to a file rather than a live DB query,
    so a re-run scores the same repositories. Negative controls and distractor
    rows are added by hand afterwards -- deciding that a repository genuinely
    carries no obligation is a human judgment, not something to sample for."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, github_reference_url FROM banking_use_cases "
            "WHERE source = 'github_mined' AND github_reference_url IS NOT NULL "
            "ORDER BY random() LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()

    with out_path.open("w", encoding="utf-8") as sink:
        kept = 0
        for use_case_id, url in rows:
            parsed = owner_repo(url)
            if not parsed:
                continue
            sink.write(json.dumps({
                "use_case_id": str(use_case_id),
                "repo": f"{parsed[0]}/{parsed[1]}",
                "control_class": "organic",
                "injected_sentence": None,
            }) + "\n")
            kept += 1
    logger.info("Wrote %d manifest entries to %s", kept, out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-manifest")
    build.add_argument("--limit", type=int, default=500)
    build.add_argument("--out", type=Path, required=True)

    run = sub.add_parser("run")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--cache-dir", type=Path, default=Path(".readme_cache"))
    run.add_argument("--models", default="claude-sonnet-5")
    run.add_argument("--arms", default="ungrounded,grounded")
    run.add_argument("--samples", type=int, default=1)
    run.add_argument(
        "--temperature", type=float, default=None,
        help="omitted from the request when unset, matching production",
    )
    run.add_argument("--run-id", default=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    args = parser.parse_args()

    if args.command == "build-manifest":
        build_manifest(args.limit, args.out)
        return

    arms = [arm.strip() for arm in args.arms.split(",") if arm.strip()]
    unknown = [arm for arm in arms if arm not in llm_compiler.ARM_PROMPTS]
    if unknown:
        parser.error(f"unknown arm(s): {unknown}; choose from {sorted(llm_compiler.ARM_PROMPTS)}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        parser.error("ANTHROPIC_API_KEY not set -- this makes real, billed calls")

    run_experiment(
        manifest_path=args.manifest,
        out_path=args.out,
        cache_dir=args.cache_dir,
        models=[m.strip() for m in args.models.split(",") if m.strip()],
        arms=arms,
        samples=args.samples,
        temperature=args.temperature,
        api_key=api_key,
        run_id=args.run_id,
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
