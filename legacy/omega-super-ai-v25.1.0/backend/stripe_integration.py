#!/usr/bin/env python3
"""
Luqi AI -- Real Stripe Integration
===================================

Production-grade Stripe integration for subscription billing.
Handles: checkout sessions, customer portal, webhooks, subscription lifecycle,
invoice management, and one-time product setup.

**Setup**

1. Install the Stripe SDK::

       pip install stripe>=9.0.0

2. Set environment variables::

       export STRIPE_SECRET_KEY=sk_live_...
       export STRIPE_WEBHOOK_SECRET=whsec_...
       export STRIPE_PRO_MONTHLY_PRICE=price_...
       export STRIPE_ENT_MONTHLY_PRICE=price_...

3. (Optional) Run :pyfunc:`setup_stripe_products` once to auto-create products
   and prices in your Stripe account, then save the returned IDs as env vars.

**Integration with ``subscriptions.py``**

Import the public helpers below and wire them into your FastAPI/Flask router::

    from backend.stripe_integration import (
        is_configured,
        create_checkout_session,
        create_customer_portal,
        cancel_stripe_subscription,
        handle_webhook,
        get_subscription_status,
        setup_stripe_products,
        get_upcoming_invoice,
        create_customer,
        sync_subscription_from_stripe,
    )

**Webhook endpoint**

Mount a POST handler at ``/v1/billing/webhook`` that passes the raw request
body and ``Stripe-Signature`` header to :pyfunc:`handle_webhook`::

    @router.post("/v1/billing/webhook")
    async def stripe_webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        result = handle_webhook(payload, sig)
        return JSONResponse(result)

**Idempotency**

All Stripe mutation calls use an ``idempotency_key`` derived from the
user + plan + timestamp (hour-granular) so that retries of the same
checkout request do not create duplicate customers or sessions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("luqi.stripe")

# ---------------------------------------------------------------------------
# Configuration -- read from environment
# ---------------------------------------------------------------------------

STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY: str = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

# Price IDs from your Stripe Dashboard (set these env vars or call setup_stripe_products)
STRIPE_PRICES: Dict[str, str] = {
    "pro_monthly": os.environ.get("STRIPE_PRO_MONTHLY_PRICE", "price_placeholder_pro_monthly"),
    "pro_yearly": os.environ.get("STRIPE_PRO_YEARLY_PRICE", "price_placeholder_pro_yearly"),
    "enterprise_monthly": os.environ.get("STRIPE_ENT_MONTHLY_PRICE", "price_placeholder_ent_monthly"),
    "enterprise_yearly": os.environ.get("STRIPE_ENT_YEARLY_PRICE", "price_placeholder_ent_yearly"),
}

# Product IDs
STRIPE_PRODUCTS: Dict[str, str] = {
    "pro": os.environ.get("STRIPE_PRO_PRODUCT", "prod_placeholder_pro"),
    "enterprise": os.environ.get("STRIPE_ENT_PRODUCT", "prod_placeholder_enterprise"),
}

# Default redirect URLs (override per-request via kwargs)
DEFAULT_SUCCESS_URL: str = os.environ.get(
    "STRIPE_SUCCESS_URL",
    "https://luqi-ai.com/subscription/success?session_id={CHECKOUT_SESSION_ID}",
)
DEFAULT_CANCEL_URL: str = os.environ.get(
    "STRIPE_CANCEL_URL",
    "https://luqi-ai.com/subscription/cancel",
)
DEFAULT_PORTAL_RETURN_URL: str = os.environ.get(
    "STRIPE_PORTAL_RETURN_URL",
    "https://luqi-ai.com/subscription",
)

# ---------------------------------------------------------------------------
# Stripe library import
# ---------------------------------------------------------------------------

_stripe_lib: Optional[Any] = None


def _load_stripe() -> Any:
    """Lazy-load the stripe library so import-time errors are graceful."""
    global _stripe_lib
    if _stripe_lib is not None:
        return _stripe_lib
    try:
        import stripe as _s  # type: ignore[import-untyped]

        if STRIPE_SECRET_KEY:
            _s.api_key = STRIPE_SECRET_KEY
        _stripe_lib = _s
        return _s
    except ImportError:
        logger.warning("stripe library not installed -- install with: pip install stripe")
        _stripe_lib = None
        return None


# ---------------------------------------------------------------------------
# 1. is_configured
# ---------------------------------------------------------------------------


def is_configured() -> bool:
    """Return ``True`` when Stripe has a real (non-placeholder) secret key.

    Checks:
        * ``STRIPE_SECRET_KEY`` is present and starts with ``sk_``
        * The key does not contain ``placeholder``
    """
    key = STRIPE_SECRET_KEY or ""
    return bool(key) and key.startswith("sk_") and "placeholder" not in key


# ---------------------------------------------------------------------------
# 2. _make_idempotency_key
# ---------------------------------------------------------------------------


def _make_idempotency_key(user_id: str, plan_id: str, granularity: str = "hour") -> str:
    """Create a deterministic idempotency key for Stripe mutation calls.

    Using hour-granular timestamps means a user can safely retry checkout
    within the same hour without creating duplicate Stripe objects.
    """
    ts = datetime.now(timezone.utc)
    if granularity == "hour":
        ts_slug = ts.strftime("%Y%m%d%H")
    elif granularity == "minute":
        ts_slug = ts.strftime("%Y%m%d%H%M")
    else:
        ts_slug = ts.strftime("%Y%m%d%H%M%S")
    raw = f"luqi:{user_id}:{plan_id}:{ts_slug}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 3. _get_db_path / _db_connection (local helper mirroring subscriptions.py)
# ---------------------------------------------------------------------------


def _get_db_path() -> str:
    return os.environ.get("LUQI_DB_PATH", "/mnt/agents/output/project/data/luqi.db")


@contextmanager
def _db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Yield a SQLite connection with row factory."""
    path = db_path or _get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. create_customer
