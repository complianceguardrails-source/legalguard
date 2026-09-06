-- LegalGuard seed data
-- Populates a starter knowledge base so the app has real content to render
-- before the ingestion crawler has run. Run this AFTER schema.sql.
--
-- NOTE ON HONESTY: the specific_regulations rows below are illustrative
-- placeholders that mirror the *shape* of real clauses discussed in your
-- design session (EU AI Act Art. 10, CFPB Circular 2026-03-style guidance,
-- FCA Consumer Duty). Verify exact clause text/citations against the primary
-- source before treating them as legally authoritative -- the ingestion
-- engine (see ingestion/) is what pulls verified, sourced text going forward.

-- ---------------------------------------------------------------------------
-- Banking use cases across the 5 tiers
-- ---------------------------------------------------------------------------
INSERT INTO banking_use_cases (name, parent_sector, modality, description, risk_tier) VALUES
-- Tier 1: Consumer Lending
('Unsecured Consumer Credit Scoring', 'Consumer Finance', 'structured', 'Automated cash-flow based approval/denial for unsecured loans and credit cards.', 'high_risk'),
('Auto Loan Underwriting', 'Consumer Finance', 'structured', 'Automated risk pricing for vehicle finance applications.', 'high_risk'),
('Payday / Micro-loan Velocity Checks', 'Consumer Finance', 'structured', 'High-frequency eligibility and repeat-borrowing risk scoring.', 'high_risk'),
('Buy-to-Let Rental Yield Stress Testing', 'Consumer Finance', 'structured', 'Forecasts rental yield and landlord affordability under rate shocks.', 'high_risk'),
('Mortgage Document Underwriting (OCR+LLM)', 'Consumer Finance', 'rag_document', 'Extracts income, tax and deed data from scanned mortgage documents.', 'high_risk'),
('Green Mortgage EPC/ESG Verification', 'Consumer Finance', 'vision', 'Validates energy-performance claims against building imagery and registries for green-rate eligibility.', 'high_risk'),
('Credit Card Dispute Triage', 'Consumer Finance', 'structured', 'Classifies and routes chargeback/dispute claims.', 'limited_risk'),
('Student Loan Underwriting', 'Consumer Finance', 'structured', 'Eligibility and repayment-plan modeling for education lending.', 'high_risk'),

-- Tier 2: Front Office / Multimodal Agentic
('Voice Agent: Inbound Account Queries', 'Front Office', 'voice_agentic', 'Real-time conversational agent (Gemini Live / Vertex AI Agent Builder) for balance/card queries.', 'limited_risk'),
('Voice Agent: Mortgage Escalation Support', 'Front Office', 'voice_agentic', 'Multimodal voice handling for escalated mortgage servicing calls.', 'high_risk'),
('Formally Escalated Complaint Drafting', 'Front Office', 'rag_document', 'Sentiment classification + drafted responses to legally-sensitive complaints.', 'high_risk'),
('Financial Distress / Crisis Support Triage', 'Front Office', 'voice_agentic', 'Detects vulnerable-customer signals and routes to human specialists.', 'high_risk'),
('Real-time Voice Translation (Retail Branch)', 'Front Office', 'voice_agentic', 'Live translation for non-native-language retail customers.', 'limited_risk'),
('Chatbot Product Recommendation', 'Front Office', 'multi_agent', 'Conversational product navigation and cross-sell suggestions.', 'limited_risk'),

-- Tier 3: CIB / Wealth Management
('M&A Due Diligence Document Parsing', 'CIB', 'rag_document', 'Cross-border contract and litigation-history extraction for acquisitions.', 'high_risk'),
('Algorithmic Trading Execution Strategy', 'CIB', 'structured', 'Agentic execution reading order books and macro news feeds.', 'high_risk'),
('Institutional Pitch-book / Prospectus Generation', 'CIB', 'rag_document', 'Synthesizes financial models into client-facing prospectus drafts.', 'high_risk'),
('Portfolio Optimization Modeling', 'Wealth Management', 'structured', 'Allocation modeling against client risk mandates.', 'limited_risk'),
('Corporate Proxy-Voting Summary Agent', 'CIB', 'rag_document', 'Summarizes proxy statements for institutional voting decisions.', 'limited_risk'),

