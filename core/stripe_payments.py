"""
OMEGA-LUQI Stripe Payment Provider — international card gateway alongside Paystack.

House payment law preserved (same as payment_hub.py / webhooks.py):
  - a webhook NEVER credits a wallet directly. Stripe's
    checkout.session.completed creates a gate task locked at the 30% human
    perimeter; settlement flows through the single release path in
    core/main.py -> core/wallet_service.py (fail-closed, idempotent on
    reference_id with a unique-index backstop).
  - checkout amounts come from a SERVER-SIDE price table (env-overridable) —
    the client picks a key, never an amount. No client-supplied pricing.
  - fail-closed: no STRIPE_SECRET_KEY -> 503 on checkout; no
    STRIPE_WEBHOOK_SECRET -> webhook refuses all events (503).

Config (see .env.example):
  STRIPE_SECRET_KEY      sk_live_... / sk_test_...   (required for checkout)
  STRIPE_WEBHOOK_SECRET  whsec_...                    (required for webhook)
  STRIPE_PRICE_TABLE     optional JSON override, e.g.
    {"topup_100": {"amount_cents": 10000, "currency": "zar", "description": "Wallet top-up R100"}}
  STRIPE_SUCCESS_URL / STRIPE_CANCEL_URL  checkout redirect targets

stripe is a runtime dependency, lazy-imported: the engine boots without it.
"""
import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .auth import LuqiAuthManager, UserSessionProfile
from .main_types import LuqiState, TaskStatus
from .state_store import get_state_store

stripe_router = APIRouter(prefix="/v1/payments/stripe", tags=["Stripe Gateway"])

SUBSIDY_ALLOCATION_RATE = 0.30  # 30% of premium revenue -> African education pool

# Default wallet top-up tiers (ZAR cents). Override wholesale via STRIPE_PRICE_TABLE.
_DEFAULT_PRICE_TABLE = {
    "topup_50": {"amount_cents": 5000, "currency": "zar", "description": "Luqi wallet top-up R50"},
    "topup_100": {"amount_cents": 10000, "currency": "zar", "description": "Luqi wallet top-up R100"},
    "topup_250": {"amount_cents": 25000, "currency": "zar", "description": "Luqi wallet top-up R250"},
}

_WEBHOOK_TOLERANCE_SECONDS = 300  # Stripe default replay window


def _stripe_sdk():
    """Lazy import: engine must boot without the stripe package installed."""
    try:
        import stripe
        return stripe
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe provider unavailable: 'stripe' package not installed on this node.",
        )


def _secret_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe checkout not configured on this node (STRIPE_SECRET_KEY unset).",
        )
    return key


def _price_table() -> Dict[str, Dict[str, Any]]:
    raw = os.getenv("STRIPE_PRICE_TABLE")
    if not raw:
        return dict(_DEFAULT_PRICE_TABLE)
    try:
        table = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="STRIPE_PRICE_TABLE is not valid JSON.")
    # Validate shape: every entry needs int amount_cents + 3-letter currency
    for key, entry in table.items():
        if not isinstance(entry.get("amount_cents"), int) or entry["amount_cents"] <= 0:
            raise HTTPException(status_code=500, detail=f"STRIPE_PRICE_TABLE[{key}]: bad amount_cents.")
        if not isinstance(entry.get("currency"), str) or len(entry["currency"]) != 3:
            raise HTTPException(status_code=500, detail=f"STRIPE_PRICE_TABLE[{key}]: bad currency.")
    return table


@stripe_router.get("/status")
async def stripe_status():
    """Honest, secret-free config state for the ops cockpit."""
    key = os.getenv("STRIPE_SECRET_KEY", "")
    mode = "unconfigured"
    if key.startswith("sk_live_"):
        mode = "live"
    elif key.startswith("sk_test_"):
        mode = "test"
    return {
        "provider": "stripe",
        "checkout_configured": bool(key),
        "webhook_configured": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        "mode": mode,
        "price_keys": sorted(_price_table().keys()) if key else [],
    }


