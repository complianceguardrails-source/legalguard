"""
Earth-observation capabilities that were not built for finance, and the
financial decision each one could feed.

The catalogue's promise is that every use case is a real system published
on GitHub or the Hub. These are too -- but they are not financial
systems, and nothing here pretends otherwise. A flood-inundation model is
a flood-inundation model; what it *could* do is tell a lender which of
its collateral sits in the floodplain, and that is a different claim,
made by a person who joins it to a loan book.

So each rule states three things: the capability, the financial decision
it could feed, and what would have to be true first. The third is the
honest part -- it is where the work actually is, and it is why these are
kept apart from systems already doing the job.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Translation:
    id: str
    capability: str  # what the system does today
    application_short: str  # the financial decision in three or four words
    application: str  # the same decision, in full
    prerequisite: str  # what a firm would have to supply or establish first
    categories: list[str]  # the financial categories that decision belongs to
    patterns: list[str]  # how the capability is recognised in name/description
    queries: list[str] = field(default_factory=list)  # GitHub discovery

    def matches(self, text: str) -> list[str]:
        return [p for p in self.patterns if re.search(p, text, re.I)]


TRANSLATIONS: list[Translation] = [
    Translation(
        "flood_exposure",
        "Maps flood extent or inundation depth from imagery or terrain.",
        "Collateral flood exposure",
        "Physical-risk exposure of property collateral, and catastrophe pricing for the same book -- which loans or policies sit in the floodplain, and how deep.",
        "The firm's own book, geocoded, joined to the hazard layer. The model says where the water goes, not what it costs you.",
        ["credit_lending", "insurance", "risk_management"],
        [r"\bflood", r"\binundation", r"\bwater level\b"],
        ["flood inundation mapping deep learning in:name,description", "flood extent segmentation satellite in:name,description"],
    ),
    Translation(
        "building_stock",
        "Detects building footprints, roofs or damage from aerial or satellite imagery.",
        "Property valuation",
        "Property valuation and insurance underwriting: what is actually on the parcel, its condition, and whether it matches the file.",
        "A link from footprint to property identifier, and a valuation model that will accept imagery as evidence. The interagency AVM quality-control standards apply once it informs a mortgage decision.",
        ["credit_lending", "insurance"],
        [r"building footprint", r"\broof\b", r"building damage", r"building segmentation"],
        ["building footprint segmentation in:name,description", "roof damage detection aerial in:name,description"],
    ),
    Translation(
        "crop_condition",
        "Classifies crop type or tracks crop condition and yield from satellite time series.",
        "Crop insurance & commodities",
        "Crop insurance assessment and commodity positions -- what is growing where, and how the season is going, before the official statistics say so.",
        "Ground truth for the region in question, and -- if it informs trading -- the market-abuse controls that come with acting on non-public information.",
        ["insurance", "trading_markets"],
        [r"crop type", r"crop classif", r"\bndvi\b", r"crop yield", r"agricultur\w+ (monitor|remote sensing)"],
        ["crop type classification sentinel in:name,description", "crop monitoring NDVI time series in:name,description"],
    ),
    Translation(
        "land_change",
        "Detects land-cover change, including forest loss, from multi-date imagery.",
        "Deforestation due diligence",
        "Deforestation-free due diligence under the EU Deforestation Regulation, and verification of green claims a product or issuer makes.",
        "Plot geolocation from the operator's own due-diligence statement. The regulation binds the operator, not the bank; this evidences their claim rather than replacing it.",
        ["compliance_legal", "esg_climate"],
        [r"land cover", r"land use change", r"change detection", r"deforestation", r"forest loss"],
        ["land cover change detection in:name,description", "forest loss detection satellite in:name,description"],
    ),
    Translation(
        "wildfire_exposure",
        "Maps wildfire perimeters, burn severity or fire risk.",
        "Catastrophe exposure",
        "Catastrophe exposure in property and insurance books, and the physical-risk half of a climate scenario.",
        "The book geocoded against the hazard layer, and a view on how the hazard shifts under a warming scenario rather than the historical record.",
        ["insurance", "credit_lending", "risk_management"],
        [r"wildfire", r"burn severity", r"fire risk", r"burned area"],
        ["wildfire burn severity mapping in:name,description", "burned area detection sentinel in:name,description"],
    ),
    Translation(
        "emissions_plume",
        "Detects methane or other emissions plumes from satellite spectra.",
        "Transition risk",
        "Transition-risk assessment of an issuer or borrower, and verification of what a sustainability claim asserts about its operations.",
        "Attribution of a plume to an operator and an asset. Detection is not attribution, and a claim built on the wrong asset is the greenwashing risk in reverse.",
        ["esg_climate", "risk_management"],
        [r"methane", r"\bplume\b", r"emission\w* detect", r"\bghg\b"],
        ["methane plume detection satellite in:name,description", "emissions monitoring satellite in:name,description"],
    ),
    Translation(
        "vessel_movement",
        "Tracks vessels from AIS or radar imagery, including dark vessels.",
        "Sanctions screening",
        "Sanctions screening and trade finance: whether a shipment moved as the documents say, and whether the vessel called somewhere it should not have.",
        "The sanctions lists and the trade documents to check against. Movement alone is evidence, not a finding.",
        ["fraud_aml", "compliance_legal"],
        [r"\bais\b.{0,20}(vessel|ship|maritime)", r"vessel track", r"dark vessel", r"maritime.{0,20}(monitor|intelligen)"],
        ["vessel detection satellite imagery in:name,description", "dark vessel detection AIS in:name,description"],
    ),
    Translation(
        "eo_foundation",
        "A general-purpose earth-observation foundation model or benchmark.",
        "Base model to fine-tune",
        "The base capability the rest of this list is fine-tuned from -- flood, crop, building and change detection all start here.",
        "A financial task to fine-tune it on, and the evaluation to show it works on that task rather than on the benchmark.",
        ["risk_management"],
        [r"foundation model.{0,30}(earth|remote sensing|geospatial)", r"\bprithvi\b", r"terramind", r"geospatial foundation"],
        ["geospatial foundation model in:name,description"],
    ),
]

BY_ID = {t.id: t for t in TRANSLATIONS}


def translate(name: str, description: str | None) -> Translation | None:
    """The first capability this system matches, or None. First rather
    than best: the list is ordered from the most specific capability to
    the most general, and a system that is several of these is listed
    under the one a reader would look for it under."""
    text = f"{name} {description or ''}"
    for t in TRANSLATIONS:
        if t.matches(text):
            return t
    return None


def all_queries() -> list[str]:
    return [q for t in TRANSLATIONS for q in t.queries]


# The Hub's search matches model ids, so the queries are the words that
# appear in a model's name rather than GitHub's field-scoped syntax.
HF_QUERIES = [
    "building footprint", "flood segmentation", "crop classification", "land cover",
    "change detection satellite", "burned area", "methane", "vessel detection",
    "remote sensing", "satellite segmentation", "prithvi", "terramind",
]


def hf_queries() -> list[str]:
    return HF_QUERIES