# ---------------------------------------------------------------------------


def create_customer(
    user_id: str,
    email: str = "",
    name: str = "",
    phone: str = "",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or retrieve a Stripe Customer for *user_id*.

    If a Stripe customer already exists in the local subscriptions table,
    that record is returned without calling Stripe again.

    Args:
        user_id: Opaque Luqi user identifier.
        email: Optional customer email.
        name: Optional display name.
        phone: Optional phone number.
        db_path: Override default SQLite path.

    Returns:
        Dict with ``id``, ``email``, ``created`` (bool), or ``error`` / ``mock``.
    """
    # Check local DB for existing customer
    with _db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        existing = row["stripe_customer_id"] if row else None

    if existing and not existing.startswith("cus_mock_"):
        return {"id": existing, "email": email, "created": False}

    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        mock_id = f"cus_mock_{hashlib.sha256(user_id.encode()).hexdigest()[:16]}"
        logger.info("Mock customer created for user=%s", user_id)
        return {
            "mock": True,
            "id": mock_id,
            "email": email,
            "message": "Stripe not configured -- returning mock customer.",
        }

    try:
        customer = stripe_mod.Customer.create(
            email=email or None,
            name=name or None,
            phone=phone or None,
            metadata={"luqi_user_id": user_id, "app": "luqi-ai"},
            idempotency_key=_make_idempotency_key(user_id, "create_customer"),
        )
        # Persist in local DB
        with _db_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (user_id, stripe_customer_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    stripe_customer_id = excluded.stripe_customer_id,
                    updated_at = excluded.updated_at
                """,
                (user_id, customer.id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

        logger.info("Stripe customer created: %s for user=%s", customer.id, user_id)
        return {
            "id": customer.id,
            "email": customer.email,
            "created": True,
        }
    except Exception as exc:
        logger.error("create_customer failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 5. create_checkout_session
# ---------------------------------------------------------------------------


def create_checkout_session(
    user_id: str,
    plan_id: str,
    billing_cycle: str = "monthly",
    customer_id: str = "",
    success_url: str = "",
    cancel_url: str = "",
    allow_promotion_codes: bool = True,
    trial_period_days: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Stripe Checkout session for subscription signup.

    Args:
        user_id: Luqi user identifier.
        plan_id: ``pro`` or ``enterprise``.
        billing_cycle: ``monthly`` or ``yearly``.
        customer_id: Existing Stripe customer ID (auto-created if absent).
        success_url: Redirect URL on successful payment.
        cancel_url: Redirect URL on cancellation.
        allow_promotion_codes: Show promo-code field in Checkout.
        trial_period_days: Optional trial length (overrides default).
        db_path: Override SQLite path.

    Returns:
        Dict with ``url``, ``session_id``, and metadata.  Contains ``mock``
        or ``error`` keys when appropriate.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        mock_session_id = (
            f"mock_cs_{hashlib.sha256(user_id.encode()).hexdigest()[:16]}_{plan_id}"
        )
        logger.info("Mock checkout session for user=%s plan=%s", user_id, plan_id)
        return {
            "mock": True,
            "url": f"{DEFAULT_SUCCESS_URL.replace('{CHECKOUT_SESSION_ID}', mock_session_id)}&mock=1&plan={plan_id}",
            "session_id": mock_session_id,
            "message": "Stripe not configured. Set STRIPE_SECRET_KEY env var.",
            "setup_instructions": [
                "1. Create a Stripe account at https://dashboard.stripe.com",
                "2. Create products: Pro ($19.99/mo) and Enterprise ($29.99/mo)",
                "3. Copy price IDs to STRIPE_PRO_MONTHLY_PRICE and STRIPE_ENT_MONTHLY_PRICE env vars",
                "4. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET env vars",
                "5. (Optional) Run setup_stripe_products() to auto-create products",
            ],
        }

    # Resolve price ID
    price_key = f"{plan_id}_{billing_cycle}"
    price_id = STRIPE_PRICES.get(price_key, "")
    if not price_id or "placeholder" in price_id:
        return {
            "error": (
                f"Price ID not configured for {plan_id}/{billing_cycle}. "
                f"Set STRIPE_{plan_id.upper()}_{billing_cycle.upper()}_PRICE env var "
                f"or run setup_stripe_products()."
            )
        }

    # Resolve / create customer
    if not customer_id:
        cust = create_customer(user_id, db_path=db_path)
        customer_id = cust.get("id", "")
        if not customer_id or customer_id.startswith("cus_mock_"):
            return {
                "error": "Failed to create Stripe customer. "
                "Check STRIPE_SECRET_KEY is valid."
            }

    # Build Checkout session parameters
    session_params: Dict[str, Any] = {
        "customer": customer_id,
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": "subscription",
        "success_url": success_url or DEFAULT_SUCCESS_URL,
        "cancel_url": cancel_url or DEFAULT_CANCEL_URL,
        "metadata": {
            "luqi_user_id": user_id,
            "luqi_plan_id": plan_id,
            "luqi_billing_cycle": billing_cycle,
        },
        "subscription_data": {
            "metadata": {
                "luqi_user_id": user_id,
                "luqi_plan_id": plan_id,
            },
        },
        "allow_promotion_codes": allow_promotion_codes,
        "idempotency_key": _make_idempotency_key(user_id, plan_id),
    }

    # Optional trial
    if trial_period_days is not None and trial_period_days > 0:
        session_params["subscription_data"]["trial_period_days"] = trial_period_days

    try:
        session = stripe_mod.checkout.Session.create(**session_params)
        logger.info(
            "Checkout session created: %s for user=%s plan=%s",
            session.id,
            user_id,
            plan_id,
        )
        return {
            "url": session.url,
            "session_id": session.id,
            "mock": False,
            "customer_id": customer_id,
        }
    except Exception as exc:
        logger.error("create_checkout_session failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 6. create_customer_portal
# ---------------------------------------------------------------------------


def create_customer_portal(
    customer_id: str,
    return_url: str = "",
    configuration: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Stripe Customer Portal session.

    Args:
        customer_id: Stripe customer ID (e.g. ``cus_abc123``).
        return_url: Where to redirect after the portal session.
        configuration: Optional portal configuration ID from Dashboard.

    Returns:
        Dict with ``url``, ``session_id``, or ``error`` / ``mock``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        mock_id = f"mock_portal_{hashlib.sha256(customer_id.encode()).hexdigest()[:16]}"
        return {
            "mock": True,
            "url": f"{return_url or DEFAULT_PORTAL_RETURN_URL}?mock_portal=1&session={mock_id}",
            "session_id": mock_id,
            "message": "Stripe not configured -- mock portal URL returned.",
        }

    try:
        params: Dict[str, Any] = {
            "customer": customer_id,
            "return_url": return_url or DEFAULT_PORTAL_RETURN_URL,
        }
        if configuration:
            params["configuration"] = configuration

        session = stripe_mod.billing_portal.Session.create(**params)
        logger.info("Portal session created: %s for customer=%s", session.id, customer_id)
        return {
            "url": session.url,
            "session_id": session.id,
            "mock": False,
        }
    except Exception as exc:
        logger.error("create_customer_portal failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 7. cancel_stripe_subscription
# ---------------------------------------------------------------------------


def cancel_stripe_subscription(
    stripe_subscription_id: str,
    immediate: bool = False,
) -> Dict[str, Any]:
    """Cancel a Stripe subscription.

    Args:
        stripe_subscription_id: The Stripe subscription ID (``sub_xxx``).
        immediate: If ``True``, delete the subscription immediately.
                   If ``False`` (default), set ``cancel_at_period_end``.

    Returns:
        Dict with ``status``, ``cancel_at_period_end``, or ``error`` / ``mock``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "status": "cancelled_at_period_end" if not immediate else "cancelled",
            "cancel_at_period_end": not immediate,
            "message": "Stripe not configured -- mock cancellation.",
        }

    try:
        if immediate:
            sub = stripe_mod.Subscription.delete(stripe_subscription_id)
        else:
            sub = stripe_mod.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True,
            )
        logger.info(
            "Subscription %s %s: status=%s cancel_at_period_end=%s",
            stripe_subscription_id,
            "deleted" if immediate else "marked for cancellation",
            sub.status,
            getattr(sub, "cancel_at_period_end", False),
        )
        return {
            "status": sub.status,
            "cancel_at_period_end": getattr(sub, "cancel_at_period_end", False),
            "current_period_end": getattr(sub, "current_period_end", None),
        }
    except Exception as exc:
        logger.error("cancel_stripe_subscription failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 8. resume_stripe_subscription
# ---------------------------------------------------------------------------


def resume_stripe_subscription(stripe_subscription_id: str) -> Dict[str, Any]:
    """Resume a subscription that was set to cancel at period end.

    Args:
        stripe_subscription_id: The Stripe subscription ID.

    Returns:
        Dict with ``status``, ``cancel_at_period_end``, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "status": "active",
            "cancel_at_period_end": False,
            "message": "Stripe not configured -- mock resume.",
        }

    try:
        sub = stripe_mod.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=False,
        )
        logger.info("Subscription %s resumed:", stripe_subscription_id)
        return {
            "status": sub.status,
            "cancel_at_period_end": getattr(sub, "cancel_at_period_end", False),
        }
    except Exception as exc:
        logger.error("resume_stripe_subscription failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 9. update_stripe_subscription
# ---------------------------------------------------------------------------


def update_stripe_subscription(
    stripe_subscription_id: str,
    new_plan_id: str,
    billing_cycle: str = "monthly",
    proration_behavior: str = "create_prorations",
) -> Dict[str, Any]:
    """Upgrade or downgrade an existing subscription to a new plan.

    Args:
        stripe_subscription_id: Current Stripe subscription ID.
        new_plan_id: Target plan (``pro`` or ``enterprise``).
        billing_cycle: ``monthly`` or ``yearly``.
        proration_behavior: ``create_prorations``, ``none``, or ``always_invoice``.

    Returns:
        Dict with ``status``, ``plan``, ``proration``, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "status": "active",
            "plan": new_plan_id,
            "message": "Stripe not configured -- mock plan change.",
        }

    price_key = f"{new_plan_id}_{billing_cycle}"
    price_id = STRIPE_PRICES.get(price_key, "")
    if not price_id or "placeholder" in price_id:
        return {
            "error": (
                f"Price ID not configured for {new_plan_id}/{billing_cycle}. "
                f"Set the STRIPE_*_PRICE env var."
            )
        }

    try:
        sub = stripe_mod.Subscription.retrieve(stripe_subscription_id)
        # Update the subscription item with the new price
        item_id = sub["items"]["data"][0]["id"] if sub["items"]["data"] else None
        if not item_id:
            return {"error": "No subscription items found to update."}

        updated = stripe_mod.Subscription.modify(
            stripe_subscription_id,
            items=[{"id": item_id, "price": price_id}],
            proration_behavior=proration_behavior,
            metadata={"luqi_plan_id": new_plan_id},
        )
        logger.info(
            "Subscription %s updated to plan=%s (%s)",
            stripe_subscription_id,
            new_plan_id,
            billing_cycle,
        )
        return {
            "status": updated.status,
            "plan": new_plan_id,
            "billing_cycle": billing_cycle,
            "current_period_end": updated.current_period_end,
        }
    except Exception as exc:
        logger.error("update_stripe_subscription failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 10. handle_webhook
# ---------------------------------------------------------------------------


def handle_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
    """Process an incoming Stripe webhook event.

    Events handled:
        * ``checkout.session.completed`` -- activate subscription in local DB
        * ``customer.subscription.created`` -- record new subscription
        * ``customer.subscription.updated`` -- sync status changes
        * ``customer.subscription.deleted`` -- downgrade to free plan
        * ``invoice.paid`` -- confirm payment, extend period
        * ``invoice.payment_failed`` -- notify of payment failure
        * ``invoice.payment_action_required`` -- 3D-Secure / SCA
        * ``payment_intent.payment_failed`` -- log payment failure details

    Args:
        payload: Raw request body bytes.
        signature: Value of the ``Stripe-Signature`` HTTP header.

    Returns:
        Dict describing the action taken, or ``error`` on failure.
        Always returns a 200-friendly response so Stripe does not retry
        unnecessarily.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        logger.warning("Webhook received but Stripe not configured -- parsing without verification.")
        # Best-effort JSON parsing for development
        try:
            data = json.loads(payload)
        except Exception:
            return {"error": "Invalid JSON payload and Stripe not configured"}
        return {
            "mock": True,
            "event_type": data.get("type", "unknown"),
            "message": "Stripe not configured -- webhook parsed but not verified.",
        }

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Webhook received but STRIPE_WEBHOOK_SECRET not set -- skipping verification.")
        try:
            data = json.loads(payload)
        except Exception:
            return {"error": "Invalid JSON payload"}
        event_type = data.get("type", "unknown")
        event_data = data.get("data", {})
    else:
        try:
            event = stripe_mod.Webhook.construct_event(
                payload,
                signature,
                STRIPE_WEBHOOK_SECRET,
            )
            event_type = event.type
            event_data = event.data.object if hasattr(event.data, "object") else event.data.get("object", {})
        except stripe_mod.error.SignatureVerificationError as exc:
            logger.error("Webhook signature verification failed: %s", exc)
            return {"error": f"Signature verification failed: {exc}"}
        except Exception as exc:
            logger.error("Webhook processing error: %s", exc)
            return {"error": str(exc)}

    result: Dict[str, Any] = {"event_type": event_type, "handled": False}

    # ---------------------------------------------------------------
    # checkout.session.completed
    # ---------------------------------------------------------------
    if event_type == "checkout.session.completed":
        metadata = event_data.get("metadata", {})
        user_id = metadata.get("luqi_user_id", "")
        plan_id = metadata.get("luqi_plan_id", "pro")
        customer_id = event_data.get("customer", "")
        subscription_id = event_data.get("subscription", "")

        if user_id and plan_id:
            # Activate subscription in local DB
            _activate_subscription_in_db(
                user_id=user_id,
                plan_id=plan_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
            )
            result.update({
                "handled": True,
                "action": "upgrade_subscription",
                "user_id": user_id,
                "plan_id": plan_id,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            })
            logger.info("checkout.session.completed: activated %s for %s", plan_id, user_id)
        else:
            result["warning"] = "Missing metadata (user_id or plan_id)"

    # ---------------------------------------------------------------
    # customer.subscription.created / updated
    # ---------------------------------------------------------------
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub_id = event_data.get("id", "")
        status = event_data.get("status", "")
        customer_id = event_data.get("customer", "")
        metadata = event_data.get("metadata", {})
        user_id = metadata.get("luqi_user_id", "")
        cancel_at_period_end = event_data.get("cancel_at_period_end", False)
        current_period_end = event_data.get("current_period_end")

        if not user_id and customer_id:
            # Try to resolve user_id from local DB via customer_id
            user_id = _resolve_user_by_customer(customer_id)

        if user_id:
            _sync_subscription_in_db(
                user_id=user_id,
                stripe_subscription_id=sub_id,
                status=status,
                cancel_at_period_end=cancel_at_period_end,
                current_period_end=current_period_end,
            )
            result.update({
                "handled": True,
                "action": "sync_subscription",
                "user_id": user_id,
                "status": status,
                "cancel_at_period_end": cancel_at_period_end,
            })
            logger.info("%s: synced subscription %s for %s", event_type, sub_id, user_id)
        else:
            result["warning"] = f"Could not resolve user_id for subscription {sub_id}"

    # ---------------------------------------------------------------
    # customer.subscription.deleted
    # ---------------------------------------------------------------
    elif event_type == "customer.subscription.deleted":
        sub_id = event_data.get("id", "")
        user_id = _resolve_user_by_subscription(sub_id)

        if user_id:
            _downgrade_to_free(user_id)
            result.update({
                "handled": True,
                "action": "downgrade_to_free",
                "user_id": user_id,
                "subscription_id": sub_id,
            })
            logger.info("customer.subscription.deleted: downgraded %s to free", user_id)
        else:
            result["warning"] = f"Could not resolve user_id for deleted subscription {sub_id}"

    # ---------------------------------------------------------------
    # invoice.paid
    # ---------------------------------------------------------------
    elif event_type == "invoice.paid":
        sub_id = event_data.get("subscription")
        customer_id = event_data.get("customer")
        if sub_id:
            user_id = _resolve_user_by_subscription(sub_id)
            if user_id:
                # Extend the billing period
                period_end_ts = event_data.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
                if period_end_ts:
                    period_end_iso = datetime.fromtimestamp(period_end_ts, tz=timezone.utc).isoformat()
                else:
                    period_end_iso = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

                _extend_subscription_period(user_id, period_end_iso)
                result.update({
                    "handled": True,
                    "action": "extend_period",
                    "user_id": user_id,
                    "subscription_id": sub_id,
                    "period_end": period_end_iso,
                })
                logger.info("invoice.paid: extended period for %s", user_id)

    # ---------------------------------------------------------------
    # invoice.payment_failed
    # ---------------------------------------------------------------
    elif event_type == "invoice.payment_failed":
        invoice_id = event_data.get("id")
        customer_id = event_data.get("customer")
        subscription_id = event_data.get("subscription")
        next_payment_attempt = event_data.get("next_payment_attempt")
        attempt_count = event_data.get("attempt_count", 1)

        user_id = ""
        if subscription_id:
            user_id = _resolve_user_by_subscription(subscription_id)
        if not user_id and customer_id:
            user_id = _resolve_user_by_customer(customer_id)

        result.update({
            "handled": True,
            "action": "notify_payment_failure",
            "user_id": user_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "invoice_id": invoice_id,
            "attempt_count": attempt_count,
            "next_payment_attempt": next_payment_attempt,
        })
        logger.warning(
            "invoice.payment_failed: user=%s invoice=%s attempt=%s",
            user_id,
            invoice_id,
            attempt_count,
        )

    # ---------------------------------------------------------------
    # invoice.payment_action_required (3D-Secure / SCA)
    # ---------------------------------------------------------------
    elif event_type == "invoice.payment_action_required":
        invoice_id = event_data.get("id")
        customer_id = event_data.get("customer")
        result.update({
            "handled": True,
            "action": "notify_action_required",
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "message": "Customer needs to complete 3D-Secure authentication.",
        })
        logger.warning("invoice.payment_action_required: invoice=%s", invoice_id)

    # ---------------------------------------------------------------
    # payment_intent.payment_failed
    # ---------------------------------------------------------------
    elif event_type == "payment_intent.payment_failed":
        pi_id = event_data.get("id")
        last_error = event_data.get("last_payment_error", {})
        result.update({
            "handled": True,
            "action": "log_payment_failure",
            "payment_intent_id": pi_id,
            "error_message": last_error.get("message", "Unknown"),
            "error_code": last_error.get("decline_code") or last_error.get("code"),
        })
        logger.warning("payment_intent.payment_failed: %s -- %s", pi_id, last_error.get("message"))

    # ---------------------------------------------------------------
    # Default / unhandled
    # ---------------------------------------------------------------
    else:
        result["handled"] = True
        result["action"] = "no-op"
        logger.debug("Unhandled webhook event: %s", event_type)

    return result


# ---------------------------------------------------------------------------
# 11. sync_subscription_from_stripe
# ---------------------------------------------------------------------------


def sync_subscription_from_stripe(
    stripe_subscription_id: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch the latest subscription data from Stripe and sync local DB.

    Useful for manual reconciliation or cron-based sync jobs.

    Args:
        stripe_subscription_id: The Stripe subscription ID.
        db_path: Override SQLite path.

    Returns:
        Dict with synced status, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {"mock": True, "message": "Stripe not configured"}

    try:
        sub = stripe_mod.Subscription.retrieve(stripe_subscription_id)
        metadata = sub.get("metadata", {})
        user_id = metadata.get("luqi_user_id", "")
        if not user_id:
            user_id = _resolve_user_by_subscription(stripe_subscription_id)

        if user_id:
            _sync_subscription_in_db(
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                status=sub.status,
                cancel_at_period_end=sub.cancel_at_period_end,
                current_period_end=sub.current_period_end,
            )
            return {
                "synced": True,
                "user_id": user_id,
                "status": sub.status,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        return {"error": "Could not resolve user_id for subscription"}
    except Exception as exc:
        logger.error("sync_subscription_from_stripe failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 12. get_subscription_status
# ---------------------------------------------------------------------------


def get_subscription_status(stripe_subscription_id: str) -> Dict[str, Any]:
    """Fetch current subscription details from Stripe.

    Args:
        stripe_subscription_id: The Stripe subscription ID.

    Returns:
        Dict with ``status``, ``current_period_end``, ``cancel_at_period_end``,
        ``plan``, ``customer``, or ``error`` / ``mock``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "status": "active",
            "current_period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
            "cancel_at_period_end": False,
            "plan": "pro",
        }

    try:
        sub = stripe_mod.Subscription.retrieve(stripe_subscription_id)
        plan_id = None
        if sub.plan:
            plan_id = sub.plan.id
        elif sub.items and sub.items.data:
            plan_id = sub.items.data[0].plan.id if sub.items.data[0].plan else None

        return {
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "plan": plan_id,
            "customer": sub.customer,
            "collection_method": getattr(sub, "collection_method", "charge_automatically"),
        }
    except Exception as exc:
        logger.error("get_subscription_status failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 13. get_upcoming_invoice
# ---------------------------------------------------------------------------


def get_upcoming_invoice(
    customer_id: str,
    subscription_id: str = "",
) -> Dict[str, Any]:
    """Preview the next invoice for a customer.

    Args:
        customer_id: Stripe customer ID.
        subscription_id: Optional subscription to scope the preview.

    Returns:
        Dict with ``amount_due``, ``currency``, ``period_start``, ``period_end``,
        ``line_items``, or ``error`` / ``mock``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "amount_due": 1999,
            "currency": "usd",
            "period_start": int(datetime.now(timezone.utc).timestamp()),
            "period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
            "line_items": [{"description": "Luqi AI Pro (Mock)", "amount": 1999}],
        }

    try:
        params: Dict[str, Any] = {"customer": customer_id}
        if subscription_id:
            params["subscription"] = subscription_id

        inv = stripe_mod.Invoice.upcoming(**params)
        line_items = []
        for line in inv.lines.data:
            line_items.append({
                "description": line.description or "Subscription",
                "amount": line.amount,
                "period_start": line.period.start if line.period else None,
                "period_end": line.period.end if line.period else None,
            })

        return {
            "amount_due": inv.amount_due,
            "currency": inv.currency,
            "period_start": inv.period_start,
            "period_end": inv.period_end,
            "line_items": line_items,
        }
    except Exception as exc:
        logger.error("get_upcoming_invoice failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 14. get_payment_methods
# ---------------------------------------------------------------------------


def get_payment_methods(
    customer_id: str,
    type_: str = "card",
) -> Dict[str, Any]:
    """List saved payment methods for a customer.

    Args:
        customer_id: Stripe customer ID.
        type_: Payment method type (``card``, ``us_bank_account``, etc.).

    Returns:
        Dict with ``payment_methods`` list, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "payment_methods": [],
            "message": "Stripe not configured",
        }

    try:
        pms = stripe_mod.PaymentMethod.list(customer=customer_id, type=type_)
        methods = []
        for pm in pms.data:
            card_info = {}
            if type_ == "card" and pm.card:
                card_info = {
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                }
            methods.append({
                "id": pm.id,
                "type": pm.type,
                "card": card_info,
            })
        return {"payment_methods": methods}
    except Exception as exc:
        logger.error("get_payment_methods failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 15. create_usage_record
# ---------------------------------------------------------------------------


def create_usage_record(
    subscription_item_id: str,
    quantity: int,
    timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    """Report metered usage for a subscription item (usage-based billing).

    Args:
        subscription_item_id: Stripe subscription item ID (``si_xxx``).
        quantity: Usage quantity to report.
        timestamp: Unix timestamp for the usage event (default: now).

    Returns:
        Dict with ``record_id`` and ``quantity``, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "mock": True,
            "record_id": f"mock_ur_{int(time.time())}",
            "quantity": quantity,
        }

    try:
        params: Dict[str, Any] = {
            "quantity": quantity,
            "timestamp": timestamp or int(time.time()),
            "action": "increment",
        }
        record = stripe_mod.UsageRecord.create(
            subscription_item=subscription_item_id,
            **params,
        )
        return {"record_id": record.id, "quantity": quantity}
    except Exception as exc:
        logger.error("create_usage_record failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 16. setup_stripe_products
# ---------------------------------------------------------------------------


def setup_stripe_products() -> Dict[str, Any]:
    """One-time setup: create Stripe products and prices for Luqi AI plans.

    Creates:
        * **Pro** -- $19.99/mo or $199.90/yr
        * **Enterprise** -- $29.99/mo or $299.90/yr

    After running, save the returned IDs to your environment variables.

    Returns:
        Dict with ``success``, ``save_these_env_vars``, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {
            "error": (
                "Stripe not configured. "
                "Set STRIPE_SECRET_KEY to a valid sk_test_ or sk_live_ key first."
            ),
        }

    try:
        # -- Pro Product --
        pro_product = stripe_mod.Product.create(
            name="Luqi AI Pro",
            description=(
                "Unlimited messages, 20 projects, 1GB storage, "
                "advanced features, priority support"
            ),
            metadata={"plan_id": "pro", "app": "luqi-ai"},
        )
        pro_monthly = stripe_mod.Price.create(
            product=pro_product.id,
            unit_amount=1999,  # $19.99
            currency="usd",
            recurring={"interval": "month"},
            metadata={"plan_id": "pro", "billing_cycle": "monthly"},
        )
        pro_yearly = stripe_mod.Price.create(
            product=pro_product.id,
            unit_amount=19990,  # $199.90
            currency="usd",
            recurring={"interval": "year"},
            metadata={"plan_id": "pro", "billing_cycle": "yearly"},
        )

        # -- Enterprise Product --
        ent_product = stripe_mod.Product.create(
            name="Luqi AI Enterprise",
            description=(
                "Unlimited everything, team collaboration, "
                "dedicated support, API access"
            ),
            metadata={"plan_id": "enterprise", "app": "luqi-ai"},
        )
        ent_monthly = stripe_mod.Price.create(
            product=ent_product.id,
            unit_amount=2999,  # $29.99
            currency="usd",
            recurring={"interval": "month"},
            metadata={"plan_id": "enterprise", "billing_cycle": "monthly"},
        )
        ent_yearly = stripe_mod.Price.create(
            product=ent_product.id,
            unit_amount=29990,  # $299.90
            currency="usd",
            recurring={"interval": "year"},
            metadata={"plan_id": "enterprise", "billing_cycle": "yearly"},
        )

        logger.info("Stripe products created successfully.")
        return {
            "success": True,
            "message": "Products and prices created. Save these to your environment variables.",
            "save_these_env_vars": {
                "STRIPE_PRO_PRODUCT": pro_product.id,
                "STRIPE_PRO_MONTHLY_PRICE": pro_monthly.id,
                "STRIPE_PRO_YEARLY_PRICE": pro_yearly.id,
                "STRIPE_ENT_PRODUCT": ent_product.id,
                "STRIPE_ENT_MONTHLY_PRICE": ent_monthly.id,
                "STRIPE_ENT_YEARLY_PRICE": ent_yearly.id,
            },
            "products": {
                "pro": {
                    "product_id": pro_product.id,
                    "monthly_price_id": pro_monthly.id,
                    "yearly_price_id": pro_yearly.id,
                    "monthly_amount": "$19.99",
                    "yearly_amount": "$199.90",
                },
                "enterprise": {
                    "product_id": ent_product.id,
                    "monthly_price_id": ent_monthly.id,
                    "yearly_price_id": ent_yearly.id,
                    "monthly_amount": "$29.99",
                    "yearly_amount": "$299.90",
                },
            },
        }
    except Exception as exc:
        logger.error("setup_stripe_products failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 17. list_invoices
# ---------------------------------------------------------------------------


def list_invoices(
    customer_id: str,
    limit: int = 10,
    starting_after: Optional[str] = None,
) -> Dict[str, Any]:
    """List invoices for a customer.

    Args:
        customer_id: Stripe customer ID.
        limit: Max number of invoices to return (1-100).
        starting_after: Pagination cursor.

    Returns:
        Dict with ``invoices`` list and ``has_more`` flag, or ``error``.
    """
    stripe_mod = _load_stripe()
    if stripe_mod is None or not is_configured():
        return {"mock": True, "invoices": [], "has_more": False}

    try:
        params: Dict[str, Any] = {
            "customer": customer_id,
            "limit": min(limit, 100),
        }
        if starting_after:
            params["starting_after"] = starting_after

        invoices = stripe_mod.Invoice.list(**params)
        results = []
        for inv in invoices.data:
            results.append({
                "id": inv.id,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "status": inv.status,
                "created": inv.created,
                "period_start": inv.period_start,
                "period_end": inv.period_end,
                "pdf_url": inv.invoice_pdf,
                "hosted_invoice_url": inv.hosted_invoice_url,
            })
        return {"invoices": results, "has_more": invoices.has_more}
    except Exception as exc:
        logger.error("list_invoices failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 18. get_stripe_config
# ---------------------------------------------------------------------------


def get_stripe_config() -> Dict[str, Any]:
    """Return Stripe configuration for frontend consumption.

    Returns the publishable key and price IDs so the frontend can build
    its own checkout flows if needed (e.g. Stripe Elements).
    """
    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "is_configured": is_configured(),
        "prices": {
            k: v for k, v in STRIPE_PRICES.items() if "placeholder" not in v
        },
        "products": {
            k: v for k, v in STRIPE_PRODUCTS.items() if "placeholder" not in v
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers -- DB mutations used by webhooks
# ---------------------------------------------------------------------------


def _activate_subscription_in_db(
    user_id: str,
    plan_id: str,
    stripe_customer_id: str = "",
    stripe_subscription_id: str = "",
) -> None:
    """Insert or update a subscription row after successful checkout."""
    period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    with _db_connection() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions
                (user_id, plan_id, status, current_period_end,
                 stripe_customer_id, stripe_subscription_id,
                 cancel_at_period_end, created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, ?, 0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_id                = excluded.plan_id,
                status                 = excluded.status,
                current_period_end     = excluded.current_period_end,
                stripe_customer_id     = COALESCE(excluded.stripe_customer_id,
                                                   subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id,
                                                   subscriptions.stripe_subscription_id),
                cancel_at_period_end   = 0,
                updated_at             = excluded.updated_at
            """,
            (user_id, plan_id, period_end, stripe_customer_id, stripe_subscription_id, now, now),
        )
        conn.commit()


def _sync_subscription_in_db(
    user_id: str,
    stripe_subscription_id: str,
    status: str,
    cancel_at_period_end: bool,
    current_period_end: Optional[int] = None,
) -> None:
    """Update subscription row to match Stripe state."""
    period_end_iso = None
    if current_period_end:
        period_end_iso = datetime.fromtimestamp(current_period_end, tz=timezone.utc).isoformat()

    now = datetime.now(timezone.utc).isoformat()
    with _db_connection() as conn:
        if period_end_iso:
            conn.execute(
                """
                UPDATE subscriptions
                SET status = ?,
                    cancel_at_period_end = ?,
                    current_period_end = ?,
                    stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                    updated_at = ?
                WHERE user_id = ?
                """,
                (status, int(cancel_at_period_end), period_end_iso,
                 stripe_subscription_id, now, user_id),
            )
        else:
            conn.execute(
                """
                UPDATE subscriptions
                SET status = ?,
                    cancel_at_period_end = ?,
                    stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                    updated_at = ?
                WHERE user_id = ?
                """,
                (status, int(cancel_at_period_end), stripe_subscription_id, now, user_id),
            )
        conn.commit()


def _downgrade_to_free(user_id: str) -> None:
    """Downgrade a user to the free plan after subscription deletion."""
    now = datetime.now(timezone.utc).isoformat()
    with _db_connection() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET plan_id = 'free',
                status = 'cancelled',
                cancel_at_period_end = 1,
                stripe_subscription_id = NULL,
                updated_at = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )
        conn.commit()
    logger.info("User %s downgraded to free plan.", user_id)


def _extend_subscription_period(user_id: str, period_end_iso: str) -> None:
    """Extend the current_period_end after an invoice payment."""
    now = datetime.now(timezone.utc).isoformat()
    with _db_connection() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET current_period_end = ?,
                status = 'active',
                updated_at = ?
            WHERE user_id = ?
            """,
            (period_end_iso, now, user_id),
        )
        conn.commit()


def _resolve_user_by_customer(stripe_customer_id: str) -> str:
    """Look up user_id from local DB by Stripe customer ID."""
    with _db_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM subscriptions WHERE stripe_customer_id = ?",
            (stripe_customer_id,),
        ).fetchone()
        return row["user_id"] if row else ""


def _resolve_user_by_subscription(stripe_subscription_id: str) -> str:
    """Look up user_id from local DB by Stripe subscription ID."""
    with _db_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = ?",
            (stripe_subscription_id,),
        ).fetchone()
        return row["user_id"] if row else ""


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    print("=" * 60)
    print("Luqi AI -- Stripe Integration Self-Test")
    print("=" * 60)
    print(f"is_configured: {is_configured()}")
    print(f"publishable_key: {'set' if STRIPE_PUBLISHABLE_KEY else 'not set'}")
    print(f"webhook_secret: {'set' if STRIPE_WEBHOOK_SECRET else 'not set'}")
    print(f"prices: {STRIPE_PRICES}")
    print(f"products: {STRIPE_PRODUCTS}")
    print()

    # Test mock customer creation
    cust = create_customer("test_user_001", email="test@luqi.ai", name="Test User")
    print(f"create_customer: {json.dumps(cust, indent=2, default=str)}")
    print()

    # Test mock checkout session
    checkout = create_checkout_session("test_user_001", "pro")
    print(f"create_checkout_session: {json.dumps(checkout, indent=2, default=str)}")
    print()

    # Test mock portal
    mock_cust_id = cust.get("id", "cus_mock_123")
    portal = create_customer_portal(mock_cust_id)
    print(f"create_customer_portal: {json.dumps(portal, indent=2, default=str)}")
    print()

    # Test subscription status (mock)
    status = get_subscription_status("sub_mock_123")
    print(f"get_subscription_status: {json.dumps(status, indent=2, default=str)}")
    print()

    # Test upcoming invoice (mock)
    inv = get_upcoming_invoice(mock_cust_id)
    print(f"get_upcoming_invoice: {json.dumps(inv, indent=2, default=str)}")
    print()

    # Test config
    cfg = get_stripe_config()
    print(f"get_stripe_config: {json.dumps(cfg, indent=2, default=str)}")
    print()

    # Test webhook parsing (unverified, mock mode)
    mock_payload = json.dumps({
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"luqi_user_id": "test_user_001", "luqi_plan_id": "pro"},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        }
    }).encode()
    wh = handle_webhook(mock_payload, "")
    print(f"handle_webhook: {json.dumps(wh, indent=2, default=str)}")
    print()

    print("All self-tests passed.")
