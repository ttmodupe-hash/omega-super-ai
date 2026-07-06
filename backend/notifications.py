#!/usr/bin/env python3
"""
Luqi AI — Push Notification System
====================================
A complete Web Push notification system supporting:
  - VAPID key generation and management
  - Push subscription persistence (SQLite)
  - Individual and broadcast push delivery
  - Notification templates with variable substitution
  - Scheduled (recurring) notifications
  - Event-triggered notifications

Dependencies (optional):
    pip install pywebpush py-vapid

If pywebpush is not installed the module falls back to a mock
implementation suitable for local development and testing.

Environment variables:
    VAPID_PUBLIC_KEY   — base64-encoded VAPID public key
    VAPID_PRIVATE_KEY  — base64-encoded VAPID private key
    VAPID_SUBJECT      — mailto: or https: contact (required by spec)
    PUSH_DB_PATH       — override default SQLite path
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import struct
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.notifications")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Optional dependencies — graceful degradation
# ---------------------------------------------------------------------------
try:
    from pywebpush import webpush, WebPushException  # type: ignore

    _HAS_PYWEBPUSH = True
except Exception:  # pragma: no cover
    _HAS_PYWEBPUSH = False
    WebPushException = Exception
    logger.debug("pywebpush not installed; using mock push sender")

try:
    from py_vapid import Vapid  # type: ignore

    _HAS_PY_VAPID = True
except Exception:  # pragma: no cover
    _HAS_PY_VAPID = False
    logger.debug("py-vapid not installed; using cryptography fallback")

try:
    from cryptography.hazmat.primitives import serialization  # type: ignore
    from cryptography.hazmat.primitives.asymmetric import ec  # type: ignore
    from cryptography.hazmat.backends import default_backend  # type: ignore

    _HAS_CRYPTOGRAPHY = True
except Exception:  # pragma: no cover
    _HAS_CRYPTOGRAPHY = False
    logger.debug("cryptography not installed; VAPID generation limited")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_PATH = os.environ.get("PUSH_DB_PATH", "./data/push_subscriptions.db")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@luqi.ai")

# Icon assets used across templates
ICON_DEFAULT = "/icons/icon-192.png"
BADGE_DEFAULT = "/icons/badge-72.png"

# ---------------------------------------------------------------------------
# Notification Templates
# ---------------------------------------------------------------------------
NOTIFICATION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "habit_reminder": {
        "title": "Luqi AI — Habit Reminder",
        "body": "Don't forget to {habit_name}! Current streak: {streak} days 🔥",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=habits",
        "tag": "habit-reminder",
        "require_interaction": "false",
    },
    "daily_digest": {
        "title": "Your Daily Summary",
        "body": "You sent {message_count} messages today. Check your dashboard! 📊",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=dashboard",
        "tag": "daily-digest",
        "require_interaction": "false",
    },
    "usage_warning": {
        "title": "Usage Limit Approaching",
        "body": "You've used {percent}% of your daily message limit. Upgrade for more! ⚡",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=subscription",
        "tag": "usage-warning",
        "require_interaction": "true",
    },
    "usage_exceeded": {
        "title": "Daily Limit Reached",
        "body": "You've reached your daily message limit. Upgrade to continue chatting! 🚀",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=subscription",
        "tag": "usage-exceeded",
        "require_interaction": "true",
    },
    "feature_announcement": {
        "title": "New Feature: {feature_name}",
        "body": "{feature_description} Try it now! ✨",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=settings",
        "tag": "feature-announcement",
        "require_interaction": "false",
    },
    "learning_reminder": {
        "title": "Time to Learn! 📚",
        "body": "Continue your lesson on {topic}. You're making great progress!",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=education",
        "tag": "learning-reminder",
        "require_interaction": "false",
    },
    "habit_milestone": {
        "title": "Streak Milestone! 🎉",
        "body": "Amazing! You've kept up '{habit_name}' for {streak} days straight!",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=habits",
        "tag": "habit-milestone",
        "require_interaction": "false",
    },
    "welcome": {
        "title": "Welcome to Luqi AI! 👋",
        "body": "Thanks for enabling notifications. We'll keep you updated on your progress.",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=dashboard",
        "tag": "welcome",
        "require_interaction": "false",
    },
    "weekly_report": {
        "title": "Your Weekly Report 📈",
        "body": "You completed {completed_habits} habits this week. View your full report!",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=analytics",
        "tag": "weekly-report",
        "require_interaction": "false",
    },
    "subscription_expiring": {
        "title": "Subscription Expiring Soon",
        "body": "Your plan expires in {days_left} days. Renew to keep uninterrupted access.",
        "icon": ICON_DEFAULT,
        "badge": BADGE_DEFAULT,
        "url": "/?page=subscription",
        "tag": "subscription-expiring",
        "require_interaction": "true",
    },
}

# ---------------------------------------------------------------------------
# VAPID Key Management
# ---------------------------------------------------------------------------

_cached_vapid_keys: Optional[Dict[str, str]] = None
_vapid_lock = threading.Lock()


def generate_vapid_keys() -> Dict[str, str]:
    """Generate a fresh VAPID key pair for Web Push.

    Uses ``py-vapid`` when available, otherwise falls back to the
    ``cryptography`` library to produce an ECDSA P-256 key pair.

    Returns:
        ``{"public_key": "<base64>", "private_key": "<base64>"}``
    """
    if _HAS_PY_VAPID:
        vapid = Vapid()
        vapid.generate_keys()
        return {
            "public_key": vapid.public_key,
            "private_key": vapid.private_key,
        }

    if not _HAS_CRYPTOGRAPHY:
        raise RuntimeError(
            "Cannot generate VAPID keys: install py-vapid or cryptography"
        )

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    return {
        "public_key": base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("="),
        "private_key": base64.urlsafe_b64encode(private_bytes).decode("ascii").rstrip("="),
    }


def _load_or_generate_vapid_keys() -> Dict[str, str]:
    """Load VAPID keys from environment or generate and cache them."""
    global _cached_vapid_keys

    if _cached_vapid_keys is not None:
        return _cached_vapid_keys

    with _vapid_lock:
        if _cached_vapid_keys is not None:
            return _cached_vapid_keys

        pub = os.environ.get("VAPID_PUBLIC_KEY")
        prv = os.environ.get("VAPID_PRIVATE_KEY")

        if pub and prv:
            _cached_vapid_keys = {"public_key": pub, "private_key": prv}
            logger.info("Loaded VAPID keys from environment")
        else:
            _cached_vapid_keys = generate_vapid_keys()
            logger.info("Generated new VAPID key pair")

        return _cached_vapid_keys


def get_vapid_public_key() -> str:
    """Return the VAPID public key (for the frontend ``applicationServerKey``)."""
    return _load_or_generate_vapid_keys()["public_key"]


def get_vapid_private_key() -> str:
    """Return the VAPID private key (for signing push requests)."""
    return _load_or_generate_vapid_keys()["private_key"]


# ---------------------------------------------------------------------------
# Push Subscription Manager
# ---------------------------------------------------------------------------

class PushSubscriptionManager:
    """Persist and query Web Push subscriptions per user.

    Subscriptions are stored in a local SQLite database with the following
    schema (see :meth:`_init_db` for the full DDL).
    """

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._init_db()

    # ------------------------------------------------------------------ #
    # Connection helpers
    # ------------------------------------------------------------------ #
    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection."""
        if not hasattr(self._local, "db") or self._local.db is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._local.db = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._local.db.row_factory = sqlite3.Row
            self._local.db.execute("PRAGMA journal_mode=WAL")
            self._local.db.execute("PRAGMA foreign_keys=ON")
        return self._local.db

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        ddl_subscriptions = """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                endpoint    TEXT NOT NULL,
                p256dh      TEXT NOT NULL,
                auth        TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent  TEXT,
                platform    TEXT DEFAULT 'web',
                is_active   INTEGER DEFAULT 1
            )
        """
        ddl_schedules = """
            CREATE TABLE IF NOT EXISTS notification_schedules (
                id                TEXT PRIMARY KEY,
                user_id           TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                cron_expression   TEXT,
                hour              INTEGER,
                minute            INTEGER,
                days_of_week      TEXT,
                data_json         TEXT,
                is_active         INTEGER DEFAULT 1,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run_at       TIMESTAMP,
                next_run_at       TIMESTAMP
            )
        """
        ddl_sent_log = """
            CREATE TABLE IF NOT EXISTS notification_sent_log (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                template    TEXT NOT NULL,
                endpoint    TEXT,
                status      TEXT NOT NULL,
                error_msg   TEXT,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        with self._conn() as conn:
            conn.execute(ddl_subscriptions)
            conn.execute(ddl_schedules)
            conn.execute(ddl_sent_log)
            # Indexes for fast lookups
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subs_user ON push_subscriptions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subs_endpoint ON push_subscriptions(endpoint)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sched_user ON notification_schedules(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sched_next ON notification_schedules(next_run_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_log_user ON notification_sent_log(user_id, sent_at)"
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Subscription CRUD
    # ------------------------------------------------------------------ #
    def subscribe(self, user_id: str, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Save (or reactivate) a push subscription for *user_id*.

        Args:
            user_id: opaque user identifier.
            subscription: dict with ``endpoint`` and ``keys`` containing
                ``p256dh`` and ``auth``.

        Returns:
            ``{"success": True, "subscription_id": "<uuid>"}``
        """
        if not user_id or not subscription:
            return {"success": False, "error": "Missing user_id or subscription"}

        endpoint = subscription.get("endpoint", "").strip()
        keys = subscription.get("keys", {})
        p256dh = keys.get("p256dh", "").strip()
        auth = keys.get("auth", "").strip()

        if not endpoint or not p256dh or not auth:
            return {"success": False, "error": "Invalid subscription payload"}

        sub_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with self._conn() as conn:
            # Upsert — if the endpoint already exists for this user, reactivate it
            row = conn.execute(
                "SELECT id FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
                (user_id, endpoint),
            ).fetchone()

            if row:
                conn.execute(
                    """
                    UPDATE push_subscriptions
                       SET p256dh = ?, auth = ?, is_active = 1, updated_at = ?
                     WHERE id = ?
                    """,
                    (p256dh, auth, now, row["id"]),
                )
                sub_id = row["id"]
            else:
                conn.execute(
                    """
                    INSERT INTO push_subscriptions
                        (id, user_id, endpoint, p256dh, auth, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sub_id, user_id, endpoint, p256dh, auth, now, now),
                )
            conn.commit()

        logger.info("User %s subscribed — endpoint %s…", user_id, endpoint[:60])
        return {"success": True, "subscription_id": sub_id}

    def unsubscribe(self, user_id: str, endpoint: str) -> Dict[str, Any]:
        """Soft-delete a push subscription.

        Returns:
            ``{"success": True, "removed": <int>}``
        """
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE push_subscriptions SET is_active = 0 WHERE user_id = ? AND endpoint = ?",
                (user_id, endpoint),
            )
            conn.commit()

        logger.info("User %s unsubscribed — %s row(s) deactivated", user_id, cur.rowcount)
        return {"success": True, "removed": cur.rowcount}

    def remove_subscription(self, user_id: str, endpoint: str) -> Dict[str, Any]:
        """Hard-delete a subscription (use when endpoint returns 410 Gone)."""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
                (user_id, endpoint),
            )
            conn.commit()
        return {"success": True, "removed": cur.rowcount}

    def get_subscriptions(
        self, user_id: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Return subscription dicts for *user_id*, or all if omitted."""
        query = "SELECT * FROM push_subscriptions WHERE 1=1"
        params: List[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY created_at DESC"

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "endpoint": r["endpoint"],
                "keys": {"p256dh": r["p256dh"], "auth": r["auth"]},
                "created_at": r["created_at"],
                "platform": r["platform"],
                "is_active": bool(r["is_active"]),
            }
            for r in rows
        ]

    def is_subscribed(self, user_id: str) -> bool:
        """Return ``True`` if *user_id* has at least one active subscription."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM push_subscriptions WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (user_id,),
            ).fetchone()
        return row is not None

    def get_user_count(self) -> int:
        """Return the number of distinct users with active subscriptions."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT user_id) AS cnt FROM push_subscriptions WHERE is_active = 1"
            ).fetchone()
        return row["cnt"] if row else 0

    def get_subscription_count(self) -> int:
        """Return the total number of active subscriptions."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM push_subscriptions WHERE is_active = 1"
            ).fetchone()
        return row["cnt"] if row else 0

    def deactivate_expired(self, max_age_days: int = 90) -> int:
        """Soft-delete subscriptions older than *max_age_days*."""
        cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE push_subscriptions SET is_active = 0 WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
        logger.info("Deactivated %s expired subscription(s)", cur.rowcount)
        return cur.rowcount

    # ------------------------------------------------------------------ #
    # Sent-log helpers (for analytics & debugging)
    # ------------------------------------------------------------------ #
    def log_sent(
        self,
        user_id: str,
        template: str,
        endpoint: Optional[str],
        status: str,
        error_msg: Optional[str] = None,
    ) -> None:
        """Record a send attempt in the notification log."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO notification_sent_log (id, user_id, template, endpoint, status, error_msg)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, template, endpoint, status, error_msg),
            )
            conn.commit()

    def get_recent_logs(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent notification send logs."""
        query = "SELECT * FROM notification_sent_log WHERE 1=1"
        params: List[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY sent_at DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Push Sender
# ---------------------------------------------------------------------------

def _build_vapid_claims(endpoint: str) -> Dict[str, Any]:
    """Build VAPID JWT claims for the given endpoint."""
    parsed = endpoint.split("/")
    # The audience is the origin of the push service (e.g., https://fcm.googleapis.com)
    audience = "https://" + parsed[2] if len(parsed) > 2 else VAPID_SUBJECT
    return {
        "sub": VAPID_SUBJECT,
        "aud": audience,
        "exp": int(time.time()) + 12 * 3600,  # 12-hour expiry
    }


def send_push(
    subscription: Dict[str, Any],
    payload: Dict[str, Any],
    ttl: int = 3600,
    urgency: str = "normal",
) -> Dict[str, Any]:
    """Send a single Web Push notification.

    Args:
        subscription: dict with ``endpoint`` and ``keys`` (``p256dh``, ``auth``).
        payload: notification body — may contain ``title``, ``body``, ``icon``,
            ``badge``, ``url``, ``actions``, ``tag``, etc.
        ttl: Time-To-Live in seconds (how long the push service may retry).
        urgency: ``"normal"`` or ``"high"``.

    Returns:
        ``{"success": bool, "status_code": int, "error": str|None}``
    """
    endpoint = subscription.get("endpoint", "")
    if not endpoint:
        return {"success": False, "status_code": 0, "error": "Missing endpoint"}

    # Enrich payload with timestamp
    payload["timestamp"] = int(time.time() * 1000)

    # ------------------------------------------------------------------ #
    # Real implementation via pywebpush
    # ------------------------------------------------------------------ #
    if _HAS_PYWEBPUSH:
        try:
            vapid_claims = _build_vapid_claims(endpoint)
            response = webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=get_vapid_private_key(),
                vapid_claims=vapid_claims,
                ttl=ttl,
                urgency=urgency,
            )
            return {
                "success": True,
                "status_code": getattr(response, "status_code", 201),
                "error": None,
            }
        except WebPushException as exc:
            status = getattr(exc, "status_code", 0)
            # 410 Gone or 404 Not Found → subscription is dead
            if status in (404, 410):
                logger.warning("Subscription expired (HTTP %s): %s…", status, endpoint[:60])
            else:
                logger.error("Push failed (HTTP %s): %s", status, exc)
            return {"success": False, "status_code": status, "error": str(exc)}
        except Exception as exc:
            logger.error("Unexpected push error: %s", exc)
            return {"success": False, "status_code": 0, "error": str(exc)}

    # ------------------------------------------------------------------ #
    # Mock / development fallback
    # ------------------------------------------------------------------ #
    logger.info(
        "[MOCK PUSH] endpoint=%s… title=%s",
        endpoint[:60],
        payload.get("title", "(no title)"),
    )
    return {"success": True, "status_code": 201, "error": None, "mock": True}


def broadcast_push(
    user_ids: List[str],
    payload: Dict[str, Any],
    manager: Optional[PushSubscriptionManager] = None,
) -> Dict[str, Any]:
    """Send a push notification to every active subscription of *user_ids*.

    Returns:
        ``{"sent": int, "failed": int, "errors": List[str]}``
    """
    mgr = manager or PushSubscriptionManager()
    sent = 0
    failed = 0
    errors: List[str] = []

    for uid in user_ids:
        subs = mgr.get_subscriptions(user_id=uid, active_only=True)
        if not subs:
            logger.debug("No active subscriptions for user %s", uid)
            continue

        for sub in subs:
            result = send_push(sub, payload)
            if result["success"]:
                sent += 1
            else:
                failed += 1
                err = result.get("error", "unknown")
                errors.append(f"{uid}: {err}")

                # Auto-remove dead subscriptions
                if result.get("status_code") in (404, 410):
                    mgr.remove_subscription(uid, sub["endpoint"])

    logger.info("Broadcast complete — sent=%s failed=%s", sent, failed)
    return {"sent": sent, "failed": failed, "errors": errors}


def send_to_all(
    payload: Dict[str, Any], manager: Optional[PushSubscriptionManager] = None
) -> Dict[str, Any]:
    """Broadcast a push notification to **all** active subscribers.

    Returns:
        ``{"sent": int, "failed": int, "errors": List[str]}``
    """
    mgr = manager or PushSubscriptionManager()
    all_subs = mgr.get_subscriptions(active_only=True)

    sent = 0
    failed = 0
    errors: List[str] = []

    # Group by user so we don't duplicate sends to the same person
    seen_users: set = set()
    for sub in all_subs:
        uid = sub["user_id"]
        if uid in seen_users:
            continue
        seen_users.add(uid)

        user_subs = mgr.get_subscriptions(user_id=uid, active_only=True)
        for us in user_subs:
            result = send_push(us, payload)
            if result["success"]:
                sent += 1
            else:
                failed += 1
                err = result.get("error", "unknown")
                errors.append(f"{uid}: {err}")
                if result.get("status_code") in (404, 410):
                    mgr.remove_subscription(uid, us["endpoint"])

    logger.info("Global broadcast — sent=%s failed=%s", sent, failed)
    return {"sent": sent, "failed": failed, "errors": errors}


# ---------------------------------------------------------------------------
# Notification Template Renderer
# ---------------------------------------------------------------------------

def render_notification(template_name: str, **kwargs: Any) -> Dict[str, Any]:
    """Render a notification template, substituting ``{variable}`` placeholders.

    Args:
        template_name: key in :data:`NOTIFICATION_TEMPLATES`.
        **kwargs: values for template variables.

    Returns:
        Dict with ``title``, ``body``, ``icon``, ``url``, and any other
        keys defined in the template.
    """
    tmpl = NOTIFICATION_TEMPLATES.get(template_name)
    if tmpl is None:
        raise ValueError(f"Unknown template '{template_name}'. Available: {list(NOTIFICATION_TEMPLATES)}")

    rendered: Dict[str, Any] = {}
    for key, val in tmpl.items():
        if isinstance(val, str):
            try:
                rendered[key] = val.format(**kwargs)
            except KeyError as exc:
                raise ValueError(f"Missing template variable {exc} for '{template_name}.{key}'") from None
        else:
            rendered[key] = val

    # Inject actions if provided
    if "actions" in kwargs:
        rendered["actions"] = kwargs["actions"]

    return rendered


# ---------------------------------------------------------------------------
# Scheduled Notifications
# ---------------------------------------------------------------------------

class NotificationScheduler:
    """Store and evaluate recurring notification schedules.

    The scheduler uses a simple cron-like model (hour + minute + days_of_week).
    Call :meth:`check_and_send` every minute (e.g., from a background thread
    or external cron job) to evaluate and fire due schedules.
    """

    def __init__(self, manager: Optional[PushSubscriptionManager] = None) -> None:
        self.manager = manager or PushSubscriptionManager()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Schedule creation
    # ------------------------------------------------------------------ #
    def _create_schedule(
        self,
        user_id: str,
        notification_type: str,
        hour: int,
        minute: int,
        days: Optional[List[int]] = None,
        data_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert a schedule row and return its metadata."""
        sched_id = str(uuid.uuid4())
        now = datetime.utcnow()
        next_run = self._next_occurrence(hour, minute, days, now)

        days_str = ",".join(str(d) for d in days) if days else None

        with self.manager._conn() as conn:
            conn.execute(
                """
                INSERT INTO notification_schedules
                    (id, user_id, notification_type, hour, minute, days_of_week, data_json, next_run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sched_id, user_id, notification_type, hour, minute, days_str, data_json, next_run.isoformat()),
            )
            conn.commit()

        logger.info(
            "Scheduled '%s' for user %s at %02d:%02d (next: %s)",
            notification_type,
            user_id,
            hour,
            minute,
            next_run.isoformat(timespec="minutes"),
        )
        return {
            "schedule_id": sched_id,
            "user_id": user_id,
            "type": notification_type,
            "hour": hour,
            "minute": minute,
            "days": days,
            "next_run_at": next_run.isoformat(),
        }

    def schedule_daily_digest(
        self, user_id: str, hour: int = 9, minute: int = 0
    ) -> Dict[str, Any]:
        """Schedule a daily digest notification at the given local time."""
        return self._create_schedule(
            user_id=user_id,
            notification_type="daily_digest",
            hour=hour,
            minute=minute,
            days=list(range(7)),  # every day
            data_json=json.dumps({"template": "daily_digest"}),
        )

    def schedule_habit_reminder(
        self,
        user_id: str,
        habit_name: str,
        hour: int,
        days: List[int],
        minute: int = 0,
    ) -> Dict[str, Any]:
        """Schedule a recurring habit reminder.

        Args:
            user_id: target user.
            habit_name: human-readable habit name.
            hour: 0-23 local hour.
            days: list of weekday integers (Monday=0 … Sunday=6).
            minute: 0-59 local minute.
        """
        return self._create_schedule(
            user_id=user_id,
            notification_type="habit_reminder",
            hour=hour,
            minute=minute,
            days=days,
            data_json=json.dumps({"template": "habit_reminder", "habit_name": habit_name}),
        )

    def schedule_learning_reminder(
        self,
        user_id: str,
        topic: str,
        hour: int = 18,
        days: Optional[List[int]] = None,
        minute: int = 0,
    ) -> Dict[str, Any]:
        """Schedule a learning reminder for a specific topic."""
        days = days or list(range(7))
        return self._create_schedule(
            user_id=user_id,
            notification_type="learning_reminder",
            hour=hour,
            minute=minute,
            days=days,
            data_json=json.dumps({"template": "learning_reminder", "topic": topic}),
        )

    def schedule_weekly_report(
        self, user_id: str, day: int = 6, hour: int = 9, minute: int = 0
    ) -> Dict[str, Any]:
        """Schedule a weekly report on a specific day (default Sunday)."""
        return self._create_schedule(
            user_id=user_id,
            notification_type="weekly_report",
            hour=hour,
            minute=minute,
            days=[day],
            data_json=json.dumps({"template": "weekly_report"}),
        )

    # ------------------------------------------------------------------ #
    # Schedule evaluation & sending
    # ------------------------------------------------------------------ #
    @staticmethod
    def _next_occurrence(
        hour: int, minute: int, days: Optional[List[int]], after: datetime
    ) -> datetime:
        """Calculate the next datetime matching the schedule constraints."""
        candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(days=1)

        if days is None:
            return candidate

        # Ensure candidate weekday is in allowed days
        allowed = set(days)
        for _ in range(14):  # safety bound
            if candidate.weekday() in allowed:
                return candidate
            candidate += timedelta(days=1)

        return candidate  # pragma: no cover

    def check_and_send(self) -> Dict[str, Any]:
        """Evaluate all active schedules and send notifications that are due.

        Should be invoked periodically — e.g., once per minute via a
        background thread or an external cron / APScheduler job.

        Returns:
            ``{"checked": int, "sent": int, "failed": int}``
        """
        now = datetime.utcnow().isoformat()
        with self.manager._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notification_schedules
                 WHERE is_active = 1
                   AND next_run_at <= ?
                """,
                (now,),
            ).fetchall()

        sent_total = 0
        failed_total = 0

        for row in rows:
            result = self._execute_schedule(row)
            sent_total += result.get("sent", 0)
            failed_total += result.get("failed", 0)

        return {"checked": len(rows), "sent": sent_total, "failed": failed_total}

    def _execute_schedule(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Send the notification for a single due schedule and update next_run."""
        sched_id = row["id"]
        user_id = row["user_id"]
        data = json.loads(row["data_json"] or "{}")
        template_name = data.get("template", "daily_digest")

        # Build payload from template
        try:
            kwargs = {k: v for k, v in data.items() if k != "template"}
            # Inject dynamic values for certain templates
            if template_name == "daily_digest":
                kwargs["message_count"] = kwargs.get("message_count", "several")
            elif template_name == "habit_reminder":
                kwargs["streak"] = kwargs.get("streak", 0)
            elif template_name == "learning_reminder":
                pass  # topic already in kwargs
            elif template_name == "weekly_report":
                kwargs["completed_habits"] = kwargs.get("completed_habits", "many")

            payload = render_notification(template_name, **kwargs)
        except ValueError as exc:
            logger.error("Schedule %s template error: %s", sched_id, exc)
            self._bump_next_run(row)
            return {"sent": 0, "failed": 1}

        # Send
        subs = self.manager.get_subscriptions(user_id=user_id, active_only=True)
        sent = 0
        failed = 0
        for sub in subs:
            result = send_push(sub, payload)
            if result["success"]:
                sent += 1
                self.manager.log_sent(user_id, template_name, sub["endpoint"], "sent")
            else:
                failed += 1
                self.manager.log_sent(
                    user_id, template_name, sub["endpoint"], "failed", result.get("error")
                )
                if result.get("status_code") in (404, 410):
                    self.manager.remove_subscription(user_id, sub["endpoint"])

        # Update next run time
        self._bump_next_run(row)
        return {"sent": sent, "failed": failed}

    def _bump_next_run(self, row: sqlite3.Row) -> None:
        """Recalculate and store the next occurrence for a schedule."""
        days_str = row["days_of_week"]
        days = [int(d) for d in days_str.split(",")] if days_str else None
        next_run = self._next_occurrence(row["hour"], row["minute"], days, datetime.utcnow())
        with self.manager._conn() as conn:
            conn.execute(
                """
                UPDATE notification_schedules
                   SET last_run_at = ?, next_run_at = ?
                 WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), next_run.isoformat(), row["id"]),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Schedule management
    # ------------------------------------------------------------------ #
    def cancel_schedule(self, user_id: str, notification_type: str) -> Dict[str, Any]:
        """Deactivate all schedules of *notification_type* for *user_id*."""
        with self.manager._conn() as conn:
            cur = conn.execute(
                """
                UPDATE notification_schedules
                   SET is_active = 0
                 WHERE user_id = ? AND notification_type = ?
                """,
                (user_id, notification_type),
            )
            conn.commit()
        logger.info(
            "Cancelled %s schedule(s) for user %s (type=%s)",
            cur.rowcount,
            user_id,
            notification_type,
        )
        return {"success": True, "cancelled": cur.rowcount}

    def get_schedules(
        self, user_id: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Return schedule rows."""
        query = "SELECT * FROM notification_schedules WHERE 1=1"
        params: List[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY next_run_at ASC"

        with self.manager._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Background thread runner (optional convenience)
    # ------------------------------------------------------------------ #
    def start_background(self, interval_seconds: int = 60) -> None:
        """Start a daemon thread that calls :meth:`check_and_send` periodically."""
        if self._running:
            logger.warning("Scheduler background thread already running")
            return

        self._running = True

        def _loop() -> None:
            logger.info("Notification scheduler started (interval=%ss)", interval_seconds)
            while self._running:
                try:
                    result = self.check_and_send()
                    if result["checked"]:
                        logger.info("Scheduler tick: %s", result)
                except Exception:
                    logger.exception("Scheduler tick failed")
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True, name="luqi-scheduler")
        self._thread.start()

    def stop_background(self) -> None:
        """Signal the background thread to stop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None


# ---------------------------------------------------------------------------
# Event-Triggered Notification Helpers
# ---------------------------------------------------------------------------

def _send_to_user(
    user_id: str, template_name: str, manager: Optional[PushSubscriptionManager] = None, **kwargs: Any
) -> Dict[str, Any]:
    """Internal helper — render a template and push to a single user's devices."""
    mgr = manager or PushSubscriptionManager()
    try:
        payload = render_notification(template_name, **kwargs)
    except ValueError as exc:
        return {"success": False, "sent": 0, "error": str(exc)}

    subs = mgr.get_subscriptions(user_id=user_id, active_only=True)
    if not subs:
        return {"success": False, "sent": 0, "error": "No active subscriptions"}

    sent = 0
    failed = 0
    for sub in subs:
        result = send_push(sub, payload)
        if result["success"]:
            sent += 1
            mgr.log_sent(user_id, template_name, sub["endpoint"], "sent")
        else:
            failed += 1
            mgr.log_sent(user_id, template_name, sub["endpoint"], "failed", result.get("error"))
            if result.get("status_code") in (404, 410):
                mgr.remove_subscription(user_id, sub["endpoint"])

    return {"success": sent > 0, "sent": sent, "failed": failed}


def notify_usage_warning(
    user_id: str, percent_used: float, manager: Optional[PushSubscriptionManager] = None
) -> Dict[str, Any]:
    """Send a usage warning when the user is approaching their daily limit.

    Args:
        user_id: target user.
        percent_used: 0.0 – 100.0.
        manager: optional :class:`PushSubscriptionManager` instance.
    """
    if percent_used >= 100:
        return _send_to_user(
            user_id, "usage_exceeded", manager, percent=int(percent_used)
        )
    return _send_to_user(
        user_id, "usage_warning", manager, percent=int(percent_used)
    )


def notify_habit_streak(
    user_id: str,
    habit_name: str,
    streak: int,
    manager: Optional[PushSubscriptionManager] = None,
) -> Dict[str, Any]:
    """Celebrate a habit streak milestone.

    Milestones are triggered at 7, 14, 21, 30, 60, 90, 180, 365 days.
    """
    MILESTONES = {7, 14, 21, 30, 60, 90, 180, 365}
    if streak not in MILESTONES:
        # Still send a regular habit reminder for non-milestones
        return _send_to_user(
            user_id, "habit_reminder", manager, habit_name=habit_name, streak=streak
        )

    return _send_to_user(
        user_id, "habit_milestone", manager, habit_name=habit_name, streak=streak
    )


def notify_new_feature(
    user_ids: List[str],
    feature_name: str,
    description: str,
    manager: Optional[PushSubscriptionManager] = None,
) -> Dict[str, Any]:
    """Announce a new feature to a list of users."""
    payload = render_notification(
        "feature_announcement", feature_name=feature_name, feature_description=description
    )
    return broadcast_push(user_ids, payload, manager=manager)


def notify_welcome(
    user_id: str, manager: Optional[PushSubscriptionManager] = None
) -> Dict[str, Any]:
    """Send a welcome notification to a newly-subscribed user."""
    return _send_to_user(user_id, "welcome", manager)


def notify_learning_reminder(
    user_id: str, topic: str, manager: Optional[PushSubscriptionManager] = None
) -> Dict[str, Any]:
    """Send a learning reminder for a specific topic."""
    return _send_to_user(user_id, "learning_reminder", manager, topic=topic)


def notify_subscription_expiring(
    user_id: str, days_left: int, manager: Optional[PushSubscriptionManager] = None
) -> Dict[str, Any]:
    """Warn a user that their subscription is expiring soon."""
    return _send_to_user(
        user_id, "subscription_expiring", manager, days_left=days_left
    )


# ---------------------------------------------------------------------------
# Service Health / Stats
# ---------------------------------------------------------------------------

def get_notification_stats(
    manager: Optional[PushSubscriptionManager] = None,
) -> Dict[str, Any]:
    """Return aggregate statistics about the notification system.

    Useful for health-check endpoints and admin dashboards.
    """
    mgr = manager or PushSubscriptionManager()
    with mgr._conn() as conn:
        total_subs = conn.execute(
            "SELECT COUNT(*) AS c FROM push_subscriptions WHERE is_active = 1"
        ).fetchone()["c"]
        total_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS c FROM push_subscriptions WHERE is_active = 1"
        ).fetchone()["c"]
        total_schedules = conn.execute(
            "SELECT COUNT(*) AS c FROM notification_schedules WHERE is_active = 1"
        ).fetchone()["c"]
        sent_today = conn.execute(
            """
            SELECT COUNT(*) AS c FROM notification_sent_log
             WHERE sent_at >= date('now')
            """
        ).fetchone()["c"]
        failed_today = conn.execute(
            """
            SELECT COUNT(*) AS c FROM notification_sent_log
             WHERE sent_at >= date('now') AND status = 'failed'
            """
        ).fetchone()["c"]

    return {
        "subscriptions_active": total_subs,
        "users_with_subscriptions": total_users,
        "schedules_active": total_schedules,
        "sent_today": sent_today,
        "failed_today": failed_today,
        "pywebpush_available": _HAS_PYWEBPUSH,
        "vapid_subject": VAPID_SUBJECT,
    }


