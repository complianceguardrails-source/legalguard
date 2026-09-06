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

import { getThresholdsForSector } from "./guardrailThresholds";

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
${perRegulationChecks}` : ""}
allow if {
${allowBody}
}
`;

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
${
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
