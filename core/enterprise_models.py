"""
OMEGA-LUQI Enterprise & Audit Persistence Layer

Implements the enterprise-grade relational structure for the sovereign
business tools: human-gate audit trail (POPIA accountability), registered
enterprises, and tender tracking.

Registered on the SAME Base metadata as models.py, so one create_all covers
the whole schema with no drift between registries.

NOTE on the source document: the pasted blueprint labeled this code
"alembic/env.py" - that filename is Alembic's configuration script, not a
model module. This is the corrected home. A real Alembic env.py + migration
autogeneration can be scaffolded from these models when you adopt versioned
migrations.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON, Enum, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base  # single shared metadata registry


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SystemAuditLog(Base):
    """Immutable record of every action released or rejected at the 30% gate.

    operator_identity is a SHA-256 hash of the admin key - the raw key is
    NEVER persisted (POPIA minimality principle).
    """
    __tablename__ = "system_audit_logs"
    __table_args__ = (
        Index("idx_audit_task_status", "action_type", "status"),
        Index("idx_audit_timestamp", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    operator_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False)
    payload_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    ip_address_origin: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv4 + IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SovereignEnterprise(Base):
    __tablename__ = "sovereign_enterprises"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_registration_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)  # "ZAF", "KEN", ...
    tax_reference_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tender_logs: Mapped[list["TenderTracking"]] = relationship(back_populates="enterprise", cascade="all, delete-orphan")


class TenderTracking(Base):
    __tablename__ = "tender_tracking"
    __table_args__ = (
        Index("idx_tender_closing_date", "closing_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sovereign_enterprises.id", ondelete="CASCADE"), nullable=False)
    tender_reference_number: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    compliance_checklist_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    # FIXED: Numeric(15,2) returns Decimal, not float
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    enterprise: Mapped["SovereignEnterprise"] = relationship(back_populates="tender_logs")


# --- Wallet ledger (ORM mirrors of core/wallet_ledger.sql; the SQL file remains
# authoritative for production: unique index, FORCE RLS, NUMERIC precision) ---
class WalletLedger(Base):
    __tablename__ = "wallet_ledgers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0.0000"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Skill infrastructure (ORM mirrors of 003_skill_infrastructure) ---
class UserSkillProfile(Base):
    __tablename__ = "user_skill_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)  # RLS anchor, matches students
    target_trade: Mapped[str] = mapped_column(String(100), nullable=False)
    market_readiness_numeric: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    total_experience_hours: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CertLedger(Base):
    __tablename__ = "cert_ledger"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    certificate_serial_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    certified_trade: Mapped[str] = mapped_column(String(100), nullable=False)
    cryptographic_signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Dead man's switch registry (ORM mirror of 004_dead_man_switch_registry) ---
class DeadManSwitchRegistry(Base):
    __tablename__ = "dead_man_switch_registry"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    inactivity_threshold_days: Mapped[int] = mapped_column(Integer, default=90)
    trusted_contact: Mapped[str] = mapped_column(String(255), nullable=False)
    execution_directive: Mapped[str] = mapped_column(String(100), default="NOTIFY_TRUSTED_CONTACT")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