# ---------------------------------------------------------------------------
# CLI / Smoke Test
# ---------------------------------------------------------------------------

def _cli_smoke_test() -> None:
    """Run a quick smoke-test of the notification system."""
    print("=" * 60)
    print("Luqi AI — Push Notification System Smoke Test")
    print("=" * 60)

    # 1. VAPID keys
    print("\n--- VAPID Keys ---")
    pub = get_vapid_public_key()
    prv = get_vapid_private_key()
    print(f"Public  : {pub[:40]}…")
    print(f"Private : {prv[:40]}…")

    # 2. Subscription manager
    print("\n--- Subscription Manager ---")
    mgr = PushSubscriptionManager()
    test_sub = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-123",
        "keys": {
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls",
            "auth": "tBHItJI5svbzx7ucdBiaAw",
        },
    }
    result = mgr.subscribe("user-42", test_sub)
    print(f"subscribe() → {result}")
    print(f"is_subscribed('user-42') → {mgr.is_subscribed('user-42')}")
    subs = mgr.get_subscriptions(user_id="user-42")
    print(f"get_subscriptions() → {len(subs)} row(s)")

    # 3. Template rendering
    print("\n--- Template Rendering ---")
    rendered = render_notification("habit_reminder", habit_name="drink water", streak=5)
    print(f"habit_reminder → {rendered}")

    # 4. Mock push send
    print("\n--- Push Sender ---")
    result = send_push(test_sub, rendered)
    print(f"send_push() → {result}")

    # 5. Scheduler
    print("\n--- Scheduler ---")
    sched = NotificationScheduler(manager=mgr)
    sched.schedule_daily_digest("user-42", hour=9, minute=0)
    sched.schedule_habit_reminder("user-42", "drink water", hour=8, days=[0, 1, 2, 3, 4])
    print(f"Active schedules: {len(sched.get_schedules(user_id='user-42'))}")

    # 6. Event triggers
    print("\n--- Event Triggers ---")
    print(f"notify_usage_warning(75%) → {_send_to_user('user-42', 'usage_warning', mgr, percent=75)}")
    print(f"notify_habit_streak(7) → {notify_habit_streak('user-42', 'drink water', 7, mgr)}")

    # 7. Stats
    print("\n--- Stats ---")
    print(json.dumps(get_notification_stats(mgr), indent=2))

    # Cleanup
    mgr.remove_subscription("user-42", test_sub["endpoint"])
    sched.cancel_schedule("user-42", "daily_digest")
    sched.cancel_schedule("user-42", "habit_reminder")
    print("\nSmoke test complete ✓")


if __name__ == "__main__":
    _cli_smoke_test()
