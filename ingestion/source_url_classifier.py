"""
Classifies a regulation's source_url as pointing at the actual issuing
regulator's own page ("primary") versus a secondary mirror, summary, or
commentary site (news, law firm, think tank, commercial compliance tool,
Wikipedia, academic mirror). Curated lists like ethicalml's often link to
whichever explains a law best -- sometimes that's the regulator, sometimes
a KPMG summary or Wikipedia -- and silently treating all of them as
authoritative would overstate how well-traced these entries actually are.

This is a domain-pattern heuristic, not a certified legal determination:
a URL on an unrecognized domain is classified "unknown" (needs manual
verification) rather than guessed either way.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# Domain suffixes/hosts genuinely operated by the regulator/government body
# itself. Deliberately specific (not just ".gov") where a body has a
# distinctive non-generic domain, e.g. the UK FCA uses .org.uk, not .gov.uk.
    # NOTE: every pattern uses (^|\.) rather than a bare leading \. -- a
    # leading \. only matches when there's a subdomain in front of it
    # (e.g. "www.ico.org.uk"), and silently misses the bare domain itself
    # ("ico.org.uk" with no subdomain), which is exactly how several of
    # these sites are actually linked in practice. Confirmed by testing
    # against real data: the bare-domain form is common enough that the
    # naive pattern misclassified real regulator pages as "unknown".
_PRIMARY_DOMAIN_PATTERNS = [
    r"(^|\.)gov$", r"(^|\.)gov\.", r"(^|\.)mil$",   # generic government TLD patterns
    r"(^|\.)gc\.ca$", r"(^|\.)canada\.ca$",           # Canada federal government
    r"(^|\.)admin\.ch$", r"(^|\.)fedlex\.admin\.ch$", # Switzerland federal government
    r"(^|\.)gv\.at$",                                 # Austria federal government
    r"(^|\.)leg\.br$", r"(^|\.)senado\.leg\.br$",     # Brazil federal legislature
    r"(^|\.)europa\.eu$",                             # official EU institution domains
    r"(^|\.)fca\.org\.uk$",                           # UK Financial Conduct Authority
    r"(^|\.)ico\.org\.uk$",                           # UK Information Commissioner's Office
    r"(^|\.)legislation\.gov\.uk$",                   # UK official legislation database
    r"(^|\.)cac\.gov\.cn$",                           # China Cyberspace Administration
    r"(^|\.)ai\.gov\.ae$", r"(^|\.)smartdubai\.ae$",  # UAE official AI bodies
    r"(^|\.)oecd\.ai$", r"(^|\.)oecd\.org$",          # OECD is itself the issuing intergovernmental body for its own publications
    r"(^|\.)bmvi\.de$", r"(^|\.)bmwk\.de$", r"(^|\.)bmi\.de$", r"(^|\.)bmj\.de$",  # German federal ministries (Bundesministerium)
]

# Known secondary sources: real, often high-quality, but NOT the regulator
# that issued the instrument -- news, think tanks, consultancies, academic
# mirrors, commercial compliance tools, or crowd-edited references.
_SECONDARY_DOMAINS = {
    "en.wikipedia.org", "wikipedia.org",
    "www.csis.org", "csis.org",
    "assets.kpmg", "kpmg.com",
    "www.newamerica.org", "newamerica.org",
    "www.globalprivacyblog.com", "globalprivacyblog.com",
    "eucomplyhub.com", "www.eucomplyhub.com",
    "www.setaicomply.com", "setaicomply.com",
    "gdpr.eu", "www.gdpr.eu",
    "artificialintelligenceact.eu", "www.artificialintelligenceact.eu",
    "en.pkulaw.cn",
    "epic.org", "www.epic.org",
    "www.ania.org.mx", "ania.org.mx",
    "www.loc.gov",  # US Library of Congress: authoritative, but a research
                     # body summarizing the law, not the issuing regulator
    "www.ailawsbystate.com", "ailawsbystate.com",  # third-party tracker
    "www.nesta.org.uk", "nesta.org.uk",            # UK innovation charity, not a regulator
    "inventory.algorithmwatch.org", "algorithmwatch.org",  # NGO watchdog, not a regulator
    "www.law.cornell.edu", "law.cornell.edu",      # Cornell LII: authoritative academic mirror of US law, not the government's own site
    "www.execxai.com", "execxai.com",              # their own atlas/tracker page, not the regulator being described
    "github.com",                                   # community-contributed resources, not an official source
}


def classify_source_url(url: str) -> tuple[str, str]:
    """Returns (classification, reason) where classification is one of
    'primary', 'secondary', 'unknown'."""
    if isinstance(url, bytes):
        url = url.decode("utf-8", errors="replace")
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "unknown", "Could not parse URL"

    if host in _SECONDARY_DOMAINS:
        return "secondary", f"{host} is a known secondary source (news/think-tank/commercial/reference mirror), not the issuing body's own site"

    for pattern in _PRIMARY_DOMAIN_PATTERNS:
        if re.search(pattern, host):
            return "primary", f"{host} matches a recognized government/regulator domain pattern"

    return "unknown", f"{host} does not match a recognized primary or secondary pattern -- verify manually"
