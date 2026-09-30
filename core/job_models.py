"""
OMEGA-LUQI Job Ledger Persistence (JOBS-1)

One table: job_records — terminal states of async jobs (completed/failed),
so results survive restarts. This is the "checkpoint" capability the
external LangGraph proposal asked for, delivered on the existing SQLAlchemy
layer (the paste's own checkpointer was MemorySaver — RAM, lost on restart).

Privacy note: bill-audit results contain user-submitted billing lines
(phone numbers, serial numbers). Retention/POPIA policy is a founder
decision; the ledger exists for dispute-trail continuity, not profiling.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base  # single shared metadata registry


class JobRecord(Base):
    __tablename__ = "job_records"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # completed | failed
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    step: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
