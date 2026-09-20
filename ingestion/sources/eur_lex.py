"""
EUR-Lex regulation source: fetches EU financial-services legislation from
EUR-Lex, splits it into articles, and returns the AI-relevant articles as
specific_regulations rows, ingestion_source='eur_lex'.

Why this exists: every other regulation source here ingests regulation
ABOUT AI -- the Federal Register queries, the curated AI-governance atlas,
the hand-entered AI Act articles. For a financial-AI compliance product
that left MiFID II, MAR and DORA entirely absent (zero rows), while a CRO
deploying a trading model cares about MiFID II Article 17 far more than
AI Act Article 27. This is the first source that ingests the financial
regulation itself.

Two real, unauthenticated endpoints, both verified live:

  CELLAR SPARQL (publications.europa.eu/webapi/rdf/sparql) -- the
  Publications Office's linked-data endpoint. Used for an act's official
  title, its document date, and to enumerate its consolidated versions.

  EUR-Lex HTML (eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:..)
  -- the act's full text. Consolidated texts (CELEX starting "0", suffixed
  with the consolidation date) carry every amendment to that date and are
  marked up per article as <div class="eli-subdivision" id="art_N">, which
  is what makes article-level splitting reliable.

The newest consolidation is preferred, resolved at run time rather than
pinned, so the rows always reflect current law. version_label is the
consolidated CELEX actually used, and it is part of the upsert's conflict
key -- a later consolidation therefore produces a NEW version row instead
of silently overwriting the text an existing guardrail was mapped to.
EUR-Lex lists a consolidation in CELLAR before its HTML is generated
(the newest MiFID II consolidation answered HTTP 202 with an empty body
when this was written), so candidates are tried newest-first and the first
one actually served wins.

Article selection is editorial and deliberately explicit: each act below
lists the articles that bear on algorithmic or AI systems, with a reason.
MiFID II alone has 92 articles in its current consolidation, most about
authorisation, passporting and supervisory cooperation; ingesting all of
them would bury the five that matter under eighty-seven that don't.
Setting articles=None ingests every article, for a reader who wants that.

What is a fact here and what is a judgement:
  - Text, title, article headings, document date: fetched, never typed.
  - application_date: NOT available from CELLAR for these acts (checked;
    only MiFID II exposes even an entry-into-force date, and that is not
    the date obligations applied). Each act's entry cites the article
    that sets it. This is the only hand-entered value per act.
  - risk_level: left NULL. It is the EU AI Act's risk tier and does not
    apply to a financial-conduct article; assigning one would be a guess.
  - origin_driver_category: 'standards_harmonization' -- the stated
    purpose of single-market financial legislation, and the same value
    the AI Act rows carry.
"""
from __future__ import annotations

import html as html_mod
import logging
import re
import time
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
HTML_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}"
_HEADERS = {"User-Agent": "LegalGuard-RegulationIngest/1.0"}
_CDM = "http://publications.europa.eu/ontology/cdm#"


@dataclass(frozen=True)
class EurLexAct:
    base_celex: str
    short_name: str
    clause_prefix: str
    application_date: str
    application_source: str
    # article number -> why it is here. None ingests every article.
    articles: dict[str, str] | None = field(default=None)


