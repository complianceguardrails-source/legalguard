// Generates the standard file layout for a brand-new guardrail repository,
// matching the structure from the original design session:
//
//   guardrail-<name>/
//   ├── README.md
//   ├── REGULATORY_PROVENANCE.md
//   ├── metadata.json
//   ├── policies/
//   │   ├── rules.rego
//   │   ├── rules_test.rego
//   │   └── thresholds.json
//   ├── middleware/
//   │   └── safety_hook.py
//   └── .github/workflows/compliance_eval.yml
//
// Every generated policy is a deliberately conservative default-deny stub --
// see docs/ARCHITECTURE.md's "what's real vs a stub" table. It is meant to
// give a compliance engineer a correct, runnable starting skeleton to edit,
// not a finished, mergeable policy.

import { getThresholdsForSector } from "./guardrailThresholds.js";

// The real, narrow compilation step this system performs: each entry below
// is gated on a genuine derived signal (manifest-scanned dependencies or
// the computed data_interception_state -- see ingestion/sources and
// db.py::derive_data_interception_state), never guessed. When a use case's
// evidence matches `appliesTo`, its `requirementId` becomes an additional,
// independent condition `allow` must satisfy -- combining naturally when a
// use case matches more than one, since each is just one more ANDed check,
// not a branch. Nothing here is emitted unless the underlying evidence is
// real; a use case matching none of these gets exactly the same template
// as before this compiler existed.
const COMPILED_REQUIREMENTS = [
  {
    requirementId: "execution",
    appliesTo: (uc) => Array.isArray(uc.agent_operational_tools) && uc.agent_operational_tools.includes("execution-tool"),
    actionType: "trade_execution",
    approvalFlag: "execution_approved_by_human",
    evidenceLabel: "agent_operational_tools:execution-tool",
    comment:
      "A real dependency on trade-execution tooling (e.g. ccxt, alpaca-trade-api,\n" +
      "# ib_insync) was detected for this use case, so a \"trade_execution\" action\n" +
      "# additionally requires explicit human approval.",
  },
  {
    requirementId: "database",
    appliesTo: (uc) => Array.isArray(uc.agent_operational_tools) && uc.agent_operational_tools.includes("database-tool"),
    actionType: "database_query",
    approvalFlag: "data_access_reviewed",
    evidenceLabel: "agent_operational_tools:database-tool",
    comment:
      "A real dependency on direct database access (e.g. sqlalchemy, psycopg2,\n" +
      "# redis) was detected for this use case, so a \"database_query\" action\n" +
      "# additionally requires confirmation the access was reviewed for\n" +
      "# PII/data-governance handling.",
  },
  {
    requirementId: "rest_api",
    appliesTo: (uc) => uc.system_interface_type === "rest-api",
    actionType: "api_request",
    approvalFlag: "caller_authenticated",
    evidenceLabel: "system_interface_type:rest-api",
    comment:
      "A real REST API dependency (e.g. FastAPI, Flask) was detected for this\n" +
      "# use case, so an \"api_request\" action additionally requires the caller\n" +
      "# to be authenticated.",
  },
  {
    requirementId: "stateful_session",
    appliesTo: (uc) => uc.data_interception_state === "stateful-trace",
    actionType: "session_continue",
    approvalFlag: "session_retention_enforced",
    evidenceLabel: "data_interception_state:stateful-trace",
    comment:
      "This use case accumulates conversational/session state (voice, multi-agent,\n" +
      "# or RAG-document interaction) rather than stateless single-shot payloads,\n" +
      "# so continuing a session additionally requires confirmation that a\n" +
      "# data-retention policy is enforced.",
  },
  {
    requirementId: "generative_disclosure",
    appliesTo: (uc) => uc.model_modality === "decoder-only",
    actionType: "generated_content_delivery",
    approvalFlag: "ai_disclosure_shown",
    evidenceLabel: "model_modality:decoder-only",
    comment:
      "This use case's declared Hugging Face pipeline_tag/library_name identified\n" +
      "# it as a real decoder-only (text-generation-capable) model, so delivering\n" +
      "# generated content additionally requires confirmation that an AI-disclosure\n" +
      "# notice was shown to the recipient -- see the Front Office sector's own\n" +
      "# ai_disclosure_required threshold above, and EU AI Act Article 50.",
  },
];

