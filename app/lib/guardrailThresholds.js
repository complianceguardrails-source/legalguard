// Sector-specific compliance thresholds surfaced in every generated
// guardrail's policies/thresholds.json and referenced by name in
// policies/rules.rego. Each entry is either:
//   (a) a genuinely fixed, citable regulatory figure (e.g. the $10,000 CTR
//       reporting threshold under the Bank Secrecy Act) -- these get a real
//       `value`, and
//   (b) something that varies by institution/product/lender and has no
//       single correct number (e.g. a debt-to-income cap) -- these get
//       `value: null` and stay a TODO for compliance to fill in.
// Never (a) faked as (b) or vice versa: a stub with a made-up-sounding
// number is worse than an honest null, because it looks authoritative
// without being true. See ingestion/risk_tier_classifier.py's docstring for
// the same principle applied to a different guess-vs-fact boundary.
const SECTOR_THRESHOLDS = {
  "Consumer Finance": [
    {
      key: "adverse_action_notice_window_days",
      value: 30,
      citation: "Regulation B / ECOA, 12 CFR 1002.9(a)(1)(i) -- adverse action notice required within 30 days of a completed application.",
    },
    {
      key: "max_debt_to_income_ratio",
      value: null,
      citation: "Lender/program-specific (e.g. the Ability-to-Repay/QM rule uses 43% for some products) -- set from your own underwriting policy, not a single universal regulatory figure.",
    },
    {
      key: "fair_lending_disparity_ratio_floor",
      value: null,
      citation: "No single regulatory figure for credit -- typically set via your own fair-lending statistical testing methodology.",
    },
  ],
  "Operations & Risk": [
    {
      key: "ctr_filing_threshold_usd",
      value: 10000,
      citation: "Bank Secrecy Act Currency Transaction Report threshold, 31 CFR 1010.311.",
    },
    {
      key: "sar_filing_window_days",
      value: 30,
      citation: "FinCEN Suspicious Activity Report filing deadline, 31 CFR 1020.320(b)(3) (60 days if no suspect is identified).",
    },
    {
      key: "human_review_required_above_risk_score",
      value: null,
      citation: "Institution-specific risk appetite -- set via your model risk management policy (see SR 11-7 / OCC 2011-12).",
    },
  ],
  "Front Office": [
    {
      key: "ai_disclosure_required",
      value: true,
      citation: "Baseline across bot-disclosure/transparency regimes (e.g. California SB 1001, EU AI Act Art. 50) -- confirm against the specific regulation(s) in REGULATORY_PROVENANCE.md.",
    },
    {
      key: "consent_capture_required_before_recording",
      value: true,
      citation: "Baseline expectation under most voice/biometric processing regimes -- confirm against applicable state/federal wiretap and biometric privacy law.",
    },
  ],
  "Wealth Management": [
    {
      key: "suitability_review_required",
      value: true,
      citation: "FINRA Rule 2111 / MiFID II suitability requirements.",
    },
  ],
  CIB: [
    {
      key: "material_nonpublic_info_flag_required",
      value: true,
      citation: "Baseline expectation under insider-trading/MNPI surveillance regimes -- confirm against the firm's information barrier policy.",
    },
  ],
};

/** Every guardrail gets this regardless of sector -- there's no regulatory
 * figure to cite here at all, just a structural requirement that a human
 * confirm the output before it's acted on. */
const UNIVERSAL_THRESHOLDS = [
  {
    key: "human_review_confirmed",
    value: null,
    citation: "Structural requirement, not a regulatory figure -- every guardrail needs an explicit human-review signal before allowing a decision through.",
  },
];

export function getThresholdsForSector(sector) {
  return [...(SECTOR_THRESHOLDS[sector] || []), ...UNIVERSAL_THRESHOLDS];
}