ACTS: list[EurLexAct] = [
    EurLexAct(
        base_celex="32014L0065",
        short_name="MiFID II",
        clause_prefix="MIFID2",
        application_date="2018-01-03",
        application_source="Art. 93(1) MiFID II as amended by Directive (EU) 2016/1034 Art. 1(7)",
        articles={
            "16": "Organisational requirements: systems, controls and record-keeping for any firm running automated processes",
            "17": "Algorithmic trading: resilience, capacity, kill functionality, notification and testing obligations",
            "24": "Information to clients must be fair, clear and not misleading -- binds LLM-generated client communications",
            "25": "Suitability and appropriateness assessment -- the obligation robo-advice automates",
            "27": "Best execution -- binds automated order routing",
        },
    ),
    EurLexAct(
        base_celex="32014R0596",
        short_name="MAR",
        clause_prefix="MAR",
        application_date="2016-07-03",
        application_source="Art. 39(2) Regulation (EU) No 596/2014",
        articles={
            "12": "Market manipulation, including algorithmic and high-frequency strategies named in Art. 12(2)(c)",
            "14": "Prohibition of insider dealing -- binds any model trained on or acting upon non-public information",
            "15": "Prohibition of market manipulation",
            "16": "Prevention and detection of market abuse -- the surveillance obligation AI monitoring tools serve",
            "20": "Investment recommendations: objectivity and disclosure -- binds generated research and analysis",
        },
    ),
    EurLexAct(
        base_celex="32022R2554",
        short_name="DORA",
        clause_prefix="DORA",
        application_date="2025-01-17",
        application_source="Art. 64 Regulation (EU) 2022/2554",
        articles={
            "5": "Governance and organisation: management body accountability for ICT risk",
            "6": "ICT risk management framework -- covers models and AI services as ICT systems",
            "8": "Identification of ICT-supported business functions and their dependencies",
            "9": "Protection and prevention: security of ICT systems and data",
            "28": "General principles for managing ICT third-party risk -- binds use of external model and API providers",
            "30": "Key contractual provisions for ICT third-party services",
        },
    ),
]


class EurLexError(Exception):
    pass