-- Tier 4: Back Office, Risk & Compliance
('AML Transaction Monitoring', 'Operations & Risk', 'structured', 'Graph-based anomaly detection for layering/structuring patterns.', 'high_risk'),
('KYC Onboarding Web/Registry Search Agent', 'Operations & Risk', 'multi_agent', 'Multi-agent search across public registries for onboarding checks.', 'high_risk'),
('Biometric Identity Verification (Face+Voice Liveness)', 'Operations & Risk', 'vision', 'Liveness testing to prevent deepfake/synthetic-identity fraud.', 'high_risk'),
('Internal Trader Communication Surveillance', 'Operations & Risk', 'rag_document', 'NLP monitoring of chat/voice for collusion and market manipulation.', 'high_risk'),
('Sanctions / PEP List Screening', 'Operations & Risk', 'structured', 'Screens counterparties against sanctioned-entity and PEP lists.', 'high_risk'),

-- Tier 5: Crisis & Vulnerability Safeguards
('Hardship Program Qualification Calculator', 'Consumer Finance', 'structured', 'Determines eligibility for mortgage holidays/overdraft relief.', 'high_risk'),
('Automated Bankruptcy Flagging', 'Operations & Risk', 'structured', 'Flags accounts showing bankruptcy-filing signals for servicing changes.', 'high_risk'),
('Vulnerable Customer De-escalation Routing', 'Front Office', 'voice_agentic', 'Detects distress markers in voice/chat and forces human handoff.', 'high_risk')
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Illustrative regulations (placeholders -- see note above)
-- ---------------------------------------------------------------------------
INSERT INTO specific_regulations
    (jurisdiction, issuing_body, clause_identifier, official_title, source_url, statutory_text, version_label, publication_date, effective_date, risk_level, origin_driver_category, origin_driver_description, content_sha256, ingestion_source)
VALUES
('EU', 'European AI Office', 'AIACT-ART10-DataGovernance', 'EU AI Act Article 10 -- Data and Data Governance',
 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai',
 'High-risk AI systems shall be developed on the basis of training, validation and testing data sets that meet quality criteria... examination of possible biases.',
 'v1', '2024-08-01', '2026-08-02', 'high_risk',
 'standards_harmonization', 'Codifies pre-existing NIST AI RMF / ISO 42001 style data-governance and bias-examination practice into binding EU law rather than responding to a single incident.',
 encode(sha256('AIACT-ART10-v1-placeholder'::bytea), 'hex'), 'manual'),

('US', 'CFPB', 'CIRC-2026-03-AdverseAction', 'CFPB Circular 2026-03 -- Adverse Action Notices for Algorithmic Lending',
 'https://www.consumerfinance.gov/compliance/circulars/',
 'Creditors using complex algorithms for credit decisions must still provide accurate and specific reasons for adverse action under Regulation B; "the algorithm decided" is not an adequate explanation.',
 'v1', '2026-03-01', '2026-03-01', 'high_risk',
 'market_scandal', 'Responds to a pattern of consumer complaints and enforcement actions where lenders used "the model decided" as a denial explanation, which CFPB found non-compliant with existing Reg B.',
 encode(sha256('CFPB-2026-03-v1-placeholder'::bytea), 'hex'), 'manual'),

('UK', 'FCA', 'CONSDUTY-VulnerableCustomers', 'FCA Consumer Duty -- Vulnerable Customer Outcomes',
 'https://www.fca.org.uk/firms/consumer-duty',
 'Firms must ensure automated customer interactions identify and appropriately support customers in vulnerable circumstances, including safe escalation to human support.',
 'v1', '2023-07-31', '2023-07-31', 'high_risk',
 'capability_leap', 'Written after conversational/voice agents became capable enough to be a customer''s primary support channel, outrunning older rules written for human-staffed contact centers.',
 encode(sha256('FCA-CONSDUTY-v1-placeholder'::bytea), 'hex'), 'manual')
