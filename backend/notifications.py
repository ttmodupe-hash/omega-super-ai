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