function regoPackageName(useCaseName) {
  return useCaseName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

/** Stable, valid Rego identifier for a regulation's per-clause check rule --
 * derived from clause_identifier when it's a usable slug, falling back to a
 * positional name so two regulations never collide on the same identifier. */
function regCheckName(r, i) {
  const slug = (r.clause_identifier || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug ? `check_${slug}` : `check_reg_${i}`;
}

/**
 * Refuses to generate a guardrail repo that cites a regulation which isn't
 * fully, verifiably sourced -- every regulation embedded into
 * REGULATORY_PROVENANCE.md/metadata.json/rules.rego must carry a real
 * source_url, clause_identifier, and jurisdiction, since those are exactly
 * the fields a reader relies on to go check the actual legal text. This is
 * a hard runtime guarantee, not just a coding convention: it makes it
 * structurally impossible for a caller bug (or, in the future, an
 * LLM-assisted tagger -- see tagger.py::tag_regulation_llm) to push a
 * fabricated or incomplete citation into a real GitHub repo.
 */
function assertRegulationProvenance(regulations) {
  const missing = regulations.filter((r) => !r.source_url || !r.clause_identifier || !r.jurisdiction);
  if (missing.length > 0) {
    const bad = missing.map((r) => r.official_title || r.reg_id || "(unidentified regulation)").join(", ");
    throw new Error(
      `buildGuardrailTemplate: refusing to generate a guardrail citing ${missing.length} regulation(s) missing ` +
        `source_url/clause_identifier/jurisdiction -- can't verifiably source: ${bad}`
    );
  }
}

const SLUG_RE = /^[a-z][a-z0-9_]*$/;

const PUNCT_NORMALIZE = [
  [/[‘’]/g, "'"],
  [/[“”]/g, '"'],
  [/[–—]/g, "-"],
  [/…/g, "..."],
  [/ /g, " "],
];

/**
 * Must stay behaviourally identical to ingestion/llm_compiler.py's
 * normalize_for_match(). The two grounding checks are deliberately
 * independent implementations either side of a process boundary, so they can
 * catch each other's bugs -- but they have to agree on what "grounded" means,
 * or an extraction accepted upstream gets silently dropped here.
 */
function normalizeForMatch(text) {
  let out = text;
  for (const [pattern, replacement] of PUNCT_NORMALIZE) out = out.replace(pattern, replacement);
  return out.replace(/\s+/g, " ").trim().toLowerCase();
}

/**
 * Converts a validated LLM extraction (ingestion/llm_compiler.py --
 * real evidence, arbitrary text, not a fixed keyword/field list) into the
 * same COMPILED_REQUIREMENTS shape as the five hand-written entries above,
 * so it compiles through the identical, already opa-test-verified Rego
 * template rather than letting an LLM author policy-engine code directly.
 *
 * Re-validates independently of ingestion/llm_compiler.py's own
 * validate_extraction() -- this function must never trust that upstream
 * check ran, matching assertRegulationProvenance()'s same principle just
 * above: a caller bug (or a future different extraction path) must not be
 * able to push an ungrounded requirement into a real generated policy.
 * Returns null (never throws) for an invalid extraction, since a missing
 * or bad LLM extraction should silently fall back to the deterministic
 * template, not break guardrail generation for the whole use case.
 */
export function llmRequirementFromExtraction(extraction, evidenceText) {
  if (!extraction || typeof extraction !== "object") return null;
  const { requirement_id, action_type, approval_flag, evidence_quote } = extraction;
  if (![requirement_id, action_type, approval_flag, evidence_quote].every((v) => typeof v === "string" && v.length > 0)) {
    return null;
  }
  if (![requirement_id, action_type, approval_flag].every((v) => SLUG_RE.test(v))) return null;
  if (typeof evidenceText !== "string") return null;
  // Exact first, then formatting-insensitive: a faithful quote reproduced from
  // line-wrapped markdown (newline as space, ' as ') would otherwise be
  // rejected as hallucinated. The empty-after-normalization guard matters --
  // "".includes("") is true, so a whitespace-only quote would pass everything
  // above and ground a requirement in nothing at all.
  const normalizedQuote = normalizeForMatch(evidence_quote);
  if (!normalizedQuote) return null;
  if (
    !evidenceText.includes(evidence_quote) &&
    !normalizeForMatch(evidenceText).includes(normalizedQuote)
  ) {
    return null;
  }

  return {
    requirementId: requirement_id,
    appliesTo: () => true, // already gated by the caller passing this extraction in at all
    actionType: action_type,
    approvalFlag: approval_flag,
    evidenceLabel: `llm_extraction:${requirement_id}`,
    comment:
      `A real compliance-relevant obligation was extracted from this use case's own\n` +
      `# README by an LLM, grounded in a verbatim quote (not guessed): "${evidence_quote.slice(0, 140)}${evidence_quote.length > 140 ? "..." : ""}"`,
  };
}

/**
 * @param {object} useCase - { name, parent_sector, modality, risk_tier }
 * @param {Array<object>} regulations - [{ jurisdiction, issuing_body, clause_identifier, official_title, source_url, mandate_summary }]
 * @returns {Record<string,string>} map of repo-relative path -> file content
 */
export function buildGuardrailTemplate(useCase, regulations) {
  assertRegulationProvenance(regulations);
  const pkg = regoPackageName(useCase.name);
  const files = {};
  const thresholds = getThresholdsForSector(useCase.parent_sector);

  // Real (non-null) thresholds become active Rego constants -- either a
  // genuinely fixed regulatory figure (e.g. the $10,000 CTR threshold) or a
  // structural "this check is required" boolean. Null ones stay a commented
  // TODO rather than an invented number: see guardrailThresholds.js's
  // docstring for why a fake-looking default is worse than an honest gap.
  const thresholdLines = thresholds
    .map((t) =>
      t.value === null
        ? `# ${t.key} -- TODO: ${t.citation} (not enforced until set)`
        : `${t.key} := ${JSON.stringify(t.value)}  # ${t.citation}`
    )
    .join("\n");

  // Rego v1 syntax (default since OPA v1.0, released 2024) requires an
  // explicit `if` before every rule body -- `allow { ... }` is a parse
  // error under v1, it must be `allow if { ... }`. The workflow below
  // downloads OPA's "latest" binary, which defaults to v1, so these
  // templates target v1 rather than pinning an old OPA version.
  // Each bundled regulation gets its own named stub rule so a reviewer can
  // see, at a glance, exactly which regulation each check maps to instead
  // of one opaque combined condition -- net enforced behavior is unchanged
  // (every rule still just requires the same two generic input flags; see
  // REGULATORY_PROVENANCE.md for what each one actually requires), this is
  // purely a structural/readability change. Falls back to today's single
  // generic block when nothing is bundled, so `allow` is never emitted as
  // an empty (always-true) conjunction.
  const perRegulationChecks =
    regulations.length > 0
      ? regulations
          .map(
            (r, i) => `
# ${r.official_title} (${r.jurisdiction})
${regCheckName(r, i)} if {
    input.compliance_checks_passed == true
    input.human_review_confirmed == true
}
`
          )
          .join("")
      : "";
  const allowBody =
    regulations.length > 0
      ? regulations.map((r, i) => `    ${regCheckName(r, i)}`).join("\n")
      : `    input.compliance_checks_passed == true
    input.human_review_confirmed == true`;

  // Which compiled requirements actually apply to this use case, based on
  // its real derived signals -- never more than what the evidence supports.
  // A validated LLM extraction (useCase.llm_compiled_requirement /
  // llm_evidence_text, from ingestion/llm_compiler.py) is appended the same
  // way, re-validated here rather than trusted -- see
  // llmRequirementFromExtraction()'s own docstring for why.
  const llmRequirement = useCase.llm_compiled_requirement
    ? llmRequirementFromExtraction(useCase.llm_compiled_requirement, useCase.llm_evidence_text)
    : null;
  const applicableRequirements = [
    ...COMPILED_REQUIREMENTS.filter((req) => req.appliesTo(useCase)),
    ...(llmRequirement ? [llmRequirement] : []),
  ];

  // Shared once per package, not per requirement: a systematic adversarial
  // harness found that comparing input.action_type with plain "==" made
  // EVERY compiled rule trivially bypassable by any caller sending a
  // case-flipped, whitespace-padded, or zero-width-space-suffixed variant
  // of the expected action type -- 48/48 such variants incorrectly reached
  // allow=true across every rule and use case tested. Normalizing before
  // comparison (lowercase, trimmed, invisible Unicode formatting
  // characters stripped) closes that: a non-string input.action_type
  // (absent, null, boolean, numeric) still makes this whole expression
  // undefined, which "not <equality>" against it still correctly treats
  // as "not this action type" -- the same safe degradation as before.
  const actionTypeNormalization =
    applicableRequirements.length > 0
      ? `
# Normalized once, referenced by every compiled rule below -- see the
# adversarial-harness finding in the comment above this block.
_normalized_action_type := regex.replace(lower(trim_space(input.action_type)), "[\\u200b\\u200c\\u200d\\ufeff]", "")
`
      : "";

  const compiledRequirementRules = applicableRequirements
    .map(
      (req) => `
# --- ${req.requirementId} guardrail (compiled from ${req.evidenceLabel}) ---
# ${req.comment}
${req.requirementId}_satisfied if {
    # "not ... ==" rather than "!=": when input.action_type is absent
    # entirely (the common case -- most inputs don't name an action type
    # at all), "!=" is undefined in Rego, not true, which would wrongly
    # make this requirement (and so \`allow\`) fail for every ordinary
    # input. "not <equality>" correctly treats "absent" the same as "not
    # this action type" -- found by a real opa test failure, not by
    # inspection.
    not _normalized_action_type == "${req.actionType}"
}

${req.requirementId}_satisfied if {
    _normalized_action_type == "${req.actionType}"
    input.${req.approvalFlag} == true
}
`
    )
    .join("");

  // Each applicable requirement is one more ANDed condition on `allow`, not
  // a branch -- so a use case matching several combines them naturally
  // (e.g. a trading agent that also exposes a REST API needs both
  // execution approval AND caller authentication), without the 2^n blowup
  // a per-signal allow-block split would cause.
  const allowRules = `
allow if {
${allowBody}${applicableRequirements.map((req) => `\n    ${req.requirementId}_satisfied`).join("")}
}
`;

  files["policies/rules.rego"] = `package legalguard.${pkg}

# Guardrail for: ${useCase.name}
# Sector: ${useCase.parent_sector} | Modality: ${useCase.modality} | Risk tier: ${useCase.risk_tier || "unclassified"}
#
# This is a default-deny stub generated by LegalGuard. Fill in the real
# conditions for each regulatory mandate listed in REGULATORY_PROVENANCE.md
# before treating this as enforceable -- see that file for what each clause
# actually requires.

# --- Sector compliance thresholds (see policies/thresholds.json for full citations) ---
${thresholdLines}

# None of the thresholds above are wired into \`allow\` yet -- LegalGuard
# doesn't know this system's actual input schema, so it won't guess field
# names for you. Reference them (e.g. \`input.transaction_amount_usd >=
# ctr_filing_threshold_usd\`) once you know what your pipeline actually sends.

default allow := false
${perRegulationChecks ? `
# --- Per-regulation checks (stubs) --------------------------------------
# One named rule per bundled regulation below, so a reviewer sees exactly
# which regulation each check maps to. Every rule here is still a
# structural placeholder -- it currently just requires the same two
# generic input flags as before. Replace each body with the regulation's
# real condition once your pipeline's input schema is known.
${perRegulationChecks}` : ""}${actionTypeNormalization}${compiledRequirementRules}${allowRules}`;

  files["policies/rules_test.rego"] = `package legalguard.${pkg}

test_allow_when_all_checks_pass if {
    allow with input as {"compliance_checks_passed": true, "human_review_confirmed": true}
}

test_deny_when_checks_missing if {
    not allow with input as {"compliance_checks_passed": false, "human_review_confirmed": true}
}

test_deny_when_review_missing if {
    not allow with input as {"compliance_checks_passed": true, "human_review_confirmed": false}
}
${applicableRequirements
  .map(
    (req) => `
# --- ${req.requirementId} guardrail coverage ---------------------------------
# Real test cases for the compiled ${req.requirementId} rule above, not just
# the generic stub checks.
test_${req.requirementId}_denied_without_approval if {
    not allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "${req.actionType}",
    }
}

test_${req.requirementId}_allowed_with_approval if {
    allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "${req.actionType}",
        "${req.approvalFlag}": true,
    }
}

test_${req.requirementId}_unaffected_by_unrelated_action if {
    allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "unrelated_action",
    }
}

