#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Email Alert System
=====================================
SMTP-based email notifications as a fallback when Discord/Slack
webhooks are not configured or fail.

Features:
  - SMTP with TLS encryption
  - HTML-formatted alert emails
  - Rate limiting (max 1 email per 5 minutes per alert type)
  - Configurable via environment variables
  - Beautiful HTML email templates for critical alerts
  - Plain text fallback for non-HTML clients

Part of Luqi AI v24.5.0 by Limitless Telecoms

Environment Variables:
    SMTP_HOST: SMTP server hostname (e.g., smtp.gmail.com)
    SMTP_PORT: SMTP port (default: 587)
    SMTP_USER: Username/email for SMTP authentication
    SMTP_PASSWORD: Password or app-specific password
    ALERT_FROM_EMAIL: Sender address (default: luqi-ai@limitlesstelecoms.com)
    ALERT_TO_EMAIL: Recipient address(es), comma-separated for multiple
    SMTP_ENABLED: Set to "true" to enable (default: false)

Example:
    >>> from email_alerts import EmailAlertSystem
    >>> alerts = EmailAlertSystem()
    >>> if alerts.is_configured():
    ...     alerts.send_critical_alert(
    ...         agent_name="DataProcessor",
    ...         error_payload={"error": "Connection timeout"},
    ...         details="Database connection failed after 3 retries"
    ...     )
