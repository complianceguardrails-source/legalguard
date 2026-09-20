"""
Which regulations a use case must comply with, decided from the use case
side: by what the system does (its categories), by why it was tiered (its
risk_basis), and by what any AI system inside a regulated financial firm
carries regardless. This replaces word-overlap as the primary link between
banking_use_cases and specific_regulations.

Each rule names regulations by clause_identifier -- every row with that
identifier, so a state-by-state family (the 25 NAIC bulletin adoptions,
the 19 state profiling opt-outs) is one selector -- and states, once, why
the instrument reaches this kind of system. The "why" is shown to the user
next to the regulations it produced, so it is written as the claim a
reviewer would have to defend, with its limits ("life and health only",
"if it drives orders") left in rather than smoothed over.

Honesty notes:
  * The EU AI Act high-risk chapter (Arts 6-27, 72) is attached only where
    an Annex III category is actually in play -- creditworthiness (5(b)),
    life/health insurance (5(c)), biometrics (1), employment (4). It is NOT
    attached to fraud/AML systems merely because the app tiers them
    high-risk: Annex III 5(b) expressly excludes fraud detection, and
    risk_tier_classifier.py says so in its basis text.
  * Some categories get only the baseline. That is a gap in the regulation
    corpus, not a finding that nothing applies: MiCA (crypto), SFDR (ESG),
    SR 11-7's EU counterparts and the CRR credit-risk model rules are not
    ingested yet. link_regulations_by_category.py reports every selector
    that resolves to zero rows so a missing instrument is loud, not silent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# --- Selector shorthands (clause_identifier values) -----------------------
AIACT_HIGH_RISK_CHAPTER = [
    "AIACT-ART6-HighRiskClassification",
    "AIACT-ART8-ComplianceWithRequirements",
    "AIACT-ART9-RiskManagementSystem",
    "AIACT-ART10-DataGovernance",
    "AIACT-ART13-TransparencyToDeployers",
    "AIACT-ART14-HumanOversight",
    "AIACT-ART15-AccuracyRobustnessCybersecurity",
    "AIACT-ART26-DeployerObligations",
    "AIACT-ART27-FundamentalRightsImpactAssessment",
    "AIACT-ART72-PostMarketMonitoring",
]
AIACT_ART50 = ["AIACT-ART50-TransparencyDisclosure"]
AIACT_ART5 = ["AIACT-ART5-ProhibitedPractices"]
DORA_ICT_RISK = [
    "DORA-ART5-GovernanceAndOrganisation",
    "DORA-ART6-ICTRiskManagementFramework",
    "DORA-ART8-Identification",
    "DORA-ART9-ProtectionAndPrevention",
]
DORA_THIRD_PARTY = ["DORA-ART28-GeneralPrinciples", "DORA-ART30-KeyContractualProvisions"]
SR_11_7 = ["https-www-federalreserve-gov-boarddocs-srletters-2011-sr1107a1-pdf"]
APRA = ["AU-APRA-CPS230-OperationalRisk", "AU-APRA-CPS234-InformationSecurity"]
GDPR = [
    "https-eur-lex-europa-eu-legal-content-EN-TXT-uri-celex-3A32016R0679",
    "https-eur-lex-europa-eu-legal-content-EN-TXT-PDF-uri-CELEX-32016R0679-from-EN",
]
STATE_PROFILING_OPTOUT = ["US-*-PRIVACYACT-ProfilingOptOut"]  # glob: every state adoption
NAIC_BULLETIN = ["NAIC-MODELBULLETIN-AI-INSURERS"]  # one identifier, 25 state rows
US_AML_PROGRAM_RULES = [
    "2024-14414",  # FinCEN AML/CFT program rule (proposed)
    "2026-07033",  # FinCEN AML/CFT programs
    "2024-02854",  # FinCEN AML/CFT
    "2024-19260",  # FinCEN AML/CFT
    "2026-13919",  # Federal Reserve AML/CFT programs
    "2024-16546",  # OCC/Fed/FDIC/NCUA joint AML/CFT programs
    "2026-06948",  # OCC/FDIC/NCUA joint AML/CFT programs
]
ECOA_REG_B = ["2025-19864", "2026-07804", "2026-08494", "https-www-law-cornell-edu-uscode-text-15-1691"]
ADVERSE_ACTION = ["CIRC-2026-03-AdverseAction", "2024-08003"]
FCRA_REG_V = [
    "2024-13208", "2024-30824",  # Reg V: medical information in credit decisions
    "https-www-ftc-gov-system-files-documents-statutes-fair-credit-reporting-act-545a-fair-credit-reporting-act-0918-pdf",
    "https-www-ftc-gov-enforcement-statutes-fair-credit-reporting-act",
]
AVM_QC = ["2024-16197"]  # interagency Quality Control Standards for Automated Valuation Models
COLORADO_AI_ACT = ["CO-SB24-205-ConsumerProtectionsAI"]
TEXAS_TRAIGA = ["TX-HB149-TRAIGA"]
UTAH_AI_POLICY = ["UT-SB149-AIPolicyAct"]
FCA_CONSUMER_DUTY = ["CONSDUTY-VulnerableCustomers"]
CN_CONTENT_LABELING = ["CN-GB45438-2025-AIContentLabeling"]
MIFID_ALGO = ["MIFID2-ART16-OrganisationalRequirements", "MIFID2-ART17-AlgorithmicTrading"]
MIFID_BEST_EXECUTION = ["MIFID2-ART27-ObligationToExecuteOrdersOnTermsMostFavourableToTheClient"]
MIFID_CONDUCT = [
    "MIFID2-ART24-GeneralPrinciplesAndInformationToClients",
    "MIFID2-ART25-AssessmentOfSuitabilityAndAppropriatenessAndReportingTo",
]
MAR_MANIPULATION = ["MAR-ART12-MarketManipulation", "MAR-ART15-ProhibitionOfMarketManipulation"]
MAR_INSIDER = ["MAR-ART14-ProhibitionOfInsiderDealingAndOfUnlawfulDisclosureOfInside"]
MAR_SURVEILLANCE = ["MAR-ART16-PreventionAndDetectionOfMarketAbuse"]
MAR_RECOMMENDATIONS = ["MAR-ART20-InvestmentRecommendationsAndStatistics"]
PAYMENTS = ["2024-27836", "2026-10375"]
STABLECOIN_AML = ["2026-06963"]
BIOMETRIC = ["IL-BIPA-Biometric"]
EMPLOYMENT = [
    "NYC-LL144-AutomatedEmploymentDecisionTools",
    "IL-HB3773-AIEmploymentDiscrimination",
    "MD-HB1106-AIEmploymentLaw",
    "NJ-LAD-DisparateImpactRules-AI",
    "2024-26099",  # CFPB Circular 2024-06: background dossiers and algorithmic scores for hiring
]


@dataclass(frozen=True)
class Rule:
    id: str
    why: str
    clauses: list[str]
    applies: Callable[[dict], bool]
    # Presentation grouping for the app: "category", "basis", "baseline".
    kind: str = "category"


def _has_category(*slugs: str) -> Callable[[dict], bool]:
    return lambda uc: bool(set(uc.get("categories") or []) & set(slugs))


def _has_basis(*keys: str) -> Callable[[dict], bool]:
    # risk_basis.basis[*].reference is the human string; the machine key is
    # recoverable from the phrases via risk_tier_classifier.KEYWORD_BASIS.
    from risk_tier_classifier import KEYWORD_BASIS

    def check(uc: dict) -> bool:
        rb = uc.get("risk_basis") or {}
        return any(KEYWORD_BASIS.get(p) in keys for p in rb.get("matched") or [])

    return check


def _either(*preds: Callable[[dict], bool]) -> Callable[[dict], bool]:
    return lambda uc: any(p(uc) for p in preds)


def _always(uc: dict) -> bool:
    return True


def _third_party_model(uc: dict) -> bool:
    return uc.get("source") == "huggingface_mined"


RULES: list[Rule] = [
    # ----- Baseline: any AI system run inside a regulated financial firm ---
    Rule(
        "baseline_dora_ict_risk",
        "An AI system is an ICT system: DORA's ICT risk-management framework (governance, framework, asset identification, protection) applies to every EU financial entity that runs it.",
        DORA_ICT_RISK, _always, kind="baseline",
    ),
    Rule(
        "baseline_sr_11_7",
        "SR 11-7 model risk management reaches any model a US banking organisation relies on: validation, ongoing monitoring, documented limitations.",
        SR_11_7, _always, kind="baseline",
    ),
    Rule(
        "baseline_apra",
        "For APRA-regulated Australian entities, CPS 230 (operational risk, critical operations) and CPS 234 (information security) cover the system and its data.",
        APRA, _always, kind="baseline",
    ),
    Rule(
        "third_party_model",
        "This is a model published by a third party. Bringing it in is ICT third-party risk under DORA: contractual provisions and the general principles for third-party arrangements apply.",
        DORA_THIRD_PARTY, _third_party_model, kind="baseline",
    ),

    # ----- Credit and lending ---------------------------------------------
    Rule(
        "credit_annex_iii_5b",
        "Evaluating the creditworthiness of natural persons or establishing their credit score is an EU AI Act Annex III point 5(b) high-risk use. The provider and deployer obligations of Chapter III apply (excluding fraud detection).",
        AIACT_HIGH_RISK_CHAPTER, _either(_has_category("credit_lending"), _has_basis("annex_iii_5b")),
    ),
    Rule(
        "credit_ecoa",
        "Credit decisions in the US fall under the Equal Credit Opportunity Act and Regulation B: no discrimination on a prohibited basis, and the model's factors must support a specific adverse-action reason.",
        ECOA_REG_B + ADVERSE_ACTION, _either(_has_category("credit_lending"), _has_basis("annex_iii_5b")),
    ),
    Rule(
        "credit_fcra",
        "Where the model consumes consumer-report data, the Fair Credit Reporting Act and Regulation V govern permissible purpose, medical information and adverse-action duties.",
        FCRA_REG_V, _has_category("credit_lending"),
    ),
    Rule(
        "credit_avm",
        "If the system values residential collateral for a mortgage decision, the interagency Automated Valuation Model quality-control standards apply.",
        AVM_QC, _has_category("credit_lending"),
    ),
    Rule(
        "consequential_decision_state_ai_laws",
        "Credit and insurance decisions are 'consequential decisions' under Colorado SB 24-205 and TRAIGA: developers and deployers owe duties of care, impact assessments and non-discrimination.",
        COLORADO_AI_ACT + TEXAS_TRAIGA, _has_category("credit_lending", "insurance"),
    ),
    Rule(
        "profiling_optout_state_privacy",
        "Profiling in furtherance of decisions with legal or similarly significant effects -- credit, insurance, financial services -- gives consumers an opt-out right under each of these state privacy acts.",
        STATE_PROFILING_OPTOUT, _has_category("credit_lending", "insurance"),
    ),
    Rule(
        "gdpr_automated_decisions",
        "Decisions about individuals made solely by automated means, and the personal data behind them, fall under the GDPR (Article 22 and the data-protection principles).",
        GDPR, _has_category("credit_lending", "insurance", "fraud_aml", "banking_support", "payments"),
    ),

    # ----- Insurance --------------------------------------------------------
    Rule(
        "insurance_annex_iii_5c",
        "Risk assessment and pricing of natural persons in life and health insurance is an EU AI Act Annex III point 5(c) high-risk use; Chapter III applies. Other insurance lines are not listed -- confirm the line of business.",
        AIACT_HIGH_RISK_CHAPTER, _either(_has_category("insurance"), _has_basis("annex_iii_5c")),
    ),
    Rule(
        "insurance_naic_bulletin",
        "The NAIC Model Bulletin on the use of AI by insurers, as adopted state by state, requires a written AI program, governance and testing for unfair discrimination.",
        NAIC_BULLETIN, _has_category("insurance"),
    ),

    # ----- Fraud, AML, sanctions -------------------------------------------
    Rule(
        "aml_program_rules",
        "Fraud, AML, KYC and sanctions systems produce the alerts and decisions a Bank Secrecy Act AML/CFT program is built on; the program rules for risk assessment, testing and reporting apply to them directly.",
        US_AML_PROGRAM_RULES, _either(_has_category("fraud_aml"), _has_basis("aml_cft")),
    ),

    # ----- Trading and markets ---------------------------------------------
    Rule(
        "trading_mifid_algo",
        "A system that generates or routes orders is algorithmic trading under MiFID II: Article 17 controls (kill switch, testing, thresholds) and the Article 16 organisational requirements apply.",
        MIFID_ALGO, _has_category("trading_markets"),
    ),
    Rule(
        "trading_best_execution",
        "Where the system executes client orders, the Article 27 best-execution obligation applies.",
        MIFID_BEST_EXECUTION, _has_category("trading_markets"),
    ),
    Rule(
        "markets_mar_manipulation",
        "Trading, prediction and market-sentiment systems can produce or spread signals that amount to market manipulation; the MAR prohibition and definition apply to what they output.",
        MAR_MANIPULATION, _has_category("trading_markets", "stock_prediction", "sentiment_news"),
    ),
    Rule(
        "markets_mar_insider",
        "A model trained or prompted on non-public information can trade on it: the MAR prohibition on insider dealing applies.",
        MAR_INSIDER, _has_category("trading_markets", "stock_prediction"),
    ),
    Rule(
        "markets_mar_surveillance",
        "Firms that arrange or execute transactions must detect and report market abuse (MAR Article 16); a trading system is inside that surveillance perimeter.",
        MAR_SURVEILLANCE, _has_category("trading_markets"),
    ),
    Rule(
        "recommendations_mar_art20",
        "Output that recommends or suggests an investment strategy, or a market view disseminated to clients, is an investment recommendation under MAR Article 20: objective presentation and disclosure of interests.",
        MAR_RECOMMENDATIONS, _has_category("stock_prediction", "sentiment_news", "portfolio_wealth"),
    ),
    Rule(
        "advice_mifid_conduct",
        "Portfolio and wealth systems that advise or manage for clients carry the MiFID II conduct duties: act honestly and fairly, and assess suitability and appropriateness before recommending.",
        MIFID_CONDUCT + MIFID_BEST_EXECUTION, _either(_has_category("portfolio_wealth"), _has_basis("mifid_advice")),
    ),

    # ----- Crypto and payments ---------------------------------------------
    Rule(
        "crypto_aml",
        "Crypto and DeFi services are money-services businesses for AML purposes: the AML/CFT program rules, and the permitted-payment-stablecoin AML rule, apply. MiCA is not yet in this corpus.",
        US_AML_PROGRAM_RULES + STABLECOIN_AML, _has_category("crypto_defi"),
    ),
    Rule(
        "payments_rules",
        "Payment systems fall under CFPB supervision of digital consumer payment applications and the Federal Reserve's payment-system-risk policy, and are inside the AML program perimeter.",
        PAYMENTS + US_AML_PROGRAM_RULES, _has_category("payments"),
    ),

    # ----- Customer-facing and generative -----------------------------------
    Rule(
        "chatbot_art50",
        "People must be told they are interacting with an AI system, and AI-generated content must be marked: EU AI Act Article 50.",
        AIACT_ART50, _either(_has_category("banking_support", "finance_llm"), _has_basis("article_50")),
    ),
    Rule(
        "chatbot_utah",
        "Utah's AI Policy Act requires disclosure when a consumer interacts with generative AI in a regulated occupation or on request.",
        UTAH_AI_POLICY, _has_category("banking_support", "finance_llm"),
    ),
    Rule(
        "support_fca_consumer_duty",
        "Customer-facing systems must deliver good outcomes for vulnerable customers under the FCA Consumer Duty.",
        FCA_CONSUMER_DUTY, _has_category("banking_support"),
    ),
    Rule(
        "genai_cn_labeling",
        "If deployed in China, AI-generated content must carry explicit and implicit labels under GB 45438-2025.",
        CN_CONTENT_LABELING, _has_category("finance_llm"),
    ),

    # ----- Basis-only: what the risk classifier found ------------------------
    Rule(
        "biometric",
        "Biometric identification is an EU AI Act Annex III point 1 high-risk use, and Illinois BIPA requires consent for biometric identifiers.",
        AIACT_HIGH_RISK_CHAPTER + BIOMETRIC, _has_basis("annex_iii_1"), kind="basis",
    ),
    Rule(
        "employment",
        "AI in recruitment or worker evaluation is an EU AI Act Annex III point 4 high-risk use, and is directly regulated by NYC Local Law 144, Illinois, Maryland and New Jersey employment-AI rules.",
        AIACT_HIGH_RISK_CHAPTER + EMPLOYMENT, _has_basis("annex_iii_4"), kind="basis",
    ),
    Rule(
        "prohibited_practice",
        "The classifier matched a phrase from the EU AI Act's prohibited practices; Article 5 bans the practice outright if the match is real.",
        AIACT_ART5, _has_basis("article_5"), kind="basis",
    ),
]

_IDS = [r.id for r in RULES]
assert len(_IDS) == len(set(_IDS)), "duplicate rule id"


def rules_for(use_case: dict) -> list[Rule]:
    return [r for r in RULES if r.applies(use_case)]
