"""
OMEGA-LUQI Truth Engine (Batch G) - dual-agent adversarial answer verification.

Honesty contract, stated plainly: no LLM pipeline can GUARANTEE truth - the
auditor shares the generator's failure modes, so "never hallucinates" is not a
claim this module makes. What it enforces deterministically:

  1. The generator cannot approve its own answer (separation of concerns).
  2. Every factual claim must carry a source tag; the auditor rejects
     unsupported or vaguely-sourced checkable claims via a strict schema.
  3. Uncertainty is explicit: the generator must list what it cannot verify.
  4. A rejected answer is NEVER presented as final. When the circuit breaker
     trips, the caller gets status="unverified" + audit findings + the draft
     under a "draft" key (never "answer") flagged verification_failed.
  5. Fail-closed: brain fault / unparseable audit / out-of-schema verdict all
     degrade to honest statuses - never a crash, never a fake "verified".

All brain calls route through core/kimi_client.chat_completion (unified key
check + cost circuit-breaker + forced JSON response format). Blocking HTTP
runs in threads so the event loop never stalls.

NOTE: no `from __future__ import annotations` here - slowapi's limiter.limit
wraps endpoints, and FastAPI resolves string annotations in the WRAPPER's
globals (pydantic 2.6 raises PydanticUndefinedAnnotation). Real annotation
objects keep route registration sound on the pinned CI dependency set.

Env: LUQI_TRUTH_PIPELINE=1 hooks /v1/agent/kimi-reason (default off),
TRUTH_MAX_REVISIONS (default 2 = max 3 generator calls), RATE_LIMIT_TRUTH.
"""
import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .admin_auth import verify_admin
from .rate_limiter import limiter, TRUTH_LIMIT
from . import ops_journal

router = APIRouter(prefix="/v1/truth", tags=["Truth Engine"])

MAX_REVISIONS = int(os.getenv("TRUTH_MAX_REVISIONS", "2"))

_meter = {"runs": 0, "verified": 0, "unverified": 0, "unavailable": 0, "revisions": 0}


class AuditVerdict(BaseModel):
    """The auditor's strict verdict schema. Bounds enforced: confidence 0..1."""
    is_truthful_and_accurate: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    audit_findings: list[str] = Field(default_factory=list)
    recalibration_instructions: str = ""


class Draft(BaseModel):
    """Generator output schema: the answer plus its epistemic receipts."""
    answer: str
    claims: list[dict] = Field(default_factory=list)        # [{"claim": ..., "source": ...}]
    uncertainties: list[str] = Field(default_factory=list)


GENERATOR_SYSTEM = (
    "You are Luqi-AI's primary answering agent with absolute epistemic discipline.\n"
    "1. Never guess. If a fact cannot be stated with confidence, move it to "
    "'uncertainties' instead of asserting it.\n"
    "2. Every factual claim in the answer must also appear in 'claims' with a "
    "'source' tag naming its origin (e.g. 'WHO 2024 report', 'user-provided data'). "
    "'general knowledge' is acceptable only for truly common knowledge.\n"
    "3. Reply with STRICT JSON only: "
    "{\"answer\": str, \"claims\": [{\"claim\": str, \"source\": str}], \"uncertainties\": [str]}"
)

AUDITOR_SYSTEM = (
    "You are an adversarial truth auditor. Audit the candidate answer line by line "
    "against the user query.\n"
    "REJECT if: a factual claim is unsupported or invented; uncertainty is "
    "concealed; a checkable fact carries a vague source; tone overstates certainty.\n"
    "APPROVE only if the answer is grounded, checkable claims carry real sources, "
    "and uncertainties are honestly disclosed.\n"
    "Reply with STRICT JSON only: {\"is_truthful_and_accurate\": bool, "
    "\"confidence_score\": number 0..1, \"audit_findings\": [str], "
    "\"recalibration_instructions\": str}"
)


async def _brain(system: str, user: str) -> str:
    """Unified fail-closed brain call (raises HTTPException on no key/budget/fault)."""
    from .kimi_client import chat_completion
    return await asyncio.to_thread(chat_completion, system, user, timeout=90)


def _parse_json(text: str) -> dict:
    start, end = text.index("{"), text.rindex("}") + 1
    return json.loads(text[start:end])


def _parse_verdict(text: str) -> AuditVerdict:
    """Fail-closed parse: malformed or out-of-schema auditor output is a REJECT,
    never a crash and never an approve."""
    try:
        return AuditVerdict(**_parse_json(text))
    except Exception as exc:
        return AuditVerdict(
            is_truthful_and_accurate=False, confidence_score=0.0,
            audit_findings=[f"auditor output unparseable or schema-invalid: {type(exc).__name__}"],
            recalibration_instructions=(
                "Regenerate with STRICT JSON: answer, claims with sources, uncertainties."))


def _parse_draft(text: str):
    try:
        return Draft(**_parse_json(text))
    except Exception:
        return None


