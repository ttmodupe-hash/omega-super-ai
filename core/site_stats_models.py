"""
OMEGA-LUQI Site Pulse — anonymous aggregate audience counter (PRIDE-1).

The founder asked for "a count to see how many people are watching the site".
This is the REAL counter — Postgres-backed, engine-served, fail-closed.

PRIVACY LAW (binding, same weight as the PII-scrub law):
  - NO IP addresses, NO cookies, NO user agents, NO fingerprints.
  - The only identifier is a client-generated rotating session id (sid),
    held in sessionStorage (dies with the tab) and regenerated per session.
  - Rows older than 24h are pruned on every heartbeat: this is a PULSE,
    not a tracker. We keep no long-term history of any visitor.

RLS NOTE — documented global exception (007_i18n precedent):
  This table holds zero PII and zero per-user content — only rotating
  anonymous ids, timestamps and counters. Country isolation would break
  the whole point (one global audience pulse for the landing page), so
  the RLS policy grants luqi_app_user access to all rows (USING/WITH CHECK
  true), exactly like the shared i18n reference table.

ACCURACY NOTE (honesty law):
  Without fingerprinting, dedup is approximate: one person with two tabs
  counts as two sids. That is the price of the privacy law and we pay it
  gladly — the widget says "exploring" not "unique humans".
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base  # single shared metadata registry


class SiteHeartbeat(Base):
    """One row per anonymous rotating session id. Pruned after 24h."""
    __tablename__ = "site_heartbeats"

    sid: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    heartbeats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


Index("idx_site_heartbeats_last_seen", SiteHeartbeat.last_seen)