"""

from __future__ import annotations

import email.mime.multipart
import email.mime.text
import json
import logging
import os
import py_compile
import smtplib
import ssl
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger: logging.Logger = logging.getLogger("luqi_ai.email_alerts")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SMTP_PORT: int = 587
DEFAULT_FROM_EMAIL: str = "luqi-ai@limitlesstelecoms.com"
RATE_LIMIT_SECONDS: int = 300  # 5 minutes
LUQI_VERSION: str = "24.5.0"
COMPANY_NAME: str = "Limitless Telecoms"

# Brand colors for HTML templates
COLOR_CRITICAL: str = "#DC2626"  # red-600
COLOR_WARNING: str = "#F59E0B"  # amber-500
COLOR_INFO: str = "#3B82F6"  # blue-500
COLOR_SUCCESS: str = "#10B981"  # emerald-500
COLOR_DARK_BG: str = "#0F172A"  # slate-900
COLOR_CARD_BG: str = "#1E293B"  # slate-800
COLOR_TEXT: str = "#E2E8F0"  # slate-200
COLOR_MUTED: str = "#94A3B8"  # slate-400
COLOR_ACCENT: str = "#8B5CF6"  # violet-500


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class AlertPayload:
    """Structured representation of an alert."""

    agent_name: str
    error_payload: dict[str, Any]
    details: str
    severity: str = "critical"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alert_type: str = "critical_alert"

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "error_payload": self.error_payload,
            "details": self.details,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "alert_type": self.alert_type,
        }


# ---------------------------------------------------------------------------
# Email Alert System (Singleton)
# ---------------------------------------------------------------------------
class EmailAlertSystem:
    """Singleton email alert system for Luqi AI.

    Provides SMTP-based email notifications with TLS encryption,
    rate limiting, and professional HTML templates.

    Usage:
        >>> alert_sys = EmailAlertSystem()
        >>> alert_sys.send_critical_alert("Agent", {"err": "x"}, "details")
    """

    _instance: EmailAlertSystem | None = None
    _lock: threading.Lock = threading.Lock()

    # Rate limit tracking: alert_type -> last_sent_timestamp
    _rate_limit_map: dict[str, float]
    _rate_limit_lock: threading.Lock

    def __new__(cls) -> EmailAlertSystem:
        """Ensure singleton behaviour."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialise the email alert system from environment variables."""
        if self._initialized:
            return

        self.smtp_host: str | None = os.environ.get("SMTP_HOST") or None
        self.smtp_port: int = int(
            os.environ.get("SMTP_PORT", str(DEFAULT_SMTP_PORT))
        )
        self.smtp_user: str | None = os.environ.get("SMTP_USER") or None
        self.smtp_password: str | None = os.environ.get("SMTP_PASSWORD") or None
        self.from_email: str = (
            os.environ.get("ALERT_FROM_EMAIL") or DEFAULT_FROM_EMAIL
        )
        self.to_emails: list[str] = self._parse_to_emails(
            os.environ.get("ALERT_TO_EMAIL", "")
        )
        self.enabled: bool = os.environ.get("SMTP_ENABLED", "false").lower() == "true"

        self._rate_limit_map = {}
        self._rate_limit_lock = threading.Lock()
        self._initialized = True

        logger.info(
            "EmailAlertSystem initialised — enabled=%s, host=%s, port=%d, "
            "recipients=%d",
            self.enabled,
            self.smtp_host or "<not set>",
            self.smtp_port,
            len(self.to_emails),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_to_emails(raw: str) -> list[str]:
        """Parse comma-separated email addresses into a clean list.

        Args:
            raw: Raw comma-separated email string.

        Returns:
            List of validated email addresses.
        """
        if not raw.strip():
            return []
        emails: list[str] = [e.strip() for e in raw.split(",") if e.strip()]
        # Basic sanity check — must contain '@'
        valid: list[str] = [e for e in emails if "@" in e]
        if len(valid) != len(emails):
            logger.warning(
                "Filtered out %d invalid email address(es)",
                len(emails) - len(valid),
            )
        return valid

    def _is_rate_limited(self, alert_type: str) -> bool:
        """Check if an alert type is currently rate-limited.

        Rate limit: max 1 email per 5 minutes per alert type.

        Args:
            alert_type: Identifier for the alert category.

        Returns:
            True if this alert type should be suppressed.
        """
        with self._rate_limit_lock:
            now = time.monotonic()
            last_sent = self._rate_limit_map.get(alert_type)
            if last_sent is not None and (now - last_sent) < RATE_LIMIT_SECONDS:
                remaining = int(RATE_LIMIT_SECONDS - (now - last_sent))
                logger.debug(
                    "Rate limit active for '%s' — %ds remaining",
                    alert_type,
                    remaining,
                )
                return True
            self._rate_limit_map[alert_type] = now
            return False

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and return an SMTP connection object.

        Returns:
            An unconnected smtplib.SMTP instance.

        Raises:
            RuntimeError: If required SMTP configuration is missing.
        """
        if not self.smtp_host:
            raise RuntimeError("SMTP_HOST is not configured")
        return smtplib.SMTP(self.smtp_host, self.smtp_port)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        """Return whether the email alert system is properly configured.

        Checks that all required SMTP settings are present and valid.

        Returns:
            True if SMTP is enabled and all required fields are set.
        """
        return (
            self.enabled
            and self.smtp_host is not None
            and self.smtp_user is not None
            and self.smtp_password is not None
            and len(self.to_emails) > 0
        )

    def test_connection(self) -> bool:
        """Verify the SMTP connection works without sending an email.

        Establishes a TLS connection, authenticates, and immediately
        disconnects.  Useful for health checks.

        Returns:
            True if the connection and authentication succeeded.
        """
        if not self.is_configured():
            logger.warning("SMTP not configured — skipping connection test")
            return False

        try:
            with self._create_smtp_connection() as server:
                server.ehlo()
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                logger.info("SMTP connection test successful for %s", self.smtp_host)
                return True
        except smtplib.SMTPAuthenticationError:
            logger.warning("SMTP authentication failed for %s", self.smtp_host)
            return False
        except smtplib.SMTPConnectError:
            logger.warning("Could not connect to SMTP server %s", self.smtp_host)
            return False
        except OSError as exc:
            logger.warning("Network error testing SMTP: %s", exc)
            return False
        except Exception as exc:
            logger.warning(
                "Unexpected error testing SMTP connection: %s",
                exc,
                exc_info=True,
            )
            return False

    def send_critical_alert(
        self,
        agent_name: str,
        error_payload: dict[str, Any],
        details: str,
    ) -> bool:
        """Send a critical alert email.

        Builds a beautiful HTML email with alert details and sends it via
        SMTP with TLS.  Rate-limited to max 1 per 5 minutes per alert type.

        Args:
            agent_name: Name of the agent that raised the alert.
            error_payload: Structured error data (serialisable dict).
            details: Human-readable description of the issue.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.debug("SMTP not configured — dropping critical alert")
            return False

        alert = AlertPayload(
            agent_name=agent_name,
            error_payload=error_payload,
            details=details,
            severity="critical",
            alert_type=f"critical_{agent_name}",
        )

        # Rate-limit check
        if self._is_rate_limited(alert.alert_type):
            logger.info(
                "Critical alert for '%s' suppressed by rate limit",
                agent_name,
            )
            return False

        subject = (
            f"[CRITICAL] Luqi AI — Agent '{agent_name}' Alert "
            f"({alert.timestamp.strftime('%H:%M:%S UTC')})"
        )
        html_body = self._build_html_email(alert)
        text_body = self._build_text_email(alert)

        return self._send_smtp(
            to=self.to_emails,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_status_report(
        self,
        metrics: dict[str, Any] | None = None,
        active_alerts: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send a daily/weekly system status summary email.

        Args:
            metrics: Optional system metrics dictionary.
            active_alerts: Optional list of currently active alerts.

        Returns:
            True if the report was sent successfully.
        """
        if not self.is_configured():
            logger.debug("SMTP not configured — dropping status report")
            return False

        now = datetime.now(timezone.utc)
        alert_type = "status_report"

        if self._is_rate_limited(alert_type):
            logger.info("Status report suppressed by rate limit")
            return False

        metrics = metrics or {}
        active_alerts = active_alerts or []

        subject = f"Luqi AI Status Report — {now.strftime('%Y-%m-%d %H:%M UTC')}"
        html_body = self._build_status_html(now, metrics, active_alerts)
        text_body = self._build_status_text(now, metrics, active_alerts)

        return self._send_smtp(
            to=self.to_emails,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    # ------------------------------------------------------------------
    # Email builders
    # ------------------------------------------------------------------
    def _build_html_email(self, alert: AlertPayload) -> str:
        """Build a professional HTML email body for a critical alert.

        Args:
            alert: The alert payload to render.

        Returns:
            HTML string suitable for multipart MIME.
        """
        severity_color = COLOR_CRITICAL if alert.severity == "critical" else COLOR_WARNING
        json_payload = json.dumps(alert.error_payload, indent=2, default=str)
        timestamp_str = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luqi AI Alert</title>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_DARK_BG};font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{COLOR_TEXT};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:{COLOR_DARK_BG};">
        <tr>
            <td align="center" style="padding:40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:{COLOR_CARD_BG};border-radius:12px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.3);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,{COLOR_ACCENT},#6366F1);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;font-size:28px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Luqi AI</h1>
                            <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);letter-spacing:2px;text-transform:uppercase;">Autonomous Multi-Agent System</p>
                        </td>
                    </tr>
                    <!-- Severity Badge -->
                    <tr>
                        <td style="padding:24px 40px 0;text-align:center;">
                            <span style="display:inline-block;background-color:{severity_color};color:#FFFFFF;padding:8px 24px;border-radius:9999px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">
                                {alert.severity.upper()} ALERT
                            </span>
                        </td>
                    </tr>
                    <!-- Timestamp -->
                    <tr>
                        <td style="padding:12px 40px 0;text-align:center;">
                            <p style="margin:0;font-size:13px;color:{COLOR_MUTED};">{timestamp_str}</p>
                        </td>
                    </tr>
                    <!-- Agent Name -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <h2 style="margin:0;font-size:20px;font-weight:600;color:#FFFFFF;">Agent: <span style="color:{COLOR_ACCENT};">{self._escape_html(alert.agent_name)}</span></h2>
                        </td>
                    </tr>
                    <!-- Details -->
                    <tr>
                        <td style="padding:16px 40px 0;">
                            <p style="margin:0;font-size:15px;line-height:1.7;color:{COLOR_TEXT};">{self._escape_html(alert.details)}</p>
                        </td>
                    </tr>
                    <!-- Error Payload -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <p style="margin:0 0 8px;font-size:11px;color:{COLOR_MUTED};text-transform:uppercase;letter-spacing:1px;font-weight:600;">Error Payload</p>
                            <pre style="margin:0;background-color:#0F172A;padding:16px;border-radius:8px;font-size:13px;line-height:1.5;color:#A5B4FC;overflow-x:auto;border:1px solid #334155;">{self._escape_html(json_payload)}</pre>
                        </td>
                    </tr>
                    <!-- Divider -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <hr style="border:0;border-top:1px solid #334155;margin:0;">
                        </td>
                    </tr>
                    <!-- Metadata -->
                    <tr>
                        <td style="padding:16px 40px 32px;">
                            <p style="margin:0;font-size:12px;color:{COLOR_MUTED};">
                                Alert Type: <strong style="color:{COLOR_TEXT};">{alert.alert_type}</strong> &nbsp;|&nbsp;
                                Severity: <strong style="color:{severity_color};">{alert.severity.upper()}</strong>
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#0F172A;padding:20px 40px;text-align:center;border-top:1px solid #334155;">
                            <p style="margin:0;font-size:12px;color:{COLOR_MUTED};">
                                Luqi AI v{LUQI_VERSION} by {COMPANY_NAME}<br>
                                <span style="font-size:11px;">This is an automated alert. Please do not reply.</span>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _build_text_email(self, alert: AlertPayload) -> str:
        """Build a plain-text fallback email body.

        Args:
            alert: The alert payload to render.

        Returns:
            Plain-text string for non-HTML mail clients.
        """
        json_payload = json.dumps(alert.error_payload, indent=2, default=str)
        timestamp_str = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"""\
====================================================================
  Luqi AI — {alert.severity.upper()} ALERT
  Autonomous Multi-Agent System
====================================================================

Timestamp : {timestamp_str}
Agent     : {alert.agent_name}
Severity  : {alert.severity.upper()}
Type      : {alert.alert_type}

--------------------------------------------------------------------
DETAILS
--------------------------------------------------------------------
{alert.details}

--------------------------------------------------------------------
ERROR PAYLOAD
--------------------------------------------------------------------
{json_payload}

====================================================================
Luqi AI v{LUQI_VERSION} by {COMPANY_NAME}
Automated alert — do not reply.
====================================================================
"""

    def _build_status_html(
        self,
        timestamp: datetime,
        metrics: dict[str, Any],
        active_alerts: list[dict[str, Any]],
    ) -> str:
        """Build HTML body for a status report email.

        Args:
            timestamp: Report generation time.
            metrics: System metrics dictionary.
            active_alerts: List of active alerts.

        Returns:
            HTML string for the status report.
        """
        metrics_rows = ""
        for key, value in metrics.items():
            metrics_rows += (
                f'<tr style="border-bottom:1px solid #334155;">'
                f'<td style="padding:10px 0;font-size:14px;color:{COLOR_MUTED};">'
                f'{self._escape_html(key)}</td>'
                f'<td style="padding:10px 0;text-align:right;font-size:14px;color:#FFFFFF;font-weight:600;">'
                f'{self._escape_html(str(value))}</td></tr>'
            )
        if not metrics_rows:
            metrics_rows = (
                f'<tr><td colspan="2" style="padding:16px 0;text-align:center;color:{COLOR_MUTED};font-size:14px;">'
                f'No metrics available</td></tr>'
            )

        alerts_html = ""
        if active_alerts:
            for alert in active_alerts:
                agent = self._escape_html(str(alert.get("agent", "Unknown")))
                msg = self._escape_html(str(alert.get("message", "N/A")))
                sev = str(alert.get("severity", "info")).lower()
                sev_color = {
                    "critical": COLOR_CRITICAL,
                    "warning": COLOR_WARNING,
                    "info": COLOR_INFO,
                }.get(sev, COLOR_INFO)
                alerts_html += (
                    f'<div style="background-color:#0F172A;padding:12px 16px;border-radius:8px;margin-bottom:8px;'
                    f'border-left:4px solid {sev_color};">'
                    f'<p style="margin:0;font-size:13px;font-weight:600;color:#FFFFFF;">{agent}</p>'
                    f'<p style="margin:4px 0 0;font-size:12px;color:{COLOR_MUTED};">{msg}</p></div>'
                )
        else:
            alerts_html = (
                f'<p style="text-align:center;color:{COLOR_MUTED};font-size:14px;">'
                f'All systems operational — no active alerts.</p>'
            )

        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luqi AI Status Report</title>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_DARK_BG};font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{COLOR_TEXT};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:{COLOR_DARK_BG};">
        <tr>
            <td align="center" style="padding:40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%;background-color:{COLOR_CARD_BG};border-radius:12px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.3);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,{COLOR_ACCENT},#6366F1);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;font-size:28px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Luqi AI</h1>
                            <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);letter-spacing:2px;text-transform:uppercase;">System Status Report</p>
                        </td>
                    </tr>
                    <!-- Timestamp -->
                    <tr>
                        <td style="padding:24px 40px 0;text-align:center;">
                            <span style="display:inline-block;background-color:{COLOR_SUCCESS};color:#FFFFFF;padding:8px 24px;border-radius:9999px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">
                                {timestamp.strftime('%Y-%m-%d %H:%M UTC')}
                            </span>
                        </td>
                    </tr>
                    <!-- Metrics -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <h3 style="margin:0 0 12px;font-size:16px;font-weight:600;color:#FFFFFF;">System Metrics</h3>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                {metrics_rows}
                            </table>
                        </td>
                    </tr>
                    <!-- Active Alerts -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <h3 style="margin:0 0 12px;font-size:16px;font-weight:600;color:#FFFFFF;">
                                Active Alerts ({len(active_alerts)})
                            </h3>
                            {alerts_html}
                        </td>
                    </tr>
                    <!-- Divider -->
                    <tr>
                        <td style="padding:24px 40px 0;">
                            <hr style="border:0;border-top:1px solid #334155;margin:0;">
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#0F172A;padding:20px 40px;text-align:center;border-top:1px solid #334155;">
                            <p style="margin:0;font-size:12px;color:{COLOR_MUTED};">
                                Luqi AI v{LUQI_VERSION} by {COMPANY_NAME}<br>
                                <span style="font-size:11px;">Automated status report — do not reply.</span>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _build_status_text(
        self,
        timestamp: datetime,
        metrics: dict[str, Any],
        active_alerts: list[dict[str, Any]],
    ) -> str:
        """Build plain-text status report.

        Args:
            timestamp: Report generation time.
            metrics: System metrics dictionary.
            active_alerts: List of active alerts.

        Returns:
            Plain-text string for the status report.
        """
        lines = [
            "=" * 66,
            "  Luqi AI — System Status Report",
            "  Autonomous Multi-Agent System",
            "=" * 66,
            "",
            f"Report Time : {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "-" * 66,
            "  SYSTEM METRICS",
            "-" * 66,
        ]
        if metrics:
            for key, value in metrics.items():
                lines.append(f"  {key:<30} {value}")
        else:
            lines.append("  No metrics available.")
        lines.extend([
            "",
            "-" * 66,
            f"  ACTIVE ALERTS ({len(active_alerts)})",
            "-" * 66,
        ])
        if active_alerts:
            for alert in active_alerts:
                agent = alert.get("agent", "Unknown")
                msg = alert.get("message", "N/A")
                sev = alert.get("severity", "info").upper()
                lines.append(f"  [{sev}] {agent}: {msg}")
        else:
            lines.append("  All systems operational — no active alerts.")
        lines.extend([
            "",
            "=" * 66,
            f"  Luqi AI v{LUQI_VERSION} by {COMPANY_NAME}",
            "  Automated status report — do not reply.",
            "=" * 66,
        ])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # SMTP sender
    # ------------------------------------------------------------------
    def _send_smtp(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send an email via SMTP with TLS encryption.

        Constructs a multipart MIME message with both HTML and plain-text
        parts, then dispatches it through the configured SMTP server.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            html_body: HTML version of the email body.
            text_body: Plain-text version for fallback.

        Returns:
            True if the message was accepted by the SMTP server.
        """
        if not to:
            logger.warning("No recipient addresses — skipping email send")
            return False

        try:
            msg = email.mime.multipart.MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to)
            msg["X-Mailer"] = f"LuqiAI-EmailAlert/{LUQI_VERSION}"
            msg["X-Priority"] = "1"  # High priority for alerts

            # Attach plain-text part first (fallback)
            part_text = email.mime.text.MIMEText(text_body, "plain", "utf-8")
            msg.attach(part_text)

            # Attach HTML part
            part_html = email.mime.text.MIMEText(html_body, "html", "utf-8")
            msg.attach(part_html)

            with self._create_smtp_connection() as server:
                server.ehlo()
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                # Password is never logged
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())
                logger.info(
                    "Email sent successfully to %d recipient(s): subject=%r",
                    len(to),
                    subject,
                )
                return True

        except smtplib.SMTPRecipientsRefused as exc:
            logger.warning("All recipients refused: %s", exc)
            return False
        except smtplib.SMTPHeloError as exc:
            logger.warning("SMTP HELO error: %s", exc)
            return False
        except smtplib.SMTPSenderRefused as exc:
            logger.warning("SMTP sender refused: %s", exc)
            return False
        except smtplib.SMTPDataError as exc:
            logger.warning("SMTP data error: %s", exc)
            return False
        except smtplib.SMTPAuthenticationError:
            # Never log the password
            logger.warning("SMTP authentication failed for user=%s", self.smtp_user)
            return False
        except smtplib.SMTPConnectError as exc:
            logger.warning("SMTP connection error: %s", exc)
            return False
        except smtplib.SMTPException as exc:
            logger.warning("SMTP error sending email: %s", exc)
            return False
        except OSError as exc:
            logger.warning("Network/OS error sending email: %s", exc)
            return False
        except Exception as exc:
            logger.warning(
                "Unexpected error sending email: %s",
                exc,
                exc_info=True,
            )
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters to prevent injection.

        Args:
            text: Raw text that may contain HTML characters.

        Returns:
            Escaped string safe for HTML inclusion.
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


# ---------------------------------------------------------------------------
# Convenience module-level functions
# ---------------------------------------------------------------------------

def send_critical_alert(
    agent_name: str,
    error_payload: dict[str, Any],
    details: str,
) -> bool:
    """Module-level convenience wrapper for sending a critical alert.

    Args:
        agent_name: Name of the agent that raised the alert.
        error_payload: Structured error data.
        details: Human-readable description.

    Returns:
        True if the email was sent successfully.
    """
    return EmailAlertSystem().send_critical_alert(agent_name, error_payload, details)


def send_status_report(
    metrics: dict[str, Any] | None = None,
    active_alerts: list[dict[str, Any]] | None = None,
) -> bool:
    """Module-level convenience wrapper for sending a status report.

    Args:
        metrics: Optional system metrics.
        active_alerts: Optional active alerts list.

    Returns:
        True if the report was sent successfully.
    """
    return EmailAlertSystem().send_status_report(metrics, active_alerts)


# ---------------------------------------------------------------------------
# Self-test / sanity check
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run a quick sanity check on the module (no network required)."""
    logging.basicConfig(level=logging.DEBUG, format="%(name)s [%(levelname)s] %(message)s")

    # 1. Singleton check
    a1 = EmailAlertSystem()
    a2 = EmailAlertSystem()
    assert a1 is a2, "Singleton failed"
    print("[PASS] Singleton pattern")

    # 2. Not configured by default
    assert not a1.is_configured(), "Should not be configured without env vars"
    print("[PASS] Not configured by default")

    # 3. HTML escaping
    assert a1._escape_html("<script>") == "&lt;script&gt;"
    print("[PASS] HTML escaping")

    # 4. Build HTML email (no send)
    alert = AlertPayload(
        agent_name="TestAgent",
        error_payload={"code": 500, "message": "DB timeout"},
        details="Connection pool exhausted after 60s",
    )
    html = a1._build_html_email(alert)
    assert "TestAgent" in html
    assert "DB timeout" in html
    assert "DOCTYPE html" in html
    print("[PASS] HTML email generation")

    # 5. Build text email (no send)
    text = a1._build_text_email(alert)
    assert "TestAgent" in text
    assert "DB timeout" in text
    print("[PASS] Text email generation")

    # 6. Rate limiting
    a1._rate_limit_map.clear()
    assert not a1._is_rate_limited("test_type")
    assert a1._is_rate_limited("test_type")  # Should be limited now
    print("[PASS] Rate limiting")

    # 7. Parse to_emails
    assert a1._parse_to_emails("a@b.com, c@d.com ") == ["a@b.com", "c@d.com"]
    assert a1._parse_to_emails("") == []
    assert a1._parse_to_emails("invalid, ok@test.com") == ["ok@test.com"]
    print("[PASS] Email parsing")

    # 8. Status report builders
    html_report = a1._build_status_html(
        datetime.now(timezone.utc),
        {"cpu": "45%", "memory": "1.2GB"},
        [{"agent": "X", "message": "Y", "severity": "warning"}],
    )
    assert "System Metrics" in html_report
    text_report = a1._build_status_text(
        datetime.now(timezone.utc),
        {"cpu": "45%"},
        [],
    )
    assert "cpu" in text_report
    print("[PASS] Status report generation")

    print("\nAll self-tests passed.")


if __name__ == "__main__":
    _self_test()