ON CONFLICT (jurisdiction, issuing_body, clause_identifier, version_label) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Sample guardrail package + mapping (many-to-many demonstration)
-- ---------------------------------------------------------------------------
INSERT INTO guardrail_packages (use_case_id, name, policy_framework, current_semver, compiled_code_payload, status, compliance_status)
SELECT id, 'guardrail-voice-agentic-customer-support', 'open_policy_agent', 'v1.2.0',
$$package legalguard.voice_agentic

default allow = false

# Requires an explicit synthetic-voice disclosure within the first exchange.
allow {
    input.disclosure_emitted == true
    input.vulnerable_customer_check_passed == true
}
$$,
'staged', 'action_required'
FROM banking_use_cases WHERE name = 'Voice Agent: Mortgage Escalation Support'
ON CONFLICT DO NOTHING;

INSERT INTO guardrail_regulatory_mapping (reg_id, guardrail_id, impact_tier, mandate_summary)
SELECT r.reg_id, g.guardrail_id, 'new_guardrail_required',
       'FCA Consumer Duty requires vulnerable-customer detection and safe human handoff in voice channels.'
FROM specific_regulations r, guardrail_packages g
WHERE r.clause_identifier = 'CONSDUTY-VulnerableCustomers'
  AND g.name = 'guardrail-voice-agentic-customer-support'
ON CONFLICT DO NOTHING;

-- Two more sample packages so all three Radar dashboard tiles (Compliant /
-- Action Req. / Breaches) have non-zero counts out of the box.
INSERT INTO guardrail_packages (use_case_id, name, policy_framework, current_semver, compiled_code_payload, status, compliance_status)
SELECT id, 'guardrail-btl-rental-stress-test', 'open_policy_agent', 'v3.0.1',
'package legalguard.btl_stress_test\n\ndefault allow = false\n\nallow {\n    input.rental_yield_stress_passed == true\n}\n',
'merged', 'compliant'
FROM banking_use_cases WHERE name = 'Buy-to-Let Rental Yield Stress Testing'
ON CONFLICT DO NOTHING;

INSERT INTO guardrail_packages (use_case_id, name, policy_framework, current_semver, compiled_code_payload, status, compliance_status)
SELECT id, 'guardrail-green-mortgage-verifier', 'open_policy_agent', 'v0.9.0',
'package legalguard.green_mortgage\n\ndefault allow = false\n\nallow {\n    input.epc_registry_verified == true\n}\n',
'proposed', 'critical_breach'
FROM banking_use_cases WHERE name = 'Green Mortgage EPC/ESG Verification'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Horizon forecast samples
-- ---------------------------------------------------------------------------
INSERT INTO regulatory_horizon_forecast
    (projected_bill_name, target_jurisdiction, estimated_arrival_window, probability_percentage,
     upstream_catalyst_drivers, underlying_driver_description, impact_blast_radius_summary,
     suggested_proactive_guardrail_logic, status)
VALUES
('Proposed Voice Agent Telemetry Amendment', 'UK', 'Q4 2027', 88,
 ARRAY['voice_deepfake_scams','vulnerable_consumer_loss'],
 'Surge in unauthorized account drain via generative voice injection is pushing FCA toward mandatory biometric liveness and voice-print telemetry checks.',
 'guardrail-voice-agentic-customer-support, guardrail-retail-ivr-navigation',
 'Add liveness-challenge gate before any balance-affecting voice transaction is authorized.',
 'watching'),

('Green Taxonomy Anti-Greenwashing Revision', 'EU', 'Q2 2027', 65,
 ARRAY['anti_greenwashing_scrutiny','satellite_data_sync'],
 'EBA moving to require third-party verification of green-mortgage eligibility rather than self-reported EPC claims.',
 'guardrail-green-mortgage-verifier',
 'Cross-reference property ID against national EPC registry API before applying green rate.',
 'watching')
ON CONFLICT DO NOTHING;