def _sparql(query: str) -> list[dict]:
    resp = requests.get(
        SPARQL_URL,
        params={"query": query},
        headers={**_HEADERS, "Accept": "application/sparql-results+json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def consolidated_celex_candidates(base_celex: str) -> list[str]:
    """Consolidated CELEX numbers for an act, newest first, then the base
    act itself as the final fallback. Consolidations are "0" + the base
    number's tail + "-YYYYMMDD"."""
    rows = _sparql(
        f'PREFIX cdm: <{_CDM}> SELECT ?celex WHERE {{ ?w cdm:resource_legal_id_celex ?celex . '
        f'FILTER(STRSTARTS(STR(?celex), "0{base_celex[1:]}-")) }} ORDER BY DESC(?celex)'
    )
    return [r["celex"]["value"] for r in rows] + [base_celex]


def fetch_act_metadata(base_celex: str) -> dict:
    """Official English title and document date from CELLAR. Returns an
    empty dict if CELLAR has nothing, so the caller can fall back to the
    act's short name rather than fail the whole act."""
    rows = _sparql(
        f'PREFIX cdm: <{_CDM}> SELECT ?title ?date WHERE {{ '
        f'?w cdm:resource_legal_id_celex "{base_celex}"^^<http://www.w3.org/2001/XMLSchema#string> . '
        f'OPTIONAL {{ ?w cdm:work_date_document ?date }} '
        f'OPTIONAL {{ ?e cdm:expression_belongs_to_work ?w ; '
        f'cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> ; '
        f'cdm:expression_title ?title }} }} LIMIT 1'
    )
    if not rows:
        return {}
    row = rows[0]
    return {
        "title": row.get("title", {}).get("value"),
        "document_date": row.get("date", {}).get("value"),
    }


def fetch_act_html(base_celex: str) -> tuple[str, str]:
    """(consolidated CELEX actually used, its HTML). Walks candidates
    newest-first; a 202 with an empty body, or a page with no article
    divs, means EUR-Lex hasn't generated that consolidation yet."""
    for celex in consolidated_celex_candidates(base_celex):
        resp = requests.get(HTML_URL.format(celex=celex), headers=_HEADERS, timeout=90, allow_redirects=True)
        time.sleep(1.0)
        if resp.status_code != 200 or 'id="art_' not in resp.text:
            logger.info("%s: not served yet (HTTP %s, %d bytes) -- trying an older consolidation",
                        celex, resp.status_code, len(resp.content))
            continue
        return celex, resp.text
    raise EurLexError(f"no servable text found for {base_celex}")


_ART_OPEN_RE = re.compile(r'<div class="eli-subdivision" id="art_([0-9]+[a-z]*)">')
_TAG_RE = re.compile(r"<[^>]+>")
# Consolidated texts mark headings title-article-norm / stitle-article-norm;
# the original OJ text of an act that has never been consolidated (DORA,
# at time of writing) marks them oj-ti-art / oj-sti-art. Same structure,
# different class names.
_TITLE_RE = re.compile(r'class="(?:title-article-norm|oj-ti-art)"[^>]*>(.*?)</p>', re.S)
_SUBTITLE_RE = re.compile(r'class="(?:stitle-article-norm|oj-sti-art)"[^>]*>(.*?)</p>', re.S)


def _text(fragment: str) -> str:
    return html_mod.unescape(re.sub(r"\s+", " ", _TAG_RE.sub(" ", fragment))).strip()


def _block_at(doc: str, start: int) -> str:
    """The <div> opening at start, through its matching </div>."""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", doc[start:]):
        depth += 1 if m.group().startswith("<div") else -1
        if depth == 0:
            return doc[start : start + m.end()]
    return doc[start:]


def split_articles(doc: str) -> dict[str, dict]:
    """article number -> {heading, text} for every top-level article div.
    Nested ids (art_17.tit_1) are not matched by the opening regex, so
    only whole articles are returned."""
    articles: dict[str, dict] = {}
    for m in _ART_OPEN_RE.finditer(doc):
        number = m.group(1)
        if number in articles:
            continue
        block = _block_at(doc, m.start())
        title = _TITLE_RE.search(block)
        subtitle = _SUBTITLE_RE.search(block)
        articles[number] = {
            "label": _text(title.group(1)) if title else f"Article {number}",
            "heading": _text(subtitle.group(1)) if subtitle else "",
            "text": _text(block),
        }
    return articles


def _camel(heading: str, max_len: int = 60) -> str:
    """CamelCase of a heading, cut at a word boundary rather than mid-word."""
    out = ""
    for word in re.findall(r"[A-Za-z0-9]+", heading):
        piece = word[:1].upper() + word[1:]
        if out and len(out) + len(piece) > max_len:
            break
        out += piece
    return out


def mine_eur_lex_regulations(acts: list[EurLexAct] = ACTS) -> list[dict]:
    """Rows ready for db.upsert_regulation(**row). One row per selected
    article. An act whose text can't be fetched is skipped with a logged
    error, not allowed to fail the others."""
    rows: list[dict] = []
    for act in acts:
        try:
            meta = fetch_act_metadata(act.base_celex)
        except requests.RequestException:
            logger.exception("%s: CELLAR metadata fetch failed, continuing without it", act.short_name)
            meta = {}
        try:
            celex, doc = fetch_act_html(act.base_celex)
        except (requests.RequestException, EurLexError):
            logger.exception("%s: could not fetch act text, skipping", act.short_name)
            continue

        articles = split_articles(doc)
        wanted = act.articles.keys() if act.articles else articles.keys()
        missing = [n for n in wanted if n not in articles]
        if missing:
            logger.warning("%s (%s): articles not found in text: %s", act.short_name, celex, missing)

        act_title = meta.get("title") or act.short_name
        before = len(rows)
        for number in wanted:
            if number not in articles:
                continue
            art = articles[number]
            heading = art["heading"]
            rows.append({
                "jurisdiction": "EU",
                "issuing_body": "European Parliament and Council",
                "clause_identifier": f"{act.clause_prefix}-ART{number}-{_camel(heading)}"[:150],
                "official_title": f"{act.short_name} Article {number} -- {heading}" if heading else f"{act.short_name} Article {number}",
                "title": f"{act.short_name} Article {number} -- {heading}" if heading else f"{act.short_name} Article {number}",
                "source_url": HTML_URL.format(celex=celex) + f"#art_{number}",
                "statutory_text": art["text"],
                "version_label": celex[:30],
                "publication_date": meta.get("document_date"),
                "effective_date": act.application_date,
                "risk_level": None,
                "ingestion_source": "eur_lex",
                "origin_driver_category": "standards_harmonization",
                "origin_driver_description": (
                    f"{act_title}. Selected because: {act.articles[number]}. "
                    f"Application date per {act.application_source}."
                    if act.articles else f"{act_title}. Application date per {act.application_source}."
                ),
            })
        logger.info("%s: %d article(s) from %s", act.short_name, len(rows) - before, celex)
    return rows
