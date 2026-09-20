// Systematic adversarial-input harness for compiled guardrail rules
// (real, runnable -- imports the actual buildGuardrailTemplate from
// ../lib/guardrailTemplate.js directly -- the same module the generation
// service serves, not a copy).
//
// For every compiled rule on a real use case, generates a battery of
// adversarial/boundary input payloads and runs the real `opa` binary
// against the real generated policy, classifying each result. This is
// deliberately scoped as "does our own generated policy hold up against
// malformed/adversarial INPUT", not "can we jailbreak an underlying
// model" -- LegalGuard doesn't wrap or call any live model, so that
// framing doesn't apply here; see docs/ARCHITECTURE.md.
//
// Two distinct outcome classes, reported separately (conflating them
// would overstate or understate the real finding):
//   - "approval-flag tamper": base checks + correct action_type present,
//     approval flag set to something other than literal boolean true.
//     Correct behavior is always allow=false; any allow=true here is a
//     real bug (the gate is bypassable by a malformed flag value).
//   - "action-type bypass": approval flag entirely absent, action_type
//     varied (case/whitespace/type) so it no longer exactly matches the
//     gated value. allow=true here is not automatically a bug in the
//     rule's own logic (Rego's exact-match `==` is working as designed)
//     -- it is a real, honestly-reportable design question: should an
//     unrecognized/malformed action_type fall back to only the baseline
//     checks (current, permissive-by-default design), or be denied
//     outright? Reported as its own category rather than silently
//     folded into "bugs" either way.
//
// Requires the real `opa` binary on PATH (https://www.openpolicyagent.org/).
//
// Usage: node adversarialHarness.mjs [output.json]

import { mkdirSync, writeFileSync, readFileSync, rmSync } from "fs";
import { dirname, join } from "path";
import { tmpdir } from "os";
import { execFileSync } from "child_process";

import { buildGuardrailTemplate } from "../lib/guardrailTemplate.js";

const OUT_FILE = process.argv[2] || "adversarial_results.json";
const WORKDIR = join(tmpdir(), "legalguard_adversarial_harness");
mkdirSync(WORKDIR, { recursive: true });

function writeFiles(outDir, files) {
  for (const [relPath, content] of Object.entries(files)) {
    const fullPath = join(outDir, relPath);
    mkdirSync(dirname(fullPath), { recursive: true });
    writeFileSync(fullPath, content);
  }
}

function opaEvalAllow(policyDir, pkg, input) {
  const inputPath = join(policyDir, "_adv_input.json");
  writeFileSync(inputPath, JSON.stringify(input));
  try {
    const out = execFileSync(
      "opa",
      ["eval", "--format=json", "--data", join(policyDir, "rules.rego"), "--input", inputPath, `data.legalguard.${pkg}.allow`],
      { encoding: "utf8" }
    );
    const parsed = JSON.parse(out);
    return parsed?.result?.[0]?.expressions?.[0]?.value === true;
  } catch {
    // opa eval exits non-zero when the query is undefined (no derived
    // value) -- that means allow was not derived true, i.e. denied.
    return false;
  }
}

