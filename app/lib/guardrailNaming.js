// Deterministic naming convention for guardrail repos, so the same use case
// always produces the same repo name regardless of who/what triggers
// creation (mobile app, ingestion engine, a future web dashboard).
//
// Pattern: guardrail-{sector-slug}-{usecase-slug}
// e.g. "Voice Agent: Mortgage Escalation Support" (Front Office)
//      -> guardrail-front-office-voice-agent-mortgage-escalation-support

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80); // GitHub repo names cap at 100 chars; leave room for the prefix
}

export function guardrailRepoName(useCase) {
  const sectorSlug = slugify(useCase.parent_sector || "general");
  const nameSlug = slugify(useCase.name);
  return `guardrail-${sectorSlug}-${nameSlug}`.slice(0, 100);
}

/** Branch name for one dispatch (new-repo init or a later bundle refresh).
 * Timestamped rather than a single deterministic name per use case: a
 * use-case-scoped guardrail repo gets updated repeatedly over its life as
 * regulations change, and reusing one branch name across dispatches would
 * try to fast-forward a fresh commit onto a branch ref still pointing at a
 * previous (already-merged) commit -- GitHub rejects that as a non-fast-
 * forward update. A new branch per dispatch sidesteps it entirely. */
export function guardrailBranchName(useCase) {
  return `legalguard/update-${slugify(useCase.name)}-${Date.now()}`;
}
