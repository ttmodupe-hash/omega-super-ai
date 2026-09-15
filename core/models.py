"""
Luqi-AI Persistence Layer (SQLAlchemy v2 + PostgreSQL)
Tracks student progress across institutional tiers and geo-specific payment rules.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base architectural layout for all Luqi-AI entity tables."""
    pass


class TierType(str, PyEnum):
    PRIMARY = "primary"
    HIGH_SCHOOL = "high_school"
    TVET = "tvet"
    UNIVERSITY = "university"
    GLOBAL_PREMIUM = "global_premium"


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)  # e.g., "ZAF", "KEN", "USA"
    tier: Mapped[TierType] = mapped_column(Enum(TierType), default=TierType.PRIMARY, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    progress_records: Mapped[List["LabProgress"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    payment_records: Mapped[List["PaymentTransaction"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class LabProgress(Base):
    __tablename__ = "lab_progress"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    lab_track: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "networking", "robotics"
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    last_known_sandbox_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    saved_state_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="progress_records")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # e.g., "ZAR", "KES", "USD"
    gateway_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "M-Pesa", "Stripe", "PayFast"
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    hitl_clearance_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="payment_records")


class CurriculumLesson(Base):
    __tablename__ = "curriculum_lessons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    track_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    lesson_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_body: Mapped[str] = mapped_column(Text, nullable=False)
    tier_target: Mapped[str] = mapped_column(String(50), nullable=False)


class VocationalModule(Base):
    __tablename__ = "vocational_modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    track_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_hours: Mapped[int] = mapped_column(Integer, nullable=False)