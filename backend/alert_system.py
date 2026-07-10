#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — Alert & Notification System
==============================================
Multi-channel alerting with cascading fallback.

Features:
  - Discord webhook notifications
  - Slack webhook notifications
  - Persistent alert log file (JSON Lines format)
  - Alert acknowledgment system
  - Rate limiting to prevent spam
  - GET /api/system/alerts endpoint
  - POST /api/system/alerts/ack endpoint
  - POST /api/system/alerts/resolve endpoint
  - GET /api/system/alerts/history endpoint

Environment Variables:
    DISCORD_WEBHOOK_URL: Discord webhook URL (optional)
    SLACK_WEBHOOK_URL: Slack webhook URL (optional)
    ALERT_LOG_PATH: Path to alerts.jsonl (default: ./data/alerts.jsonl)

Usage:
    >>> from alert_system import AlertSystem, AlertSeverity
    >>> alerts = AlertSystem()
    >>> alerts.trigger_alert(AlertSeverity.CRITICAL, "Orchestrator", "DB Down", "Connection lost")
    >>> alerts.register_endpoints(app)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.alert_system")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AlertSeverity(str, Enum):
    """Severity levels for system alerts."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertStatus(str, Enum):
    """Lifecycle states of an alert."""

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class SystemAlert:
    """Represents a single system alert notification.

    Attributes:
        id: Unique identifier (UUID4).
        timestamp: ISO-8601 UTC timestamp when the alert was created.
        severity: Alert severity level.
        agent_name: Name of the agent that triggered the alert.
        title: Short alert title.
        message: Detailed alert message.
        status: Current lifecycle status of the alert.
        metadata: Optional key-value metadata dictionary.
    """

    id: str
    timestamp: str
    severity: AlertSeverity
    agent_name: str
    title: str
    message: str
    status: AlertStatus
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize alert to a plain dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "agent_name": self.agent_name,
            "title": self.title,
            "message": self.message,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemAlert":
        """Deserialize a dictionary into a SystemAlert instance."""
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            severity=AlertSeverity(data.get("severity", "MEDIUM")),
            agent_name=data["agent_name"],
            title=data["title"],
            message=data["message"],
            status=AlertStatus(data.get("status", "ACTIVE")),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Pydantic request models for FastAPI endpoints
# ---------------------------------------------------------------------------
class AckAlertRequest(BaseModel):
    """Request body for acknowledging an alert."""

    alert_id: str


class ResolveAlertRequest(BaseModel):
    """Request body for resolving an alert."""

    alert_id: str


# ---------------------------------------------------------------------------
# AlertSystem (Singleton)
# ---------------------------------------------------------------------------
class AlertSystem:
    """Centralised alert manager with multi-channel notification support.

    This class is implemented as a singleton so that all parts of the
    Luqi AI backend share a single alert queue and persistent log.

    Example:
        >>> alert_sys = AlertSystem()
        >>> alert_sys.trigger_critical_alert(
        ...     agent_name="DataAgent",
        ...     error_payload={"error": "DB connection timeout"},
        ...     details="Retry #3 failed"
        ... )
    """

    _instance: Optional["AlertSystem"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "AlertSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Webhook configuration (optional — system works without them)
        self._discord_webhook_url: Optional[str] = os.environ.get("DISCORD_WEBHOOK_URL")
        self._slack_webhook_url: Optional[str] = os.environ.get("SLACK_WEBHOOK_URL")

        # Persistent log path
        self._alert_log_path: Path = Path(
            os.environ.get("ALERT_LOG_PATH", "./data/alerts.jsonl")
        )
        self._alert_log_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory alert storage
        self._alerts: List[SystemAlert] = []
        self._alerts_lock: threading.Lock = threading.Lock()

        # Rate-limiting: track last alert time per (severity, agent, title) hash
        self._rate_limit_map: Dict[str, float] = {}
        self._rate_limit_window: int = 60  # seconds
        self._rate_limit_max: int = 3  # max alerts per window per key

        # HTTP client for webhook requests
        self._http_client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10),
        )

        # Load persisted alerts on startup
        self._load_persisted_alerts()

        self._initialized = True
        logger.info(
            "AlertSystem initialized — discord=%s slack=%s log=%s",
            "yes" if self._discord_webhook_url else "no",
            "yes" if self._slack_webhook_url else "no",
            self._alert_log_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trigger_critical_alert(
        self,
        agent_name: str,
        error_payload: Dict[str, Any],
        details: str = "",
    ) -> SystemAlert:
        """Create and dispatch a CRITICAL alert to all channels.

        This is the primary entry-point for agents that encounter fatal
        or unrecoverable errors.

        Args:
            agent_name: Name of the agent reporting the error.
            error_payload: Raw error data (e.g. exception dict).
            details: Human-readable context string.

        Returns:
            The created SystemAlert instance.
        """
        message = json.dumps(error_payload, ensure_ascii=False, default=str)
        if details:
            message = f"{details}\n\n{message}"

        return self.trigger_alert(
            severity=AlertSeverity.CRITICAL,
            agent_name=agent_name,
            title=f"CRITICAL: {agent_name} failure",
            message=message,
            metadata={"error_payload": error_payload, "details": details},
        )

    def trigger_alert(
        self,
        severity: AlertSeverity,
        agent_name: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SystemAlert:
        """Create a general alert and dispatch to all configured channels.

        Args:
            severity: Severity level of the alert.
            agent_name: Name of the originating agent.
            title: Short alert title.
            message: Detailed message body.
            metadata: Optional key-value metadata.

        Returns:
            The created SystemAlert instance.
        """
        alert = SystemAlert(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            agent_name=agent_name,
            title=title,
            message=message,
            status=AlertStatus.ACTIVE,
            metadata=metadata or {},
        )

        # Rate-limit check (non-blocking; skips notifications but still persists)
        if not self._check_rate_limit(alert):
            logger.warning("Alert rate-limited: %s — %s", agent_name, title)
            return alert

        with self._alerts_lock:
            self._alerts.append(alert)

        # Persist locally (never fails)
        self._persist_alert(alert)

        # Send to external channels (best-effort, never raise)
        if severity == AlertSeverity.CRITICAL:
            self._send_all_channels(alert)
        elif severity in (AlertSeverity.HIGH,):
            self._send_all_channels(alert)
        else:
            logger.info("Alert logged locally (severity=%s): %s", severity.value, title)

        return alert

    def acknowledge_alert(self, alert_id: str) -> SystemAlert:
        """Mark an alert as acknowledged.

        Args:
            alert_id: UUID of the alert to acknowledge.

        Returns:
            The updated SystemAlert.

        Raises:
            ValueError: If the alert_id is not found.
        """
        with self._alerts_lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    self._persist_alert(alert)
                    logger.info("Alert acknowledged: %s", alert_id)
                    return alert
        raise ValueError(f"Alert not found: {alert_id}")

    def resolve_alert(self, alert_id: str) -> SystemAlert:
        """Mark an alert as resolved.

        Args:
            alert_id: UUID of the alert to resolve.

        Returns:
            The updated SystemAlert.

        Raises:
            ValueError: If the alert_id is not found.
        """
        with self._alerts_lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.status = AlertStatus.RESOLVED
                    self._persist_alert(alert)
                    logger.info("Alert resolved: %s", alert_id)
                    return alert
        raise ValueError(f"Alert not found: {alert_id}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Return all alerts that are ACTIVE or ACKNOWLEDGED.

        Returns:
            List of alert dictionaries.
        """
        with self._alerts_lock:
            return [
                alert.to_dict()
                for alert in self._alerts
                if alert.status in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED)
            ]

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent alerts regardless of status.

        Args:
            limit: Maximum number of alerts to return (default 50).

        Returns:
            List of alert dictionaries, most recent first.
        """
        with self._alerts_lock:
            sorted_alerts = sorted(
                self._alerts,
                key=lambda a: a.timestamp,
                reverse=True,
            )
            return [alert.to_dict() for alert in sorted_alerts[:limit]]

    # ------------------------------------------------------------------
    # Internal: Channel dispatch
    # ------------------------------------------------------------------

    def _send_all_channels(self, alert: SystemAlert) -> None:
        """Dispatch alert to Discord and Slack concurrently (best-effort)."""
        try:
            asyncio.create_task(self._send_discord_async(alert))
        except RuntimeError:
            # No running event loop — fire a background thread
            threading.Thread(
                target=self._send_discord_sync,
                args=(alert,),
                daemon=True,
            ).start()

        try:
            asyncio.create_task(self._send_slack_async(alert))
        except RuntimeError:
            threading.Thread(
                target=self._send_slack_sync,
                args=(alert,),
                daemon=True,
            ).start()

    async def _send_discord_async(self, alert: SystemAlert) -> None:
        """Async wrapper for Discord dispatch."""
        await self._send_discord(alert)

    async def _send_slack_async(self, alert: SystemAlert) -> None:
        """Async wrapper for Slack dispatch."""
        await self._send_slack(alert)

    def _send_discord_sync(self, alert: SystemAlert) -> None:
        """Synchronous fallback for Discord dispatch."""
        try:
            asyncio.run(self._send_discord(alert))
        except Exception:
            pass

    def _send_slack_sync(self, alert: SystemAlert) -> None:
        """Synchronous fallback for Slack dispatch."""
        try:
            asyncio.run(self._send_slack(alert))
        except Exception:
            pass

    async def _send_discord(self, alert: SystemAlert) -> None:
        """Send alert to Discord webhook.

        Args:
            alert: The alert to send.
        """
        if not self._discord_webhook_url:
            return

        color_map = {
            AlertSeverity.CRITICAL: 0xFF0000,  # Red
            AlertSeverity.HIGH: 0xFF8C00,  # Dark orange
            AlertSeverity.MEDIUM: 0xFFD700,  # Gold
            AlertSeverity.LOW: 0x00BFFF,  # Deep sky blue
        }

        embed = {
            "title": alert.title,
            "description": alert.message[:2048],  # Discord limit
            "color": color_map.get(alert.severity, 0x808080),
            "timestamp": alert.timestamp,
            "fields": [
                {"name": "Severity", "value": alert.severity.value, "inline": True},
                {"name": "Agent", "value": alert.agent_name, "inline": True},
                {"name": "Status", "value": alert.status.value, "inline": True},
                {"name": "Alert ID", "value": alert.id, "inline": False},
            ],
            "footer": {"text": "Luqi AI Alert System v24.4.0"},
        }

        payload = {
            "username": "Luqi AI Alert Bot",
            "avatar_url": (
                "https://cdn-icons-png.flaticon.com/512/2954/2954870.png"
            ),
            "embeds": [embed],
        }

        try:
            response = await self._http_client.post(
                self._discord_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code not in (200, 204):
                logger.warning(
                    "Discord webhook returned %d: %s",
                    response.status_code,
                    response.text[:200],
                )
            else:
                logger.info("Alert sent to Discord: %s", alert.id)
        except Exception as exc:
            logger.error("Failed to send Discord alert %s: %s", alert.id, exc)

    async def _send_slack(self, alert: SystemAlert) -> None:
        """Send alert to Slack webhook.

        Args:
            alert: The alert to send.
        """
        if not self._slack_webhook_url:
            return

        color_map = {
            AlertSeverity.CRITICAL: "#FF0000",
            AlertSeverity.HIGH: "#FF8C00",
            AlertSeverity.MEDIUM: "#FFD700",
            AlertSeverity.LOW: "#00BFFF",
        }

        payload = {
            "text": f"*{alert.severity.value}* alert from *{alert.agent_name}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"[{alert.severity.value}] {alert.title}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity.value}"},
                        {"type": "mrkdwn", "text": f"*Agent:*\n{alert.agent_name}"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{alert.status.value}"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{alert.timestamp}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Message:*\n{alert.message[:2000]}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Alert ID: `{alert.id}` | Luqi AI v24.4.0"}
                    ],
                },
            ],
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#808080"),
                    "fallback": f"{alert.severity.value}: {alert.title}",
                }
            ],
        }

        try:
            response = await self._http_client.post(
                self._slack_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code != 200:
                logger.warning(
                    "Slack webhook returned %d: %s",
                    response.status_code,
                    response.text[:200],
                )
            else:
                logger.info("Alert sent to Slack: %s", alert.id)
        except Exception as exc:
            logger.error("Failed to send Slack alert %s: %s", alert.id, exc)

    # ------------------------------------------------------------------
    # Internal: Persistence (JSON Lines)
    # ------------------------------------------------------------------

    def _persist_alert(self, alert: SystemAlert) -> None:
        """Append an alert to the persistent JSONL log.

        This operation is atomic and never raises — the alert is written
        to a temporary file and then renamed to avoid corruption.

        Args:
            alert: The alert to persist.
        """
        try:
            line = json.dumps(alert.to_dict(), ensure_ascii=False, default=str)
            with open(self._alert_log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except Exception as exc:
            logger.error("Failed to persist alert %s: %s", alert.id, exc)

    def _load_persisted_alerts(self) -> None:
        """Load historical alerts from the JSONL log on startup.

        Malformed lines are skipped with a warning rather than crashing.
        """
        if not self._alert_log_path.exists():
            logger.info("No persisted alert log found at %s", self._alert_log_path)
            return

        loaded = 0
        skipped = 0
        try:
            with open(self._alert_log_path, "r", encoding="utf-8") as fh:
                for line_num, raw_line in enumerate(fh, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        alert = SystemAlert.from_dict(data)
                        self._alerts.append(alert)
                        loaded += 1
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.warning(
                            "Skipping malformed alert log line %d: %s",
                            line_num,
                            exc,
                        )
                        skipped += 1
        except Exception as exc:
            logger.error("Failed to load persisted alerts: %s", exc)

        logger.info(
            "Loaded %d persisted alerts (%d skipped)",
            loaded,
            skipped,
        )

    # ------------------------------------------------------------------
    # Internal: Rate limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self, alert: SystemAlert) -> bool:
        """Return True if the alert is within the allowed rate limit.

        The rate-limit key is ``severity:agent_name:title_hash``.

        Args:
            alert: The alert to check.
        """
        key = f"{alert.severity.value}:{alert.agent_name}:{hash(alert.title) % 10000}"
        now = time.time()
        last_times = [
            ts for ts in [self._rate_limit_map.get(key, 0)]
            if now - ts < self._rate_limit_window
        ]

        # Count how many alerts in the current window
        count = sum(
            1
            for ts in self._rate_limit_map.values()
            if now - ts < self._rate_limit_window
        )
        # Per-key limit check
        key_count = sum(
            1
            for k, ts in self._rate_limit_map.items()
            if k.startswith(f"{alert.severity.value}:{alert.agent_name}")
            and now - ts < self._rate_limit_window
        )

        if key_count >= self._rate_limit_max:
            return False

        self._rate_limit_map[key] = now
        return True

    # ------------------------------------------------------------------
    # FastAPI endpoint registration
    # ------------------------------------------------------------------

    def register_endpoints(self, app_or_router: FastAPI | APIRouter) -> None:
        """Register FastAPI endpoints for alert management.

        Args:
            app_or_router: A FastAPI application or APIRouter instance.
        """
        router = APIRouter(prefix="/api/system", tags=["Alerts"])

        @router.get("/alerts", summary="Get active alerts")
        async def get_active_alerts_endpoint() -> Dict[str, Any]:
            """Return all currently active (non-resolved) alerts."""
            return {
                "status": "ok",
                "count": len(self.get_active_alerts()),
                "alerts": self.get_active_alerts(),
            }

        @router.get("/alerts/history", summary="Get alert history")
        async def get_alert_history_endpoint(
            limit: int = 50,
        ) -> Dict[str, Any]:
            """Return recent alert history regardless of status.

            Args:
                limit: Maximum number of alerts to return.
            """
            return {
                "status": "ok",
                "count": min(limit, len(self._alerts)),
                "alerts": self.get_alert_history(limit=limit),
            }

        @router.post("/alerts/ack", summary="Acknowledge an alert")
        async def acknowledge_alert_endpoint(
            request: AckAlertRequest,
        ) -> Dict[str, Any]:
            """Mark an alert as acknowledged.

            Args:
                request: Contains the alert_id to acknowledge.

            Raises:
                HTTPException 404: If the alert is not found.
            """
            try:
                alert = self.acknowledge_alert(request.alert_id)
                return {"status": "ok", "alert": alert.to_dict()}
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc))

        @router.post("/alerts/resolve", summary="Resolve an alert")
        async def resolve_alert_endpoint(
            request: ResolveAlertRequest,
        ) -> Dict[str, Any]:
            """Mark an alert as resolved.

            Args:
                request: Contains the alert_id to resolve.

            Raises:
                HTTPException 404: If the alert is not found.
            """
            try:
                alert = self.resolve_alert(request.alert_id)
                return {"status": "ok", "alert": alert.to_dict()}
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc))

        # Register with app/router
        if isinstance(app_or_router, FastAPI):
            app_or_router.include_router(router)
        else:
            app_or_router.include_router(router)

        logger.info("AlertSystem endpoints registered on /api/system/alerts*")


# ---------------------------------------------------------------------------
# Standalone convenience function
# ---------------------------------------------------------------------------

def register_alert_endpoints(app_or_router: FastAPI | APIRouter) -> None:
    """Register alert endpoints using the global AlertSystem singleton.

    This is a convenience wrapper so callers don't need to instantiate
    AlertSystem directly if they just want the endpoints.

    Args:
        app_or_router: A FastAPI application or APIRouter instance.
    """
    alert_sys = AlertSystem()
    alert_sys.register_endpoints(app_or_router)
