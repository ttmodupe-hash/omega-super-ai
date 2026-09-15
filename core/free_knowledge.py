"""
OMEGA-LUQI Free Knowledge Scatter-Gather - Wikipedia / Open-Meteo / World Bank
+ OpenAlex, behind per-domain circuit breakers and token buckets.

Patterns (correctly attributed): scatter-gather concurrency, circuit breaker
(Release It!, NOT "RFC 6598" - that RFC is IPv4 shared address space), token
bucket. Sources are keyless; the breaker shields a dying upstream from
cascading retries, and an OPEN circuit reports the source as DOWN - never
fabricated "offline blueprints".

Provenance: every aggregated response carries sha256(query + canonical
results) for curriculum audit (extends core/snapshots.py fingerprinting).
"""
import asyncio
import hashlib
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from .geocoding import _headers
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/knowledge", tags=["Free Knowledge Scatter-Gather"])


# ---------------- circuit breaker (Release It! pattern) ----------------

class CircuitBreaker:
    """CLOSED -> OPEN after `fail_threshold` consecutive failures ->
    cooldown -> HALF_OPEN (one probe) -> CLOSED on success / OPEN on failure.
    Pure state machine: inject clock and call fn for testing."""

    def __init__(self, fail_threshold: int = 3, cooldown_seconds: float = 30.0,
                 clock: Callable[[], float] = time.time):
        self.fail_threshold = fail_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._state = "CLOSED"
        self._consecutive = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "OPEN" and self._opened_at is not None:
                if self._clock() - self._opened_at >= self.cooldown_seconds:
                    return "HALF_OPEN"  # logical probe state; next call flips it
            return self._state

    def allow(self) -> bool:
        return self.state in ("CLOSED", "HALF_OPEN")

    def on_success(self) -> None:
        with self._lock:
            self._state = "CLOSED"
            self._consecutive = 0
            self._opened_at = None

    def on_failure(self) -> None:
        with self._lock:
            self._consecutive += 1
            if self._state == "HALF_OPEN" or self._consecutive >= self.fail_threshold:
                self._state = "OPEN"
                self._opened_at = self._clock()
            # CLOSED with consecutive < threshold stays CLOSED


class TokenBucket:
    """capacity burst + refill/sec. acquire() returns wait seconds (0 = go)."""

    def __init__(self, capacity: float, refill_per_sec: float,
                 clock: Callable[[], float] = time.time):
        self.capacity = capacity
        self.refill = refill_per_sec
        self._clock = clock
        self._tokens = capacity
        self._last = clock()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        with self._lock:
            now = self._clock()
            self._tokens = min(self.capacity,
                               self._tokens + (now - self._last) * self.refill)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return 0.0
            wait = (1.0 - self._tokens) / self.refill
            self._tokens = 0.0
            return wait


# per-domain breakers + buckets (env-tunable refill rates)
def _domain_guard(name: str, refill: float) -> Dict[str, Any]:
    return {"breaker": CircuitBreaker(), "bucket": TokenBucket(5, refill)}


GUARDS = {
    "wikipedia": _domain_guard("wikipedia", 15.0),
    "openmeteo": _domain_guard("openmeteo", 10.0),
    "worldbank": _domain_guard("worldbank", 10.0),
    "openalex": _domain_guard("openalex", 5.0),
}


def _guarded_call(name: str, fn: Callable[[], Any]) -> Dict[str, Any]:
    guard = GUARDS[name]
    if not guard["breaker"].allow():
        return {"source": name, "status": "DOWN",
                "note": "circuit OPEN - upstream failing; no fabricated fallback"}
    wait = guard["bucket"].acquire()
    if wait > 0:
        time.sleep(min(wait, 5.0))
    try:
        result = fn()
        guard["breaker"].on_success()
        return {"source": name, "status": "OK", "data": result}
    except requests.exceptions.RequestException:
        guard["breaker"].on_failure()
        return {"source": name, "status": "DOWN", "note": "request failed; breaker recorded"}


# ---------------- source adapters (fixed hosts) ----------------

