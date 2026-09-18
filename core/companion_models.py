"""
OMEGA-LUQI Companion Persistence Layer (UNIFY-12)

Tables for the persistent, trainable companion:
  - companion_profiles      one row per user: identity, personality, trust, streak
  - companion_memories      durable long-term memory (durable upgrade of core/memory.py)
  - companion_feedback      durable ratings (durable upgrade of core/feedback.py)
  - companion_directives    bounded behavior knobs derived from feedback
  - companion_training_log  audit trail: feedback -> directive change (measurable
                            behavior-change path, UNIFY-12 acceptance evidence)

Registered on the SAME shared Base as models.py / enterprise_models.py.

DESIGN NOTE - no FK to students(id) yet: the auth registry
(core/auth.py) is in-memory for v1, so authenticated user_ids are NOT rows
in students. A hard FK would make every companion endpoint 500 for real
users today. user_id stays a plain indexed UUID until the accounts
unification lands; country_code remains the RLS anchor (003/004 pattern).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Boolean, JSON, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base  # single shared metadata registry


class CompanionProfile(Base):
    """One companion identity per user - name, personality, relationship state."""
    __tablename__ = "companion_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)  # RLS anchor
    companion_name: Mapped[str] = mapped_column(String(60), default="Luqi", nullable=False)
    personality: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # personality keys (all int 1-5): warmth, humor, formality
    level: Mapped[str] = mapped_column(String(20), default="beginner", nullable=False)
    trust_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.100"), nullable=False)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CompanionMemory(Base):
    """Durable per-user memory. PII-scrubbed on write, capped per user."""
    __tablename__ = "companion_memories"
    __table_args__ = (
        Index("idx_companion_mem_user_topic", "user_id", "topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5
    recall_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_recalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CompanionFeedback(Base):
    """Durable companion ratings. The trainer consumes unconsumed rows."""
    __tablename__ = "companion_feedback"
    __table_args__ = (
        Index("idx_companion_fb_user_consumed", "user_id", "consumed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="chat", nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CompanionDirective(Base):
    """Bounded behavior knob. Whitelisted knob/value pairs ONLY - the trainer
    writes these, the prompt builder renders them as fixed template sentences.
    Raw user text never becomes a directive value."""
    __tablename__ = "companion_directives"
    __table_args__ = (
        UniqueConstraint("user_id", "knob", name="uq_companion_directive_user_knob"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    knob: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(60), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="feedback", nullable=False)  # feedback | explicit
    evidence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CompanionTrainingLog(Base):
    """Immutable audit row for every directive change the trainer makes.
    This IS the measurable behavior-change path: old_value -> new_value with
    the feedback row ids that caused it."""
    __tablename__ = "companion_training_log"
    __table_args__ = (
        Index("idx_companion_trainlog_user", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    knob: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    new_value: Mapped[str] = mapped_column(String(60), nullable=False)
    feedback_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
