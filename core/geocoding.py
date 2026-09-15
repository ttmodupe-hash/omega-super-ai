"""
OMEGA-LUQI Free Geocoding Layer (OpenStreetMap Nominatim)

Free, key-less forward/reverse geocoding. Policy-compliant by construction:
  - FIXED host (nominatim.openstreetmap.org) - the pasted code used
    openstreetmap.org, which is the website and 404s on every API call.
  - Identifying User-Agent from env (Nominatim blocks generic agents).
  - SHARED rate gate (>=1s between calls) - process-wide, so multi-worker
    deployments don't get the IP banned (per-instance sleep is not enough).
  - PII scrub: addresses often contain personal names - scrubbed before exit.
  - OSM attribution string exposed in every response (license requirement).
"""
import asyncio
import os
import threading
import time
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Query

from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/tools", tags=["Free Utility APIs"])

HOST = "https://nominatim.openstreetmap.org"
OSM_ATTRIBUTION = "Data (c) OpenStreetMap contributors"
MIN_INTERVAL_SECONDS = 1.0  # Nominatim usage policy

_state = {"last_call": 0.0}
_gate = threading.Lock()


def compute_delay(last_call: float, now: float, interval: float = MIN_INTERVAL_SECONDS) -> float:
    """Pure rate-gate math (unit-tested): seconds to wait before next call."""
    return max(0.0, interval - (now - last_call))


def _respect_rate_limit() -> None:
    with _gate:
        delay = compute_delay(_state["last_call"], time.time())
        if delay > 0:
            time.sleep(delay)
        _state["last_call"] = time.time()


def _headers() -> Dict[str, str]:
    app = os.getenv("GEOCODING_APP_NAME", "luqi-ai")
    contact = os.getenv("ACADEMIC_CONTACT_EMAIL", "luqi-ai@localhost")
    return {"User-Agent": f"{app}/1.0 ({contact})"}


# ---------------- pure parsers ----------------

def _parse_search(payload: list) -> Dict[str, Any]:
    if not payload:
        return {"status": "error", "message": "No results found"}
    r = payload[0]
    return {"status": "success", "lat": float(r["lat"]), "lon": float(r["lon"]),
            "display_name": r.get("display_name", "")}


def _parse_reverse(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "address" not in payload:
        return {"status": "error", "message": "No results found"}
    return {"status": "success", "display_name": payload.get("display_name", ""),
            "address_details": payload.get("address", {})}


# ---------------- live calls (blocking; offloaded) ----------------

def forward_geocode(address: str) -> Dict[str, Any]:
    _respect_rate_limit()
    r = requests.get(f"{HOST}/search",
                     headers=_headers(),
                     params={"q": scrub_pii(address), "format": "jsonv2", "limit": 1},
                     timeout=15)
    r.raise_for_status()
    out = _parse_search(r.json())
    out["attribution"] = OSM_ATTRIBUTION
    return out


def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    _respect_rate_limit()
    r = requests.get(f"{HOST}/reverse",
                     headers=_headers(),
                     params={"lat": lat, "lon": lon, "format": "jsonv2"},
                     timeout=15)
    r.raise_for_status()
    out = _parse_reverse(r.json())
    out["attribution"] = OSM_ATTRIBUTION
    return out


@router.get("/geocode")
async def geocode(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    """Public, key-less forward geocoding. Network failure -> 503, not 500."""
    try:
        return await asyncio.to_thread(forward_geocode, q)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Geocoding service unreachable: {e.__class__.__name__}")


@router.get("/reverse-geocode")
async def reverse(lat: float, lon: float) -> Dict[str, Any]:
    """Public, key-less reverse geocoding. Network failure -> 503, not 500."""
    try:
        return await asyncio.to_thread(reverse_geocode, lat, lon)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Geocoding service unreachable: {e.__class__.__name__}")
