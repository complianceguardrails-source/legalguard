// Client for the guardrail generation service (service/ at the repo root).
//
// Generation used to run inside this bundle (lib/guardrailTemplate.js).
// Moving it server-side buys three things the app cannot provide itself:
// the real opa binary verifies every package before we ever see it, so a
// policy that fails its own generated tests never reaches a user; a rule
// change ships without an App Store release; and the generation logic no
// longer lives inside a client binary. The GitHub token stays on this
// device (lib/auth.js, Keychain) -- the service holds no credentials and
// the push still happens from here.
//
// Unlike lib/api.js there is no mock fallback: a generated policy that was
// never verified is exactly what this service exists to prevent, so with
// no service configured the screen shows that plainly instead.

const GENERATOR_URL = process.env.EXPO_PUBLIC_GENERATOR_URL || ""; // e.g. https://legalguard-generator.onrender.com

export function isGeneratorConfigured() {
  return !!GENERATOR_URL;
}

/**
 * @param {object} useCase
 * @param {Array<object>} regulations - the use case's matched regulations
 * @returns {Promise<{files: Record<string,string>, thresholds: Array<object>, verification: object}>}
 */
export async function fetchGuardrailPackage(useCase, regulations) {
  if (!GENERATOR_URL) {
    throw new Error("Generation service not configured (EXPO_PUBLIC_GENERATOR_URL).");
  }
  let res;
  try {
    res = await fetch(`${GENERATOR_URL}/v1/guardrails/generate`, {
      method: "POST",
      headers: { "content-type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ useCase, regulations }),
    });
  } catch (err) {
    // fetch rejects only on network failure; "Failed to fetch" tells a
    // user nothing about what to do.
    throw new Error(`Could not reach the generation service at ${GENERATOR_URL} (${err.message}).`);
  }
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    // fall through with a status-only message
  }
  if (!res.ok) {
    const detail = payload?.error ? `: ${payload.error}` : "";
    throw new Error(`Generation service returned ${res.status}${detail}`);
  }
  if (!payload?.files || !payload?.verification) {
    throw new Error("Generation service returned an unexpected response.");
  }
  return payload;
}
