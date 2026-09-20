"""
Use-case categories: what a system DOES -- fraud, credit, trading, crypto,
insurance -- as distinct from parent_sector (usecase_classifier.py), which
is which part of a bank would own it. This is the axis a user browses by:
the app's landing screen is a multi-select cloud of these, and a use case
can sit in several at once, so assign_categories returns a list.

Built from the corpus, not from a prior. The category set and keyword
lists were arrived at by running candidate maps across all 1,438 use
cases (names, descriptions, and the model-card / README prose the
enrichment steps store) and inspecting sizes, overlap and what fell
through. Two keywords that looked reasonable were dropped after that:
bare "policy" (matched insurance policies, return policies and RL
policies alike) and bare "document"/"qa"/"rag" (caught every generic LLM
card). Mortgage was folded into Credit & Lending: nine rows is not a
tile.

Chinese terms are included because the data has them: the XuanYuan
family (Duxiaoman-DI) is the largest Chinese finance-LLM lineage in the
corpus and its cards say 金融大模型, which no English keyword reaches.

An empty result is meaningful. Tagging showed roughly a quarter of the
corpus is not financial AI at all -- interview-question lists, scraping
frameworks, an Android tools list, leaks from bank-org and generic-keyword
mining -- and "no financial category" is what keeps those off the front
page. The tagger runner writes them to a review list rather than deleting.

Same short-keyword rule as the other classifiers: a keyword of four
characters or fewer must match at a word boundary ("aml" in "seamless",
"eth" in "method", "etf" in "netflix"), longer phrases match as substrings.
"""
from __future__ import annotations

import re

# Stored value is the slug, not the display name: the app filters with
# PostgREST array operators in a query string, and a value like
# "Crypto & DeFi" needs quoting that breaks at the first ampersand. The
# display names live in CATEGORY_LABELS (and in the app, which owns the
# tone for each). Order is the display order in the app's cloud.
CATEGORY_LABELS: dict[str, str] = {
    "trading_markets": "Trading & Markets",
    "banking_support": "Banking & Support",
    "sentiment_news": "Sentiment & News",
    "compliance_legal": "Compliance & Legal",
    "insurance": "Insurance",
    "credit_lending": "Credit & Lending",
    "crypto_defi": "Crypto & DeFi",
    "stock_prediction": "Stock Prediction",
    "finance_llm": "General Finance LLM",
    "portfolio_wealth": "Portfolio & Wealth",
    "risk_management": "Risk Management",
    "economics_macro": "Economics & Macro",
    "filings_reports": "Filings & Reports",
    "payments": "Payments",
    "tax_accounting": "Tax & Accounting",
    "esg_climate": "ESG & Climate",
    "fraud_aml": "Fraud & AML",
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "trading_markets": [
        "trading", "trader", "backtest", "algorithmic", "order execution", "market making", "hft",
        "quant ", "quantitative", "trading signal", "exchange", "market data", "交易",
    ],
    # Banking operations vocabulary came from the curated rows: eight
    # hand-entered banking use cases (vulnerable-customer routing, inbound
    # account queries, branch voice translation) matched nothing until
    # these were added.
    "banking_support": [
        "banking", "bank ", "banks", "intent", "chatbot", "customer support", "customer service",
        "retail customer", "customer churn", "complaint", "function calling", "vulnerable", "distress",
        "retail branch", "bank branch", "account quer", "account balance", "balance quer", "voice agent",
        "银行",
    ],
    "sentiment_news": [
        "sentiment", "financial news", "finbert", "tone", "headline", "fintwit", "market news",
    ],
    "compliance_legal": [
        "compliance", "regulat", "legal", "gdpr", "mifid", "contract analysis", "litigation",
        "due diligence",
    ],
    # Not bare "claims": it matched ClimateBERT's environmental-claims model
    # in the sector classifier (usecase_classifier.py), same trap here.
    "insurance": [
        "insurance", "insurer", "insurance claim", "claims processing", "claim settlement", "actuar",
        "underwrit", "policyholder", "reinsur", "保险",
    ],
    "credit_lending": [
        "credit", "loan", "lending", "borrower", "default prediction", "scoring", "bnpl",
        "mortgage", "home loan", "refinanc", "bankrupt", "信贷", "贷款",
    ],
    "crypto_defi": [
        "crypto", "bitcoin", "btc", "ethereum", "blockchain", "defi", "solana", "binance", "web3",
        "usdt", "altcoin",
    ],
    "stock_prediction": [
        "stock", "share price", "price prediction", "price forecast", "ticker", "nasdaq", "nifty",
        "candlestick", "股票",
    ],
    "finance_llm": [
        "finance llm", "financial llm", "finllm", "fingpt", "finma", "finllama", "fino1", "xuanyuan",
        "financial assistant", "finance assistant", "financial analyst", "financial reasoning",
        "financial domain", "finance domain", "financial language", "金融",
    ],
    "portfolio_wealth": [
        "portfolio", "asset allocation", "wealth", "robo advis", "investment advice", "invest",
        "asset management", "hedge fund", "etf",
    ],
    "risk_management": [
        "risk management", "value at risk", "stress test", "basel", "capital adequacy",
        "credit risk", "market risk", "volatility", "风控", "风险",
    ],
    "economics_macro": [
        "economic", "macro", "gdp", "inflation", "central bank", "federal reserve", "fomc", "monetary",
    ],
    "filings_reports": [
        "sec filing", "10 k", "10k", "earnings call", "annual report", "financial report",
        "financial document", "financial statement", "edgar", "financial qa", "financial question",
        "prospectus", "pitch book", "proxy statement", "proxy vot", "due diligence", "m&a",
    ],
    "payments": [
        "payment", "transaction", "iso20022", "remittance", "upi ", "checkout", "支付",
    ],
    "tax_accounting": [
        "tax", "accounting", "audit", "invoice", "receipt", "bookkeep", "cpa ", "ledger",
    ],
    "esg_climate": [
        "esg", "climate", "sustainab", "carbon", "net zero", "environmental",
    ],
    "fraud_aml": [
        "fraud", "anti money", "money launder", "aml", "sanction", "kyc", "suspicious", "scam",
        "phishing", "反洗钱",
    ],
}