// Real use cases spanning every compiled rule type, including one real
// LLM extraction (ingestion/llm_compiler.py's actual validated output
// against dungnotnull/niche-insurance-underwriting-automation-agent-skill's
// real README -- see conversation record / paper Section 3.5 for the
// live Anthropic API call this came from). To test against more use
// cases, fetch real rows from banking_use_cases (any with a non-null
// agent_operational_tools/system_interface_type/data_interception_state/
// model_modality/llm_compiled_requirement) and map them into this shape.
const useCases = [
  {
    name: "Lumiwealth/lumibot", parent_sector: "CIB", modality: "structured", risk_tier: "minimal_risk",
    agent_operational_tools: ["database-tool", "execution-tool"], system_interface_type: "rest-api", data_interception_state: "stateful-trace",
  },
  {
    name: "achang/fin_gpt2_one_nvda", parent_sector: "CIB", modality: "structured", risk_tier: "limited_risk",
    model_modality: "decoder-only",
  },
  {
    name: "dungnotnull/niche-insurance-underwriting-automation-agent-skill", parent_sector: "Insurance", modality: "structured", risk_tier: "high_risk",
    llm_compiled_requirement: {
      applies: true,
      requirement_id: "hard_gate_before_pricing",
      action_type: "insurance_pricing",
      approval_flag: "hard_gate_pass_or_refer",
      evidence_quote: "a HARD GATE (BLOCK / REFER / PASS) runs before pricing; uninsurable exposures are declined, never silently priced",
      rationale: "The README explicitly states pricing must not proceed until the HARD GATE evaluation completes and does not result in a BLOCK, making gate clearance a concrete precondition for the pricing action.",
    },
    // In production this is the use case's real llm_evidence_text column;
    // only the substring actually being validated against is needed here.
    llm_evidence_text: "...a HARD GATE (BLOCK / REFER / PASS) runs before pricing; uninsurable exposures are declined, never silently priced...",
  },
];

let results = [];

for (const uc of useCases) {
  const files = buildGuardrailTemplate(uc, []);
  const pkg = uc.name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const outDir = join(WORKDIR, pkg);
  writeFiles(outDir, files);
  const policyDir = join(outDir, "policies");

  // Parsed straight out of the generated Rego, not hand-copied from
  // source, so this harness stays correct if a use case's rule set changes.
  const rego = readFileSync(join(policyDir, "rules.rego"), "utf8");
  const reqMatches = [...rego.matchAll(/(\w+)_satisfied if \{\n\s*_normalized_action_type == "([^"]+)"\n\s*input\.(\w+) == true\n\}/g)];

  for (const [, requirementId, actionType, approvalFlag] of reqMatches) {
    const baseValid = { compliance_checks_passed: true, human_review_confirmed: true };

    const tamperCases = [
      ["string_true", "true"], ["string_True", "True"], ["int_1", 1], ["null", null],
      ["absent", undefined], ["empty_array", []], ["empty_object", {}],
      ["explicit_false", false], ["string_yes", "yes"],
    ];
    for (const [label, val] of tamperCases) {
      const input = { ...baseValid, action_type: actionType };
      if (val !== undefined) input[approvalFlag] = val;
      const allowed = opaEvalAllow(policyDir, pkg, input);
      results.push({ useCase: uc.name, requirementId, category: "approval_flag_tamper", variant: label, allowed, isBug: allowed === true });
    }

    const bypassCases = [
      ["uppercase", actionType.toUpperCase()], ["leading_space", " " + actionType],
      ["trailing_space", actionType + " "], ["zero_width_space", actionType + "​"],
      ["null_action_type", null], ["boolean_action_type", true],
      ["numeric_action_type", 1], ["substring_extra", actionType + "_extra"],
    ];
    for (const [label, val] of bypassCases) {
      const input = { ...baseValid, action_type: val };
      const allowed = opaEvalAllow(policyDir, pkg, input);
      results.push({ useCase: uc.name, requirementId, category: "action_type_bypass", variant: label, allowed, isBug: false });
    }
  }
}

const byCategory = {};
for (const r of results) {
  byCategory[r.category] = byCategory[r.category] || { total: 0, allowed: 0, bugs: 0 };
  byCategory[r.category].total++;
  if (r.allowed) byCategory[r.category].allowed++;
  if (r.isBug) byCategory[r.category].bugs++;
}

console.log("Total adversarial cases:", results.length);
console.log(JSON.stringify(byCategory, null, 2));

const bugs = results.filter((r) => r.isBug);
if (bugs.length > 0) {
  console.log("\nReal bugs found (approval_flag_tamper with allowed=true):");
  console.log(bugs);
}

writeFileSync(OUT_FILE, JSON.stringify(results, null, 2));
rmSync(WORKDIR, { recursive: true, force: true });
console.log(`\nWrote ${results.length} results to ${OUT_FILE}`);
