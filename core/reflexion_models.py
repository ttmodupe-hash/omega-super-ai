"""
OMEGA-LUQI Reflexion Persistence Layer (UNIFY-16)

One table: reflexion_traces — the observable critique trail.
Every Reflexion pipeline run (draft -> critique -> accept/revise/flag)
writes one row: question, draft, parsed critique, verdict, final answer,
and per-stage latency. This is the acceptance evidence for UNIFY-16:
"critique traces in DB".

Registered on the SAME shared Base as models.py / companion_models.py.

RLS anchor: country_code (003/004/005 pattern). user_id is a plain UUID
when a session token is present, NULL for anonymous calls — traces are
request-scoped diagnostics, not identity records.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base  # single shared metadata registry


class ReflexionTrace(Base):
    __tablename__ = "reflexion_traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Request context
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, default="")  # RLS anchor
    ab_group: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # shared id per A/B pair
    ab_arm: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)    # "direct" | "critique"

    # Routing decision
    question: Mapped[str] = mapped_column(Text, nullable=False)
    routed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    route_reason: Mapped[str] = mapped_column(String(200), nullable=False)

    # Pipeline artifacts
    draft: Mapped[str] = mapped_column(Text, nullable=False)
    critique: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False)  # accepted | revised | flagged | unrouted
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Latency budget observability (milliseconds per stage)
    draft_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critique_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revise_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_reflexion_traces_user", "user_id", "created_at"),
        Index("idx_reflexion_traces_ab", "ab_group"),
    )