def _journal(status: str, revisions: int, verdict, query: str) -> None:
    ops_journal.record({"kind": "truth_verdict", "status": status, "revisions": revisions,
                        "confidence": verdict.confidence_score if verdict else None,
                        "findings": len(verdict.audit_findings) if verdict else 0,
                        "query": query[:200]})


async def _generate(query: str, verdict):
    recalibration = ""
    if verdict is not None and not verdict.is_truthful_and_accurate:
        recalibration = (
            "\n\n[CRITICAL AUDIT REJECTION - RECALIBRATION REQUIRED]\n"
            f"Audit findings: {'; '.join(verdict.audit_findings)}\n"
            f"Instructions: {verdict.recalibration_instructions}\n"
            "Fix every point. Do not speculate - move unverifiable facts to uncertainties."
        )
    raw = await _brain(GENERATOR_SYSTEM, f"User question: {query}{recalibration}")
    return _parse_draft(raw)


async def _audit(query: str, answer_text: str) -> AuditVerdict:
    raw = await _brain(AUDITOR_SYSTEM,
                       f"User query: {query}\n\nCandidate answer:\n{answer_text}\n\n"
                       "Perform a strict line-by-line audit and return your verdict.")
    return _parse_verdict(raw)


async def truth_seek(query: str, max_revisions: int = MAX_REVISIONS) -> dict:
    """The full pipeline: generate -> adversarial audit -> recalibrate, capped.

    Returns status verified | unverified. Brain faults raise HTTPException
    (fail-closed, repo-standard) after meter + journal accounting."""
    if not (query or "").strip():
        raise HTTPException(status_code=400, detail="empty query")
    _meter["runs"] += 1
    verdict = None
    draft = None
    revisions = 0
    try:
        while True:
            draft = await _generate(query, verdict)
            revisions += 1
            _meter["revisions"] += 1
            if draft is None:
                verdict = AuditVerdict(
                    is_truthful_and_accurate=False, confidence_score=0.0,
                    audit_findings=["generator returned malformed JSON"],
                    recalibration_instructions=(
                        "Reply with STRICT JSON only: {answer, claims, uncertainties}."))
            else:
                verdict = await _audit(query, draft.answer)
            if verdict.is_truthful_and_accurate and draft is not None:
                _meter["verified"] += 1
                _journal("verified", revisions, verdict, query)
                return {"status": "verified", "answer": draft.answer,
                        "claims": draft.claims, "uncertainties": draft.uncertainties,
                        "audit": verdict.model_dump(), "revisions": revisions}
            if revisions > max_revisions:
                break
    except HTTPException:
        _meter["unavailable"] += 1
        _journal("unavailable", revisions, None, query)
        raise
    # Circuit breaker tripped: the draft is delivered as UNVERIFIED, never as the answer.
    _meter["unverified"] += 1
    _journal("unverified", revisions, verdict, query)
    report = {"status": "unverified", "verification_failed": True,
              "audit": verdict.model_dump() if verdict else None, "revisions": revisions,
              "note": "Circuit breaker tripped: the auditor did not pass this answer within "
                      "the revision cap. The draft below did NOT pass verification."}
    if draft is not None:
        report["draft"] = {"answer": draft.answer, "claims": draft.claims,
                           "uncertainties": draft.uncertainties}
    return report


async def verify_draft(query: str, draft_text: str) -> dict:
    """Gateway hook: audit an existing plain-text draft. Verified -> pass through
    unchanged. Rejected -> run the full recalibration loop and report honestly."""
    _meter["runs"] += 1
    verdict = await _audit(query, draft_text)
    if verdict.is_truthful_and_accurate:
        _meter["verified"] += 1
        _journal("verified", 0, verdict, query)
        return {"status": "verified", "answer": draft_text,
                "audit": verdict.model_dump(), "revisions": 0}
    report = await truth_seek(query)
    if report["status"] == "verified":
        report["note"] = ("Initial draft was rejected by the auditor; the answer was "
                          "regenerated inside the verification loop.")
    return report


class TruthRequest(BaseModel):
    query: str = ""


@router.post("/answer")
@limiter.limit(TRUTH_LIMIT)
async def answer(request: Request, req: TruthRequest = None,
                 _: bool = Depends(verify_admin)) -> dict:
    """Admin-gated verification pipeline. JSON body {"query": "..."} preferred
    (keeps queries out of URL logs); ?query= accepted for curl/console use."""
    query = ""
    if req is not None and req.query.strip():
        query = req.query
    else:
        try:
            body = await request.json()
            query = str(body.get("query", ""))
        except Exception:
            pass
        if not query.strip():
            query = dict(request.query_params).get("query", "")
    return await truth_seek(query)


@router.get("/metrics")
async def truth_metrics(_: bool = Depends(verify_admin)) -> dict:
    return dict(_meter)
