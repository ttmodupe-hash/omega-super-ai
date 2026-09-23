"""Unified Agentic Router (ORCH-1) — POST /v1/ask.

One entry point that routes a natural-language prompt across the zero-cost,
deterministic capability packs, in routing-law order (SAFETY FIRST):

  1. Scam Shield        (core/finlit.py — scam_check, deterministic patterns)
  2. Everyday Services  (core/everyday_services.py — _load_pack / _search)
  3. African History    (core/african_history.py — _load_archive / _search)
  4. NOTHING matches    -> honest KNOWLEDGE_GAP. NEVER fabricate an answer or
                           citations. A pasted design doc proposed faking a
                           "synthesized research guide" with a fake citation —
                           that is explicitly REJECTED here (anti-hallucination
                           law). The gap payload only names the real modes.

Zero new dependencies: fastapi + pydantic + the pack internals already in repo.

DEVIATION (documented): the packs' `_search(entries, q)` is a verbatim
substring matcher, so a full natural-language question ("how do I appeal my
SRD grant") matches NOTHING as one needle (verified empirically). The router
therefore tokenises the prompt into significant keywords and unions the real
`_search` result per keyword, ranked by distinct-keyword coverage. The pack
search internals themselves are used unmodified.
"""
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .finlit import ScamCheckRequest, _load_patterns, scam_check
from .everyday_services import _load_pack, _search as _services_search
from .african_history import _load_archive, _search as _history_search

router = APIRouter(prefix="/v1/ask", tags=["orchestrator"])

_VALID_OVERRIDES = ("scam", "services", "history")

# Cap on entries embedded in a routed payload (ranked by keyword coverage).
_MAX_PAYLOAD_ENTRIES = 5

# English stopwords for keyword extraction. The packs are deterministic
# English corpora; `language` is accepted for forward compatibility and
# carried on the request, but routing is always over the real pack text.
_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "with", "this", "that", "from",
    "your", "you", "your", "have", "has", "had", "how", "what", "when", "where",
    "which", "who", "why", "can", "could", "should", "would", "does", "did",
    "tell", "about", "please", "best", "way", "ways", "want", "need", "like",
    "know", "explain", "give", "show", "help", "there", "their", "them",
    "they", "then", "than", "into", "out", "all", "any", "some", "not",
    "but", "its", "his", "her", "she", "him", "our", "ours", "mine", "yours",
}


def _keywords(text: str) -> List[str]:
    """Significant keyword tokens: lowercase alnum words, len > 2, non-stopword,
    order-preserving, de-duplicated."""
    seen, out = set(), []
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if len(tok) > 2 and tok not in _STOPWORDS and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def _ranked_hits(
    entries: List[Dict[str, Any]],
    prompt: str,
    search_fn,
) -> List[Dict[str, Any]]:
    """Union the REAL pack `_search` over each keyword; rank full entries by
    distinct-keyword coverage (ties broken by entry id for determinism)."""
    coverage: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for kw in _keywords(prompt):
        for ent in search_fn(entries, kw):
            count, _ = coverage.get(ent["id"], (0, ent))
            coverage[ent["id"]] = (count + 1, ent)
    ranked = sorted(coverage.values(), key=lambda cv: (-cv[0], cv[1]["id"]))
    return [ent for _, ent in ranked]


def _dedup_sources(entries: List[Dict[str, Any]]) -> List[str]:
    """Real source strings from matched entries, order-preserving, deduped."""
    seen, out = set(), []
    for ent in entries:
        for s in ent.get("sources", []):
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


# ── Schemas ──────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    mode_override: Optional[str] = Field(
        default=None,
        description=f"Force one route only: one of {list(_VALID_OVERRIDES)}.",
    )
    language: Optional[str] = "en"


class AskResponse(BaseModel):
    query: str
    mode_executed: str  # scam_shield | everyday_services | african_history | knowledge_gap
    payload: Dict[str, Any]
    sources: List[str]
    is_verified: bool
    knowledge_gap: bool
    routing_trace: List[str]
    execution_time_ms: float


# ── Route handlers (each returns None when it does not claim the prompt) ──

async def _route_scam(prompt: str, trace: List[str]) -> Optional[AskResponse]:
    """Route 1 — SAFETY FIRST. Calls the REAL finlit logic.

    HIT definition (from the real scam_check response shape in core/finlit.py):
    a prompt is a scam hit when
        risk_level in ("critical", "high")  OR  matched_patterns is non-empty.
    scam_check returns risk_level/risk_score/verdict/matched_patterns/
    questions_to_ask/golden_rules/report_line/disclaimer; even a 'low'/'medium'
    risk with a matched catalogue pattern is routed to the shield, because a
    known fraud pattern is never answered by a content pack.
    """
    result = await scam_check(ScamCheckRequest(text=prompt))
    hit = result["risk_level"] in ("critical", "high") or bool(result["matched_patterns"])
    if not hit:
        trace.append("scam: no match")
        return None
    trace.append(
        f"scam: HIT risk={result['risk_level']} "
        f"score={result['risk_score']} patterns={len(result['matched_patterns'])}"
    )
    version = _load_patterns()["version"]
    sources = [
        f"core/data/scam_patterns.json v{version} "
        "(versioned scam-pattern catalogue, omega-super-ai repo)"
    ]
    sources += [
        f"pattern '{m['pattern_id']}': {m['name']}" for m in result["matched_patterns"]
    ]
    return AskResponse(
        query=prompt,
        mode_executed="scam_shield",
        payload=result,  # the verbatim scam_check payload
        sources=sources,
        is_verified=True,
        knowledge_gap=False,
        routing_trace=trace,
        execution_time_ms=0.0,  # stamped by the caller
    )


