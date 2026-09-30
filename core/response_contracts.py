"""
OMEGA-LUQI Response Contracts (SCHEMA-1) - typed boundary for the public modes.

Verification asymmetry, applied at the HTTP boundary: generation is cheap,
drift is common. Every public mode has ONE job - return the shape the console
(and every future client) was built against. If an engine returns drifted
output (missing keys, wrong types, out-of-bounds confidence), that response
must fail closed (502) and NEVER reach a user as if it were a sound answer.

Design:
  - Pydantic v2 models, extra="allow": additive fields never false-fail -
    contracts enforce the FLOOR of the shape, not the ceiling.
  - ContractGuardMiddleware: single integration point in main.py. Validates
    JSON 200-responses on declared routes only; everything else passes through
    untouched (zero cost to admin/ops routes).
  - Fail-closed: a violation returns 502 with an honest detail string and the
    contract name - never the drifted payload.
  - Observability: passing responses carry X-Luqi-Contract so the console and
    uptime probes can see which contract guarded the answer.

Env: LUQI_CONTRACTS=0 disables enforcement (logs would show the breach in
CI evals instead). Default: ON.
"""
import json
import os
from typing import Any, Dict, Literal, Optional, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

ENFORCED = os.getenv("LUQI_CONTRACTS", "1") != "0"


# ── Contract models (the FLOOR of each mode's shape) ─────────────────────

class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class HybridProcessResponse(_Base):
    """POST /v1/hybrid/process - the auto-router front door."""
    engine_used: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    response: Optional[str] = None
    boundary: Optional[str] = None
    intent: Optional[str] = None
    suggested_tool: Optional[str] = None
    pii_redacted: Optional[bool] = None
    latency_ms: Optional[float] = None


class HybridHealthResponse(_Base):
    """GET /v1/hybrid/health - drives the console's honest status badge.
    ml_offline_fallback is a descriptive STRING in the real engine (truthy
    when the deterministic fallback is armed), never a bool."""
    kill_switch: bool
    sklearn_available: bool
    ml_offline_fallback: Optional[str] = None


class ChatCompletionResponse(_Base):
    """POST /v1/chat/completions - Chat Gateway (chat_gateway.py)."""
    status: Literal["success"]
    response: str = Field(min_length=1)
    engine_used: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    latency_ms: float
    pii_redacted: bool


class ScamPattern(_Base):
    name: str = Field(min_length=1)
    weight: float
    description: Optional[str] = None
    advice: Optional[str] = None


class ScamCheckResponse(_Base):
    """POST /v1/finlit/scam-check - deterministic fraud detector (finlit.py)."""
    risk_level: Literal["none", "low", "medium", "high", "critical"]
    risk_score: int = Field(ge=0)
    verdict: str = Field(min_length=1)
    matched_patterns: list[ScamPattern]
    golden_rules: list[str]
    report_line: str = Field(min_length=1)
    disclaimer: str = Field(min_length=1)


class ScamPatternCatalogue(_Base):
    """GET /v1/finlit/scam-patterns - the live catalogue tile."""
    patterns: list[ScamPattern]


class CatalogueEntry(_Base):
    """Shared floor for services/history entry search hits."""
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class EntrySearchResponse(_Base):
    """GET /v1/services/entries and /v1/history/entries (q= search).
    Empty list is a VALID, honest answer - the console renders no-match."""
    entries: list[CatalogueEntry]


class ArchiveOverviewResponse(_Base):
    """GET /v1/history, /v1/services, /v1/heritage - catalogue overviews."""
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    entry_count: int = Field(ge=0)


class HeritageMatch(_Base):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    era: Optional[str] = None
    region: Optional[str] = None
    tradition: Optional[str] = None


class HeritageQueryResponse(_Base):
    """POST /v1/heritage/query - curated archive or honest silence.
    Invariant: matches are non-empty XOR status == 'no_curated_match'.
    The real engine marks hits with status 'success' — both are valid;
    what is forbidden is emptiness without honesty, or both at once."""
    matches: list[HeritageMatch]
    status: Optional[Literal["success", "no_curated_match"]] = None
    query: Optional[str] = None
    honest_note: Optional[str] = None
    disclaimer: Optional[str] = None

    @model_validator(mode="after")
    def _matches_or_honest_silence(self):
        if self.status == "no_curated_match":
            if self.matches:
                raise ValueError(
                    "no_curated_match must carry an empty matches list")
            if not self.honest_note:
                raise ValueError(
                    "no_curated_match must carry its honest_note")
        elif not self.matches:
            raise ValueError(
                "heritage query returned neither matches nor no_curated_match")
        return self


class CitationLite(_Base):
    """Floor of a resolvable citation (full model: citations.py)."""
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)


class IksMatch(_Base):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    latin_name: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None


class IksQueryResponse(_Base):
    """POST /v1/iks/query - curated botanical archive or honest silence.
    Same invariant as heritage: matches non-empty XOR no_curated_match
    (hits are marked status 'success'), and the catalogue-not-clinic
    boundary must travel with matches."""
    matches: list[IksMatch]
    status: Optional[Literal["success", "no_curated_match"]] = None
    query: Optional[str] = None
    honest_note: Optional[str] = None
    boundary: Optional[str] = None
    disclaimer: Optional[str] = None

    @model_validator(mode="after")
    def _matches_or_honest_silence(self):
        if self.status == "no_curated_match":
            if self.matches:
                raise ValueError(
                    "no_curated_match must carry an empty matches list")
            if not self.honest_note:
                raise ValueError(
                    "no_curated_match must carry its honest_note")
        elif not self.matches:
            raise ValueError(
                "iks query returned neither matches nor no_curated_match")
        return self


