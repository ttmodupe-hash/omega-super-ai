#!/usr/bin/env python3
"""
Luqi AI — Subscription & Billing Management Module
====================================================

Production-grade subscription system with SQLite backend, usage tracking,
rate limiting, Stripe integration (with graceful mock fallback), and
tier-based access control via decorator factories.

Intended usage in `backend/router.py`::

    from backend.subscriptions import (
        init_db, get_plans, get_or_create_subscription,
        check_quota, increment_usage, get_usage,
        require_plan, get_health_detailed,
        create_checkout_session, create_customer_portal, handle_webhook,
        get_analytics, log_api_call, get_user_id, track_request,
    )
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("luqi.subscriptions")

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = os.environ.get("LUQI_DB_PATH", "/mnt/agents/output/project/data/luqi.db")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
STRIPE_ENABLED = False  # determined at import time below

# Rate-limiting settings
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_FREE = 30          # requests per window
RATE_LIMIT_PRO = 120
RATE_LIMIT_ENTERPRISE = 600

# API key → user_id cache (in-memory, per-process)
_user_id_cache: Dict[str, str] = {}
_rate_limit_buckets: Dict[str, List[float]] = {}
_lock = threading.RLock()

# ---------------------------------------------------------------------------
# Stripe availability
# ---------------------------------------------------------------------------

try:
    import stripe as stripe_lib

    if STRIPE_SECRET_KEY.startswith("sk_"):
        stripe_lib.api_key = STRIPE_SECRET_KEY
        STRIPE_ENABLED = True
        logger.info("Stripe library loaded and configured.")
    else:
        logger.warning("Stripe key not set or invalid — using mock mode.")
except ImportError:
    stripe_lib = None  # type: ignore[assignment]
    logger.warning("stripe library not installed — using mock mode.")


# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

class PlanId(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLANS: List[Dict[str, Any]] = [
    {
        "id": PlanId.FREE,
        "name": "Free",
        "price_monthly": 0.0,
        "price_id": "",
        "features": {
            "messages_per_day": 50,
            "projects": 3,
            "storage_mb": 100,
            "unlimited_messages": False,
            "unlimited_projects": False,
            "team_features": False,
            "priority_support": False,
        },
    },
    {
        "id": PlanId.PRO,
        "name": "Pro",
        "price_monthly": 19.99,
        "price_id": "price_pro_monthly",
        "features": {
            "messages_per_day": -1,  # unlimited
            "projects": 20,
            "storage_mb": 1024,
            "unlimited_messages": True,
            "unlimited_projects": False,
            "team_features": False,
            "priority_support": True,
        },
    },
    {
        "id": PlanId.ENTERPRISE,
        "name": "Enterprise",
        "price_monthly": 29.99,
        "price_id": "price_enterprise_monthly",
        "features": {
            "messages_per_day": -1,  # unlimited
            "projects": -1,          # unlimited
            "storage_mb": 10240,
            "unlimited_messages": True,
            "unlimited_projects": True,
            "team_features": True,
            "priority_support": True,
        },
    },
]

_PLAN_BY_ID: Dict[str, Dict[str, Any]] = {p["id"]: p for p in PLANS}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@contextmanager
def _db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Yield a SQLite connection with row factory, auto-create parent dirs."""
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. init_db
# ---------------------------------------------------------------------------

