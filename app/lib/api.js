// Thin client for the shared LegalGuard knowledge base, served over
// PostgREST (see docs/POSTGREST.md) so there is no custom backend server to
// run or pay for. Every function degrades to bundled mock data if
// EXPO_PUBLIC_API_URL isn't reachable, so the app is demoable standalone.

import {
  MOCK_USE_CASES,
  MOCK_REGULATIONS,
  MOCK_HORIZON,
  MOCK_PENDING_REGULATIONS,
  MOCK_COMPLIANCE_SUMMARY,
  MOCK_ADMIN_REFERENCE_GUARDRAILS,
} from "./mockData";

const API_URL = process.env.EXPO_PUBLIC_API_URL || ""; // e.g. https://legalguard-api.onrender.com

async function getJson(path, fallback) {
  if (!API_URL) return fallback;
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[api] falling back to mock data for ${path}:`, err.message);
    return fallback;
  }
}

export async function fetchUseCases() {
  // PostgREST auto-exposes tables as REST resources: GET /banking_use_cases
  return getJson("/banking_use_cases?select=*&order=parent_sector", MOCK_USE_CASES);
}

export async function fetchRegulations({ limit = 20 } = {}) {
  return getJson(
    `/specific_regulations?select=*&order=publication_date.desc&limit=${limit}`,
    MOCK_REGULATIONS
  );
}

/** The Radar dashboard's three tiles: Compliant / Action Req. / Breaches --
 * matches Base44's exact layout. Backed by the guardrail_compliance_summary
 * view (see database/schema.sql section 9), which does the GROUP BY server-side
 * since PostgREST can't aggregate on the fly. */
export async function fetchComplianceSummary() {
  const rows = await getJson("/guardrail_compliance_summary?select=*", MOCK_COMPLIANCE_SUMMARY);
  const byStatus = Object.fromEntries(rows.map((r) => [r.compliance_status, r.guardrail_count]));
  return {
    compliant: byStatus.compliant || 0,
    actionRequired: byStatus.action_required || 0,
    criticalBreach: byStatus.critical_breach || 0,
  };
}

export async function fetchHorizonForecasts() {
  return getJson(
    "/regulatory_horizon_forecast?select=*&order=probability_percentage.desc",
    MOCK_HORIZON
  );
}

/** Shared helper: real row count for a table via PostgREST's exact-count
 * Prefer header, without pulling the full rows down (limit=1, minimal
 * select) -- used for the Radar dashboard's top metric tiles. */
async function fetchExactCount(path, fallbackCount) {
  if (!API_URL) return fallbackCount;
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Accept: "application/json", Prefer: "count=exact" },
    });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    const range = res.headers.get("content-range"); // e.g. "0-0/461"
    return range ? parseInt(range.split("/")[1], 10) || 0 : 0;
  } catch (err) {
    console.warn(`[api] falling back to mock count for ${path}:`, err.message);
    return fallbackCount;
  }
}

/** Real count of every use case in the shared knowledge base -- the
 * Radar dashboard's "Finance Use Cases" tile. */
export async function fetchUseCaseCount() {
  return fetchExactCount("/banking_use_cases?select=id&limit=1", MOCK_USE_CASES.length);
}

/** Real count of every tracked regulation (every row -- individual
 * articles of the same act count separately, since there's no "parent
 * act" grouping in the schema yet) -- the Radar dashboard's "Regulatory
 * Acts" tile. */
export async function fetchRegulationCount() {
  return fetchExactCount("/specific_regulations?select=reg_id&limit=1", MOCK_REGULATIONS.length);
}

/**
 * Regulations still awaiting a guardrail dispatch decision, most recent
 * effective date first (undated ones last) -- feeds the Radar dashboard's
 * "Pending Regulatory Actions" section using the same RegulationCard the
 * Audit tab uses. Lists the full set, same as the Audit tab, rather than a
 * short preview. Returns { rows, total } so callers can still tell if a
 * `limit` override left anything out.
 */
export async function fetchPendingRegulations({ limit = 500 } = {}) {
  if (!API_URL) return { rows: MOCK_PENDING_REGULATIONS, total: MOCK_PENDING_REGULATIONS.length };
  const path = `/specific_regulations?select=*&dispatch_status=eq.Not Dispatched&order=effective_date.desc.nullslast&limit=${limit}`;
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Accept: "application/json", Prefer: "count=exact" },
    });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    const rows = await res.json();
    const range = res.headers.get("content-range"); // e.g. "0-9/138"
    const total = range ? parseInt(range.split("/")[1], 10) || rows.length : rows.length;
    return { rows, total };
  } catch (err) {
    console.warn(`[api] falling back to mock data for ${path}:`, err.message);
    return { rows: MOCK_PENDING_REGULATIONS, total: MOCK_PENDING_REGULATIONS.length };
  }
}

/**
 * Real, hand-built reference guardrail repos the admin has curated for
 * specific use cases (guardrail_packages rows where is_admin_reference =
 * true -- see database/migrations/003_add_admin_reference_guardrails.sql
 * and ingestion/register_admin_reference.py). Distinct from a per-user
 * generated repo, which is tracked only on-device (see repoMapping.js) and
 * never written to this shared table. Used by ImpactDiffScreen to suggest
 * "a reference implementation already exists" before a user generates
 * their own.
 */
export async function fetchAdminReferenceGuardrails() {
  return getJson(
    "/guardrail_packages?select=*&is_admin_reference=eq.true",
    MOCK_ADMIN_REFERENCE_GUARDRAILS
  );
}

/**
 * Self-service use-case submission: a user describes their own AI use case
 * and it's added to the shared knowledge base as source='user_submitted'.
 * Requires PostgREST's anon (or an authenticated) role to have INSERT on
 * banking_use_cases -- see docs/POSTGREST.md. Throws if EXPO_PUBLIC_API_URL
 * isn't set, since there's nowhere to persist a mock write to.
 */
export async function submitUseCase({ name, parentSector, modality, description, submittedByGithubUsername }) {
  if (!API_URL) {
    throw new Error("No backend configured (EXPO_PUBLIC_API_URL not set) -- can't persist a new use case yet.");
  }
  const res = await fetch(`${API_URL}/banking_use_cases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify({
      name,
      parent_sector: parentSector,
      modality,
      description,
      source: "user_submitted",
      submitted_by_github_username: submittedByGithubUsername || null,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Failed to submit use case (${res.status}): ${detail}`);
  }
  const [created] = await res.json();
  return created;
}
