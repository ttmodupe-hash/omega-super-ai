"""
OMEGA-LUQI Free Geocoding Family - the blog's full keyless list, integrated.

Adds to geocoding.py (Nominatim):
  photon     photon.komoot.io        - global forward/reverse (Nominatim fallback)
  fr_gouv    api-adresse.data.gouv.fr - France (official BAN, returns match score)
  zippopotam api.zippopotam.us        - postal code <-> place, ~60 countries
  uk_post    api.postcodes.io         - UK postcodes + ~80 admin geography fields
  openplz    openplzapi.org           - DE/AT/CH/LI postal directory
  geo3names  api.3geonames.org        - lightweight global reverse
  ip_api     ip-api.com               - IP -> location (HTTP-only, NON-COMMERCIAL
                                         free tier per their terms - flagged on
                                         every response; use only for that purpose)

All: fixed hosts (no SSRF surface), pure parsers (offline-tested), PII scrub,
503-on-network-failure, OSM attribution where the data is OSM-derived.
"""
import asyncio
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, HTTPException, Query

from .pii_scrub import scrub_pii
from .geocoding import forward_geocode as _nominatim_forward, OSM_ATTRIBUTION

router = APIRouter(prefix="/v1/tools/geo", tags=["Free Geocoding Family"])

IP_API_TERMS_WARNING = ("ip-api.com free tier: HTTP-only and NON-COMMERCIAL use. "
                        "HTTPS/commercial requires their paid tier.")


# ---------------- pure parsers ----------------

def _parse_photon(payload: Dict[str, Any]) -> Dict[str, Any]:
    feats = payload.get("features", [])
    if not feats:
        return {"status": "error", "message": "No results found"}
    f = feats[0]
    props = f.get("properties", {})
    lon, lat = f.get("geometry", {}).get("coordinates", [None, None])
    return {"status": "success", "lat": lat, "lon": lon,
            "name": props.get("name", ""), "city": props.get("city", ""),
            "country": props.get("country", ""),
            "display_name": ", ".join(x for x in [props.get("name"), props.get("street"),
                                                  props.get("city"), props.get("country")] if x),
            "attribution": OSM_ATTRIBUTION}


def _parse_fr_gouv(payload: Dict[str, Any]) -> Dict[str, Any]:
    feats = payload.get("features", [])
    if not feats:
        return {"status": "error", "message": "No results found"}
    f = feats[0]
    props = f.get("properties", {})
    lon, lat = f.get("geometry", {}).get("coordinates", [None, None])
    return {"status": "success", "lat": lat, "lon": lon,
            "label": props.get("label", ""), "score": props.get("score"),
            "postcode": props.get("postcode", ""), "city": props.get("city", "")}


def _parse_zippopotam(payload: Dict[str, Any]) -> Dict[str, Any]:
    places = payload.get("places", [])
    if not places:
        return {"status": "error", "message": "No results found"}
    p = places[0]
    return {"status": "success", "postcode": payload.get("post code", ""),
            "country": payload.get("country", ""),
            "place": p.get("place name", ""), "region": p.get("state", ""),
            "lat": float(p.get("latitude", 0)), "lon": float(p.get("longitude", 0))}