def _route_pack(
    prompt: str,
    trace: List[str],
    *,
    mode: str,
    label: str,
    entries: List[Dict[str, Any]],
    search_fn,
    pack_version: str,
) -> Optional[AskResponse]:
    """Shared deterministic-pack route (services / history)."""
    hits = _ranked_hits(entries, prompt, search_fn)
    if not hits:
        trace.append(f"{label}: no match")
        return None
    trace.append(f"{label}: {len(hits)} hits")
    top = hits[:_MAX_PAYLOAD_ENTRIES]
    return AskResponse(
        query=prompt,
        mode_executed=mode,
        payload={
            "count": len(hits),
            "entries": top,  # full pack entries, verbatim from the data file
            "pack_version": pack_version,
        },
        sources=_dedup_sources(top),
        is_verified=True,
        knowledge_gap=False,
        routing_trace=trace,
        execution_time_ms=0.0,
    )


def _route_services(prompt: str, trace: List[str]) -> Optional[AskResponse]:
    pack = _load_pack()
    return _route_pack(
        prompt, trace,
        mode="everyday_services", label="services",
        entries=pack["entries"], search_fn=_services_search,
        pack_version=pack["version"],
    )


def _route_history(prompt: str, trace: List[str]) -> Optional[AskResponse]:
    archive = _load_archive()
    return _route_pack(
        prompt, trace,
        mode="african_history", label="history",
        entries=archive["entries"], search_fn=_history_search,
        pack_version=archive["version"],
    )


def _knowledge_gap(prompt: str, trace: List[str]) -> AskResponse:
    """The honest fallback. ANTI-HALLUCINATION LAW: no fabricated answer, no
    fabricated citation — only guidance naming the real, available modes."""
    trace.append("gap: no pack matched — honest knowledge gap")
    return AskResponse(
        query=prompt,
        mode_executed="knowledge_gap",
        payload={
            "guidance": (
                "No verified pack covers this query, so no answer is given "
                "rather than a fabricated one. The real deterministic modes are: "
                "scam (fraud-pattern analysis of any suspicious message), "
                "services (SASSA grants, SRD R370, SARS tax, UIF, NSFAS — "
                "plain-language guides from official sources), and history "
                "(the sourced African History Archive). Rephrase toward one of "
                "those, or pass mode_override to force a route."
            ),
            "available_modes": list(_VALID_OVERRIDES),
        },
        sources=[],
        is_verified=False,
        knowledge_gap=True,
        routing_trace=trace,
        execution_time_ms=0.0,
    )


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("")
async def routing_law() -> Dict[str, Any]:
    """The routing law, documented — what POST /v1/ask does and why."""
    return {
        "endpoint": "POST /v1/ask",
        "routing_law": [
            "1. scam (SAFETY FIRST): deterministic scam_check; a hit is "
            "risk_level in (critical, high) OR any matched_patterns.",
            "2. services: Everyday Services Pack keyword search (SASSA/SRD/"
            "SARS/UIF/NSFAS).",
            "3. history: African History Archive keyword search.",
            "4. knowledge_gap: honest no-answer. Fabricated answers and fake "
            "citations are forbidden (anti-hallucination law).",
        ],
        "mode_override": {
            "valid": list(_VALID_OVERRIDES),
            "effect": "forces exactly one route; if it does not match, the "
                      "honest knowledge_gap is returned. Invalid values -> 400.",
        },
        "response_contract": list(AskResponse.model_fields),
        "zero_cost": "No LLM, no external calls — deterministic packs only.",
    }


@router.post("", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    start = time.perf_counter()
    trace: List[str] = []

    override: Optional[str] = None
    if req.mode_override is not None:
        override = req.mode_override.strip().lower()
        if override not in _VALID_OVERRIDES:
            raise HTTPException(
                status_code=400,
                detail=f"mode_override must be one of {list(_VALID_OVERRIDES)}",
            )
        trace.append(f"override: {override} (forced)")

    response: Optional[AskResponse] = None
    if override == "scam":
        response = await _route_scam(req.prompt, trace)
    elif override == "services":
        response = _route_services(req.prompt, trace)
    elif override == "history":
        response = _route_history(req.prompt, trace)
    else:
        # Routing law order — SAFETY FIRST, then services, then history.
        response = await _route_scam(req.prompt, trace)
        if response is None:
            response = _route_services(req.prompt, trace)
        if response is None:
            response = _route_history(req.prompt, trace)

    if response is None:
        response = _knowledge_gap(req.prompt, trace)

    response.routing_trace = trace
    response.execution_time_ms = (time.perf_counter() - start) * 1000.0
    return response
