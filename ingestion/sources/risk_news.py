"""
Headlines from trusted financial outlets and regulators, via their RSS
feeds, mapped onto the risk taxonomy (risk_news_keywords.py).

Why RSS: paywalled outlets do not expose article text, but every one of
them publishes title + summary + link as RSS, which is enough to decide
whether a story is about an AI risk and to send the reader to it. Nothing
is copied beyond what the feed itself distributes. Where an outlet has no
feed of its own (Reuters, Bloomberg) the Google News RSS query for that
outlet is used, which returns the outlet's headline and link.

Allowlist, not discovery: only the outlets and regulators named here.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests

from risk_news_keywords import is_about_ai, match_risks
from risk_taxonomy import BY_SLUG

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "legalguard-ingest/1.0 (+https://github.com/complianceguardrails-source/legalguard)"}


def _gnews(query: str) -> str:
    return "https://news.google.com/rss/search?q=" + requests.utils.quote(query) + "&hl=en-US&gl=US&ceid=US:en"


@dataclass(frozen=True)
class Feed:
    outlet: str  # "" = take the outlet from the item itself (Google News query feeds)
    kind: str  # news | regulator
    url: str


# Outlets a Google News query feed may return; anything else is dropped.
# Keyed by the domain in the link's "site:" and the name Google appends.
ALLOWED_OUTLETS = {
    "Financial Times": "ft.com", "The Wall Street Journal": "wsj.com", "Reuters": "reuters.com",
    "Bloomberg": "bloomberg.com", "Bloomberg.com": "bloomberg.com", "CNBC": "cnbc.com",
    "The Economist": "economist.com", "American Banker": "americanbanker.com", "Finextra": "finextra.com",
}
_SITES = " OR ".join(f"site:{d}" for d in sorted(set(ALLOWED_OUTLETS.values())))


def _family_query(terms: str) -> str:
    # Recent only, from the allowlisted outlets, with AI in the story.
    # Without a when: filter Google News happily returns 2016 articles.
    return _gnews(f'({terms}) (AI OR "artificial intelligence" OR algorithm OR chatbot OR "machine learning") ({_SITES}) when:60d')


FAMILY_QUERY_FEEDS: list[Feed] = [
    Feed("", "news", _family_query('"flash crash" OR herding OR procyclical OR "liquidity" OR "systemic risk"')),
    Feed("", "news", _family_query('hallucination OR hallucinated OR "wrong answers" OR "black box" OR explainability OR "model risk"')),
    Feed("", "news", _family_query('deepfake OR "voice clone" OR "prompt injection" OR "data poisoning" OR phishing OR "synthetic identity"')),
    Feed("", "news", _family_query('"AI Act" OR "high-risk" OR copyright OR "human oversight" OR liability')),
    Feed("", "news", _family_query('"concentration risk" OR outage OR "third-party" OR "supply chain attack" OR "open source" vulnerability')),
    Feed("", "news", _family_query('bias OR discrimination OR redlining OR "vulnerable customers" OR "robo-advisers"')),
    Feed("", "news", _family_query('"data centre" OR "data center" OR greenwashing OR "net zero" OR "carbon" OR "water"')),
]


FEEDS: list[Feed] = [
    # --- outlets ---
    Feed("Financial Times", "news", "https://www.ft.com/technology?format=rss"),
    Feed("Financial Times", "news", "https://www.ft.com/companies/banks?format=rss"),
    Feed("Financial Times", "news", "https://www.ft.com/markets?format=rss"),
    Feed("Wall Street Journal", "news", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),
    Feed("Wall Street Journal", "news", "https://feeds.content.dowjones.io/public/rss/RSSWSJD"),
    Feed("Reuters", "news", _gnews('site:reuters.com ("artificial intelligence" OR AI) (bank OR finance OR trading OR insurer OR regulator) when:90d')),
    Feed("Bloomberg", "news", _gnews('site:bloomberg.com ("artificial intelligence" OR AI) (bank OR finance OR trading OR insurer OR regulator) when:90d')),
    Feed("CNBC", "news", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),  # Finance
    Feed("CNBC", "news", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),  # Technology
    Feed("The Economist", "news", "https://www.economist.com/finance-and-economics/rss.xml"),
    Feed("American Banker", "news", _gnews('site:americanbanker.com AI when:90d')),
    Feed("Finextra", "news", "https://www.finextra.com/rss/headlines.aspx"),
    # --- regulators ---
    Feed("SEC", "regulator", "https://www.sec.gov/news/pressreleases.rss"),
    Feed("FCA", "regulator", "https://www.fca.org.uk/news/rss.xml"),
    Feed("ESMA", "regulator", "https://www.esma.europa.eu/rss.xml"),
    Feed("BIS", "regulator", "https://www.bis.org/doclist/all_rss.rss"),
    Feed("ECB", "regulator", "https://www.ecb.europa.eu/rss/press.html"),
    Feed("Bank of England", "regulator", "https://www.bankofengland.co.uk/rss/news"),
    Feed("CFPB", "regulator", "https://www.consumerfinance.gov/about-us/newsroom/feed/"),
]


# An item is news only if it reports something that has happened. These
# three guards drop the rest, in order of how certain each one is.
MAX_AGE_DAYS = 400  # a year plus slack, so the corpus stays current
FUTURE_TOLERANCE_HOURS = 36  # timezone and scheduling slack, nothing more

# Pages that are an invitation, not a report. Finextra and the trade press
# publish these through the same feed as their news.
_EVENT_URL_MARKERS = ("/event-info/", "/events/", "/event/", "/webinar", "/webinars/", "/conference",
                      "/whitepaper", "/white-paper", "/research-paper", "/podcast", "/register")
_EVENT_PHRASES = ("webinar", "join us", "register now", "registration", "sign up now", "book your place",
                  "save the date", "keynote", "panel discussion", "roundtable", "fireside chat",
                  "on-demand session", "our upcoming", "this event", "sponsored by", "in partnership with",
                  "tickets", "agenda and speakers", "call for papers", "nominations are open", "awards")


def is_event_announcement(title: str, summary: str, url: str) -> bool:
    if any(m in url.lower() for m in _EVENT_URL_MARKERS):
        return True
    text = f"{title} {summary or ''}".lower()
    return any(p in text for p in _EVENT_PHRASES)


def is_current(published: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """A story with no date is kept (the feed simply did not say); one
    dated in the future is an announcement of something yet to happen, and
    one older than MAX_AGE_DAYS is not news any more."""
    if published is None:
        return True
    now = now or datetime.now(timezone.utc)
    if published > now + timedelta(hours=FUTURE_TOLERANCE_HOURS):
        return False
    return (now - published).days <= MAX_AGE_DAYS


def _published(entry) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _clean(text: str) -> str:
    import html
    import re
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def fetch_feed(feed: Feed) -> list[dict]:
    try:
        resp = requests.get(feed.url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("%s: feed unavailable (%s)", feed.outlet, exc.__class__.__name__)
        return []
    parsed = feedparser.parse(resp.content)
    rows = []
    for e in parsed.entries:
        title = _clean(e.get("title", ""))
        summary = _clean(e.get("summary", "") or e.get("description", ""))
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        # Google News wraps titles as "Headline - Outlet"; keep the headline,
        # and for an outlet-less query feed the outlet is that suffix.
        outlet = feed.outlet
        if "news.google.com" in feed.url and " - " in title:
            title, suffix = title.rsplit(" - ", 1)
            if not outlet:
                if suffix.strip() not in ALLOWED_OUTLETS:
                    continue
                outlet = "Wall Street Journal" if suffix.strip() == "The Wall Street Journal" else suffix.strip().replace("Bloomberg.com", "Bloomberg")
        if not outlet:
            continue
        rows.append({"title": title, "summary": summary[:600], "url": link, "published_at": _published(e), "outlet": outlet})
    return rows


def mine_risk_news() -> list[dict]:
    """Every story from every feed that is about AI and matches a risk."""
    out: list[dict] = []
    skipped_event = skipped_stale = 0
    seen: set[str] = set()  # URLs and normalised titles: the same story reaches us by both
    for feed in FEEDS + FAMILY_QUERY_FEEDS:
        entries = fetch_feed(feed)
        kept = 0
        for e in entries:
            title_key = re.sub(r"[^a-z0-9]+", " ", e["title"].lower()).strip()
            if e["url"] in seen or title_key in seen:
                continue
            if is_event_announcement(e["title"], e["summary"], e["url"]):
                skipped_event += 1
                continue
            if not is_current(e["published_at"]):
                skipped_stale += 1
                continue
            if not is_about_ai(e["title"], e["summary"]):
                continue
            matches = match_risks(e["title"], e["summary"])
            if not matches:
                continue
            seen.add(e["url"])
            seen.add(title_key)
            slugs = sorted(matches)
            out.append({
                **e,
                "outlet_kind": feed.kind,
                "risk_slugs": slugs,
                "families": sorted({BY_SLUG[s]["family"] for s in slugs}),
                "matched_terms": sorted({t for hits in matches.values() for t in hits}),
            })
            kept += 1
        logger.info("%-20s %3d entries, %2d kept", feed.outlet or "(query feed)", len(entries), kept)
        time.sleep(0.5)
    logger.info("dropped %d event announcement(s), %d out-of-date item(s)", skipped_event, skipped_stale)
    return out
