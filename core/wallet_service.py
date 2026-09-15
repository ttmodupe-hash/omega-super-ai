"""
OMEGA-LUQI Wallet Ledger Service

Post-release credit hook for the 30% Human Gate. Called from the single
release path (human_intervention_override in core/main.py) - there is
deliberately NO parallel release route, so the gate has exactly one door.

Fail-closed rule: if the ledger write cannot complete, credit_ledger_for_task
raises WalletCreditError and the gate STAYS LOCKED. No settlement without a
written ledger row. Idempotency is enforced twice: application check + the
unique index on wallet_transactions.reference_id.
"""
from decimal import Decimal
from typing import Optional
import uuid as _uuid


class WalletCreditError(Exception):
    """Raised when a wallet credit cannot be safely written - gate must stay locked."""


def is_wallet_task(task) -> bool:
    return task.payload.get("reference") is not None


def credit_ledger_for_task(task, db_engine) -> Optional[float]:
    """Credit a wallet-shaped gate task. Returns the new balance.

    - Non-wallet tasks: returns None (nothing to do).
    - No database: raises (fail-closed - gate stays locked).
    - Duplicate reference: raises (unique index is the final backstop).
    """
    if not is_wallet_task(task):
        return None

    reference = task.payload["reference"]
    amount = float(task.payload.get("amount", 0.0))
    student_id = task.payload.get("student_id")

    if db_engine is None:
        raise WalletCreditError("Database unavailable - cannot settle ledger; gate release blocked.")

    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from .enterprise_models import WalletLedger, WalletTransaction

    try:
        student_uuid = _uuid.UUID(str(student_id))
    except (TypeError, ValueError):
        raise WalletCreditError("Task payload missing valid student_id - settlement refused.")

    with Session(db_engine) as session:
        # Idempotency check (application layer; unique index is the DB backstop)
        existing = session.execute(
            text("SELECT 1 FROM wallet_transactions WHERE reference_id = :ref"),
            {"ref": reference},
        ).first()
        if existing:
            raise WalletCreditError(f"Payment reference '{reference}' already settled - duplicate blocked.")

        session.add(WalletTransaction(
            student_id=student_uuid,
            amount=Decimal(str(amount)),
            transaction_type="deposit",
            reference_id=reference,
        ))

        ledger = session.get(WalletLedger, student_uuid)
        if ledger is None:
            ledger = WalletLedger(student_id=student_uuid, balance=Decimal("0.0000"))
            session.add(ledger)
        ledger.balance = Decimal(str(float(ledger.balance) + amount))
        session.commit()
        return float(ledger.balance)
