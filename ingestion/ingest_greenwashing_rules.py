"""
The two greenwashing rules that don't come from EUR-Lex: the FCA's
anti-greenwashing rule (ESG 4.3.1R, from the FCA Handbook) and the SEC's
Investment Company Names rule (from the Federal Register). Both are
fetched from the regulator's own text -- nothing here is paraphrased --
and upserted like every other source.

    DATABASE_URL=postgres://... python ingest_greenwashing_rules.py [--dry-run]
"""
from __future__ import annotations

import argparse
import html
import logging
import re
import sys

import requests

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.ingest_greenwashing")

_HEADERS = {"User-Agent": "legalguard-ingest/1.0 (+https://github.com/complianceguardrails-source/legalguard)"}

FCA_ESG_4_3_URL = "https://www.handbook.fca.org.uk/handbook/ESG/4/3.html"
FR_DOCUMENT_URL = "https://www.federalregister.gov/api/v1/documents/{number}.json"
SEC_NAMES_RULE_DOCUMENT = "2023-20793"  # Investment Company Names, final rule, 88 FR 70436


def fetch_fca_anti_greenwashing_rule() -> dict:
    """ESG 4.3.1R as published in the Handbook: the rule's own text, from
    its number to the next rule's heading."""
    resp = requests.get(FCA_ESG_4_3_URL, headers=_HEADERS, timeout=60, allow_redirects=True)
    resp.raise_for_status()
    page = resp.text
    start = page.find("4.3.1")
    end = page.find("ESG 4.3.2", start)
    if start < 0 or end < 0:
        raise RuntimeError("FCA Handbook page no longer has ESG 4.3.1 where expected")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page[start:end]))).strip()
    # The rule text begins after its date/status stamp ("4.3.1 28/02/2025 R").
    m = re.match(r"4\.3\.1\s+(\d{2}/\d{2}/\d{4})\s+R\s+(.*)$", text)
    if not m:
        raise RuntimeError(f"unexpected ESG 4.3.1 layout: {text[:120]!r}")
    stamp, body = m.group(1), m.group(2).strip()
    day, month, year = stamp.split("/")
    body = body.split(" Use of sustainability-related terms")[0].strip()
    return {
        "jurisdiction": "UK",
        "issuing_body": "FCA",
        "clause_identifier": "ESG-4.3.1R-AntiGreenwashing",
        "official_title": "FCA Handbook ESG 4.3.1R -- Anti-greenwashing rule",
        "title": "FCA anti-greenwashing rule (ESG 4.3.1R)",
        "source_url": resp.url,
        "statutory_text": body,
        "version_label": f"ESG4.3.1R-{year}-{month}-{day}",
        "publication_date": f"{year}-{month}-{day}",
        # PS23/16: the anti-greenwashing rule applied from 31 May 2024.
        "effective_date": "2024-05-31",
        "risk_level": None,
        "ingestion_source": "manual",
        "origin_driver_category": "market_scandal",
        "origin_driver_description": "Adopted with the Sustainability Disclosure Requirements after FCA supervisory work found sustainability claims in fund marketing that the products' characteristics did not support.",
    }


def fetch_sec_names_rule() -> dict:
    resp = requests.get(FR_DOCUMENT_URL.format(number=SEC_NAMES_RULE_DOCUMENT), headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    doc = resp.json()
    agencies = ", ".join(a.get("name", "") for a in doc.get("agencies", [])) or "Securities and Exchange Commission"
    return {
        "jurisdiction": "US",
        "issuing_body": agencies,
        "clause_identifier": doc["document_number"],
        "official_title": doc["title"],
        "title": "SEC Investment Company Names rule (2023 amendments)",
        "source_url": doc["html_url"],
        # Same choice as sources/federal_register.py: the abstract is the
        # structured summary the API exposes; the full XML is linked.
        "statutory_text": doc.get("abstract") or doc["title"],
        "version_label": "v1",
        "publication_date": doc.get("publication_date"),
        "effective_date": doc.get("effective_on"),
        "risk_level": None,
        "ingestion_source": "federal_register",
        "origin_driver_category": "market_scandal",
        "origin_driver_description": "Extends the 80% investment policy requirement to names suggesting ESG or similar characteristics, after fund names were found to promise sustainability the portfolios did not deliver.",
    }


def run(dry_run: bool) -> None:
    docs = [fetch_fca_anti_greenwashing_rule(), fetch_sec_names_rule()]
    for d in docs:
        logger.info("%s | %s | eff=%s | %d chars", d["clause_identifier"], d["official_title"], d["effective_date"], len(d["statutory_text"]))
        if dry_run:
            logger.info("  %s", d["statutory_text"][:400])
    if dry_run:
        return
    with db.get_conn() as conn:
        for d in docs:
            db.upsert_regulation(conn, **d)
            logger.info("Upserted %s", d["clause_identifier"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    try:
        run(parser.parse_args().dry_run)
    except (requests.RequestException, RuntimeError) as exc:
        logger.error(str(exc))
        sys.exit(1)
