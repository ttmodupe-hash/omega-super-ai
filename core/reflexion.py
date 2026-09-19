"""
Reflexion critique stage — UNIFY-16 (luqi-ai #61)

Draft answer -> critique (factuality, grounding, policy) -> accept / revise / flag,
with the full critique trail persisted (reflexion_traces, migration 006) and
per-stage latency recorded against a documented budget.

Latency budget (docs/REFLEXION.md is the prose version; these constants are law):
  - Simple queries SKIP the critique entirely  -> 0 added LLM calls (1x latency)
  - Complex/risky queries add AT MOST 2 calls  -> critique (45s cap) + revise (60s cap)
  - Worst case is therefore bounded at 3x a single call, never a runaway loop.
  - One critique pass only. No recursive self-reflection loops by design.

Routing heuristic (deterministic, cheap, no LLM):
  route to critique when the question is long/multi-part, or touches risky
  domains (health, finance, law, statistics/verifiable claims, recommendations).
"""
import asyncio
import json
import re
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import kimi_client

router = APIRouter(prefix="/v1/reflexion", tags=["reflexion"])

# ── Latency budget (documented in docs/REFLEXION.md) ─────────────────────
DRAFT_TIMEOUT_S = 60
CRITIQUE_TIMEOUT_S = 45
REVISE_TIMEOUT_S = 60
MAX_ADDED_CALLS = 2  # critique + at most one revise — hard structural cap

# ── Routing heuristic ────────────────────────────────────────────────────
_LONG_QUESTION_CHARS = 280
_RISKY_RE = re.compile(
    r"\b(should i|is it true|guarantee[ds]?|law|legal|tax|sars|disease|symptom|diagnos|"
    r"medicin|dosage|invest|loan|debt|statistics?|percent|\d+%|how many|how much|"
    r"deadline|penalty|court|contract|side effects?)\b",
    re.I,
)


def should_route(question: str, force: Optional[bool] = None) -> Tuple[bool, str]:
    """Deterministic routing decision. Returns (routed, reason)."""
    if force is True:
        return True, "forced by caller"
    if force is False:
        return False, "skipped by caller"
    reasons = []
    if len(question) > _LONG_QUESTION_CHARS:
        reasons.append(f"long question ({len(question)} chars > {_LONG_QUESTION_CHARS})")
    if question.count("?") > 1:
        reasons.append("multi-part question")
    if _RISKY_RE.search(question):
        reasons.append("risk-domain keyword (health/finance/law/claims)")
    if reasons:
        return True, "; ".join(reasons)
    return False, "simple query — critique skipped (0 added latency)"


# ── Prompts ──────────────────────────────────────────────────────────────
_DRAFT_SYSTEM = (
    "You are Luqi, a careful assistant. Answer the user's question directly and "
    "completely. If you are unsure of a fact, say so instead of guessing."
)

_CRITIQUE_SYSTEM = (
    "You are a strict fact-checking critic. Review the DRAFT answer to the QUESTION on three axes:\n"
    "1. FACTUALITY — are claims accurate? Flag anything unverifiable or wrong.\n"
    "2. GROUNDING — does the answer actually address the question, or drift/pad?\n"
    "3. POLICY — medical/financial/legal claims must carry appropriate caution; "
    "no invented statistics, citations, or guarantees.\n"
    "Respond with STRICT JSON only:\n"
    '{"factuality": {"pass": true|false, "notes": "..."}, '
    '"grounding": {"pass": true|false, "notes": "..."}, '
    '"policy": {"pass": true|false, "notes": "..."}, '
    '"verdict": "accept"|"revise"|"flag", '
    '"issues": ["..."]}\n'
    'verdict rules: accept = ship as-is; revise = fixable issues, produce a corrected answer; '
    "flag = unsafe/unanswerable, must not ship."
)

_REVISE_SYSTEM = (
    "You are Luqi, a careful assistant. Rewrite your draft answer to fix EVERY issue "
    "the critic raised. Keep what was correct. If the critic flagged unverifiable "
    "claims, remove them or mark them explicitly as unverified."
)

_FLAGGED_MESSAGE = (
    "I drafted an answer but my self-critique flagged it as unsafe to send "
    "(unverifiable or policy-sensitive claims). Rather than guess, please "
    "rephrase the question or consult a qualified professional."
)


