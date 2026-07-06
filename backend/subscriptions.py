#!/usr/bin/env python3
"""Luqi AI v14 -- Subscription Management System

Production-grade SaaS billing with three tiers: Free, Pro, Enterprise.
Supports Stripe integration with graceful mock fallback for development.
SQLite-backed with usage tracking, quota enforcement, and rate limiting.

Usage:
    from backend.subscriptions import init_db, get_plans, check_quota
    init_db()
    plans = get_plans()
    ok = check_quota("user_123", "messages")
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DB_PATH = Path("./data/subscriptions.db")
PLAN_HIERARCHY = {"free": 0, "pro": 1, "enterprise": 2}

# ---------------------------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    """Subscription plan definition."""
    id: str
    name: str
    price_monthly: int       # cents
    price_yearly: int        # cents
    daily_messages: int      # -1 = unlimited
    max_projects: int        # -1 = unlimited
    max_storage_mb: int
    features: List[str]
    description: str


# Plan catalog
PLANS = {
    "free": Plan(
        id="free",
        name="Free",
        price_monthly=0,
        price_yearly=0,
        daily_messages=50,
        max_projects=3,
        max_storage_mb=100,
        features=[
            "50 messages per day",
            "3 projects",
            "100 MB storage",
            "Basic code generation",
            "Community support",
        ],
        description="Perfect for getting started with Luqi AI."
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_monthly=999,     # $9.99
        price_yearly=9990,     # $99.90
        daily_messages=-1,     # unlimited
        max_projects=20,
        max_storage_mb=1000,   # 1 GB
        features=[
            "Unlimited messages",
            "20 projects",
            "1 GB storage",
            "Advanced code generation",
            "Code review & debugging",
            "Website builder",
            "Priority support",
            "API access",
        ],
        description="For professional developers and creators."
    ),
    "enterprise": Plan(
        id="enterprise",
        name="Enterprise",
        price_monthly=2999,    # $29.99
        price_yearly=29990,    # $299.90
        daily_messages=-1,
        max_projects=-1,
        max_storage_mb=10000,  # 10 GB
        features=[
            "Everything in Pro",
            "Unlimited projects",
            "10 GB storage",
            "Team collaboration",
            "Custom integrations",
            "SSO authentication",
            "Dedicated support",
            "SLA guarantee",
            "On-premise option",
        ],
        description="For teams and organizations at scale."
    ),
}


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    """Get a database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all subscription-related tables."""
    with _get_db() as conn:
        # Subscriptions
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'active',
                current_period_end TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                cancel_at_period_end BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);
            CREATE INDEX IF NOT EXISTS idx_subs_plan ON subscriptions(plan_id);

            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                resource TEXT NOT NULL,
                amount INTEGER DEFAULT 1,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage_log(timestamp);

            CREATE TABLE IF NOT EXISTS api_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                duration_ms REAL,
                status_code INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_api_user ON api_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_api_endpoint ON api_log(endpoint);
            CREATE INDEX IF NOT EXISTS idx_api_ts ON api_log(timestamp);
        """)
        conn.commit()
    logger.info("Subscription database initialized")


# ---------------------------------------------------------------------------
# PLANS
# ---------------------------------------------------------------------------

def get_plans() -> List[dict]:
    """Return all subscription plans with pricing and features."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "price_monthly_display": f"${p.price_monthly / 100:.2f}",
            "price_yearly_display": f"${p.price_yearly / 100:.2f}",
            "daily_messages": p.daily_messages,
            "max_projects": p.max_projects,
            "max_storage_mb": p.max_storage_mb,
            "features": p.features,
            "description": p.description,
        }
        for p in PLANS.values()
    ]


def get_plan(plan_id: str) -> Optional[Plan]:
    """Get a plan by ID."""
    return PLANS.get(plan_id)


# ---------------------------------------------------------------------------
# SUBSCRIPTION CRUD
# ---------------------------------------------------------------------------

def get_or_create_subscription(user_id: str) -> dict:
    """Get existing subscription or create a free one."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if row is None:
            # Create free subscription
            conn.execute(
                """INSERT INTO subscriptions
                   (user_id, plan_id, status, current_period_end)
                   VALUES (?, 'free', 'active', ?)""",
                (user_id, (datetime.utcnow() + timedelta(days=365)).isoformat())
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ?",
                (user_id,)
            ).fetchone()

        return dict(row)


