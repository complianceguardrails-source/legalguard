// Use-case categories: what a system does (fraud, credit, trading, crypto)
// as distinct from parent_sector (which part of a bank would own it). The
// slugs are the stored values -- assigned server-side by
// ingestion/usecase_categories.py from a row's real name, description and
// card/README prose -- and must match that file exactly. Labels and tones
// are the app's: a display change here never touches the data.
//
// Eleven tones for seventeen categories; related categories share one, so
// the cloud reads as a small palette rather than a rainbow. Every tone was
// chosen dark enough for white Poppins at 4.5:1. The app's amber accent is
// deliberately absent: it is reserved for actions, and a card is not one.

const TONES = {
  teal: "#0E6B6B",
  indigo: "#3B3F9E",
  slate: "#2F4A7A",
  rust: "#A34A17",
  plum: "#6B2D5C",
  royal: "#234FA3",
  forest: "#2E6B3A",
  ochre: "#8A6A16",
  green: "#1F7A4D",
  steel: "#3E5C76",
  charcoal: "#2B2D42",
};

// Display order is the order the cloud shows them in.
export const CATEGORIES = [
  { slug: "trading_markets", label: "Trading & Markets", tone: TONES.teal },
  { slug: "banking_support", label: "Banking & Support", tone: TONES.royal },
  { slug: "sentiment_news", label: "Sentiment & News", tone: TONES.forest },
  { slug: "compliance_legal", label: "Compliance & Legal", tone: TONES.plum },
  { slug: "insurance", label: "Insurance", tone: TONES.steel },
  { slug: "credit_lending", label: "Credit & Lending", tone: TONES.rust },
  { slug: "crypto_defi", label: "Crypto & DeFi", tone: TONES.indigo },
  { slug: "stock_prediction", label: "Stock Prediction", tone: TONES.slate },
  { slug: "finance_llm", label: "General Finance LLM", tone: TONES.charcoal },
  { slug: "portfolio_wealth", label: "Portfolio & Wealth", tone: TONES.ochre },
  { slug: "risk_management", label: "Risk Management", tone: TONES.slate },
  { slug: "economics_macro", label: "Economics & Macro", tone: TONES.forest },
  { slug: "filings_reports", label: "Filings & Reports", tone: TONES.forest },
  { slug: "payments", label: "Payments", tone: TONES.royal },
  { slug: "tax_accounting", label: "Tax & Accounting", tone: TONES.ochre },
  { slug: "esg_climate", label: "ESG & Climate", tone: TONES.green },
  { slug: "fraud_aml", label: "Fraud & AML", tone: TONES.plum },
];

const BY_SLUG = Object.fromEntries(CATEGORIES.map((c) => [c.slug, c]));

export function categoryLabel(slug) {
  return BY_SLUG[slug]?.label ?? slug;
}

export function categoryTone(slug) {
  return BY_SLUG[slug]?.tone ?? TONES.charcoal;
}

/** The tone a use case is painted in: its first category's. */
export function useCaseTone(useCase) {
  return categoryTone((useCase.categories || [])[0]);
}

// Semantic risk-tier colours for the small dot on a card -- separate from
// the category tones on purpose, so tier never competes with category.
export const TIER_DOT = {
  prohibited: "#FF6B6B",
  high_risk: "#FFB347",
  limited_risk: "#9EC5FF",
  minimal_risk: "#7EDCA2",
  unclassified: "rgba(255,255,255,0.55)",
};

export const TIER_LABEL = {
  prohibited: "Prohibited",
  high_risk: "High risk",
  limited_risk: "Limited risk",
  minimal_risk: "Minimal risk",
  unclassified: "Unclassified",
};
