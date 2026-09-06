// Derives a risk_tier suggestion for a self-submitted use case from two
// plain-language proxy answers, instead of asking a submitter to know EU AI
// Act risk taxonomy directly. "Solely automated decision about an
// individual" is literally the trigger nearly every profiling/automated-
// decision law already in this database uses (VCDPA-model state privacy
// laws, GDPR-style provisions, NYC Local Law 144) -- this mirrors that
// actual legal logic rather than inventing a new one.
//
// Deliberately never returns 'prohibited' -- that EU AI Act category
// (banned practices) isn't derivable from this proxy.

export function deriveRiskTier({ affectsIndividual, automationDegree }) {
  if (!affectsIndividual) return "minimal_risk";
  return automationDegree === "full" ? "high_risk" : "limited_risk";
}