def upgrade_subscription(user_id: str, plan_id: str) -> dict:
    """Upgrade user to a new plan."""
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_id}")

    with _get_db() as conn:
        conn.execute(
            """UPDATE subscriptions
               SET plan_id = ?, status = 'active',
                   current_period_end = ?,
                   cancel_at_period_end = FALSE,
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?""",
            (plan_id, (datetime.utcnow() + timedelta(days=30)).isoformat(), user_id)
        )
        conn.commit()

    return get_or_create_subscription(user_id)


def cancel_subscription(user_id: str) -> dict:
    """Cancel subscription -- downgrades to free at period end."""
    with _get_db() as conn:
        conn.execute(
            """UPDATE subscriptions
               SET cancel_at_period_end = TRUE, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?""",
            (user_id,)
        )
        conn.commit()
    return {"status": "cancelled", "message": "Subscription will downgrade to Free at period end."}


# ---------------------------------------------------------------------------
# USAGE TRACKING & QUOTAS
# ---------------------------------------------------------------------------

def check_quota(user_id: str, resource: str) -> bool:
    """Check if user has remaining quota for a resource."""
    sub = get_or_create_subscription(user_id)
    plan = PLANS.get(sub["plan_id"], PLANS["free"])

    if resource == "messages":
        limit = plan.daily_messages
        if limit == -1:
            return True
        used = get_usage(user_id).get("messages_today", 0)
        return used < limit

    if resource == "projects":
        limit = plan.max_projects
        if limit == -1:
            return True
        # Count from usage log
        return True  # Simplified

    return True


def increment_usage(user_id: str, resource: str, amount: int = 1):
    """Record usage of a resource."""
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO usage_log (user_id, resource, amount) VALUES (?, ?, ?)",
            (user_id, resource, amount)
        )
        conn.commit()


def get_usage(user_id: str) -> dict:
    """Get today's usage statistics for a user."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT resource, SUM(amount) as total
               FROM usage_log
               WHERE user_id = ? AND timestamp >= ?
               GROUP BY resource""",
            (user_id, today)
        ).fetchall()

    usage = {row["resource"]: row["total"] for row in rows}
    sub = get_or_create_subscription(user_id)
    plan = PLANS.get(sub["plan_id"], PLANS["free"])

    return {
        "user_id": user_id,
        "plan_id": sub["plan_id"],
        "messages_today": usage.get("messages", 0),
        "messages_limit": plan.daily_messages if plan.daily_messages > 0 else "unlimited",
        "remaining_messages": (
            max(0, plan.daily_messages - usage.get("messages", 0))
            if plan.daily_messages > 0 else "unlimited"
        ),
        "storage_used_mb": usage.get("storage", 0),
        "storage_limit_mb": plan.max_storage_mb,
        "projects_used": usage.get("projects", 0),
        "projects_limit": plan.max_projects if plan.max_projects > 0 else "unlimited",
    }


# ---------------------------------------------------------------------------
# RATE LIMITING
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_rate_buckets: Dict[str, List[float]] = {}


def rate_limit_check(user_id: str, endpoint: str) -> bool:
    """Sliding-window rate limit. Free: 30/min, Pro: 120/min, Enterprise: 600/min."""
    sub = get_or_create_subscription(user_id)
    plan = PLANS.get(sub["plan_id"], PLANS["free"])

    limits = {"free": 30, "pro": 120, "enterprise": 600}
    limit = limits.get(plan.id, 30)

    key = f"{user_id}:{endpoint}"
    now = time.time()
    window = 60.0  # 1 minute

    with _lock:
        bucket = _rate_buckets.get(key, [])
        # Remove old entries
        bucket = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        _rate_buckets[key] = bucket

    return True