CATEGORIES: list[str] = list(CATEGORY_KEYWORDS)

_SEPARATORS_RE = re.compile(r"[-_/]")


def _normalize(text: str) -> str:
    # Same transform the other classifiers apply: hyphens, underscores and
    # slashes become spaces so "credit-scoring-model" reads as words, and
    # a leading/trailing space lets a keyword ending in a space ("bank ")
    # match at the end of the text.
    return " " + _SEPARATORS_RE.sub(" ", text.lower()) + " "


# Short keywords that legitimately occur inside a longer token: "usdt" is
# the suffix of every trading-pair symbol (BTCUSDT, BLESSUSDT), so a word
# boundary would miss exactly the crypto models it is there to find. The
# reverse of usecase_classifier._BOUNDARY_KEYWORDS.
_SUBSTRING_OK = {"usdt"}


def _keyword_matches(kw: str, text: str) -> bool:
    if len(kw.strip()) <= 4 and kw.isascii() and kw not in _SUBSTRING_OK:
        return re.search(r"\b" + re.escape(kw.strip()) + r"\b", text) is not None
    return kw in text


_OWNER_SLASH_NAME_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def _describing_name(name: str) -> str:
    # For an "owner/repo" or "org/model" name, only the second half describes
    # the system; the owner is provenance. Left in, every repo ING Bank
    # publishes tags as banking -- popmon, a dataframe monitor, included --
    # which un-hides exactly the bank-org mining leak the NULL rule exists
    # to hide. A curated name with a slash in its prose ("Distress / Crisis
    # Support") has spaces and is left whole.
    return name.split("/", 1)[1] if _OWNER_SLASH_NAME_RE.match(name) else name


def assign_categories(name: str, description: str | None, evidence: str | None) -> list[str]:
    """Categories for one use case, in CATEGORY_KEYWORDS order. evidence is
    the row's real prose -- the model card's opening (card_prose_head) or
    the README -- and may be empty. Returns [] when nothing matches; the
    caller stores that as NULL."""
    text = _normalize(f"{_describing_name(name)} {description or ''} {evidence or ''}")
    return [cat for cat, kws in CATEGORY_KEYWORDS.items() if any(_keyword_matches(k, text) for k in kws)]