def init_db(db_path: Optional[str] = None) -> None:
    """Create all required tables and indexes if they do not exist.

    Tables created:
        - subscriptions
        - usage_log
        - api_log
    """
    schema = """
    CREATE TABLE IF NOT EXISTS subscriptions (
        user_id                 TEXT PRIMARY KEY,
        plan_id                 TEXT NOT NULL DEFAULT 'free',
        status                  TEXT NOT NULL DEFAULT 'active',
        current_period_end      TEXT,
        stripe_customer_id      TEXT,
        stripe_subscription_id  TEXT,
        cancel_at_period_end    INTEGER NOT NULL DEFAULT 0,
        created_at              TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_subs_plan       ON subscriptions(plan_id);
    CREATE INDEX IF NOT EXISTS idx_subs_status     ON subscriptions(status);
    CREATE INDEX IF NOT EXISTS idx_subs_period_end ON subscriptions(current_period_end);

    CREATE TABLE IF NOT EXISTS usage_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        resource    TEXT NOT NULL,
        amount      INTEGER NOT NULL DEFAULT 1,
        timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_usage_user_ts   ON usage_log(user_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_usage_resource  ON usage_log(resource);

    CREATE TABLE IF NOT EXISTS api_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        endpoint    TEXT NOT NULL,
        method      TEXT NOT NULL,
        duration_ms REAL,
        status_code INTEGER,
        timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_api_user_ts     ON api_log(user_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_api_endpoint    ON api_log(endpoint);
    CREATE INDEX IF NOT EXISTS idx_api_status      ON api_log(status_code);
    """
    with _db_connection(db_path) as conn:
        conn.executescript(schema)
        conn.commit()
    logger.info("Database initialised at %s", db_path or DEFAULT_DB_PATH)


# ---------------------------------------------------------------------------
# 2. get_plans
# ---------------------------------------------------------------------------

def get_plans() -> List[Dict[str, Any]]:
    """Return the three available subscription plans with full feature lists.

    Returns:
        A list of plan dictionaries (id, name, price_monthly, price_id, features).
    """
    return [p.copy() for p in PLANS]


# ---------------------------------------------------------------------------
# 3. get_or_create_subscription
# ---------------------------------------------------------------------------