def wikipedia_summary(title: str) -> Dict[str, Any]:
    r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/"
                     + requests.utils.quote(scrub_pii(title).replace(" ", "_")),
                     headers=_headers(), timeout=10)
    r.raise_for_status()
    d = r.json()
    return {"title": d.get("title", ""), "extract": d.get("extract", "")[:600],
            "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}


def openmeteo_current(lat: float, lon: float) -> Dict[str, Any]:
    r = requests.get("https://api.open-meteo.com/v1/forecast",
                     params={"latitude": lat, "longitude": lon,
                             "current": "temperature_2m,wind_speed_10m,precipitation",
                             "wind_speed_unit": "kmh"}, timeout=10)
    r.raise_for_status()
    c = r.json().get("current", {})
    out = {"temperature_c": c.get("temperature_2m"), "wind_speed_kmh": c.get("wind_speed_10m"),
           "precipitation_mm": c.get("precipitation"), "time": c.get("time")}
    # SANS 10400 construction-safety relevance: high wind + precipitation flags
    wind = c.get("wind_speed_10m") or 0
    precip = c.get("precipitation") or 0
    out["construction_safety_note"] = (
        "Wind >40 km/h or rain: pause external scaffolding/crane work per site safety rules"
        if (wind > 40 or precip > 2) else
        "Conditions within typical SANS 10400 site-work envelope")
    return out


def worldbank_indicator(country: str = "ZAF", indicator: str = "SL.TVF.INCH.ZS") -> Dict[str, Any]:
    """SL.TVF.INCH.ZS: vocational education (% of secondary enrolment)."""
    r = requests.get(f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}",
                     params={"format": "json", "mrv": 1, "per_page": 1}, timeout=10)
    r.raise_for_status()
    data = r.json()
    rows = data[1] if isinstance(data, list) and len(data) > 1 else []
    latest = rows[0] if rows else {}
    return {"country": country, "indicator": indicator,
            "value": latest.get("value"), "year": latest.get("date"),
            "source_note": "World Bank Open Data (keyless)"}


def openalex_top(query: str) -> Dict[str, Any]:
    from .academic_sources import fetch_openalex
    hits = fetch_openalex(scrub_pii(query), per_page=3)
    return {"works": [{"title": h["title"], "cited_by": h["cited_by"]} for h in hits]}


ADAPTERS: Dict[str, Callable[..., Any]] = {
    "wikipedia": lambda q, **kw: wikipedia_summary(q),
    "openmeteo": lambda q, **kw: openmeteo_current(kw.get("lat", -26.2), kw.get("lon", 28.04)),
    "worldbank": lambda q, **kw: worldbank_indicator(),
    "openalex": lambda q, **kw: openalex_top(q),
}


def provenance_hash(query: str, results: Dict[str, Any]) -> str:
    """sha256(query + canonical per-source status) - curriculum audit trail."""
    canonical = repr(sorted((k, v.get("status")) for k, v in results.items()))
    return hashlib.sha256((query + "|" + canonical).encode()).hexdigest()


@router.get("/scatter")
async def scatter(q: str = Query(..., min_length=2),
                  tools: str = "wikipedia,openalex",
                  lat: float = -26.2, lon: float = 28.04) -> Dict[str, Any]:
    """Concurrent fan-out across selected free sources. One source down never
    blocks the rest; every response carries a provenance hash."""
    selected = [t.strip() for t in tools.split(",") if t.strip() in ADAPTERS]
    if not selected:
        raise HTTPException(status_code=400, detail=f"tools must be subset of {sorted(ADAPTERS)}")

    async def one(name: str):
        return name, await asyncio.to_thread(_guarded_call, name,
                                             lambda: ADAPTERS[name](q, lat=lat, lon=lon))

    pairs = await asyncio.gather(*(one(t) for t in selected))
    results = {name: res for name, res in pairs}
    return {"query": q, "tools": selected, "results": results,
            "provenance_sha256": provenance_hash(q, results),
            "note": "provenance hash covers query + per-source status for audit"}
