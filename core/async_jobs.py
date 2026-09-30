"""
OMEGA-LUQI Async Job Runner (JOBS-1) — 2026-09-30

Zero-infra background execution with polling and persistent results.

The external proposal wanted Celery + Redis worker fleets. House verdict
(cost law — everything is founder-funded, no revenue yet):
  * The engine's background workloads are deterministic rule passes measured
    in microseconds — there is no heavy compute to offload to a paid worker
    fleet.
  * Celery + a Redis broker + always-on worker processes would add recurring
    Railway cost for zero user-visible gain today.
  * If genuine scale-out is ever needed, STATE_BACKEND=redis already exists
    as the multi-worker option; revisit with revenue, not before.

So JOBS-1 delivers the same CONTRACT with zero new infrastructure:
  POST /v1/jobs/bill-audit   -> 202 Accepted + job_id + poll_url (in-process
                                asyncio execution, real stage-by-stage progress)
  GET  /v1/jobs/{job_id}     -> honest status: queued | running | completed |
                                failed, with progress %, current step, result
  GET  /v1/jobs/health       -> runner status + honest backend declaration

Persistence law: terminal job states (completed/failed) are written to
Postgres (job_records table) when the DB layer is up, so results survive
restarts — the "checkpoint" the proposal asked for, delivered on the
existing SQLAlchemy layer instead of a LangGraph MemorySaver (which is RAM
and loses everything on restart — the paste's own production path was a
comment). In-memory registry is LRU-capped; DB fetch is the fallback.

Kill switch: DISABLED_ENGINES containing "async_jobs" -> 503, honestly.
"""
import asyncio
import os
import threading
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/jobs", tags=["Async Jobs (JOBS-1)"])

_JOB_CAP = 500  # LRU bound on the in-memory registry