def _parse_uk_postcode(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("status") != 200 or not payload.get("result"):
        return {"status": "error", "message": payload.get("error", "No results found")}
    r = payload["result"]
    return {"status": "success", "postcode": r.get("postcode", ""),
            "lat": r.get("latitude"), "lon": r.get("longitude"),
            "region": r.get("region", ""), "admin_district": r.get("admin_district", ""),
            "country": r.get("country", "")}


def _parse_openplz(payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {"status": "error", "message": "No results found"}
    p = payload[0]
    return {"status": "success", "postal_code": p.get("postalCode", ""),
            "locality": p.get("name", ""),
            "municipality": (p.get("municipality") or {}).get("name", ""),
            "federal_state": (p.get("federalState") or {}).get("name", "")}


def _parse_3geonames(payload: Dict[str, Any]) -> Dict[str, Any]:
    n = payload.get("nearest", {})
    if not n:
        return {"status": "error", "message": "No results found"}
    return {"status": "success", "name": n.get("name", ""), "city": n.get("city", ""),
            "region": n.get("region", ""), "distance_km": n.get("distance", ""),
            "timezone": n.get("timezone", "")}


def _parse_ip_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("status") != "success":
        return {"status": "error", "message": payload.get("message", "lookup failed")}
    return {"status": "success", "ip": payload.get("query", ""),
            "city": payload.get("city", ""), "region": payload.get("regionName", ""),
            "country": payload.get("country", ""), "lat": payload.get("lat"),
            "lon": payload.get("lon"), "isp": payload.get("isp", ""),
            "terms": IP_API_TERMS_WARNING}


# ---------------- live calls ----------------

def _get(url: str, params: Dict[str, Any]) -> Any:
    from .geocoding import _headers
    r = requests.get(url, headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def photon_forward(query: str) -> Dict[str, Any]:
    return _parse_photon(_get("https://photon.komoot.io/api/", {"q": scrub_pii(query), "limit": 1}))


def fr_gouv_search(query: str) -> Dict[str, Any]:
    return _parse_fr_gouv(_get("https://api-adresse.data.gouv.fr/search/",
                               {"q": scrub_pii(query), "limit": 1}))


def zippopotam_lookup(country: str, postal_code: str) -> Dict[str, Any]:
    return _parse_zippopotam(_get(
        f"https://api.zippopotam.us/{country.lower()}/{postal_code}", {}))


def uk_postcode_lookup(postcode: str) -> Dict[str, Any]:
    return _parse_uk_postcode(_get(
        f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '')}", {}))


def openplz_lookup(postal_code: str) -> Dict[str, Any]:
    return _parse_openplz(_get(
        "https://openplzapi.org/de/Localities", {"postalCode": postal_code}))


def geo3names_reverse(lat: float, lon: float) -> Dict[str, Any]:
    return _parse_3geonames(_get(f"https://api.3geonames.org/{lat},{lon}.json", {}))


def ip_lookup(ip: str) -> Dict[str, Any]:
    out = _parse_ip_api(_get(f"http://ip-api.com/json/{ip}", {}))
    out["terms_warning"] = IP_API_TERMS_WARNING  # never let the terms flag detach
    return out


async def geocode_with_fallback(query: str) -> Dict[str, Any]:
    """Nominatim first (rate-gated); Photon catches rate-limit/timeout days."""
    try:
        return await asyncio.to_thread(_nominatim_forward, query)
    except Exception:
        result = await asyncio.to_thread(photon_forward, query)
        result["fallback_used"] = "photon"
        return result


# ---------------- endpoints (503 on network failure, uniformly) ----------------

def _wrap(func):
    """Adapt a SYNC live-call function to an async endpoint handler:
    thread-pool offload + uniform 503 on network failure."""
    async def handler(*args, **kwargs):
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503,
                                detail=f"Geocoding service unreachable: {e.__class__.__name__}")
    return handler


@router.get("/search")
async def geo_search(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    """Chained global search: Nominatim -> Photon fallback."""
    return await geocode_with_fallback(q)


@router.get("/france")
async def france(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    return await _wrap(fr_gouv_search)(q)


@router.get("/postcode/{country}/{code}")
async def postcode(country: str, code: str) -> Dict[str, Any]:
    return await _wrap(zippopotam_lookup)(country, code)


@router.get("/uk/{postcode}")
async def uk_postcode(postcode: str) -> Dict[str, Any]:
    return await _wrap(uk_postcode_lookup)(postcode)


@router.get("/dach")
async def dach(postal_code: str = Query(..., min_length=3)) -> Dict[str, Any]:
    return await _wrap(openplz_lookup)(postal_code)


@router.get("/reverse-quick")
async def reverse_quick(lat: float, lon: float) -> Dict[str, Any]:
    return await _wrap(geo3names_reverse)(lat, lon)


@router.get("/ip")
async def ip(ip: str = Query(...)) -> Dict[str, Any]:
    return await _wrap(ip_lookup)(ip)