def get_or_create_subscription(user_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Fetch the subscription for *user_id*, creating a free tier row if absent.

    Args:
        user_id: Opaque user identifier.

    Returns:
        Subscription row as a dict.
    """
    with _db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row is None:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO subscriptions
                    (user_id, plan_id, status, current_period_end, created_at, updated_at)
                VALUES (?, 'free', 'active', ?, ?, ?)
                """,
                (user_id, now, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
            ).fetchone()
            logger.info("Created free subscription for user=%s", user_id)

        return dict(row)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. upgrade_subscription
# ---------------------------------------------------------------------------

def upgrade_subscription(
    user_id: str,
    plan_id: str,
    stripe_subscription_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Move *user_id* onto *plan_id* and activate the new period.

    Args:
        user_id: Target user.
        plan_id: One of ``free``, ``pro``, ``enterprise``.
        stripe_subscription_id: Optional Stripe subscription identifier.

    Returns:
        Updated subscription dict.

    Raises:
        ValueError: If *plan_id* is not recognised.
    """
    if plan_id not in _PLAN_BY_ID:
        raise ValueError(f"Unknown plan_id: {plan_id!r}")

    period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    with _db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (user_id, plan_id, status, current_period_end,
                                       stripe_subscription_id, cancel_at_period_end,
                                       created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, 0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_id                = excluded.plan_id,
                status                 = excluded.status,
                current_period_end     = excluded.current_period_end,
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id,
                                                   subscriptions.stripe_subscription_id),
                cancel_at_period_end   = 0,
                updated_at             = excluded.updated_at
            """,
            (user_id, plan_id, period_end, stripe_subscription_id, now, now),
        )
        conn.commit()

    logger.info("User %s upgraded to plan=%s", user_id, plan_id)
    return get_or_create_subscription(user_id, db_path)


# ---------------------------------------------------------------------------
# 5. cancel_subscription
# ---------------------------------------------------------------------------

def cancel_subscription(user_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Mark *user_id*'s subscription as cancelling at period end and downgrade
    them to the free plan immediately.

    Args:
        user_id: Target user.

    Returns:
        Updated subscription dict.
    """
    now = datetime.now(timezone.utc).isoformat()
    with _db_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET plan_id = 'free',
                status = 'cancelled',
                cancel_at_period_end = 1,
                updated_at = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )
        conn.commit()

    logger.info("User %s subscription cancelled (downgraded to free).", user_id)
    return get_or_create_subscription(user_id, db_path)


# ---------------------------------------------------------------------------
# 6. check_quota
# ---------------------------------------------------------------------------

def check_quota(user_id: str, resource: str, db_path: Optional[str] = None) -> bool:
    """Return ``True`` if *user_id* has not exceeded their quota for *resource*.

    Supported resources: ``messages``, ``projects``, ``storage_mb``.
    """
    sub = get_or_create_subscription(user_id, db_path)
    plan = _PLAN_BY_ID.get(sub["plan_id"], _PLAN_BY_ID[PlanId.FREE])
    features = plan["features"]

    # Map resource name to plan feature key
    resource_map = {
        "messages": "messages_per_day",
        "projects": "projects",
        "storage_mb": "storage_mb",
    }
    feature_key = resource_map.get(resource)
    if feature_key is None:
        # Unknown resource — allow by default
        return True

    limit = features.get(feature_key, 0)
    if limit == -1:
        return True  # unlimited

    # Compute today's usage
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM usage_log
            WHERE user_id = ? AND resource = ? AND date(timestamp) = ?
            """,
            (user_id, resource, today),
        ).fetchone()
    used = row["total"] if row else 0

    return used < limit


# ---------------------------------------------------------------------------
# 7. increment_usage
# ---------------------------------------------------------------------------

def increment_usage(
    user_id: str, resource: str, amount: int = 1, db_path: Optional[str] = None
) -> None:
    """Record *amount* consumption of *resource* for *user_id*.

    Args:
        user_id: Target user.
        resource: Resource slug, e.g. ``messages``, ``projects``.
        amount: How much to increment by (default 1).
    """
    with _db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO usage_log (user_id, resource, amount, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, resource, amount, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 8. get_usage
# ---------------------------------------------------------------------------

def get_usage(user_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return today's usage counts for *user_id* plus plan limits.

    Returns:
        Dict with keys: ``plan``, ``limits``, ``used``, ``remaining``.
    """
    sub = get_or_create_subscription(user_id, db_path)
    plan = _PLAN_BY_ID.get(sub["plan_id"], _PLAN_BY_ID[PlanId.FREE])
    features = plan["features"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT resource, COALESCE(SUM(amount), 0) as total
            FROM usage_log
            WHERE user_id = ? AND date(timestamp) = ?
            GROUP BY resource
            """,
            (user_id, today),
        ).fetchall()

    used: Dict[str, int] = {r["resource"]: r["total"] for r in rows}
    limits: Dict[str, Any] = {
        "messages": features.get("messages_per_day", 0),
        "projects": features.get("projects", 0),
        "storage_mb": features.get("storage_mb", 0),
    }
    remaining: Dict[str, Any] = {}
    for key, limit in limits.items():
        if limit == -1:
            remaining[key] = "unlimited"
        else:
            remaining[key] = max(0, limit - used.get(key, 0))

    return {
        "plan": sub["plan_id"],
        "limits": limits,
        "used": used,
        "remaining": remaining,
    }


# ---------------------------------------------------------------------------
# 9. get_analytics
# ---------------------------------------------------------------------------

def get_analytics(
    user_id: Optional[str] = None, days: int = 7, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Aggregate usage and API analytics for the last *days* days.

    Args:
        user_id: If given, restrict to this user; otherwise workspace-wide.
        days: Look-back window in days.

    Returns:
        Dict containing ``period_days``, ``total_requests``, ``total_api_calls``,
        ``resource_breakdown``, ``status_breakdown``, ``top_endpoints``,
        ``daily_counts``.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    params: List[Any] = [since]
    user_filter_usage = ""
    user_filter_api = ""
    if user_id:
        params_user = [since, user_id]
    else:
        params_user = [since]

    with _db_connection(db_path) as conn:
        # Total usage events
        q_usage = "SELECT COALESCE(SUM(amount), 0) as total FROM usage_log WHERE timestamp >= ?"
        q_api = "SELECT COUNT(*) as total FROM api_log WHERE timestamp >= ?"
        if user_id:
            q_usage += " AND user_id = ?"
            q_api += " AND user_id = ?"
            total_requests = conn.execute(q_usage, [since, user_id]).fetchone()["total"]
            total_api_calls = conn.execute(q_api, [since, user_id]).fetchone()["total"]
        else:
            total_requests = conn.execute(q_usage, [since]).fetchone()["total"]
            total_api_calls = conn.execute(q_api, [since]).fetchone()["total"]

        # Resource breakdown
        q = """
            SELECT resource, COALESCE(SUM(amount), 0) as total
            FROM usage_log WHERE timestamp >= ?
        """
        p = [since]
        if user_id:
            q += " AND user_id = ?"
            p.append(user_id)
        q += " GROUP BY resource"
        resource_breakdown = {r["resource"]: r["total"] for r in conn.execute(q, p).fetchall()}

        # Status breakdown
        q = """
            SELECT status_code, COUNT(*) as total
            FROM api_log WHERE timestamp >= ?
        """
        p = [since]
        if user_id:
            q += " AND user_id = ?"
            p.append(user_id)
        q += " GROUP BY status_code"
        status_breakdown = {r["status_code"]: r["total"] for r in conn.execute(q, p).fetchall()}

        # Top endpoints
        q = """
            SELECT endpoint, COUNT(*) as total
            FROM api_log WHERE timestamp >= ?
        """
        p = [since]
        if user_id:
            q += " AND user_id = ?"
            p.append(user_id)
        q += " GROUP BY endpoint ORDER BY total DESC LIMIT 10"
        top_endpoints = [
            {"endpoint": r["endpoint"], "calls": r["total"]}
            for r in conn.execute(q, p).fetchall()
        ]

        # Daily counts
        q = """
            SELECT date(timestamp) as day, COUNT(*) as total
            FROM api_log WHERE timestamp >= ?
        """
        p = [since]
        if user_id:
            q += " AND user_id = ?"
            p.append(user_id)
        q += " GROUP BY day ORDER BY day"
        daily_counts = [
            {"date": r["day"], "calls": r["total"]}
            for r in conn.execute(q, p).fetchall()
        ]

    return {
        "period_days": days,
        "total_requests": total_requests,
        "total_api_calls": total_api_calls,
        "resource_breakdown": resource_breakdown,
        "status_breakdown": status_breakdown,
        "top_endpoints": top_endpoints,
        "daily_counts": daily_counts,
    }


# ---------------------------------------------------------------------------
# 10. log_api_call
# ---------------------------------------------------------------------------

def log_api_call(
    user_id: str,
    endpoint: str,
    method: str,
    duration_ms: float,
    status_code: int,
    db_path: Optional[str] = None,
) -> None:
    """Persist a single API request telemetry row.

    Args:
        user_id: Caller identifier.
        endpoint: Request path, e.g. ``/v1/chat``.
        method: HTTP method upper-cased.
        duration_ms: Wall-clock latency in milliseconds.
        status_code: HTTP response status code.
    """
    with _db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO api_log (user_id, endpoint, method, duration_ms, status_code, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                endpoint,
                method.upper(),
                round(duration_ms, 3),
                status_code,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 11. require_plan — decorator factory
# ---------------------------------------------------------------------------

def require_plan(min_plan: str):
    """Return a decorator that blocks access unless the caller is on *min_plan*
    or higher.

    Plan ordering: ``free`` < ``pro`` < ``enterprise``.

    Usage::

        @router.get("/premium")
        @require_plan("pro")
        async def premium_endpoint(user_id: str = Header(...)):
            ...

    Args:
        min_plan: Minimum acceptable plan identifier.

    Returns:
        A decorator function.
    """
    _order = {"free": 0, "pro": 1, "enterprise": 2}
    min_level = _order.get(min_plan, 0)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or kwargs.get("x_user_id")
            if not user_id:
                raise PermissionError("user_id required for plan-gated endpoint.")
            sub = get_or_create_subscription(user_id)
            user_level = _order.get(sub["plan_id"], 0)
            if user_level < min_level:
                raise PermissionError(
                    f"Plan '{sub['plan_id']}' insufficient — requires '{min_plan}'."
                )
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or kwargs.get("x_user_id")
            if not user_id:
                raise PermissionError("user_id required for plan-gated endpoint.")
            sub = get_or_create_subscription(user_id)
            user_level = _order.get(sub["plan_id"], 0)
            if user_level < min_level:
                raise PermissionError(
                    f"Plan '{sub['plan_id']}' insufficient — requires '{min_plan}'."
                )
            return func(*args, **kwargs)

        # Heuristic: if the wrapped function is a coroutine, expose the async wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# 12. rate_limit_check
# ---------------------------------------------------------------------------

def rate_limit_check(user_id: str, endpoint: str) -> bool:
    """Sliding-window rate-limit check per *user_id*.

    Limits are tier-based:
        - Free: 30 req/min
        - Pro: 120 req/min
        - Enterprise: 600 req/min

    Args:
        user_id: Caller identifier.
        endpoint: Request path (included in key for endpoint-level granularity).

    Returns:
        ``True`` if the request is within the limit.
    """
    sub = get_or_create_subscription(user_id)
    plan_limits = {
        PlanId.FREE: RATE_LIMIT_FREE,
        PlanId.PRO: RATE_LIMIT_PRO,
        PlanId.ENTERPRISE: RATE_LIMIT_ENTERPRISE,
    }
    limit = plan_limits.get(sub["plan_id"], RATE_LIMIT_FREE)

    key = f"{user_id}:{endpoint}"
    now = time.time()

    with _lock:
        bucket = _rate_limit_buckets.get(key, [])
        # Evict stale entries outside the window
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        bucket = [ts for ts in bucket if ts > cutoff]
        if len(bucket) >= limit:
            _rate_limit_buckets[key] = bucket
            logger.debug("Rate-limit exceeded for user=%s endpoint=%s", user_id, endpoint)
            return False
        bucket.append(now)
        _rate_limit_buckets[key] = bucket
        return True


# ---------------------------------------------------------------------------
# 13. get_health_detailed
# ---------------------------------------------------------------------------

def get_health_detailed(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return extended health diagnostics for monitoring dashboards.

    Checks:
        - Database connectivity
        - Row counts per table
        - Stripe connectivity status
        - In-memory cache sizes

    Returns:
        Dict with ``status``, ``checks``, ``timestamp``.
    """
    now = datetime.now(timezone.utc).isoformat()
    checks: Dict[str, Any] = {}

    # DB check
    try:
        with _db_connection(db_path) as conn:
            subs = conn.execute("SELECT COUNT(*) as c FROM subscriptions").fetchone()["c"]
            usage = conn.execute("SELECT COUNT(*) as c FROM usage_log").fetchone()["c"]
            api = conn.execute("SELECT COUNT(*) as c FROM api_log").fetchone()["c"]
        checks["database"] = {
            "reachable": True,
            "subscriptions": subs,
            "usage_rows": usage,
            "api_rows": api,
        }
    except Exception as exc:
        checks["database"] = {"reachable": False, "error": str(exc)}

    # Stripe check
    checks["stripe"] = {
        "enabled": STRIPE_ENABLED,
        "mode": "live" if (STRIPE_SECRET_KEY or "").startswith("sk_live_") else "test/mock",
    }

    # Memory
    checks["memory"] = {
        "user_cache_entries": len(_user_id_cache),
        "rate_limit_buckets": len(_rate_limit_buckets),
    }

    overall = "ok" if checks["database"].get("reachable") else "degraded"
    return {"status": overall, "checks": checks, "timestamp": now}


# ---------------------------------------------------------------------------
# 14. create_checkout_session
# ---------------------------------------------------------------------------

def create_checkout_session(
    user_id: str, plan_id: str, base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Create a Stripe Checkout session for *user_id* to subscribe to *plan_id*.

    If Stripe is unavailable, returns a mock checkout URL for local development.

    Args:
        user_id: Target user.
        plan_id: Plan to purchase.
        base_url: Absolute base URL for success/cancel redirects.

    Returns:
        Dict with ``checkout_url`` and ``session_id`` (or mock equivalents).
    """
    plan = _PLAN_BY_ID.get(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan_id: {plan_id!r}")

    if STRIPE_ENABLED and stripe_lib is not None:
        try:
            # Upsert Stripe customer
            with _db_connection() as conn:
                row = conn.execute(
                    "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                customer_id = row["stripe_customer_id"] if row else None

            if not customer_id:
                customer = stripe_lib.Customer.create(
                    metadata={"luqi_user_id": user_id}
                )
                customer_id = customer.id
                with _db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE subscriptions
                        SET stripe_customer_id = ?,
                            updated_at = ?
                        WHERE user_id = ?
                        """,
                        (customer_id, datetime.now(timezone.utc).isoformat(), user_id),
                    )
                    conn.commit()

            session = stripe_lib.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": plan["price_id"],
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=f"{base_url}/v1/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/v1/billing/cancel",
                metadata={"luqi_user_id": user_id, "luqi_plan_id": plan_id},
            )
            return {"checkout_url": session.url, "session_id": session.id}
        except Exception as exc:
            logger.error("Stripe checkout failed: %s", exc)
            # Fall through to mock

    # Mock fallback for development / testing
    mock_session_id = f"mock_cs_{hashlib.sha256(user_id.encode()).hexdigest()[:16]}_{plan_id}"
    logger.info("Mock checkout session created for user=%s plan=%s", user_id, plan_id)
    return {
        "checkout_url": f"{base_url}/v1/billing/mock-checkout?session_id={mock_session_id}",
        "session_id": mock_session_id,
        "note": "Stripe not configured — mock mode.",
    }


# ---------------------------------------------------------------------------
# 15. create_customer_portal
# ---------------------------------------------------------------------------

def create_customer_portal(
    user_id: str, base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Create a Stripe Customer Portal session for *user_id*.

    Args:
        user_id: Target user.
        base_url: Absolute base URL for the return redirect.

    Returns:
        Dict with ``portal_url`` and ``session_id``.
    """
    if STRIPE_ENABLED and stripe_lib is not None:
        try:
            with _db_connection() as conn:
                row = conn.execute(
                    "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                customer_id = row["stripe_customer_id"] if row else None

            if customer_id:
                session = stripe_lib.billing_portal.Session.create(
                    customer=customer_id,
                    return_url=f"{base_url}/v1/billing/portal-return",
                )
                return {"portal_url": session.url, "session_id": session.id}
        except Exception as exc:
            logger.error("Stripe portal failed: %s", exc)

    mock_id = f"mock_portal_{hashlib.sha256(user_id.encode()).hexdigest()[:16]}"
    return {
        "portal_url": f"{base_url}/v1/billing/mock-portal?session_id={mock_id}",
        "session_id": mock_id,
        "note": "Stripe not configured — mock mode.",
    }


# ---------------------------------------------------------------------------
# 16. handle_webhook
# ---------------------------------------------------------------------------

def handle_webhook(payload: dict, sig: str) -> Dict[str, Any]:
    """Process a Stripe webhook payload.

    Handles:
        - ``checkout.session.completed``  → activate subscription
        - ``invoice.payment_succeeded``   → extend period
        - ``customer.subscription.deleted`` → downgrade to free

    Args:
        payload: Decoded JSON body from Stripe.
        sig: Stripe-Signature header value.

    Returns:
        Dict with ``received``, ``event_type``, ``result``.
    """
    event_type = payload.get("type", "unknown")
    data_obj = payload.get("data", {}).get("object", {})

    result = "no-op"

    if STRIPE_ENABLED and stripe_lib is not None:
        try:
            event = stripe_lib.Webhook.construct_event(
                payload=json.dumps(payload),
                sig_header=sig,
                secret=STRIPE_WEBHOOK_SECRET,
            )
            event_type = event.type
            data_obj = event.data.object
        except Exception as exc:
            logger.warning("Webhook signature verification failed: %s", exc)
            # Still attempt best-effort processing below

    # Unified event handling (works for both real and mock paths)
    if event_type == "checkout.session.completed":
        metadata = data_obj.get("metadata", {})
        user_id = metadata.get("luqi_user_id")
        plan_id = metadata.get("luqi_plan_id")
        sub_id = data_obj.get("subscription")
        if user_id and plan_id:
            upgrade_subscription(user_id, plan_id, stripe_subscription_id=sub_id)
            result = f"activated {plan_id} for {user_id}"

    elif event_type == "invoice.payment_succeeded":
        sub_id = data_obj.get("subscription")
        if sub_id:
            with _db_connection() as conn:
                row = conn.execute(
                    "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = ?",
                    (sub_id,),
                ).fetchone()
            if row:
                period_end = (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()
                with _db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE subscriptions
                        SET current_period_end = ?,
                            status = 'active',
                            updated_at = ?
                        WHERE user_id = ?
                        """,
                        (period_end, datetime.now(timezone.utc).isoformat(), row["user_id"]),
                    )
                    conn.commit()
                result = f"extended period for {row['user_id']}"

    elif event_type == "customer.subscription.deleted":
        sub_id = data_obj.get("id")
        if sub_id:
            with _db_connection() as conn:
                row = conn.execute(
                    "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = ?",
                    (sub_id,),
                ).fetchone()
            if row:
                cancel_subscription(row["user_id"])
                result = f"cancelled for {row['user_id']}"

    logger.info("Webhook %s processed: %s", event_type, result)
    return {"received": True, "event_type": event_type, "result": result}


# ---------------------------------------------------------------------------
# 17. get_user_id
# ---------------------------------------------------------------------------

def get_user_id(api_key: str) -> str:
    """Derive a stable, opaque *user_id* from *api_key* using SHA-256 hashing.

    The original API key is never stored; only the hash is used as the
    persistent user identifier in the subscription tables.

    Args:
        api_key: Raw API key string (e.g. ``Bearer luqi_abc123`` or just the key).

    Returns:
        Hex-encoded 64-character user identifier.
    """
    # Strip common prefix noise
    cleaned = api_key.strip()
    if " " in cleaned:
        cleaned = cleaned.split()[-1]
    if cleaned in _user_id_cache:
        return _user_id_cache[cleaned]
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    _user_id_cache[cleaned] = digest
    return digest


# ---------------------------------------------------------------------------
# 18. track_request
# ---------------------------------------------------------------------------

def track_request(
    api_key: str,
    endpoint: str,
    method: str,
    duration_ms: float,
    status_code: int,
) -> str:
    """Middleware helper: resolve *api_key* → *user_id*, log the request,
    and increment usage for ``messages`` if the endpoint looks like a chat call.

    Args:
        api_key: Raw API key.
        endpoint: Request path.
        method: HTTP method.
        duration_ms: Request latency in milliseconds.
        status_code: HTTP status.

    Returns:
        The resolved *user_id*.
    """
    user_id = get_user_id(api_key)
    log_api_call(user_id, endpoint, method, duration_ms, status_code)

    # Auto-count message-like endpoints toward daily quota
    msg_endpoints = {"/v1/chat", "/v1/ask", "/v1/generate", "/chat", "/ask"}
    if endpoint.rstrip("/") in msg_endpoints:
        increment_usage(user_id, "messages")

    return user_id


# ---------------------------------------------------------------------------
# Auto-init on import (development convenience)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick self-test when run directly
    init_db()
    print("Plans:", json.dumps(get_plans(), indent=2))
    uid = "test-user-1"
    print("Sub:", get_or_create_subscription(uid))
    print("Quota messages:", check_quota(uid, "messages"))
    increment_usage(uid, "messages", 5)
    print("Usage:", json.dumps(get_usage(uid), indent=2))
    print("Health:", json.dumps(get_health_detailed(), indent=2))