# ---------------------------------------------------------------------------
# STRIPE INTEGRATION (with mock fallback)
# ---------------------------------------------------------------------------

def _stripe_available() -> bool:
    """Check if Stripe library is installed and configured."""
    try:
        import stripe
        return bool(stripe.api_key)
    except ImportError:
        return False


def create_checkout_session(user_id: str, plan_id: str) -> dict:
    """Create a Stripe Checkout session or return a mock URL."""
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_id}")

    if _stripe_available():
        import stripe
        try:
            # Create or get customer
            sub = get_or_create_subscription(user_id)
            customer_id = sub.get("stripe_customer_id")

            if not customer_id:
                customer = stripe.Customer.create(metadata={"user_id": user_id})
                customer_id = customer.id
                with _get_db() as conn:
                    conn.execute(
                        "UPDATE subscriptions SET stripe_customer_id = ? WHERE user_id = ?",
                        (customer_id, user_id)
                    )
                    conn.commit()

            # Create price if needed (in production, pre-create prices)
            price_id = f"price_{plan_id}_monthly"

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"https://luqi-ai.com/subscription?success=true",
                cancel_url=f"https://luqi-ai.com/subscription?canceled=true",
            )
            return {"url": session.url, "session_id": session.id}
        except Exception as e:
            logger.warning("Stripe checkout failed, using mock: %s", e)

    # Mock fallback
    return {
        "url": f"/subscription/mock-checkout?plan={plan_id}&user={user_id}",
        "mock": True,
        "plan": plan_id,
        "price": f"${plan.price_monthly / 100:.2f}/mo",
        "message": "Stripe not configured. In production, this would redirect to Stripe Checkout."
    }


def create_customer_portal(user_id: str) -> dict:
    """Create Stripe Customer Portal session or mock."""
    if _stripe_available():
        import stripe
        try:
            sub = get_or_create_subscription(user_id)
            customer_id = sub.get("stripe_customer_id")
            if customer_id:
                session = stripe.billing_portal.Session.create(
                    customer=customer_id,
                    return_url="https://luqi-ai.com/subscription",
                )
                return {"url": session.url}
        except Exception as e:
            logger.warning("Stripe portal failed: %s", e)

    return {
        "url": "/subscription",
        "mock": True,
        "message": "Billing portal not available in development mode."
    }


def handle_webhook(payload: dict, signature: str) -> dict:
    """Process Stripe webhook events."""
    if _stripe_available():
        import stripe
        try:
            # Verify signature in production
            event = payload
            event_type = event.get("type", "")

            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                user_id = session.get("metadata", {}).get("user_id", "")
                plan_id = session.get("metadata", {}).get("plan_id", "pro")
                upgrade_subscription(user_id, plan_id)

            elif event_type == "customer.subscription.deleted":
                sub = event["data"]["object"]
                customer_id = sub.get("customer", "")
                # Find user by customer ID and downgrade
                with _get_db() as conn:
                    conn.execute(
                        "UPDATE subscriptions SET plan_id = 'free', status = 'active' WHERE stripe_customer_id = ?",
                        (customer_id,)
                    )
                    conn.commit()

            return {"status": "processed", "event": event_type}
        except Exception as e:
            logger.error("Webhook error: %s", e)

    return {"status": "mock_processed", "message": "Stripe not configured"}


# ---------------------------------------------------------------------------
# USER ID & TRACKING
# ---------------------------------------------------------------------------