@stripe_router.get("/prices")
async def list_prices(user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """Server-side price table - the ONLY amounts a client can choose from."""
    return {"prices": _price_table()}


@stripe_router.post("/checkout")
async def create_checkout_session(
    body: Dict[str, str],
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Create a Stripe Checkout Session for a wallet top-up.

    The client sends only a price_key; amount/currency/description are
    resolved server-side. client_reference_id binds the session to the
    authenticated user so the webhook can join the settlement to a profile.
    """
    price_key = (body or {}).get("price_key", "")
    table = _price_table()
    if price_key not in table:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown price_key. Choose one of: {sorted(table)}",
        )
    price = table[price_key]
    stripe = _stripe_sdk()
    stripe.api_key = _secret_key()

    base = str(request.base_url).rstrip("/")
    success_url = os.getenv("STRIPE_SUCCESS_URL", f"{base}/v1/payments/stripe/return?session_id={{CHECKOUT_SESSION_ID}}")
    cancel_url = os.getenv("STRIPE_CANCEL_URL", f"{base}/v1/payments/stripe/return?cancelled=1")

    import asyncio

    def _create():
        return stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=str(user.user_id),
            line_items=[{
                "price_data": {
                    "currency": price["currency"],
                    "unit_amount": price["amount_cents"],
                    "product_data": {"name": price.get("description", price_key)},
                },
                "quantity": 1,
            }],
            metadata={"price_key": price_key, "luqi_user_id": str(user.user_id)},
            success_url=success_url,
            cancel_url=cancel_url,
        )

    try:
        session = await asyncio.to_thread(_create)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe gateway error: {e}")

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "amount": price["amount_cents"] / 100.0,
        "currency": price["currency"].upper(),
        "educational_subsidy_allocated": round(price["amount_cents"] / 100.0 * SUBSIDY_ALLOCATION_RATE, 2),
        "message": "Complete payment at the checkout URL. Wallet credits after gateway confirmation + 30% gate release.",
    }


@stripe_router.post("/webhook")
async def stripe_webhook(request: Request):
    """Signature-verified Stripe event receiver.

    checkout.session.completed -> create a wallet top-up task LOCKED at the
    30% human gate (reference = stripe:{session_id}, idempotent via the
    wallet ledger's unique reference backstop). The webhook itself never
    credits anything.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook not configured on this node (STRIPE_WEBHOOK_SECRET unset).",
        )

    stripe = _stripe_sdk()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret, tolerance=_WEBHOOK_TOLERANCE_SECONDS
        ).to_dict()  # StripeObject -> plain dict (nested objects included)
    except Exception:
        # Signature failure / replay outside tolerance / malformed body:
        # uniform rejection, never reveal which check failed.
        raise HTTPException(status_code=400, detail="Webhook signature verification failed.")

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored", "event_type": event["type"]}

    session_obj = event["data"]["object"]
    if session_obj.get("payment_status") != "paid":
        return {"status": "ignored", "reason": "payment_status not paid"}

    student_id: Optional[str] = session_obj.get("client_reference_id")
    amount_total = session_obj.get("amount_total")
    currency = (session_obj.get("currency") or "").upper()
    session_id = session_obj.get("id")
    if not student_id or not amount_total or not session_id:
        # Authentic Stripe event but missing the join data - refuse loudly.
        raise HTTPException(status_code=422, detail="Session missing client_reference_id/amount.")

    task = LuqiState(
        student_tier="global_premium",
        action_type="process_payment",
        payload={
            "item": f"Stripe wallet top-up for profile {student_id}",
            "student_id": student_id,
            "amount": amount_total / 100.0,
            "currency": currency,
            "reference": f"stripe:{session_id}",
            "stripe_event_id": event.get("id"),
        },
    )
    task.status = TaskStatus.PENDING_HUMAN_APPROVAL
    task.required_human_action = "Stripe payment confirmed by gateway webhook. Human release required to credit wallet."
    get_state_store().set(task.task_id, task)
    from .notifications import notify_gate_lock
    notify_gate_lock(task)

    return {
        "status": "accepted",
        "gate_task_id": str(task.task_id),
        "message": "Payment confirmed and locked at the 30% human perimeter pending release.",
    }


@stripe_router.get("/return")
async def checkout_return(session_id: Optional[str] = None, cancelled: Optional[str] = None):
    """Browser landing after Stripe checkout. No secrets, no settlement here -
    the webhook + human gate do that. This endpoint only informs."""
    if cancelled:
        return {"status": "cancelled", "message": "Checkout cancelled - no charge was made."}
    return {
        "status": "pending_confirmation",
        "session_id": session_id,
        "message": "Payment is being confirmed by the gateway; your wallet credits after verification and gate release.",
    }
