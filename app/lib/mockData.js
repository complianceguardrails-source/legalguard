// Bundled fallback data -- mirrors the shapes returned by database/seed.sql
// via PostgREST, so the app renders something real-looking even before a
// backend is deployed. Swap for live data automatically once
// EXPO_PUBLIC_API_URL is set (see lib/api.js).

export const MOCK_USE_CASES = [
  {
    id: "uc-1",
    name: "Voice Agent: Mortgage Escalation Support",
    parent_sector: "Front Office",
    modality: "voice_agentic",
    risk_tier: "high_risk",
    github_reference_url: null,
  },
  {
    id: "uc-2",
    name: "Green Mortgage EPC/ESG Verification",
    parent_sector: "Consumer Finance",
    modality: "vision",
    risk_tier: "high_risk",
    github_reference_url: null,
  },
  {
    id: "uc-3",
    name: "Buy-to-Let Rental Yield Stress Testing",
    parent_sector: "Consumer Finance",
    modality: "structured",
    risk_tier: "high_risk",
    github_reference_url: null,
  },
  {
    id: "uc-4",
    name: "Unsecured Consumer Credit Scoring",
    parent_sector: "Consumer Finance",
    modality: "structured",
    risk_tier: "high_risk",
    github_reference_url: null,
  },
];

export const MOCK_REGULATIONS = [
  {
    reg_id: "reg-1",
    jurisdiction: "EU",
    issuing_body: "European AI Office",
    clause_identifier: "AIACT-ART10-DataGovernance",
    official_title: "EU AI Act Article 10 — Data and Data Governance",
    effective_date: "2026-08-02",
    risk_level: "high_risk",
  },
  {
    reg_id: "reg-2",
    jurisdiction: "US",
    issuing_body: "CFPB",
    clause_identifier: "CIRC-2026-03-AdverseAction",
    official_title: "CFPB Circular 2026-03 — Adverse Action Notices for Algorithmic Lending",
    effective_date: "2026-03-01",
    risk_level: "high_risk",
  },
  {
    reg_id: "reg-3",
    jurisdiction: "UK",
    issuing_body: "FCA",
    clause_identifier: "CONSDUTY-VulnerableCustomers",
    official_title: "FCA Consumer Duty — Vulnerable Customer Outcomes",
    effective_date: "2023-07-31",
    risk_level: "high_risk",
  },
];

export const MOCK_HORIZON = [
  {
    id: "horizon-1",
    projected_bill_name: "Proposed Voice Agent Telemetry Amendment",
    target_jurisdiction: "UK",
    estimated_arrival_window: "Q4 2027",
    probability_percentage: 88,
    upstream_catalyst_drivers: ["voice_deepfake_scams", "vulnerable_consumer_loss"],
    underlying_driver_description:
      "Surge in unauthorized account drain via generative voice injection is pushing FCA toward mandatory biometric liveness and voice-print telemetry checks.",
    impact_blast_radius_summary: "guardrail-voice-agentic-customer-support, guardrail-retail-ivr-navigation",
    status: "watching",
  },
  {
    id: "horizon-2",
    projected_bill_name: "Green Taxonomy Anti-Greenwashing Revision",
    target_jurisdiction: "EU",
    estimated_arrival_window: "Q2 2027",
    probability_percentage: 65,
    upstream_catalyst_drivers: ["anti_greenwashing_scrutiny", "satellite_data_sync"],
    underlying_driver_description:
      "EBA moving to require third-party verification of green-mortgage eligibility rather than self-reported EPC claims.",
    impact_blast_radius_summary: "guardrail-green-mortgage-verifier",
    status: "watching",
  },
];

// Mirrors database/schema.sql's guardrail_compliance_summary view shape.
export const MOCK_COMPLIANCE_SUMMARY = [
  { compliance_status: "compliant", guardrail_count: 6 },
  { compliance_status: "action_required", guardrail_count: 376 },
  { compliance_status: "critical_breach", guardrail_count: 2 },
];

// Shaped like real specific_regulations rows so MOCK_PENDING_REGULATIONS can
// be rendered directly by the shared RegulationCard component -- same shape
// fetchRegulations()/MOCK_REGULATIONS uses, plus the dispatch/impact/source
// provenance fields RegulationCard displays.
// Mirrors guardrail_packages rows where is_admin_reference = true -- a
// real, hand-built reference repo the admin curated for a use case, as
// opposed to a per-user generated one (tracked only on-device, never in
// this shared table). Only uc-1 has one here so the mock/demo mode shows
// both UI states (reference found vs. not yet) without a backend.
export const MOCK_ADMIN_REFERENCE_GUARDRAILS = [
  {
    guardrail_id: "guardrail-ref-1",
    use_case_id: "uc-1",
    name: "guardrail-voice-agentic-customer-support",
    github_owner: "complianceguardrails-source",
    github_repo_url: "https://github.com/complianceguardrails-source/guardrail-voice-agentic-customer-support",
    is_admin_reference: true,
  },
];

export const MOCK_PENDING_REGULATIONS = [
  {
    reg_id: "reg-3",
    jurisdiction: "UK",
    issuing_body: "FCA",
    clause_identifier: "CONSDUTY-VulnerableCustomers",
    title: "FCA Consumer Duty — Vulnerable Customer Outcomes",
    official_title: "FCA Consumer Duty — Vulnerable Customer Outcomes",
    statutory_text:
      "Firms must identify and respond to characteristics of vulnerability, including harms arising from voice-agentic customer support channels.",
    effective_date: "2023-07-31",
    impact_level: "Version Revision Trigger",
    dispatch_status: "Not Dispatched",
    source_url: "https://www.fca.org.uk/firms/consumer-duty",
    source_url_classification: "primary",
    affected_use_case_ids: ["uc-1"],
  },
];