# --- ${req.requirementId} malformed-input robustness --------------------------
# Real cases beyond the happy path / missing-flag path above -- not an
# adversarial or jailbreak evaluation (Section 5's "No evaluation harness"
# limitation stands), just confirming the compiled rule degrades safely
# (denies) rather than erroring or, worse, silently allowing, when the
# input is malformed rather than merely incomplete.
test_${req.requirementId}_denied_when_approval_flag_wrong_type if {
    not allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "${req.actionType}",
        "${req.approvalFlag}": "true",
    }
}

test_${req.requirementId}_denied_when_approval_flag_null if {
    not allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "${req.actionType}",
        "${req.approvalFlag}": null,
    }
}

test_${req.requirementId}_unaffected_by_unexpected_extra_field if {
    allow with input as {
        "compliance_checks_passed": true,
        "human_review_confirmed": true,
        "action_type": "${req.actionType}",
        "${req.approvalFlag}": true,
        "unexpected_extra_field": {"nested": ["junk", 1, false]},
    }
}
`
  )
  .join("")}${
  regulations.length > 0
    ? `
# --- Per-regulation stub coverage -----------------------------------------
# One pass/fail pair per bundled regulation, so \`opa test\` output shows
# which specific regulation's stub check is being exercised rather than
# only the combined \`allow\` result.
${regulations
  .map(
    (r, i) => `
test_${regCheckName(r, i)}_passes_when_checks_confirmed if {
    ${regCheckName(r, i)} with input as {"compliance_checks_passed": true, "human_review_confirmed": true}
}

test_${regCheckName(r, i)}_fails_when_checks_missing if {
    not ${regCheckName(r, i)} with input as {"compliance_checks_passed": false, "human_review_confirmed": false}
}
`
  )
  .join("")}`
    : ""
}`;

  files["policies/thresholds.json"] = JSON.stringify(
    {
      note: "Compliance thresholds referenced by name in policies/rules.rego. `value: null` means there's no single correct figure to default to -- see `citation` for why, and set it from your own policy before enforcing.",
      thresholds: Object.fromEntries(thresholds.map((t) => [t.key, { value: t.value, citation: t.citation }])),
    },
    null,
    2
  );

  files["middleware/safety_hook.py"] = `"""
Pluggable safety hook for ${useCase.name}.

Wraps a model/pipeline call and enforces the compiled OPA policy in
policies/rules.rego before letting output through. Requires the \`opa\`
CLI on PATH (https://www.openpolicyagent.org/docs/latest/#running-opa) --
this wrapper shells out to \`opa eval\` rather than reimplementing Rego
evaluation in Python, so the policy file stays the single source of truth.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

POLICY_PATH = Path(__file__).parent.parent / "policies" / "rules.rego"
QUERY = "data.legalguard.${pkg}.allow"


class ComplianceBreach(Exception):
    """Raised when the OPA policy denies the given input."""


def check_compliance(input_payload: dict) -> bool:
    """Returns True if \`input_payload\` satisfies the compiled guardrail.

    Raises ComplianceBreach (not a bare bool) when it doesn't, so calling
    code can't accidentally ignore a False return value.
    """
    result = subprocess.run(
        ["opa", "eval", "--format=json", "--data", str(POLICY_PATH), "--stdin-input", QUERY],
        input=json.dumps(input_payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"opa eval failed: {result.stderr.strip()}")

    parsed = json.loads(result.stdout)
    allowed = bool(parsed["result"][0]["expressions"][0]["value"])
    if not allowed:
        raise ComplianceBreach(f"Denied by ${pkg} guardrail for input: {input_payload}")
    return True


def guarded(fn):
    """Decorator: run check_compliance(kwargs) before calling fn(**kwargs)."""

    def wrapper(*args, **kwargs):
        check_compliance(kwargs)
        return fn(*args, **kwargs)

    return wrapper
`;

  files["metadata.json"] = JSON.stringify(
    {
      guardrail_package_metadata: {
        name: `guardrail-${pkg.replace(/_/g, "-")}`,
        use_case: useCase.name,
        sector: useCase.parent_sector,
        modality: useCase.modality,
        risk_tier: useCase.risk_tier || "unclassified",
        active_semver: "v0.1.0",
        framework: "open_policy_agent",
        // Which policy rules, if any, were compiled from a real derived
        // signal on this use case rather than the generic template --
        // see docs/ARCHITECTURE.md's compiler-gap note. Empty for every
        // use case without that signal, so this stays an honest audit
        // trail rather than a claim made unconditionally.
        compiled_from_signals: applicableRequirements.map((req) => req.evidenceLabel),
        indexed_global_regulatory_dependencies: regulations.map((r) => ({
          legal_reference_id: `${r.jurisdiction}-${r.issuing_body}-${r.clause_identifier}`,
          authority: r.issuing_body,
          jurisdiction: r.jurisdiction,
          source_url: r.source_url,
          mandate: r.mandate_summary || r.official_title,
        })),
      },
    },
    null,
    2
  );

  files["REGULATORY_PROVENANCE.md"] = `# Regulatory Provenance

![Regulations](https://img.shields.io/badge/regulations-${regulations.length}-blue)
![Framework](https://img.shields.io/badge/framework-open%20policy%20agent-informational)

This guardrail was initialized by LegalGuard in response to the following
regulation(s). Every entry here should have a matching row in the shared
LegalGuard knowledge base's \`guardrail_regulatory_mapping\` table -- this
file is the human-readable mirror of that audit trail, checked directly
into the repo so it travels with the code.

${regulations
  .map(
    (r) => `> [!IMPORTANT]
