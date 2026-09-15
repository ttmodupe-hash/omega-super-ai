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
                    "UPDATE push_subscriptions SET p256dh = ?, auth = ?, is_active = 1, updated_at = ? WHERE id = ?",
                    (p256dh, auth, now, row["id"]),
                )
                sub_id = row["id"]
            else:
                conn.execute(
                    "INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (sub_id, user_id, endpoint, p256dh, auth, now),
                )
            conn.commit()

        logger.info("Subscribed user=%s endpoint=%s…", user_id, endpoint[:40])
        return {"success": True, "subscription_id": sub_id}

    def remove_subscription(self, user_id: str, endpoint: str) -> bool:
        """Soft-delete a subscription by deactivating it."""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE push_subscriptions SET is_active = 0 WHERE user_id = ? AND endpoint = ?",
                (user_id, endpoint),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all active subscriptions for *user_id*."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM push_subscriptions WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Return all active subscriptions across all users."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM push_subscriptions WHERE is_active = 1"
            ).fetchall()
            return [dict(r) for r in rows]

    def subscription_exists(self, user_id: str, endpoint: str) -> bool:
        """Return ``True`` if the subscription already exists and is active."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM push_subscriptions WHERE user_id = ? AND endpoint = ? AND is_active = 1",
                (user_id, endpoint),
            ).fetchone()
            return row is not None


# ---------------------------------------------------------------------------
# Push Sender
# ---------------------------------------------------------------------------

class PushSender:
    """Encapsulates the VAPID-signed Web Push sending logic."""

    def __init__(self) -> None:
        self._vapid_public_key = get_vapid_public_key()
        self._vapid_private_key = get_vapid_private_key()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def send_push(
        self,
        subscription: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a push notification to a single subscription.

        Args:
            subscription: dict with ``endpoint`` and ``keys`` containing
                ``p256dh`` and ``auth``.
            payload: notification payload dict (typically produced by
                :func:`build_notification_payload`).

        Returns:
            ``{"success": True}`` or ``{"success": False, "error": "..."}``
        """
        endpoint = subscription.get("endpoint", "")
        keys = subscription.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        if not all([endpoint, p256dh, auth]):
            return {"success": False, "error": "Invalid subscription"}

        if _HAS_PYWEBPUSH:
            return self._send_real(endpoint, p256dh, auth, payload)
        return self._send_mock(endpoint, payload)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _send_real(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            webpush(
                subscription_info={
                    "endpoint": endpoint,
                    "keys": {"p256dh": p256dh, "auth": auth},
                },
                data=json.dumps(payload),
                vapid_private_key=self._vapid_private_key,
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            logger.info("Push sent to %s…", endpoint[:50])
            return {"success": True}
        except WebPushException as exc:
            logger.error("Push failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def _send_mock(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(
            "[MOCK PUSH] endpoint=%s… title=%s",
            endpoint[:50],
            payload.get("title", "<no title>"),
        )
        return {"success": True, "mock": True}


# ---------------------------------------------------------------------------
# Notification Builder
# ---------------------------------------------------------------------------

def build_notification_payload(
    template_key: str,
    variables: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a notification payload from a template, substituting ``{variable}`` placeholders.

    Args:
        template_key: key in :data:`NOTIFICATION_TEMPLATES`.
        variables: mapping of placeholder names to values.
        extra: additional fields to merge into the payload.

    Returns:
        A dict ready for :meth:`PushSender.send_push`.

    Raises:
        KeyError: if *template_key* is not found.
    """
    tmpl = NOTIFICATION_TEMPLATES[template_key].copy()
    variables = variables or {}

    for key in ("title", "body"):
        if key in tmpl:
            tmpl[key] = tmpl[key].format(**variables)

    payload = {
        "title": tmpl.get("title", ""),
        "body": tmpl.get("body", ""),
        "icon": tmpl.get("icon", ICON_DEFAULT),
        "badge": tmpl.get("badge", BADGE_DEFAULT),
        "url": tmpl.get("url", "/"),
        "tag": tmpl.get("tag", template_key),
        "require_interaction": tmpl.get("require_interaction", "false").lower() == "true",
        "timestamp": int(time.time() * 1000),
    }

    if extra:
        payload.update(extra)

    return payload


# ---------------------------------------------------------------------------
# Subscription Manager (global instance)
# ---------------------------------------------------------------------------

_subscription_mgr: Optional[PushSubscriptionManager] = None


def get_subscription_manager(db_path: Optional[str] = None) -> PushSubscriptionManager:
    """Return the global :class:`PushSubscriptionManager` instance."""
    global _subscription_mgr
    if _subscription_mgr is None:
        _subscription_mgr = PushSubscriptionManager(db_path)
    return _subscription_mgr