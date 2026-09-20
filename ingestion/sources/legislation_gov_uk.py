"""
UK legislation from legislation.gov.uk, provision by provision.

The site serves every act, and every section or schedule paragraph of it,
as XML at <act uri>/<provision>/data.xml, in force as of the date the
site last revised it (dct:valid). Unlike EUR-Lex there is no article
markup convention to walk: each provision is fetched on its own and the
<P1> element carrying that provision's id is its text. Provisions are
named the way the site names them ("schedule/7A/paragraph/2", "section/98").

First instrument: biodiversity net gain -- Schedule 7A to the Town and
Country Planning Act 1990, inserted by Schedule 14 to the Environment Act
2021. It is planning law binding developers; it reaches finance through
development and property lending (the obligation is a cost on the land
being financed) and through nature-market claims (statutory biodiversity
credits). The rule that attaches it says exactly that.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "legalguard-ingest/1.0 (+https://github.com/complianceguardrails-source/legalguard)"}
DATA_URL = "https://www.legislation.gov.uk/{act}/{provision}/data.xml"
PAGE_URL = "https://www.legislation.gov.uk/{act}/{provision}"


@dataclass(frozen=True)
class UkProvision:
    provision: str  # as the site names it, e.g. "schedule/7A/paragraph/2"
    label: str  # human label for the title, e.g. "Sch. 7A para. 2"
    heading: str
    why: str


@dataclass(frozen=True)
class UkAct:
    act: str  # site path, e.g. "ukpga/1990/8"
    short_name: str
    clause_prefix: str
    issuing_body: str
    application_date: str
    application_source: str
    provisions: list[UkProvision]


ACTS: list[UkAct] = [
    UkAct(
        act="ukpga/1990/8",
        short_name="Biodiversity net gain (TCPA 1990 Sch. 7A)",
        clause_prefix="UK-BNG",
        issuing_body="UK Parliament",
        application_date="2024-02-12",
        application_source="Environment Act 2021 (Commencement No. 8 and Transitional Provisions) Regulations 2024 (SI 2024/44): mandatory BNG for major development from 12 February 2024",
        provisions=[
            UkProvision("schedule/7A/paragraph/1", "Sch. 7A para. 1", "Overview and interpretation",
                        "Defines biodiversity value, onsite habitat and the biodiversity metric -- the terms any valuation or credit model must use as the statute uses them"),
            UkProvision("schedule/7A/paragraph/2", "Sch. 7A para. 2", "Biodiversity gain objective",
                        "The 10% net gain objective and how the post-development value, offsite gains and biodiversity credits add up -- the cost a development-lending model must price"),
            UkProvision("schedule/7A/paragraph/13", "Sch. 7A para. 13", "Biodiversity gain condition",
                        "Planning permission is deemed subject to the condition that a biodiversity gain plan is approved before development begins -- the gating event for drawdown on a development loan"),
        ],
    ),
]


def _fetch_provision(act: str, provision: str) -> tuple[str, str]:
    """(text, valid_date) for one provision, from its own data.xml."""
    resp = requests.get(DATA_URL.format(act=act, provision=provision), headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    xml = resp.text
    element_id = provision.replace("/", "-")
    m = re.search(rf'<P1 [^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</P1>', xml, re.S)
    if not m:
        raise RuntimeError(f"{act}/{provision}: no <P1 id={element_id}> in the XML")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
    valid = re.search(r"<dct:valid>([^<]+)", xml)
    return text, (valid.group(1) if valid else "")


def mine_uk_legislation() -> list[dict]:
    rows: list[dict] = []
    for act in ACTS:
        for prov in act.provisions:
            try:
                text, valid = _fetch_provision(act.act, prov.provision)
            except (requests.RequestException, RuntimeError) as exc:
                logger.error("%s %s: %s", act.short_name, prov.provision, exc)
                continue
            number = prov.provision.rsplit("/", 1)[-1]
            slug = re.sub(r"[^A-Za-z0-9]+", "", prov.heading.title())
            rows.append({
                "jurisdiction": "UK",
                "issuing_body": act.issuing_body,
                "clause_identifier": f"{act.clause_prefix}-PARA{number}-{slug}",
                "official_title": f"{act.short_name} {prov.label} -- {prov.heading}",
                "title": f"Biodiversity net gain -- {prov.label} {prov.heading}",
                "source_url": PAGE_URL.format(act=act.act, provision=prov.provision),
                "statutory_text": text,
                # The site's own revision date is the version: a later
                # amendment changes it, and the row is re-upserted under it.
                "version_label": f"lgu-{valid}"[:30],
                "publication_date": valid or None,
                "effective_date": act.application_date,
                "risk_level": None,
                "ingestion_source": "manual",
                "origin_driver_category": "standards_harmonization",
                "origin_driver_description": f"{act.application_source}. Selected because: {prov.why}",
            })
            logger.info("%s: %s (%d chars, valid %s)", act.short_name, prov.provision, len(text), valid)
    return rows
