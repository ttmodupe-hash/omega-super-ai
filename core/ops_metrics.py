"""
OMEGA-LUQI Ops Metrics - the article's KPI mandate, made concrete.

Tracks deployment and incident events; computes DORA-style metrics:
  deployment_frequency   deploys per week (sliding window)
  change_failure_rate    incidents / deploys (%) in window
  mttr_hours             mean time to resolve incidents

Events are admin-recorded (POST /v1/ops/event) - honest scope: this measures
what the team logs. Computation is pure and unit-tested without a clock.
"""
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .admin_auth import verify_admin

router = APIRouter(prefix="/v1/ops", tags=["Ops Metrics"])

_lock = threading.Lock()
_events: List[Dict[str, Any]] = []  # {"type": "deploy"|"incident_start"|"incident_resolved", "at": epoch}

WINDOW_SECONDS = 7 * 24 * 3600  # 1-week sliding window


class OpsEvent(BaseModel):
    type: str  # deploy | incident_start | incident_resolved


# ---------------- pure computation (offline-tested) ----------------

def compute_metrics(events: List[Dict[str, Any]], now: Optional[float] = None) -> Dict[str, Any]:
    now = now if now is not None else time.time()
    window = [e for e in events if now - e["at"] <= WINDOW_SECONDS]
    deploys = [e for e in window if e["type"] == "deploy"]
    starts = [e for e in window if e["type"] == "incident_start"]
    resolves = [e for e in window if e["type"] == "incident_resolved"]

    # MTTR: pair each start with the next resolve after it
    resolutions = []
    used = set()
    for s in starts:
        for r in resolves:
            if r["at"] >= s["at"] and id(r) not in used:
                resolutions.append(r["at"] - s["at"])
                used.add(id(r))
                break
    mttr_hours = round(sum(resolutions) / len(resolutions) / 3600, 2) if resolutions else None

    open_incidents = len(starts) - len(resolutions)
    change_failure_rate = round(len(starts) / len(deploys) * 100, 1) if deploys else None

    return {
        "window_days": WINDOW_SECONDS // 86400,
        "deployments": len(deploys),
        "deployment_frequency_per_week": round(len(deploys) / (WINDOW_SECONDS / 604800), 2),
        "incidents_started": len(starts),
        "incidents_resolved": len(resolutions),
        "open_incidents": max(0, open_incidents),
        "change_failure_rate_pct": change_failure_rate,
        "mttr_hours": mttr_hours,
    }


def error_budget_remaining(slo_percent: float, window_seconds: float,
                           downtime_seconds: float) -> Dict[str, Any]:
    """Pure SRE math: how much failure allowance is left in the window.
    Budget = (1 - SLO) * window; remaining = budget - downtime."""
    budget = (1.0 - slo_percent / 100.0) * window_seconds
    remaining = budget - downtime_seconds
    return {
        "slo_percent": slo_percent,
        "budget_seconds": round(budget, 1),
        "downtime_seconds": round(downtime_seconds, 1),
        "remaining_seconds": round(remaining, 1),
        "budget_exhausted": remaining < 0,
        "burn_rate": round(downtime_seconds / budget, 2) if budget > 0 else None,
    }


def freeze_required(slo_percent: float, window_seconds: float,
                    downtime_seconds: float) -> bool:
    """True when the error budget is exhausted - deployments must freeze.
    CI gate: assert not freeze_required(...) before non-hotfix deploys."""
    return error_budget_remaining(slo_percent, window_seconds, downtime_seconds)["budget_exhausted"]


# ---------------- endpoints ----------------

@router.post("/event", status_code=201)
async def record_event(event: OpsEvent,
                       is_authenticated: bool = Depends(verify_admin)):
    if event.type not in ("deploy", "incident_start", "incident_resolved"):
        return {"recorded": False, "error": "type must be deploy|incident_start|incident_resolved"}
    with _lock:
        _events.append({"type": event.type, "at": time.time()})
    return {"recorded": True, "type": event.type}


@router.get("/metrics")
async def metrics(is_authenticated: bool = Depends(verify_admin)):
    with _lock:
        snapshot = list(_events)
    return compute_metrics(snapshot)
