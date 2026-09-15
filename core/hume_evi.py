"""
OMEGA-LUQI Hume EVI Ingestion Hooks - receives Hume webhook session payloads.

Honest scope: these are the RECEIVING endpoints (Hume -> Luqi). The Hume EVI
client subscription (student -> Hume voice sessions) remains the integration
step - see docs/OMEGA_STREAM_COVERAGE.md.

Security: HMAC-SHA256 of the RAW body against HUME_WEBHOOK_SECRET, compared
with compare_digest. Secret unset -> 503 (hooks disabled, fail-closed).
The pasted blueprint "verified" any non-empty header - that is fake security
and is not how these endpoints behave.
"""
import hashlib
import hmac
import os
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .admin_auth import verify_admin
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/voice/hume", tags=["Hume EVI Ingestion"])

CRISIS_LINE = "SADAG 24hr: 0800 567 567 | Emergency: 10177"


class EmotiveState(BaseModel):
    calm: float = 0.0
    anxiety: float = 0.0
    distress: float = 0.0


class HumeSessionPayload(BaseModel):
    session_id: str
    student_id: str
    duration_seconds: float = 0.0
    transcript_snippet: str = ""
    predominant_emotive_state: EmotiveState = Field(default_factory=EmotiveState)


def _secret() -> str:
    s = os.getenv("HUME_WEBHOOK_SECRET", "")
    if not s:
        raise HTTPException(status_code=503, detail="HUME_WEBHOOK_SECRET not set - hooks disabled (fail-closed)")
    return s


def verify_signature(raw_body: bytes, signature_header: Optional[str]) -> None:
    """Real verification: HMAC-SHA256 of raw bytes, constant-time compare.
    Raises 401 on missing header, 403 on mismatch. 503 when hooks unconfigured."""
    _secret()  # fail-closed when unconfigured
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hume-Signature header")
    expected = hmac.new(_secret().encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="Signature mismatch")


_sessions: List[Dict[str, Any]] = []
_lock = threading.Lock()

DISTRESS_ANXIETY = float(os.getenv("HUME_DISTRESS_ANXIETY", "0.85"))
DISTRESS_DISTRESS = float(os.getenv("HUME_DISTRESS_DISTRESS", "0.80"))


def is_intervention(emotive: EmotiveState) -> bool:
    return emotive.anxiety >= DISTRESS_ANXIETY or emotive.distress >= DISTRESS_DISTRESS


@router.post("/session-complete", status_code=202)
async def ingest_session(request: Request) -> Dict[str, Any]:
    raw = await request.body()
    verify_signature(raw, request.headers.get("X-Hume-Signature"))
    payload = HumeSessionPayload(**(__import__("json").loads(raw)))

    emotive = payload.predominant_emotive_state
    intervention = is_intervention(emotive)
    record = {"session_id": payload.session_id, "student_id": payload.student_id[:8],
              "duration_s": payload.duration_seconds,
              "transcript": scrub_pii(payload.transcript_snippet)[:200],
              "anxiety": emotive.anxiety, "distress": emotive.distress,
              "intervention": intervention, "at": time.time()}
    with _lock:
        _sessions.append(record)

    if intervention:
        # Real action: crisis line in the response + alert a human mentor now.
        try:
            from .notifications import _gateway
            import asyncio
            asyncio.get_running_loop().create_task(
                _gateway.send_gate_lock_alert(payload.session_id, "hume_distress",
                                              f"High distress in voice session {payload.session_id[:8]} - follow up"))
        except Exception:
            pass  # alerting must never break ingestion
        return {"session_id": payload.session_id, "status": "INTERVENTION_TRIGGERED",
                "crisis_line": CRISIS_LINE, "telemetry_logged": True}

    return {"session_id": payload.session_id, "status": "TELEMETRY_INGESTED",
            "telemetry_logged": True}


@router.get("/stats")
async def hume_stats(is_authenticated: bool = Depends(verify_admin)):
    with _lock:
        snap = list(_sessions)
    interventions = [s for s in snap if s["intervention"]]
    return {"sessions": len(snap), "interventions": len(interventions),
            "avg_anxiety": round(sum(s["anxiety"] for s in snap) / len(snap), 3) if snap else 0,
            "scope_note": "ingestion hooks only - Hume EVI client subscription is the remaining integration step"}
