"""
OMEGA-LUQI Free-API Tool Router - decides WHICH tool a query needs.

Deterministic, zero-cost intent detection (no LLM spend on routing): keyword
signals map a query to the free utility APIs. Both tools can fire together
("research papers on water quality in Nairobi" -> literature + geocode).

Extend by adding hints/rules - keep it deterministic and unit-tested.
"""
import requests
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from . import geocoding
from .academic_sources import aggregate_literature

router = APIRouter(prefix="/v1/tools", tags=["Free Utility APIs"])

GEO_HINTS = (
    "near ", "nearby", "closest", "distance between", "how far",
    "coordinates", "latitude", "longitude", "location of", "address of",
    "directions", "map of", "cities in", "towns in", "provinces in",
    "gps", "where is", "in soweto", " in nairobi", " in cape town",
)
POSTCODE_HINTS = ("postcode", "postal code", "zip code", "zip")
KNOWLEDGE_HINTS = ("what is", "definition of", "weather", "wind speed",
                  "unemployment rate", "gdp of", "vocational statistics")
HEALTH_HINTS = ("drug", "medicine", "clinical trial", "compound", "fda label", "rxcui")
IP_HINTS = ("ip address", "ip location", "where is this ip", "visitor location")
LITERATURE_HINTS = (
    "papers", "research", "studies", "citations", "journal", "pubmed",
    "arxiv", "literature", "doi", "bibliography", "peer-reviewed",
)

# map detected tool -> handler availability note (for the response)
TOOLS = {"knowledge": "GET /v1/knowledge/scatter (wiki/meteo/wb/openalex)",
         "health_data": "GET /v1/health-data/{drug,trial,compound,fda-label} (NIH/FDA, keyless)",
         "geocode": "GET /v1/tools/geo/search (Nominatim->Photon chain)",
         "postcode": "GET /v1/tools/geo/postcode/{country}/{code} | /uk | /dach",
         "ip_lookup": "GET /v1/tools/geo/ip (non-commercial terms!)",
         "literature": "GET /v1/research/literature"}


def detect_tools(query: str) -> Dict[str, Any]:
    """Pure decision logic (unit-tested). Returns tools + which hints fired."""
    q = query.lower()
    tools: List[str] = []
    reasons: Dict[str, list] = {}
    geo_hits = [h.strip() for h in GEO_HINTS if h in q]
    if geo_hits:
        tools.append("geocode")
        reasons["geocode"] = geo_hits[:3]
    lit_hits = [h for h in LITERATURE_HINTS if h in q]
    if lit_hits:
        tools.append("literature")
        reasons["literature"] = lit_hits[:3]
    pc_hits = [h for h in POSTCODE_HINTS if h in q]
    if pc_hits:
        tools.append("postcode")
        reasons["postcode"] = pc_hits[:3]
    k_hits = [h for h in KNOWLEDGE_HINTS if h in q]
    if k_hits:
        tools.append("knowledge")
        reasons["knowledge"] = k_hits[:3]
    h_hits = [h for h in HEALTH_HINTS if h in q]
    if h_hits:
        tools.append("health_data")
        reasons["health_data"] = h_hits[:3]
    ip_hits = [h for h in IP_HINTS if h in q]
    if ip_hits:
        tools.append("ip_lookup")
        reasons["ip_lookup"] = ip_hits[:3]
    return {"query": query, "tools": tools, "reasons": reasons,
            "handlers": {t: TOOLS[t] for t in tools}}


@router.get("/detect")
async def detect(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    """Tell me which free APIs this query needs - zero cost, deterministic."""
    return detect_tools(q)


@router.get("/auto")
async def auto_route(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    """Detect AND execute: runs every detected tool and returns combined results."""
    decision = detect_tools(q)
    results: Dict[str, Any] = {}
    if "geocode" in decision["tools"]:
        import asyncio
        try:
            results["geocode"] = await asyncio.to_thread(geocoding.forward_geocode, q)
        except requests.exceptions.RequestException as e:
            results["geocode"] = {"error": f"geocoding unreachable: {e.__class__.__name__}"}
    if "literature" in decision["tools"]:
        results["literature"] = await aggregate_literature(q)  # self-resilient per source
    if "health_data" in decision["tools"]:
        from . import health_sources
        try:
            results["health_data"] = await asyncio.to_thread(health_sources.dailymed_search, q)
        except requests.exceptions.RequestException as e:
            results["health_data"] = {"error": f"health registry unreachable: {e.__class__.__name__}"}
    if not decision["tools"]:
        results["note"] = "No free-tool signal detected - route to the LLM engines instead."
    return {"decision": decision, "results": results}
