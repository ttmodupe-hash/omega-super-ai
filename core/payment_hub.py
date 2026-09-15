"""
OMEGA-LUQI Payment Hub - Paystack gateway stubs.

Verifies transaction references against Paystack clearing nodes, locks the
settlement at the proven 30% Human Gate, and computes the 30% education-pool
allocation. Wallet BALANCES are credited only after an authenticated human
releases the gate (see docs/OMEGA-LUQI_Subsidy_Model.md) - crediting needs
the DB-backed wallet ledger, which is a tracked build item.

DEV MODE: a PAYSTACK_SECRET_KEY starting with sk_test_ short-circuits to a
canned success payload. Never deploy to production with a test key.
"""
import os
import asyncio
from typing import Dict, Any

import requests
from fastapi import APIRouter, Depends, HTTPException, status

from .auth import LuqiAuthManager, UserSessionProfile
from .main_types import LuqiState, TaskStatus
from .state_store import get_state_store

payment_router = APIRouter(prefix="/v1/payments", tags=["Financial Engine"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_MockSecretTestingKey2026_ChangeMe!")
# FIXED: was paystack.co (website domain) - the API lives on api.paystack.co
PAYSTACK_BASE_URL = "https://api.paystack.co"

SUBSIDY_ALLOCATION_RATE = 0.30  # 30% of premium revenue -> African education pool


class PaystackPaymentManager:
    @staticmethod
    def verify_transaction_on_gateway(reference_id: str) -> Dict[str, Any]:
        """Verify a reference against Paystack. Stub-intercepted in dev mode."""
        if PAYSTACK_SECRET_KEY.startswith("sk_test_"):
            # STUB INTERCEPTOR: canned success for development loops only
            return {
                "status": True,
                "data": {
                    "status": "success",
                    "amount": 45000,  # smallest currency unit (cents for ZAR)
                    "currency": "ZAR",
                    "reference": reference_id,
                },
            }

        endpoint = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference_id}"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            if response.status_code != 200:
                return {"status": False, "message": "Gateway communications failure."}
            return response.json()
        except Exception as err:
            return {"status": False, "message": str(err)}


@payment_router.post("/verify-credit/{reference_id}")
async def verify_and_credit_wallet(
    reference_id: str,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Verify + lock at the 30% gate. Idempotency and wallet crediting are
    post-release steps - see the 'missing pieces' notes in the README."""
    verification_payload = await asyncio.to_thread(
        PaystackPaymentManager.verify_transaction_on_gateway, reference_id
    )

    if not verification_payload.get("status") or verification_payload["data"]["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction verification failed: reference invalid or unexecuted.",
        )

    tx_data = verification_payload["data"]
    actual_amount = float(tx_data["amount"]) / 100.0  # smallest unit -> main unit

    task = LuqiState(
        student_tier=current_user.tier,
        action_type="process_payment",
        payload={
            "item": f"Wallet top-up for profile {current_user.user_id}",
            "student_id": str(current_user.user_id),
            "amount": actual_amount,
            "currency": tx_data["currency"],
            "reference": reference_id,
        },
    )
    task.status = TaskStatus.PENDING_HUMAN_APPROVAL
    task.required_human_action = "Payment verified by gateway. Human release required to credit wallet."
    get_state_store().set(task.task_id, task)
    from .notifications import notify_gate_lock
    notify_gate_lock(task)

    return {
        "verification_status": "SUCCESS_LOCKED_AT_GATE",
        "gate_task_id": str(task.task_id),
        "processed_amount": actual_amount,
        "currency": tx_data["currency"],
        "educational_subsidy_allocated": round(actual_amount * SUBSIDY_ALLOCATION_RATE, 2),
        "message": "Payment verified by gateway. Locked at the 30% human perimeter pending release.",
    }
