"""
OMEGA-LUQI Centralized Free-Provider Registry - one status story for all
keyless sources (consolidates adapters scattered across academic_sources,
geocoding, free_geo_apis, health_sources, free_knowledge).

What the registry owns: provider metadata, uniform response envelope, typed
provider errors (ONE class with kinds - not eight boilerplate subclasses),
concurrent health checks, provenance, and an ESTIMATED tokens/cost saved
counter (free resolution avoided an LLM call - labeled an estimate).

What stays in the owning modules: the actual fetch logic and rate gates.
Circuit state for the four guarded domains (free_knowledge.GUARDS) is read
here; other modules keep their own polite gates.
"""
import asyncio
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from .admin_auth import verify_admin
from .geocoding import _headers
from .free_knowledge import GUARDS as FK_GUARDS

router = APIRouter(prefix="/v1/registry", tags=["Free-Provider Registry"])


class ProviderError(Exception):
    """One typed error: provider + kind. Kinds: timeout, rate_limited,
    circuit_open, unreachable, http_<code>."""
    def __init__(self, provider: str, kind: str, detail: str = ""):
        self.provider, self.kind = provider, kind
        super().__init__(f"{provider}: {kind} {detail}".strip())


# provider -> metadata. health_path is a cheap, cache-friendly endpoint.
REGISTRY: Dict[str, Dict[str, Any]] = {
    "openalex":    {"base": "https://api.openalex.org", "health_path": "/works?per_page=1",
                    "guard": "openalex"},
    "arxiv":       {"base": "https://export.arxiv.org", "health_path": "/api/query?search_query=all:x&max_results=1"},
    "wikipedia":   {"base": "https://en.wikipedia.org", "health_path": "/api/rest_v1/page/summary/Linux",
                    "guard": "wikipedia"},
    "openmeteo":   {"base": "https://api.open-meteo.com", "health_path": "/v1/forecast?latitude=0&longitude=0&current=temperature_2m",
                    "guard": "openmeteo"},
    "worldbank":   {"base": "https://api.worldbank.org", "health_path": "/v2/country/ZAF/indicator/NY.GDP.MKTP.CD?format=json&mrv=1&per_page=1",
                    "guard": "worldbank"},
    "openfda":     {"base": "https://api.fda.gov", "health_path": "/drug/label.json?limit=1"},
    "crossref":    {"base": "https://api.crossref.org", "health_path": "/works?rows=1"},
    "nominatim":   {"base": "https://nominatim.openstreetmap.org", "health_path": "/search?q=x&format=jsonv2&limit=1"},
}

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Typed free-provider response. Generic over the payload shape; validated
    on every envelope() build, so malformed responses fail at the boundary."""
    provider: str
    endpoint: str
    status: str                      # HEALTHY|DEGRADED|UNREACHABLE|CIRCUIT_OPEN|RATE_LIMITED
    status_code: Optional[int] = None
    data: Optional[T] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_saved: int = 0
    cost_saved_usd: float = 0.0
    cached: bool = False             # honest: no response cache yet; flag reserved
    provenance: str = ""
    query: str = ""
    timestamp: str = ""              # ISO-8601 UTC


# ESTIMATED saving when a free provider resolves what would have been an LLM call
_AVOIDED_LLM_CALL_USD = float(os.getenv("REGISTRY_AVOIDED_CALL_USD", "0.0008"))
_tokens_saved = {"count": 0, "est_usd": 0.0}


def envelope(provider: str, status: str, data: Any = None, error: Optional[str] = None,
             status_code: Optional[int] = None, latency_ms: Optional[float] = None,
             query: str = "", endpoint: str = "") -> Dict[str, Any]:
    """Uniform free-provider response: status enum, provenance, saved estimate."""
    if status == "HEALTHY":
        _tokens_saved["count"] += 1
        _tokens_saved["est_usd"] += _AVOIDED_LLM_CALL_USD
    prov = hashlib.sha256(f"{provider}|{status}|{query}".encode()).hexdigest()[:16]
    return ApiResponse(
        provider=provider, endpoint=endpoint or "", status=status,
        status_code=status_code, data=data, error=error, latency_ms=latency_ms,
        tokens_saved=_tokens_saved["count"],
        cost_saved_usd=round(_tokens_saved["est_usd"], 5),
        cached=False,
        provenance=prov, query=query,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ).model_dump()


def _classify(provider: str, e: Exception) -> ProviderError:
    if isinstance(e, requests.exceptions.Timeout):
        return ProviderError(provider, "timeout", str(e)[:120])
    if isinstance(e, requests.exceptions.HTTPError) and getattr(e.response, "status_code", 0) == 429:
        return ProviderError(provider, "rate_limited")
    return ProviderError(provider, "unreachable", str(e)[:120])


def health_check(provider: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Ping one provider's cheap endpoint. Pure mapping of outcomes to statuses."""
    meta = REGISTRY.get(provider)
    if not meta:
        raise HTTPException(status_code=404, detail=f"unknown provider: {provider}")
    guard_name = meta.get("guard")
    if guard_name and guard_name in FK_GUARDS and not FK_GUARDS[guard_name]["breaker"].allow():
        return envelope(provider, "CIRCUIT_OPEN", error="breaker OPEN")
    t0 = time.perf_counter()
    try:
        r = requests.get(meta["base"] + meta["health_path"], headers=_headers(),
                         timeout=timeout)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if r.status_code == 429:
            return envelope(provider, "RATE_LIMITED", status_code=429, latency_ms=ms)
        if r.status_code >= 400:
            return envelope(provider, "UNREACHABLE", status_code=r.status_code, latency_ms=ms)
        return envelope(provider, "HEALTHY", status_code=r.status_code, latency_ms=ms)
    except requests.exceptions.RequestException as e:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        pe = _classify(provider, e)
        status = {"timeout": "UNREACHABLE", "rate_limited": "RATE_LIMITED"}.get(pe.kind, "UNREACHABLE")
        return envelope(provider, status, error=str(pe), latency_ms=ms)