def _parse_critique(raw: str) -> Dict[str, Any]:
    """Parse the critic's JSON defensively. An unparseable critique is treated
    as 'flag' (fail-closed: unverifiable critique => do not ship blindly)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            return {"verdict": "flag", "issues": ["critique unparseable"], "parse_error": True}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"verdict": "flag", "issues": ["critique unparseable"], "parse_error": True}
    if not isinstance(data, dict):
        return {"verdict": "flag", "issues": ["critique not an object"], "parse_error": True}
    verdict = str(data.get("verdict", "")).lower()
    if verdict not in ("accept", "revise", "flag"):
        data["verdict"] = "flag"
        data.setdefault("issues", []).append(f"invalid verdict '{verdict}' — fail-closed to flag")
    return data


def _db(request: Request):
    return getattr(request.app.state, "db_engine", None)


def _persist_trace(engine, **fields) -> Optional[str]:
    """Write the critique trail. Returns trace id, or None when the DB layer
    is unavailable (reported honestly as trace_persisted=false)."""
    if engine is None:
        return None
    from sqlalchemy.orm import Session
    from .reflexion_models import ReflexionTrace

    trace = ReflexionTrace(**fields)
    with Session(engine) as session:
        session.add(trace)
        session.commit()
        return str(trace.id)


async def run_pipeline(
    question: str,
    *,
    force: Optional[bool],
    country_code: str,
    user_id: Optional[uuid.UUID],
    ab_group: Optional[str] = None,
    ab_arm: Optional[str] = None,
    db_engine=None,
) -> Dict[str, Any]:
    """The full Reflexion pipeline. Exactly one critique pass, at most one
    revise pass (MAX_ADDED_CALLS). Every stage timed."""
    t0 = time.perf_counter()
    routed, reason = should_route(question, force)

    t = time.perf_counter()
    draft = await asyncio.to_thread(
        kimi_client.chat_completion, _DRAFT_SYSTEM, question, timeout=DRAFT_TIMEOUT_S
    )
    draft_ms = int((time.perf_counter() - t) * 1000)

    critique: Optional[Dict[str, Any]] = None
    critique_ms = revise_ms = 0
    verdict = "unrouted"
    final = draft

    if routed:
        t = time.perf_counter()
        raw_critique = await asyncio.to_thread(
            kimi_client.chat_completion,
            _CRITIQUE_SYSTEM,
            f"QUESTION:\n{question}\n\nDRAFT:\n{draft}",
            timeout=CRITIQUE_TIMEOUT_S,
        )
        critique_ms = int((time.perf_counter() - t) * 1000)
        critique = _parse_critique(raw_critique)
        verdict = {"accept": "accepted", "revise": "revised", "flag": "flagged"}[critique["verdict"]]

        if critique["verdict"] == "revise":
            t = time.perf_counter()
            issues = "\n".join(f"- {i}" for i in critique.get("issues", [])) or "- general quality"
            final = await asyncio.to_thread(
                kimi_client.chat_completion,
                _REVISE_SYSTEM,
                f"QUESTION:\n{question}\n\nDRAFT:\n{draft}\n\nCRITIC ISSUES:\n{issues}",
                timeout=REVISE_TIMEOUT_S,
            )
            revise_ms = int((time.perf_counter() - t) * 1000)
        elif critique["verdict"] == "flag":
            final = _FLAGGED_MESSAGE

    total_ms = int((time.perf_counter() - t0) * 1000)
    trace_id = await asyncio.to_thread(
        _persist_trace,
        db_engine,
        user_id=user_id, country_code=country_code, ab_group=ab_group, ab_arm=ab_arm,
        question=question[:8000], routed=routed, route_reason=reason[:200],
        draft=draft, critique=critique, verdict=verdict, final_answer=final,
        draft_ms=draft_ms, critique_ms=critique_ms, revise_ms=revise_ms, total_ms=total_ms,
    )
    return {
        "answer": final,
        "routed": routed,
        "route_reason": reason,
        "verdict": verdict,
        "critique": critique,
        "trace_id": trace_id,
        "trace_persisted": trace_id is not None,
        "latency_ms": {
            "draft": draft_ms, "critique": critique_ms,
            "revise": revise_ms, "total": total_ms,
        },
    }


# ── Schemas ──────────────────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    force: Optional[bool] = Field(
        default=None,
        description="true = always critique; false = never critique; null = heuristic routing.",
    )


class ABRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/answer")
async def reflexion_answer(req: AnswerRequest, request: Request) -> Dict[str, Any]:
    """Answer with the Reflexion pipeline: draft -> (routed) critique -> ship/revise/flag."""
    country = getattr(request.state, "user_country", "") or ""
    try:
        import requests as _rq
        return await run_pipeline(
            req.question, force=req.force, country_code=country,
            user_id=None, db_engine=_db(request),
        )
    except _rq.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Upstream AI unreachable: {e}")


@router.post("/ab")
async def reflexion_ab(req: ABRequest, request: Request) -> Dict[str, Any]:
    """A/B harness: answers the SAME question twice — direct (never critiqued)
    vs full pipeline (always critiqued) — and links both traces with one
    ab_group id for side-by-side evaluation."""
    country = getattr(request.state, "user_country", "") or ""
    group = str(uuid.uuid4())
    try:
        import requests as _rq
        direct = await run_pipeline(
            req.question, force=False, country_code=country, user_id=None,
            ab_group=group, ab_arm="direct", db_engine=_db(request),
        )
        critiqued = await run_pipeline(
            req.question, force=True, country_code=country, user_id=None,
            ab_group=group, ab_arm="critique", db_engine=_db(request),
        )
    except _rq.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Upstream AI unreachable: {e}")

    d_lat, c_lat = direct["latency_ms"]["total"], critiqued["latency_ms"]["total"]
    return {
        "ab_group": group,
        "question": req.question,
        "arm_direct": direct,
        "arm_critique": critiqued,
        "comparison": {
            "answers_differ": direct["answer"] != critiqued["answer"],
            "critique_verdict": critiqued["verdict"],
            "latency_cost_ms": c_lat - d_lat,
            "latency_multiplier": round(c_lat / d_lat, 2) if d_lat else None,
        },
    }


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, request: Request) -> Dict[str, Any]:
    """Fetch a stored critique trace (the observable trail)."""
    engine = _db(request)
    if engine is None:
        raise HTTPException(status_code=503, detail="Database layer unavailable.")
    try:
        tid = uuid.UUID(trace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trace id.")

    from sqlalchemy.orm import Session
    from .reflexion_models import ReflexionTrace

    with Session(engine) as session:
        trace = session.get(ReflexionTrace, tid)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found.")
        return {
            "id": str(trace.id),
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
            "ab_group": trace.ab_group,
            "ab_arm": trace.ab_arm,
            "question": trace.question,
            "routed": trace.routed,
            "route_reason": trace.route_reason,
            "draft": trace.draft,
            "critique": trace.critique,
            "verdict": trace.verdict,
            "final_answer": trace.final_answer,
            "latency_ms": {
                "draft": trace.draft_ms, "critique": trace.critique_ms,
                "revise": trace.revise_ms, "total": trace.total_ms,
            },
        }


@router.get("/config")
async def reflexion_config() -> Dict[str, Any]:
    """The routing policy and latency budget — inspectable, documented law."""
    return {
        "routing": {
            "long_question_chars": _LONG_QUESTION_CHARS,
            "multi_part_threshold": "more than one '?'",
            "risk_domains": ["health", "finance", "law", "statistics/verifiable claims", "recommendations"],
            "override": "POST /answer with force=true|false",
        },
        "latency_budget": {
            "simple_query_added_calls": 0,
            "max_added_calls": MAX_ADDED_CALLS,
            "draft_timeout_s": DRAFT_TIMEOUT_S,
            "critique_timeout_s": CRITIQUE_TIMEOUT_S,
            "revise_timeout_s": REVISE_TIMEOUT_S,
            "worst_case": "3x a single LLM call (draft + critique + revise), hard-capped by timeouts",
            "no_recursive_loops": True,
        },
        "observability": "every run persists a reflexion_traces row with per-stage latency and the parsed critique",
        "docs": "docs/REFLEXION.md",
    }