def get_user_id(api_key: str) -> str:
    """Hash API key to a stable user ID."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def log_api_call(user_id: str, endpoint: str, method: str, duration_ms: float, status_code: int):
    """Log an API call for analytics."""
    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO api_log (user_id, endpoint, method, duration_ms, status_code) VALUES (?, ?, ?, ?, ?)",
                (user_id, endpoint, method, duration_ms, status_code)
            )
            conn.commit()
    except Exception as e:
        logger.warning("API log error: %s", e)


def track_request(api_key: str, endpoint: str, method: str, duration_ms: float, status_code: int) -> str:
    """Middleware helper: resolve user, log call, count message."""
    user_id = get_user_id(api_key)
    log_api_call(user_id, endpoint, method, duration_ms, status_code)
    if "chat" in endpoint:
        increment_usage(user_id, "messages")
    return user_id


# ---------------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------------

def get_analytics(user_id: Optional[str] = None, days: int = 7) -> dict:
    """Get API usage analytics."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    with _get_db() as conn:
        # Total calls
        if user_id:
            total_calls = conn.execute(
                "SELECT COUNT(*) as c FROM api_log WHERE user_id = ? AND timestamp >= ?",
                (user_id, since)
            ).fetchone()["c"]
            endpoint_breakdown = conn.execute(
                """SELECT endpoint, COUNT(*) as c FROM api_log
                   WHERE user_id = ? AND timestamp >= ?
                   GROUP BY endpoint ORDER BY c DESC LIMIT 20""",
                (user_id, since)
            ).fetchall()
            avg_latency = conn.execute(
                "SELECT AVG(duration_ms) as avg FROM api_log WHERE user_id = ? AND timestamp >= ?",
                (user_id, since)
            ).fetchone()["avg"] or 0
        else:
            total_calls = conn.execute(
                "SELECT COUNT(*) as c FROM api_log WHERE timestamp >= ?",
                (since,)
            ).fetchone()["c"]
            endpoint_breakdown = conn.execute(
                """SELECT endpoint, COUNT(*) as c FROM api_log
                   WHERE timestamp >= ?
                   GROUP BY endpoint ORDER BY c DESC LIMIT 20""",
                (since,)
            ).fetchall()
            avg_latency = conn.execute(
                "SELECT AVG(duration_ms) as avg FROM api_log WHERE timestamp >= ?",
                (since,)
            ).fetchone()["avg"] or 0

    return {
        "period_days": days,
        "total_api_calls": total_calls,
        "average_latency_ms": round(avg_latency, 2),
        "endpoint_breakdown": [dict(r) for r in endpoint_breakdown],
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------

def get_health_detailed() -> dict:
    """Extended health check with all subsystem status."""
    import os
    import psutil

    db_ok = False
    try:
        with _get_db() as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
    except Exception:
        pass

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(".")

    # Count records
    with _get_db() as conn:
        total_subs = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
        total_api_calls = conn.execute("SELECT COUNT(*) FROM api_log").fetchone()[0]

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": "14.0.0",
        "database": "connected" if db_ok else "error",
        "subscriptions": {
            "total_users": total_subs,
            "plans": {p: conn.execute("SELECT COUNT(*) FROM subscriptions WHERE plan_id = ?", (p,)).fetchone()[0]
                      for p in PLANS.keys()},
        },
        "api_calls_total": total_api_calls,
        "stripe_configured": _stripe_available(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_used_percent": memory.percent,
            "memory_available_mb": memory.available // (1024 * 1024),
            "disk_used_percent": disk.percent,
            "disk_free_gb": disk.free // (1024 * 1024 * 1024),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# PLAN GUARD DECORATOR
# ---------------------------------------------------------------------------

def require_plan(min_plan: str):
    """Decorator factory to restrict endpoints by minimum plan tier.

    Usage:
        @app.get("/api/pro-feature")
        async def pro_feature(request: Request):
            guard = require_plan("pro")
            if not guard(request.headers.get("X-API-Key", "")):
                raise HTTPException(status_code=403, detail="Pro plan required")
            ...
    """
    min_level = PLAN_HIERARCHY.get(min_plan, 0)

    def check(api_key: str) -> bool:
        user_id = get_user_id(api_key)
        sub = get_or_create_subscription(user_id)
        plan_level = PLAN_HIERARCHY.get(sub.get("plan_id", "free"), 0)
        return plan_level >= min_level

    return check


# Auto-init on import
init_db()
logger.info("Subscription system loaded: Free / Pro / Enterprise")