async def health_check_all(timeout: float = 5.0) -> Dict[str, Any]:
    """Concurrent validation of every registered provider."""
    results = await asyncio.gather(*(asyncio.to_thread(health_check, p, timeout)
                                     for p in REGISTRY))
    by_status: Dict[str, List[str]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r["provider"])
    return {"providers": {r["provider"]: r for r in results},
            "summary": {k: sorted(v) for k, v in by_status.items()},
            "registered": len(REGISTRY),
            "checked_at": time.time()}


# Unified dispatch front: one async entry point per provider, delegating to the
# OWNING module's adapter (no fetch logic duplicated here). Guarded by the
# domain breaker + bucket from free_knowledge; raises ProviderError on failure.
_DISPATCH: Dict[str, Callable[..., Any]] = {}


def register_dispatch(provider: str, fn: Callable[..., Any]) -> None:
    _DISPATCH[provider] = fn


async def query(provider: str, q: str = "", **kwargs) -> Dict[str, Any]:
    """Front-door async query: breaker -> bucket -> owning adapter -> typed envelope."""
    t0 = __import__("time").perf_counter()
    if provider not in _DISPATCH:
        raise ProviderError(provider, "unknown_provider")
    meta = REGISTRY.get(provider) or {}   # registered dispatchers need not be registry members
    guard_name = meta.get("guard")
    if guard_name:
        from .free_knowledge import GUARDS
        if guard_name in GUARDS and not GUARDS[guard_name]["breaker"].allow():
            raise ProviderError(provider, "circuit_open")
    try:
        data = await asyncio.to_thread(_DISPATCH[provider], q, **kwargs)
    except ProviderError:
        raise
    except Exception as e:
        raise ProviderError(provider, "unreachable", str(e)[:120]) from e
    ms = round((__import__("time").perf_counter() - t0) * 1000, 1)
    return envelope(provider, "HEALTHY", data=data, status_code=200,
                    latency_ms=ms, query=q, endpoint=meta.get("health_path", ""))


@router.get("/providers")
async def list_providers() -> Dict[str, Any]:
    return {"providers": sorted(REGISTRY),
            "metadata": {k: {"base": v["base"], "guarded": "guard" in v}
                         for k, v in REGISTRY.items()}}


@router.get("/health")
async def registry_health(provider: Optional[str] = Query(None),
                          is_authenticated: bool = Depends(verify_admin)):
    """Concurrent health of all free providers (or one). Admin: reveals infra state."""
    if provider:
        return health_check(provider)
    return await health_check_all()


@router.get("/savings")
async def savings(is_authenticated: bool = Depends(verify_admin)):
    return {"free_resolutions": _tokens_saved["count"],
            "estimated_cost_saved_usd": round(_tokens_saved["est_usd"], 5),
            "disclaimer": "estimate - free-provider resolutions that avoided an LLM call"}


# Dispatch registrations (owning modules own the fetch logic; imported lazily
# inside a function to keep module import light and cycle-free).
def _register_all_dispatches() -> None:
    from .free_knowledge import wikipedia_summary, openmeteo_current, worldbank_indicator
    from .academic_sources import fetch_openalex, fetch_arxiv, fetch_crossref
    from .geocoding import forward_geocode
    from .health_sources import openfda_label, dailymed_search
    register_dispatch("wikipedia", lambda q, **kw: wikipedia_summary(q))
    register_dispatch("openmeteo", lambda q, **kw: openmeteo_current(kw.get("lat", -26.2), kw.get("lon", 28.04)))
    register_dispatch("worldbank", lambda q, **kw: worldbank_indicator())
    register_dispatch("openalex", lambda q, **kw: {"works": fetch_openalex(q, per_page=3)})
    register_dispatch("arxiv", lambda q, **kw: {"works": fetch_arxiv(q, max_results=3)})
    register_dispatch("crossref", lambda q, **kw: {"works": fetch_crossref(q, rows=3)})
    register_dispatch("nominatim", lambda q, **kw: forward_geocode(q))
    register_dispatch("openfda", lambda q, **kw: openfda_label(q))
    register_dispatch("openfda_dailymed", lambda q, **kw: dailymed_search(q))
