import { buildGuardrailTemplate } from "./guardrailTemplate.js";
import { getThresholdsForSector } from "./guardrailThresholds.js";
import { opaVersion, verifyPackage } from "./opa.js";

export class InvalidRequestError extends Error {}

function validate(body) {
  const useCase = body?.useCase;
  const regulations = body?.regulations;
  if (!useCase || typeof useCase !== "object" || Array.isArray(useCase)) {
    throw new InvalidRequestError("useCase must be an object");
  }
  if (typeof useCase.name !== "string" || !useCase.name.trim()) {
    throw new InvalidRequestError("useCase.name must be a non-empty string");
  }
  if (!Array.isArray(regulations) || regulations.some((r) => !r || typeof r !== "object")) {
    throw new InvalidRequestError("regulations must be an array of objects");
  }
  return { useCase, regulations };
}

/**
 * The whole contract in one place: validate the request, build the
 * package with the exact same template the app used to bundle, verify it
 * with the real opa binary, and only then return it. The app receives
 * either a package whose generated test suite passes, or an error.
 */
export async function generateGuardrail(body) {
  const { useCase, regulations } = validate(body);
  // buildGuardrailTemplate throws on a regulation with no verifiable
  // source (assertRegulationProvenance); that propagates as-is.
  const files = buildGuardrailTemplate(useCase, regulations);
  const verification = await verifyPackage(files);
  return {
    files,
    thresholds: getThresholdsForSector(useCase.parent_sector),
    verification: { ...verification, opa_version: await opaVersion() },
  };
}