class _JobStore:
    """Thread-safe LRU registry; Postgres is the restart-surviving layer."""

    def __init__(self) -> None:
        self._jobs: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    def put(self, job_id: str, record: Dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = record
            self._jobs.move_to_end(job_id)
            while len(self._jobs) > _JOB_CAP:
                self._jobs.popitem(last=False)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                self._jobs.move_to_end(job_id)
            return rec

    def counts(self) -> Dict[str, int]:
        with self._lock:
            out: Dict[str, int] = {}
            for r in self._jobs.values():
                out[r["status"]] = out.get(r["status"], 0) + 1
            return out

    def tracked(self) -> int:
        with self._lock:
            return len(self._jobs)


_STORE = _JobStore()


# ── Postgres persistence (best-effort; never breaks the job path) ────────

def _persist(engine, record: Dict[str, Any]) -> bool:
    """Write the terminal job record. Returns True when the row landed."""
    if engine is None:
        return False
    try:
        import json
        from sqlalchemy.orm import Session
        from .job_models import JobRecord

        with Session(engine) as s:
            s.merge(JobRecord(
                job_id=record["job_id"], kind=record["kind"],
                status=record["status"], progress=record["progress"],
                step=record.get("step"),
                result_json=json.dumps(record.get("result")) if record.get("result") is not None else None,
                error=record.get("error"),
                updated_at=datetime.utcnow()))
            s.commit()
        return True
    except Exception as e:
        print(f"[OMEGA-LUQI] Job persistence failed (non-fatal): {e}")
        return False


def _load_persisted(engine, job_id: str) -> Optional[Dict[str, Any]]:
    if engine is None:
        return None
    try:
        import json
        from sqlalchemy.orm import Session
        from .job_models import JobRecord

        with Session(engine) as s:
            row = s.get(JobRecord, job_id)
            if row is None:
                return None
            return {"job_id": row.job_id, "kind": row.kind, "status": row.status,
                    "progress": row.progress, "step": row.step,
                    "result": json.loads(row.result_json) if row.result_json else None,
                    "error": row.error, "persisted": True,
                    "note": "served from the Postgres job ledger (restart-surviving)"}
    except Exception:
        return None


# ── Job kind registry (extensible, explicit) ─────────────────────────────

def _run_bill_audit(payload: Dict[str, Any], progress: Callable[[str, int], None]) -> Dict[str, Any]:
    from .bill_audit import audit_lines
    progress("ingesting billing lines", 25)
    lines = payload["lines"]
    progress("applying deterministic anomaly rules", 60)
    result = audit_lines(lines)
    progress("compiling reconciliation report", 90)
    return result


JOB_KINDS: Dict[str, Dict[str, Any]] = {
    "bill-audit": {
        "runner": _run_bill_audit,
        "description": "Consumer Shield telecom billing anomaly audit (deterministic)",
    },
}


# ── Schemas ──────────────────────────────────────────────────────────────

class BillAuditJobRequest(BaseModel):
    lines: List[Dict[str, Any]] = Field(min_length=1, max_length=10_000)


# ── Runner ───────────────────────────────────────────────────────────────

async def _execute(job_id: str, kind: str, payload: Dict[str, Any],
                   engine) -> None:
    def progress(step: str, pct: int) -> None:
        rec = _STORE.get(job_id)
        if rec is not None:
            rec.update(status="running", step=step, progress=pct)

    rec = _STORE.get(job_id)
    if rec is None:
        return
    rec.update(status="running", step="starting", progress=5)
    try:
        result = await asyncio.to_thread(JOB_KINDS[kind]["runner"], payload, progress)
        rec.update(status="completed", step="done", progress=100, result=result)
    except Exception as e:
        rec.update(status="failed", step="failed", progress=100, error=str(e))
    rec["persisted"] = _persist(engine, rec)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/bill-audit", status_code=202)
async def dispatch_bill_audit(req: BillAuditJobRequest, request: Request) -> JSONResponse:
    """Dispatch a billing audit as a trackable background job (202 + poll)."""
    if "async_jobs" in os.getenv("DISABLED_ENGINES", ""):
        raise HTTPException(status_code=503, detail={
            "error": "async job runner offline (kill switch)", "fail_closed": True})
    job_id = str(uuid.uuid4())
    _STORE.put(job_id, {"job_id": job_id, "kind": "bill-audit",
                        "status": "queued", "progress": 0, "step": "queued",
                        "result": None, "error": None})
    engine = getattr(request.app.state, "db_engine", None)
    asyncio.get_event_loop().create_task(
        _execute(job_id, "bill-audit", {"lines": req.lines}, engine))
    return JSONResponse(status_code=202, content={
        "job_id": job_id, "kind": "bill-audit", "status": "queued",
        "poll_url": f"/v1/jobs/{job_id}",
        "note": "in-process execution (JOBS-1) - no paid worker fleet; "
                "terminal results persist to Postgres when the DB is up"})


@router.get("/health")
async def jobs_health(request: Request) -> Dict[str, Any]:
    engine = getattr(request.app.state, "db_engine", None)
    return {
        "kill_switch": "async_jobs" in os.getenv("DISABLED_ENGINES", ""),
        "backend": "in-process asyncio + Postgres job ledger" if engine is not None
                   else "in-process asyncio (Postgres unavailable - memory only, honest)",
        "kinds": sorted(JOB_KINDS),
        "tracked_jobs": _STORE.tracked(),
        "status_counts": _STORE.counts(),
        "memory_cap": _JOB_CAP,
    }


@router.get("/{job_id}")
async def job_status(job_id: str, request: Request) -> Dict[str, Any]:
    """Poll a job. Memory first; Postgres ledger as the restart-surviving fallback."""
    rec = _STORE.get(job_id)
    if rec is not None:
        return rec
    persisted = _load_persisted(getattr(request.app.state, "db_engine", None), job_id)
    if persisted is not None:
        return persisted
    raise HTTPException(status_code=404, detail={
        "error": f"job '{job_id}' not found",
        "honest_note": "in-memory jobs are lost on restart; only terminal "
                       "states persist to the Postgres job ledger"})