> **${r.official_title}** (${r.jurisdiction})
>
> - **Issuing body:** ${r.issuing_body}
> - **Clause:** \`${r.clause_identifier}\`
> - **Source:** ${r.source_url}
> - **Mandate:** ${r.mandate_summary || "(summary not yet captured -- see source)"}
`
  )
  .join("\n")}

> [!WARNING]
> This guardrail was auto-merged to \`main\` on generation -- it still needs
> human legal/compliance review before you rely on it. LegalGuard drafts a
> conservative default-deny starting point; it does not certify compliance.
> Review \`policies/rules.rego\` against the mandate(s) above and open a
> follow-up PR to tighten it before treating this as enforceable.
`;

  const useCaseLabel = useCase.github_reference_url
    ? `[${useCase.name}](${useCase.github_reference_url})`
    : useCase.name;

  files["README.md"] = `# guardrail-${pkg.replace(/_/g, "-")}

![Guardrail Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Risk Tier](https://img.shields.io/badge/risk_tier-${encodeURIComponent(useCase.risk_tier || "unclassified")}-orange)
![Regulations Bundled](https://img.shields.io/badge/regulations-${regulations.length}-informational)

Auto-generated guardrail repository for **${useCaseLabel}** (${useCase.parent_sector}, ${useCase.modality}).

- \`policies/rules.rego\` -- the Open Policy Agent policy. Start here.
- \`policies/thresholds.json\` -- the sector's compliance thresholds, each with a citation for where the figure comes from (or why there isn't a single correct one).
- \`policies/rules_test.rego\` -- run with \`opa test policies/\`.
- \`middleware/safety_hook.py\` -- Python wrapper that shells out to \`opa eval\` to enforce the policy at inference time.
- \`REGULATORY_PROVENANCE.md\` -- which regulation(s) motivated this repo, and what they require.
- \`metadata.json\` -- machine-readable version of the same provenance, for the LegalGuard app to read back.

> [!WARNING]
> This repo's initial scaffold was auto-merged to \`main\` rather than left
> open for review. It still needs human legal/compliance review -- see
> \`REGULATORY_PROVENANCE.md\` for what each bundled regulation requires, and
> treat \`policies/rules.rego\` as a starting skeleton, not a certified policy.
`;

  files[".github/workflows/compliance_eval.yml"] = `name: Guardrail Policy Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  opa-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install OPA
        run: |
          curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static
          chmod +x opa
          sudo mv opa /usr/local/bin/opa
          # Pin to a specific released version instead of "latest" once this
          # repo is doing anything beyond prototyping -- "latest" can change
          # underneath you between CI runs.

      - name: Run policy tests
        run: opa test policies/ -v
`;

  return files;
}
