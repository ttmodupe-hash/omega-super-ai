"""
OMEGA-LUQI Site Pulse API (PRIDE-1) — real, anonymous audience counter.

Endpoints:
  POST /v1/stats/heartbeat  {sid}  -> upsert pulse + return live aggregates
  GET  /v1/stats/audience          -> read-only aggregates (no write)

Aggregates returned (all computed from Postgres, never fabricated):
  total_views      sum of all heartbeat events in the last 24h window
                   (plus surviving history: heartbeats counter is cumulative
                   per sid while the sid row lives)
  unique_visitors  distinct anonymous session ids seen in the last 24h
  watching_now     distinct sids with a heartbeat in the last 3 minutes

House laws honoured:
  - fail-closed: honest 503 when the persistence layer is down, the landing
    page hides the widget rather than showing a fake number
  - privacy: no IP, no cookie, no fingerprint; sid is client-generated,
    sessionStorage-scoped, 8-64 chars of [A-Za-z0-9_-] (regex-enforced)
  - bounded: every heartbeat prunes rows older than 24h so the table is
    always a pulse, never a dossier
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .site_stats_models import SiteHeartbeat

site_stats_router = APIRouter(prefix="/v1/stats", tags=["Site Pulse"])

WATCHING_NOW_WINDOW = timedelta(minutes=3)
PRUNE_AFTER = timedelta(hours=24)
SID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class HeartbeatIn(BaseModel):
    sid: str = Field(..., min_length=8, max_length=64)


def _db(request: Request) -> Session:
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Site pulse unavailable: database layer is down.")
    return Session(engine)


def _now(session: Session) -> datetime:
    """Timezone-safe 'now': aware UTC on Postgres (TIMESTAMPTZ columns),
    naive UTC on the SQLite dev fallback (house companion pattern)."""
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        return datetime.now(timezone.utc)
    return datetime.utcnow()


def _aggregates(session: Session) -> Dict[str, int]:
    now = _now(session)
    watching_cutoff = now - WATCHING_NOW_WINDOW
    prune_cutoff = now - PRUNE_AFTER
    # Bounded-table law: prune the pulse's history older than 24h.
    session.query(SiteHeartbeat).filter(SiteHeartbeat.last_seen < prune_cutoff).delete()
    total_views = session.query(func.coalesce(func.sum(SiteHeartbeat.heartbeats), 0)).scalar()
    unique_visitors = session.query(func.count(SiteHeartbeat.sid)).scalar()
    watching_now = (
        session.query(func.count(SiteHeartbeat.sid))
        .filter(SiteHeartbeat.last_seen >= watching_cutoff)
        .scalar()
    )
    return {
        "total_views": int(total_views or 0),
        "unique_visitors": int(unique_visitors or 0),
        "watching_now": int(watching_now or 0),
        "watching_now_window_seconds": int(WATCHING_NOW_WINDOW.total_seconds()),
    }


@site_stats_router.post("/heartbeat")
def heartbeat(payload: HeartbeatIn, request: Request) -> Dict[str, object]:
    """One call per page view + every ~45s while the tab is open.

    The same call returns the live aggregates, so low-bandwidth African
    nodes pay ONE round-trip for both counting and display.
    """
    if not SID_PATTERN.match(payload.sid):
        raise HTTPException(status_code=422, detail="sid must be 8-64 chars of [A-Za-z0-9_-].")
    with _db(request) as session:
        row = session.get(SiteHeartbeat, payload.sid)
        if row is None:
            row = SiteHeartbeat(sid=payload.sid)
            session.add(row)
            try:
                session.flush()
            except IntegrityError:
                # Concurrent first-heartbeat for the same sid: another worker
                # won the insert race; reload and fall through to the update.
                session.rollback()
                row = session.get(SiteHeartbeat, payload.sid)
                if row is None:
                    raise HTTPException(status_code=503, detail="Site pulse busy: retry the heartbeat.")
        row.last_seen = _now(session)
        row.heartbeats = (row.heartbeats or 0) + 1
        stats = _aggregates(session)
        session.commit()
    return {"ok": True, **stats}


@site_stats_router.get("/audience")
def audience(request: Request) -> Dict[str, object]:
    """Read-only pulse for display widgets that must not inflate the count."""
    with _db(request) as session:
        stats = _aggregates(session)
        session.commit()  # persist the prune
    return {"ok": True, **stats}