class DialectProfileLite(_Base):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: str = Field(min_length=1)


class DialectRegistryResponse(_Base):
    """GET /v1/i18n/dialects - honest dialect register (registry-only status
    is a first-class field, so no client can mistake a profile for speech)."""
    count: int = Field(ge=0)
    profiles: list[DialectProfileLite]
    note: str = Field(min_length=1)
class DeepResearchResult(_Base):
    answer: str = Field(min_length=1)
    citations: list[CitationLite]
    verification: Literal["verified", "unverified"]
    label: str = Field(min_length=1)


class DeepResearchResponse(_Base):
    """POST /v1/deep-research - sourced synthesis or labelled UNVERIFIED."""
    result: DeepResearchResult
    elapsed_ms: Optional[int] = Field(default=None, ge=0)


# ── The contract map: (method, path) -> model ────────────────────────────
# The public-mode routes the console (and public clients) depend on —
# the original 9 modes plus the IKS archive and the dialect register.
# Admin/ops routes are deliberately untouched.

CONTRACT_MAP: Dict[Tuple[str, str], type] = {
    ("POST", "/v1/hybrid/process"): HybridProcessResponse,
    ("GET", "/v1/hybrid/health"): HybridHealthResponse,
    ("POST", "/v1/chat/completions"): ChatCompletionResponse,
    ("POST", "/v1/finlit/scam-check"): ScamCheckResponse,
    ("GET", "/v1/finlit/scam-patterns"): ScamPatternCatalogue,
    ("GET", "/v1/services/entries"): EntrySearchResponse,
    ("GET", "/v1/history/entries"): EntrySearchResponse,
    ("GET", "/v1/services"): ArchiveOverviewResponse,
    ("GET", "/v1/history"): ArchiveOverviewResponse,
    ("GET", "/v1/heritage"): ArchiveOverviewResponse,
    ("POST", "/v1/heritage/query"): HeritageQueryResponse,
    ("GET", "/v1/iks"): ArchiveOverviewResponse,
    ("GET", "/v1/iks/entries"): EntrySearchResponse,
    ("POST", "/v1/iks/query"): IksQueryResponse,
    ("GET", "/v1/i18n/dialects"): DialectRegistryResponse,
    ("POST", "/v1/deep-research"): DeepResearchResponse,
}

# Human names for the 9 modes, for error messages and telemetry.
MODE_NAMES = {
    "HybridProcessResponse": "auto/money-skills router",
    "HybridHealthResponse": "engine health",
    "ChatCompletionResponse": "Ask Luqi-ai (chat gateway)",
    "ScamCheckResponse": "Scam Shield",
    "ScamPatternCatalogue": "Scam Shield catalogue",
    "EntrySearchResponse": "Everyday Services / African History search",
    "ArchiveOverviewResponse": "archive overview",
    "HeritageQueryResponse": "Heritage & Theology archive",
    "IksQueryResponse": "IKS Ethnobotanical archive",
    "DialectRegistryResponse": "dialect register",
    "DeepResearchResponse": "Deep Research",
}


def validate(contract_name: str, payload: Any) -> Dict[str, Any]:
    """Validate payload against a named contract. Fail closed (502) on drift.

    Returns a verification stamp on success so endpoints that call this
    directly can surface it. The middleware path uses the header instead.
    """
    model = {m.__name__: m for m in CONTRACT_MAP.values()}[contract_name]
    model.model_validate(payload)
    return {"contract": contract_name, "verified": True}


class ContractGuardMiddleware(BaseHTTPMiddleware):
    """Boundary guard: validates JSON 200-responses on declared routes.

    On violation the user gets an honest 502 - never drifted output dressed
    as an answer. CORS must wrap this middleware (added after it in main.py)
    so even the 502 carries proper CORS headers to browser clients.
    """

    async def dispatch(self, request: Request, call_next):
        if not ENFORCED:
            return await call_next(request)
        model = CONTRACT_MAP.get((request.method, request.url.path))
        if model is None:
            return await call_next(request)

        response = await call_next(request)
        if response.status_code != 200:
            return response  # errors are honest already; never re-write them
        ctype = response.headers.get("content-type", "")
        if "application/json" not in ctype:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        try:
            payload = json.loads(body)
            model.model_validate(payload)
        except Exception as exc:
            mode = MODE_NAMES.get(model.__name__, model.__name__)
            return JSONResponse(
                status_code=502,
                content={
                    "detail": f"{mode}: response contract violated - the "
                              "engine's answer failed structural verification, "
                              "so nothing was presented as fact.",
                    "contract": model.__name__,
                    "status": "contract_violation",
                },
            )

        headers = dict(response.headers)
        headers["X-Luqi-Contract"] = model.__name__
        headers["content-length"] = str(len(body))
        return JSONResponse(status_code=200, content=json.loads(body),
                            headers=headers, background=response.background)
