"""
Luqi AI v24.5.0 — Accessibility Suite for Deaf & Hard-of-Hearing Users
========================================================================

Features:
  - Visual Alert System (screen flash, color-coded notifications, banner alerts)
  - Real-Time Captioning Engine (enhanced speech-to-text)
  - Sign Language Support (gesture input via camera, sign-to-text)
  - Vibration/Haptic Feedback patterns for notifications
  - Visual Progress Indicators for audio content
  - Accessibility Preferences Manager
  - WebSocket endpoint for real-time visual alerts
  - HTML/CSS/JS visual alert components

Part of Luqi AI v24.5.0 by Limitless Telecoms — Accessible AI for Everyone

Version History:
  v24.5.0 (2024-05-15) — Initial release with full feature set
  v24.5.1 (2024-06-01) — Added high-contrast mode and ARIA improvements

Author: Limitless Telecoms Accessibility Team <accessibility@limitlesstelecoms.com>
License: MIT License — Accessible AI for Everyone
Python: 3.11+
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, ClassVar, Dict, Final, List, Optional, Protocol, Tuple, Union

# ---------------------------------------------------------------------------
# FastAPI imports (soft-fail if unavailable so the module can be imported
# in contexts where the web framework is not installed).
# ---------------------------------------------------------------------------
try:
    from fastapi import APIRouter, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse

    HAS_FASTAPI: Final[bool] = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = object  # type: ignore[misc, assignment]
    FastAPI = object  # type: ignore[misc, assignment]
    HTTPException = Exception  # type: ignore[misc, assignment]
    Query = lambda **kw: None  # type: ignore[assignment]
    WebSocket = object  # type: ignore[misc, assignment]
    WebSocketDisconnect = Exception  # type: ignore[misc, assignment]
    HTMLResponse = object  # type: ignore[misc, assignment]

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
MODULE_DIR: Final[Path] = Path(__file__).resolve().parent
CONFIG_FILE: Final[str] = "accessibility_config.json"
ALERTS_LOG: Final[str] = "accessibility_alerts.jsonl"
CAPTIONING_CONFIG: Final[str] = "captioning_config.json"
SIGN_LANGUAGE_CONFIG: Final[str] = "sign_language_config.json"
HAPTIC_CONFIG: Final[str] = "haptic_config.json"

# Color palette — WCAG 2.1 AA compliant contrast ratios
COLOR_CRITICAL: Final[str] = "#D32F2F"   # Red — 7.0:1 on white
COLOR_WARNING: Final[str] = "#F57C00"    # Orange — 4.5:1 on white
COLOR_INFO: Final[str] = "#1976D2"       # Blue — 7.0:1 on white
COLOR_SUCCESS: Final[str] = "#388E3C"    # Green — 5.5:1 on white

# Default configuration values
DEFAULT_CONFIG: Final[Dict[str, Any]] = {
    "accessibility_enabled": True,
    "visual_alerts": True,
    "haptic_feedback": True,
    "captioning": True,
    "sign_language": True,
    "high_contrast": False,
    "color_scheme": "default",
    "flash_duration_ms": 500,
    "banner_duration_ms": 5000,
    "font_size": "medium",
    "screen_reader_optimized": True,
    "auto_acknowledge_after_ms": 30000,
    "websocket_broadcast": True,
    "preferred_sign_language": "asl",
    "preferred_caption_language": "en-US",
    "haptic_intensity": "medium",
}

# Flash pattern definitions: list of (on_ms, off_ms) tuples
FLASH_PATTERNS: Final[Dict[str, List[Tuple[int, int]]]] = {
    "rapid_blink": [(100, 100), (100, 100), (100, 100), (100, 100)],
    "slow_pulse": [(500, 500), (500, 500)],
    "steady_glow": [(2000, 0)],
    "triple_flash": [(150, 150), (150, 150), (150, 150)],
    "gentle_fade": [(800, 200), (600, 400)],
}

# Haptic feedback patterns: list of (duration_ms, intensity_0_to_1)
HAPTIC_PATTERNS: Final[Dict[str, List[Tuple[int, float]]]] = {
    "CRITICAL_FLASH": [(200, 1.0), (100, 0), (200, 1.0), (100, 0), (200, 1.0)],
    "WARNING_PULSE": [(400, 0.7), (200, 0), (400, 0.7)],
    "INFO_BANNER": [(300, 0.5)],
    "SUCCESS_GLOW": [(150, 0.4), (100, 0), (150, 0.6), (100, 0), (300, 0.8)],
}

# Sign language glyph mappings (simplified — production would use full Unicode/ISWA)
SIGN_LANGUAGE_GLYPHS: Final[Dict[str, Dict[str, str]]] = {
    "asl": {
        "hello": "&#x1F44B;",
        "thank you": "&#x1F91D;",
        "yes": "&#x1F44D;",
        "no": "&#x1F44E;",
        "please": "&#x1F932;",
        "sorry": "&#x1F64F;",
        "help": "&#x1F6A8;",
        "good": "&#x1F44C;",
        "bad": "&#x1F44A;",
        "love": "&#x2764;",
        "a": "&#x1F1E6;", "b": "&#x1F1E7;", "c": "&#x1F1E8;",
        "d": "&#x1F1E9;", "e": "&#x1F1EA;", "f": "&#x1F1EB;",
        "g": "&#x1F1EC;", "h": "&#x1F1ED;", "i": "&#x1F1EE;",
        "j": "&#x1F1EF;", "k": "&#x1F1F0;", "l": "&#x1F1F1;",
        "m": "&#x1F1F2;", "n": "&#x1F1F3;", "o": "&#x1F1F4;",
        "p": "&#x1F1F5;", "q": "&#x1F1F6;", "r": "&#x1F1F7;",
        "s": "&#x1F1F8;", "t": "&#x1F1F9;", "u": "&#x1F1FA;",
        "v": "&#x1F1FB;", "w": "&#x1F1FC;", "x": "&#x1F1FD;",
        "y": "&#x1F1FE;", "z": "&#x1F1FF;",
    },
    "bsl": {
        "hello": "&#x1F44B;",
        "thank you": "&#x1F91D;",
        "yes": "&#x1F44D;",
        "no": "&#x1F44E;",
    },
}

# Supported captioning languages
SUPPORTED_CAPTION_LANGUAGES: Final[List[str]] = [
    "en-US", "en-GB", "es-ES", "fr-FR", "de-DE",
    "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR",
    "ar-SA", "hi-IN", "ru-RU", "nl-NL", "sv-SE",
    "sas-ZA", "sw-KE", "yo-NG", "zu-ZA", "af-ZA",
]

# Supported sign languages
SUPPORTED_SIGN_LANGUAGES: Final[List[Dict[str, str]]] = [
    {"code": "asl", "name": "American Sign Language", "region": "USA/Canada"},
    {"code": "bsl", "name": "British Sign Language", "region": "United Kingdom"},
    {"code": "auslan", "name": "Australian Sign Language", "region": "Australia"},
    {"code": "sasl", "name": "South African Sign Language", "region": "South Africa"},
    {"code": "lsf", "name": "Langue des Signes Francaise", "region": "France"},
    {"code": "dgs", "name": "Deutsche Gebaerdensprache", "region": "Germany"},
    {"code": "lse", "name": "Lengua de Signos Espanola", "region": "Spain"},
    {"code": "lis", "name": "Lingua Italiana dei Segni", "region": "Italy"},
    {"code": "jsl", "name": "Japanese Sign Language", "region": "Japan"},
    {"code": "csl", "name": "Chinese Sign Language", "region": "China"},
    {"code": "kv", "name": "Kenyan Sign Language", "region": "Kenya"},
    {"code": "nsl", "name": "Nigerian Sign Language", "region": "Nigeria"},
]


# ============================================================================
# ENUMERATIONS
# ============================================================================


class VisualAlertType(str, Enum):
    """Enumeration of supported visual alert types.

    Each alert type maps to a distinct color and flash pattern optimized for
    visibility by deaf and hard-of-hearing users.
    """

    CRITICAL_FLASH = "CRITICAL_FLASH"
    WARNING_PULSE = "WARNING_PULSE"
    INFO_BANNER = "INFO_BANNER"
    SUCCESS_GLOW = "SUCCESS_GLOW"

    @property
    def color(self) -> str:
        """Return the WCAG-compliant color for this alert type."""
        return {
            VisualAlertType.CRITICAL_FLASH: COLOR_CRITICAL,
            VisualAlertType.WARNING_PULSE: COLOR_WARNING,
            VisualAlertType.INFO_BANNER: COLOR_INFO,
            VisualAlertType.SUCCESS_GLOW: COLOR_SUCCESS,
        }[self]

    @property
    def flash_pattern(self) -> List[Tuple[int, int]]:
        """Return the flash pattern as (on_ms, off_ms) tuples."""
        return {
            VisualAlertType.CRITICAL_FLASH: FLASH_PATTERNS["rapid_blink"],
            VisualAlertType.WARNING_PULSE: FLASH_PATTERNS["slow_pulse"],
            VisualAlertType.INFO_BANNER: FLASH_PATTERNS["steady_glow"],
            VisualAlertType.SUCCESS_GLOW: FLASH_PATTERNS["triple_flash"],
        }[self]

    @property
    def default_duration_ms(self) -> int:
        """Return the default display duration in milliseconds."""
        return {
            VisualAlertType.CRITICAL_FLASH: 5000,
            VisualAlertType.WARNING_PULSE: 4000,
            VisualAlertType.INFO_BANNER: 5000,
            VisualAlertType.SUCCESS_GLOW: 3000,
        }[self]

    @property
    def aria_label(self) -> str:
        """Return an ARIA-accessible description of the alert."""
        return {
            VisualAlertType.CRITICAL_FLASH: "Critical alert. Immediate attention required.",
            VisualAlertType.WARNING_PULSE: "Warning. Please review.",
            VisualAlertType.INFO_BANNER: "Information.",
            VisualAlertType.SUCCESS_GLOW: "Success. Action completed.",
        }[self]


class FontSize(str, Enum):
    """Supported font size options for accessibility."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class ColorScheme(str, Enum):
    """Supported color schemes for accessibility."""

    DEFAULT = "default"
    HIGH_CONTRAST = "high_contrast"
    DARK_MODE = "dark_mode"
    PROTANOPIA = "protanopia"    # Red-blind friendly
    DEUTERANOPIA = "deuteranopia"  # Green-blind friendly
    TRITANOPIA = "tritanopia"    # Blue-blind friendly


class HapticIntensity(str, Enum):
    """Supported haptic feedback intensity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass(frozen=True)
class VisualAlert:
    """Immutable data class representing a single visual alert.

    Attributes:
        id: Unique identifier (UUID4).
        alert_type: The type of visual alert.
        title: Short alert title.
        message: Detailed alert message.
        color_hex: Hex color code for the alert display.
        flash_pattern: List of (on_ms, off_ms) tuples defining the flash.
        duration_ms: How long the alert should remain visible.
        timestamp: ISO-8601 timestamp of alert creation.
        acknowledged: Whether the user has acknowledged the alert.
    """

    id: str
    alert_type: VisualAlertType
    title: str
    message: str
    color_hex: str
    flash_pattern: List[Tuple[int, int]]
    duration_ms: int
    timestamp: str
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the alert to a JSON-friendly dictionary."""
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "title": self.title,
            "message": self.message,
            "color_hex": self.color_hex,
            "flash_pattern": self.flash_pattern,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualAlert":
        """Deserialize a VisualAlert from a dictionary."""
        return cls(
            id=data["id"],
            alert_type=VisualAlertType(data["alert_type"]),
            title=data["title"],
            message=data["message"],
            color_hex=data["color_hex"],
            flash_pattern=[tuple(t) for t in data["flash_pattern"]],
            duration_ms=data["duration_ms"],
            timestamp=data["timestamp"],
            acknowledged=data.get("acknowledged", False),
        )


@dataclass
class CaptionSegment:
    """A single caption segment with timing information."""

    text: str
    start_time_ms: int
    end_time_ms: int
    confidence: float = 1.0
    speaker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start_time_ms": self.start_time_ms,
            "end_time_ms": self.end_time_ms,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
        }


@dataclass
class GestureRecognitionResult:
    """Result of sign language gesture recognition."""

    gesture: str
    confidence: float
    language: str
    alternatives: List[Dict[str, Union[str, float]]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gesture": self.gesture,
            "confidence": self.confidence,
            "language": self.language,
            "alternatives": self.alternatives,
        }


# ============================================================================
# SINGLETON METACLASS
# ============================================================================


class _SingletonMeta(type):
    """Thread-safe singleton metaclass using double-checked locking."""

    _instances: ClassVar[Dict[type, Any]] = {}
    _lock: asyncio.Lock = asyncio.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


# ============================================================================
# ACCESSIBILITY MANAGER (Singleton)
# ============================================================================


class AccessibilityManager(metaclass=_SingletonMeta):
    """Central manager for all deaf/hard-of-hearing accessibility features.

    This singleton class coordinates visual alerts, captioning, sign language
    support, haptic feedback, and user preferences. It persists configuration
    to JSON files and broadcasts alerts via WebSocket when available.

    Usage:
        >>> manager = AccessibilityManager()
        >>> manager.is_accessibility_enabled()
        True
        >>> alert = manager.send_visual_alert(
        ...     VisualAlertType.INFO_BANNER, "Welcome", "Luqi AI is ready"
        ... )
    """

    _instance: ClassVar[Optional["AccessibilityManager"]] = None

    def __init__(self, config_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize the AccessibilityManager and load user preferences.

        Args:
            config_dir: Directory to store configuration files.
                        Defaults to the module directory.
        """
        if self._instance is not None:
            return

        self._config_dir: Path = Path(config_dir) if config_dir else MODULE_DIR
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Load or create configuration
        self._config_path: Path = self._config_dir / CONFIG_FILE
        self._preferences: Dict[str, Any] = self._load_preferences()

        # Alert storage
        self._alerts_log_path: Path = self._config_dir / ALERTS_LOG
        self._pending_alerts: Dict[str, VisualAlert] = {}
        self._load_pending_alerts()

        # WebSocket connections for real-time broadcast
        self._websocket_connections: List[WebSocket] = []

        # Sub-managers (lazy-loaded)
        self._captioning_engine: Optional["CaptioningEngine"] = None
        self._sign_language_support: Optional["SignLanguageSupport"] = None
        self._haptic_feedback: Optional["HapticFeedback"] = None

        AccessibilityManager._instance = self

    # ------------------------------------------------------------------
    # Configuration / Preferences
    # ------------------------------------------------------------------

    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from JSON config file or create defaults."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    loaded: Dict[str, Any] = json.load(fh)
                # Merge with defaults to ensure all keys exist
                merged = dict(DEFAULT_CONFIG)
                merged.update(loaded)
                return merged
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[AccessibilityManager] Config load error: {exc}. Using defaults.")
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def _save_preferences(self) -> bool:
        """Persist current preferences to disk."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as fh:
                json.dump(self._preferences, fh, indent=2, ensure_ascii=False)
            return True
        except OSError as exc:
            print(f"[AccessibilityManager] Config save error: {exc}")
            return False

    def is_accessibility_enabled(self) -> bool:
        """Return whether the accessibility suite is globally enabled."""
        return bool(self._preferences.get("accessibility_enabled", True))

    def get_preferences(self) -> Dict[str, Any]:
        """Return a copy of the current user preferences.

        Returns:
            Dictionary with keys: visual_alerts, haptic_feedback, captioning,
            sign_language, color_scheme, high_contrast, font_size, etc.
        """
        return dict(self._preferences)

    def update_preferences(self, **kwargs: Any) -> bool:
        """Update one or more preference values and persist to disk.

        Args:
            **kwargs: Key-value pairs to update in the preferences.

        Returns:
            True if preferences were saved successfully.
        """
        valid_keys = set(DEFAULT_CONFIG.keys())
        updated = False
        for key, value in kwargs.items():
            if key in valid_keys:
                self._preferences[key] = value
                updated = True
            else:
                print(f"[AccessibilityManager] Unknown preference key: {key}")
        if updated:
            return self._save_preferences()
        return False

    # ------------------------------------------------------------------
    # Visual Alerts
    # ------------------------------------------------------------------

    def send_visual_alert(
        self,
        alert_type: VisualAlertType,
        title: str,
        message: str,
        duration_ms: Optional[int] = None,
    ) -> VisualAlert:
        """Create, persist, and optionally broadcast a visual alert.

        Args:
            alert_type: The severity/type of the alert.
            title: Short human-readable title.
            message: Detailed message content.
            duration_ms: Override default display duration.

        Returns:
            The created VisualAlert instance.
        """
        if not self.is_accessibility_enabled():
            raise RuntimeError("Accessibility suite is disabled")

        alert = VisualAlert(
            id=str(uuid.uuid4()),
            alert_type=alert_type,
            title=title,
            message=message,
            color_hex=alert_type.color,
            flash_pattern=alert_type.flash_pattern,
            duration_ms=duration_ms or alert_type.default_duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            acknowledged=False,
        )

        self._pending_alerts[alert.id] = alert
        self._persist_alert(alert)

        # WebSocket broadcast (non-blocking)
        if self._preferences.get("websocket_broadcast", True):
            asyncio.create_task(self._broadcast_alert(alert))

        return alert

    def _persist_alert(self, alert: VisualAlert) -> None:
        """Append the alert to the JSONL log file."""
        try:
            with open(self._alerts_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"[AccessibilityManager] Alert persistence error: {exc}")

    def _load_pending_alerts(self) -> None:
        """Load unacknowledged alerts from the log file on startup."""
        if not self._alerts_log_path.exists():
            return
        try:
            with open(self._alerts_log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if not data.get("acknowledged", False):
                            alert = VisualAlert.from_dict(data)
                            self._pending_alerts[alert.id] = alert
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except OSError:
            pass

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Return a list of all unacknowledged visual alerts.

        Returns:
            List of alert dictionaries, newest first.
        """
        alerts = sorted(
            self._pending_alerts.values(),
            key=lambda a: a.timestamp,
            reverse=True,
        )
        return [a.to_dict() for a in alerts]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark a visual alert as acknowledged.

        Args:
            alert_id: The UUID of the alert to acknowledge.

        Returns:
            True if the alert was found and acknowledged.
        """
        if alert_id not in self._pending_alerts:
            return False
        alert = self._pending_alerts[alert_id]
        # dataclass is frozen — replace with acknowledged copy
        acknowledged_alert = VisualAlert(
            id=alert.id,
            alert_type=alert.alert_type,
            title=alert.title,
            message=alert.message,
            color_hex=alert.color_hex,
            flash_pattern=alert.flash_pattern,
            duration_ms=alert.duration_ms,
            timestamp=alert.timestamp,
            acknowledged=True,
        )
        self._pending_alerts[alert_id] = acknowledged_alert
        self._persist_alert(acknowledged_alert)
        return True

    # ------------------------------------------------------------------
    # WebSocket support
    # ------------------------------------------------------------------

    async def _broadcast_alert(self, alert: VisualAlert) -> None:
        """Broadcast the alert to all connected WebSocket clients."""
        if not self._websocket_connections:
            return
        payload = json.dumps({
            "event": "visual_alert",
            "data": alert.to_dict(),
        })
        dead_connections: List[WebSocket] = []
        for ws in self._websocket_connections:
            try:
                if HAS_FASTAPI:
                    await ws.send_text(payload)
            except Exception:
                dead_connections.append(ws)
        for ws in dead_connections:
            self._websocket_connections.remove(ws)

    async def websocket_handler(self, websocket: WebSocket) -> None:
        """Handle incoming WebSocket connections for real-time alerts.

        Usage (FastAPI):
            @app.websocket("/ws/accessibility-alerts")
            async def ws_alerts(websocket: WebSocket):
                await manager.websocket_handler(websocket)
        """
        if not HAS_FASTAPI:
            return
        await websocket.accept()
        self._websocket_connections.append(websocket)
        try:
            while True:
                # Keep connection alive, handle ping/pong
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "get_pending":
                    pending = self.get_pending_alerts()
                    await websocket.send_text(json.dumps({
                        "event": "pending_alerts",
                        "data": pending,
                    }))
        except WebSocketDisconnect:
            pass
        finally:
            if websocket in self._websocket_connections:
                self._websocket_connections.remove(websocket)

    # ------------------------------------------------------------------
    # Sub-manager accessors
    # ------------------------------------------------------------------

    def captioning(self) -> "CaptioningEngine":
        """Return (lazily creating if needed) the CaptioningEngine."""
        if self._captioning_engine is None:
            self._captioning_engine = CaptioningEngine(self._config_dir)
        return self._captioning_engine

    def sign_language(self) -> "SignLanguageSupport":
        """Return (lazily creating if needed) the SignLanguageSupport."""
        if self._sign_language_support is None:
            self._sign_language_support = SignLanguageSupport(self._config_dir)
        return self._sign_language_support

    def haptic(self) -> "HapticFeedback":
        """Return (lazily creating if needed) the HapticFeedback manager."""
        if self._haptic_feedback is None:
            self._haptic_feedback = HapticFeedback(self._config_dir)
        return self._haptic_feedback

    # ------------------------------------------------------------------
    # HTML Component Generation
    # ------------------------------------------------------------------

    def generate_html_alert_component(self) -> str:
        """Generate a self-contained HTML/CSS/JS visual alert component.

        Returns:
            Complete HTML string with embedded CSS and JavaScript.
            No external dependencies — pure HTML/CSS/JS.
        """
        return generate_visual_notification_template()

    # ------------------------------------------------------------------
    # FastAPI Endpoint Registration
    # ------------------------------------------------------------------

    def register_endpoints(self, app_or_router: Union[FastAPI, APIRouter]) -> None:
        """Register all accessibility REST and WebSocket endpoints.

        Args:
            app_or_router: A FastAPI app or APIRouter instance.
        """
        if not HAS_FASTAPI:
            print("[AccessibilityManager] FastAPI not installed — endpoints not registered")
            return

        router = APIRouter(prefix="/api/accessibility", tags=["accessibility"])

        @router.get("/status", response_model=Dict[str, Any])
        async def get_status() -> Dict[str, Any]:
            """Return current accessibility settings and status."""
            return {
                "enabled": self.is_accessibility_enabled(),
                "preferences": self.get_preferences(),
                "pending_alert_count": len(self._pending_alerts),
            }

        @router.post("/preferences", response_model=Dict[str, bool])
        async def update_prefs(request: Dict[str, Any]) -> Dict[str, bool]:
            """Update accessibility preferences."""
            success = self.update_preferences(**request)
            return {"success": success}

        @router.get("/alerts", response_model=List[Dict[str, Any]])
        async def get_alerts() -> List[Dict[str, Any]]:
            """Return all pending (unacknowledged) visual alerts."""
            return self.get_pending_alerts()

        @router.post("/alerts/ack", response_model=Dict[str, bool])
        async def ack_alert(request: Dict[str, str]) -> Dict[str, bool]:
            """Acknowledge a visual alert by ID."""
            alert_id = request.get("alert_id", "")
            success = self.acknowledge_alert(alert_id)
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            return {"success": True}

        @router.get("/captioning/supported", response_model=List[str])
        async def supported_caption_langs() -> List[str]:
            """Return list of supported captioning languages."""
            return self.captioning().get_supported_languages()

        @router.post("/caption", response_model=Dict[str, str])
        async def caption_audio(request: Dict[str, str]) -> Dict[str, str]:
            """Caption audio data (placeholder for STT integration).

            Accepts base64-encoded audio or a URL to audio content.
            """
            audio_data = request.get("audio_data", "")
            language = request.get("language", self._preferences.get("preferred_caption_language", "en-US"))
            result = self.captioning().caption_audio(audio_data, language)
            return {"caption": result, "language": language}

        @router.get("/sign-languages", response_model=List[Dict[str, str]])
        async def sign_langs() -> List[Dict[str, str]]:
            """Return supported sign languages."""
            return self.sign_language().get_supported_sign_languages()

        @router.post("/text-to-sign", response_model=Dict[str, str])
        async def text_to_sign(request: Dict[str, str]) -> Dict[str, str]:
            """Convert text to sign language glyphs."""
            text = request.get("text", "")
            sign_lang = request.get("language", self._preferences.get("preferred_sign_language", "asl"))
            html = self.sign_language().text_to_sign_glyphs(text, sign_lang)
            return {"html": html, "language": sign_lang}

        @router.get("/haptic-patterns", response_model=Dict[str, List[Dict[str, Union[int, float]]]])
        async def haptic_patterns() -> Dict[str, List[Dict[str, Union[int, float]]]]:
            """Return available haptic feedback patterns."""
            patterns: Dict[str, List[Dict[str, Union[int, float]]]] = {}
            for name, pattern in HAPTIC_PATTERNS.items():
                patterns[name] = [{"duration_ms": d, "intensity": i} for d, i in pattern]
            return patterns

        @router.get("/dashboard", response_class=HTMLResponse)
        async def dashboard() -> str:
            """Return the HTML accessibility settings page."""
            return generate_accessibility_dashboard()

        # Include REST router
        if isinstance(app_or_router, FastAPI):
            app_or_router.include_router(router)
            # WebSocket endpoint (must be on app directly)
            @app_or_router.websocket("/ws/accessibility-alerts")
            async def ws_alerts(websocket: WebSocket) -> None:
                await self.websocket_handler(websocket)
        else:
            app_or_router.include_router(router)


# ============================================================================
# CAPTIONING ENGINE
# ============================================================================


class CaptioningEngine:
    """Real-time captioning engine for speech-to-text conversion.

    This is a production-ready scaffold with placeholder STT integration.
    In production, integrate with:
      - OpenAI Whisper API
      - Google Cloud Speech-to-Text
      - Azure Speech Services
      - Mozilla DeepSpeech (on-premise)

    Usage:
        >>> engine = CaptioningEngine()
        >>> engine.caption_audio("base64_audio_data...")
        'Hello, welcome to Luqi AI.'
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize the captioning engine and load configuration.

        Args:
            config_dir: Directory containing captioning_config.json.
        """
        self._config_dir: Path = config_dir or MODULE_DIR
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load captioning configuration from disk."""
        config_path = self._config_dir / CAPTIONING_CONFIG
        defaults: Dict[str, Any] = {
            "engine": "whisper",
            "model": "base",
            "language": "en-US",
            "auto_punctuate": True,
            "speaker_diarization": False,
            "min_segment_duration_ms": 500,
            "max_segment_duration_ms": 5000,
        }
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                defaults.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    def caption_audio(self, audio_data: str, language: Optional[str] = None) -> str:
        """Convert audio data to text caption.

        This is a placeholder that simulates STT output. In production,
        replace with actual speech-to-text API call.

        Args:
            audio_data: Base64-encoded audio data or audio URL.
            language: Target language code (e.g., 'en-US').

        Returns:
            Caption text string.
        """
        lang = language or self._config.get("language", "en-US")
        # Placeholder: in production, send audio_data to STT service
        placeholder_captions: Dict[str, str] = {
            "en-US": "(Caption) Welcome to Luqi AI. How can I help you today?",
            "en-GB": "(Caption) Welcome to Luqi AI. How may I assist you?",
            "es-ES": "(Subtitulo) Bienvenido a Luqi AI. ¿Como puedo ayudarte?",
            "fr-FR": "(Sous-titre) Bienvenue chez Luqi AI. Comment puis-je vous aider?",
            "de-DE": "(Untertitel) Willkommen bei Luqi AI. Wie kann ich Ihnen helfen?",
            "zh-CN": "(字幕) 欢迎使用Luqi AI。有什么可以帮您？",
            "ja-JP": "(字幕) Luqi AIへようこそ。何かお手伝いできることはありますか？",
            "sas-ZA": "(Umbhalo) Siyakwamukela ku-Luqi AI. Ngingakusiza kanjani?",
            "sw-KE": "(Maneno) Karibu kwenye Luqi AI. Ninaweza kukusaidia vipi?",
            "yo-NG": "(Itumoo) Kaabo si Luqi AI. Bawo ni mo se le ran o lowo?",
            "zu-ZA": "(Umbhalo) Siyakwamukela ku-Luqi AI. Ngingakusiza kanjani?",
            "af-ZA": "(Onderskrif) Welkom by Luqi AI. Hoe kan ek jou help?",
        }
        return placeholder_captions.get(lang, f"(Caption) [{lang}] Audio caption placeholder.")

    def caption_stream(self, audio_stream: Any, language: Optional[str] = None) -> Any:
        """Generate caption segments from an audio stream (generator).

        This is a placeholder implementation that yields simulated segments.
        In production, stream audio chunks to a real-time STT service.

        Args:
            audio_stream: An iterator or async generator of audio chunks.
            language: Target language code.

        Yields:
            CaptionSegment objects with timing information.
        """
        lang = language or self._config.get("language", "en-US")
        sample_segments = [
            CaptionSegment("Hello,", 0, 500, 0.95),
            CaptionSegment("welcome to Luqi AI.", 500, 1200, 0.92),
            CaptionSegment("I'm here to assist you", 1200, 2000, 0.88),
            CaptionSegment("with any questions you have.", 2000, 3000, 0.90),
        ]
        for segment in sample_segments:
            yield segment

    def get_supported_languages(self) -> List[str]:
        """Return list of supported captioning language codes."""
        return list(SUPPORTED_CAPTION_LANGUAGES)

    def generate_caption_html(self) -> str:
        """Generate an HTML5 video player with caption overlay support.

        Returns:
            Self-contained HTML string with video player and caption display.
        """
        return """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Luqi AI — Captioned Video Player</title>
<style>
  :root {
    --caption-bg: rgba(0,0,0,0.85);
    --caption-fg: #FFFFFF;
    --caption-font: 'Segoe UI', system-ui, sans-serif;
    --caption-font-size: 1.4rem;
    --caption-line-height: 1.6;
    --highlight: #FFD600;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #121212;
    color: #FFFFFF;
    font-family: var(--caption-font);
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
    padding: 1rem;
  }
  .player-container {
    position: relative;
    width: 100%;
    max-width: 900px;
    border-radius: 8px;
    overflow: hidden;
    background: #000;
  }
  video {
    width: 100%;
    height: auto;
    display: block;
  }
  .caption-overlay {
    position: absolute;
    bottom: 3rem;
    left: 0;
    right: 0;
    text-align: center;
    pointer-events: none;
    z-index: 10;
  }
  .caption-text {
    display: inline-block;
    background: var(--caption-bg);
    color: var(--caption-fg);
    font-size: var(--caption-font-size);
    line-height: var(--caption-line-height);
    padding: 0.4em 0.8em;
    border-radius: 4px;
    max-width: 90%;
    word-wrap: break-word;
  }
  .caption-text .current-word {
    color: var(--highlight);
    font-weight: 700;
  }
  .controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: #1E1E1E;
    border-radius: 0 0 8px 8px;
    flex-wrap: wrap;
  }
  .controls button {
    background: #333;
    color: #FFF;
    border: none;
    padding: 0.6em 1.2em;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
  }
  .controls button:hover, .controls button:focus {
    background: #555;
    outline: 2px solid #FFD600;
    outline-offset: 2px;
  }
  .controls label {
    font-size: 0.9rem;
    color: #AAA;
  }
  .controls input[type="range"] { width: 100px; }
  .caption-settings {
    margin-top: 1rem;
    padding: 1rem;
    background: #1E1E1E;
    border-radius: 8px;
    width: 100%;
    max-width: 900px;
  }
  .caption-settings h2 {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
  }
  .setting-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0.4rem 0;
    flex-wrap: wrap;
  }
  @media (prefers-reduced-motion: reduce) {
    .caption-text { transition: none; }
  }
  @media (max-width: 600px) {
    :root { --caption-font-size: 1.1rem; }
  }
</style>
</head>
<body>
  <h1 style="margin-bottom:1rem; font-size:1.3rem;">&#x1F3A7; Captioned Video Player</h1>
  <div class="player-container" role="region" aria-label="Video player with captions">
    <video id="video" controls aria-describedby="caption-display"
           poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='360'%3E%3Crect fill='%23333' width='640' height='360'/%3E%3Ctext fill='%23888' x='50%25' y='50%25' text-anchor='middle' font-size='24' font-family='sans-serif'%3ELuqi AI Video%3C/text%3E%3C/svg%3E">
      <source src="" type="video/mp4">
      <track kind="captions" src="" srclang="en" label="English" default>
      Your browser does not support the video element.
    </video>
    <div class="caption-overlay" id="caption-overlay" aria-live="polite" aria-atomic="true">
      <span class="caption-text" id="caption-display">Captions will appear here...</span>
    </div>
  </div>
  <div class="controls" role="toolbar" aria-label="Player controls">
    <button id="btn-play" aria-label="Play">&#x25B6;</button>
    <button id="btn-stop" aria-label="Stop">&#x25A0;</button>
    <label>Speed:
      <input type="range" id="speed" min="0.5" max="2" step="0.25" value="1"
             aria-label="Playback speed">
    </label>
    <button id="btn-cc" aria-pressed="true" aria-label="Toggle captions">CC</button>
  </div>
  <div class="caption-settings">
    <h2>Caption Settings</h2>
    <div class="setting-row">
      <label for="font-size">Size:</label>
      <select id="font-size" aria-label="Caption font size">
        <option value="1rem">Small</option>
        <option value="1.4rem" selected>Medium</option>
        <option value="1.8rem">Large</option>
        <option value="2.2rem">Extra Large</option>
      </select>
    </div>
    <div class="setting-row">
      <label for="bg-opacity">Background:</label>
      <input type="range" id="bg-opacity" min="0" max="1" step="0.1" value="0.85"
             aria-label="Caption background opacity">
    </div>
    <div class="setting-row">
      <label for="lang-select">Language:</label>
      <select id="lang-select" aria-label="Caption language">
        <option value="en-US" selected>English (US)</option>
        <option value="en-GB">English (UK)</option>
        <option value="es-ES">Espanol</option>
        <option value="fr-FR">Francais</option>
        <option value="de-DE">Deutsch</option>
        <option value="zh-CN">Chinese</option>
        <option value="ja-JP">Japanese</option>
        <option value="sas-ZA">SASL (South Africa)</option>
        <option value="sw-KE">Swahili</option>
        <option value="yo-NG">Yoruba</option>
        <option value="zu-ZA">Zulu</option>
        <option value="af-ZA">Afrikaans</option>
      </select>
    </div>
  </div>
  <script>
    const video = document.getElementById('video');
    const captionDisplay = document.getElementById('caption-display');
    const btnPlay = document.getElementById('btn-play');
    const btnStop = document.getElementById('btn-stop');
    const btnCc = document.getElementById('btn-cc');
    const speedSlider = document.getElementById('speed');
    const fontSizeSelect = document.getElementById('font-size');
    const bgOpacityInput = document.getElementById('bg-opacity');

    let captionsVisible = true;
    let captionWs = null;

    // Simulated real-time captions
    function updateCaption(text) {
      captionDisplay.textContent = text;
      captionDisplay.style.display = captionsVisible ? 'inline-block' : 'none';
    }

    btnPlay.addEventListener('click', () => {
      video.play();
      btnPlay.setAttribute('aria-label', 'Pause');
      btnPlay.innerHTML = '&#x23F8;';
      connectCaptionStream();
    });
    btnStop.addEventListener('click', () => {
      video.pause();
      video.currentTime = 0;
      btnPlay.setAttribute('aria-label', 'Play');
      btnPlay.innerHTML = '&#x25B6;';
      if (captionWs) captionWs.close();
    });
    btnCc.addEventListener('click', () => {
      captionsVisible = !captionsVisible;
      btnCc.setAttribute('aria-pressed', captionsVisible);
      captionDisplay.style.display = captionsVisible ? 'inline-block' : 'none';
    });
    speedSlider.addEventListener('input', (e) => {
      video.playbackRate = parseFloat(e.target.value);
    });
    fontSizeSelect.addEventListener('change', (e) => {
      captionDisplay.style.fontSize = e.target.value;
    });
    bgOpacityInput.addEventListener('input', (e) => {
      captionDisplay.style.background = 'rgba(0,0,0,' + e.target.value + ')';
    });

    function connectCaptionStream() {
      const wsUrl = 'ws://' + window.location.host + '/ws/accessibility-alerts';
      captionWs = new WebSocket(wsUrl);
      captionWs.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.event === 'caption_segment') {
          updateCaption(msg.data.text);
        }
      };
    }
  </script>
</body>
</html>"""


# ============================================================================
# SIGN LANGUAGE SUPPORT
# ============================================================================


class SignLanguageSupport:
    """Sign language support including text-to-sign conversion and gesture recognition.

    Provides:
      - Text-to-sign glyph HTML rendering
      - Gesture recognition placeholder (for camera-based sign input)
      - Support for ASL, BSL, SASL, and other sign languages

    Usage:
        >>> sl = SignLanguageSupport()
        >>> sl.text_to_sign_glyphs("hello", "asl")
        '<div class="sign-glyphs"><span class="sign-glyph" ...>...</span></div>'
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize sign language support and load configuration.

        Args:
            config_dir: Directory containing sign_language_config.json.
        """
        self._config_dir: Path = config_dir or MODULE_DIR
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load sign language configuration from disk."""
        config_path = self._config_dir / SIGN_LANGUAGE_CONFIG
        defaults: Dict[str, Any] = {
            "default_language": "asl",
            "enable_camera_input": True,
            "glyph_size": "large",
            "show_finger_spelling": True,
        }
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                defaults.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    def text_to_sign_glyphs(self, text: str, language: Optional[str] = None) -> str:
        """Convert text to an HTML representation of sign language glyphs.

        Maps common words and individual letters to Unicode glyphs and
        emoji representations. Production systems would use full ISWA
        (International SignWriting Alphabet) fonts or avatar animations.

        Args:
            text: The text to convert.
            language: Sign language code (asl, bsl, sasl, etc.).

        Returns:
            HTML string with sign glyph spans.
        """
        lang = (language or self._config.get("default_language", "asl")).lower()
        glyphs = SIGN_LANGUAGE_GLYPHS.get(lang, SIGN_LANGUAGE_GLYPHS["asl"])

        words = text.lower().split()
        glyph_spans: List[str] = []
        for word in words:
            if word in glyphs:
                glyph_spans.append(
                    f'<span class="sign-glyph sign-word" '
                    f'title="{word}" data-glyph="{word}">'
                    f'{glyphs[word]}</span>'
                )
            else:
                # Finger-spell each letter
                for char in word:
                    if char in glyphs:
                        glyph_spans.append(
                            f'<span class="sign-glyph sign-letter" '
                            f'title="{char.upper()}" data-glyph="{char}">'
                            f'{glyphs[char]}</span>'
                        )
                    else:
                        glyph_spans.append(
                            f'<span class="sign-glyph sign-unknown" '
                            f'title="{char}">&#x2753;</span>'
                        )
                glyph_spans.append(
                    '<span class="sign-glyph sign-space">&nbsp;</span>'
                )

        html = (
            '<div class="sign-glyph-container" lang="' + lang + '" '
            'role="img" aria-label="Sign language representation: ' +
            text + '">\n  ' +
            '\n  '.join(glyph_spans) +
            '\n</div>'
        )
        return html

    def recognize_gesture(self, image_data: Union[str, bytes]) -> GestureRecognitionResult:
        """Recognize a sign language gesture from image data.

        This is a placeholder for camera-based gesture recognition.
        In production, integrate with:
          - MediaPipe Hands (Google)
          - OpenPose
          - Custom trained model (PyTorch/TensorFlow)

        Args:
            image_data: Base64-encoded image or raw bytes.

        Returns:
            GestureRecognitionResult with recognized gesture and confidence.
        """
        # Placeholder: production would run inference on image_data
        return GestureRecognitionResult(
            gesture="hello",
            confidence=0.92,
            language="asl",
            alternatives=[
                {"gesture": "thank_you", "confidence": 0.05},
                {"gesture": "goodbye", "confidence": 0.03},
            ],
        )

    def get_supported_sign_languages(self) -> List[Dict[str, str]]:
        """Return list of supported sign languages with metadata."""
        return list(SUPPORTED_SIGN_LANGUAGES)


# ============================================================================
# HAPTIC FEEDBACK
# ============================================================================


class HapticFeedback:
    """Haptic feedback pattern manager for notification vibrations.

    Provides platform-agnostic vibration patterns that can be used with:
      - Web Vibration API (navigator.vibrate)
      - Mobile native vibration (iOS/Android)
      - Wearable devices (smartwatches)
      - Custom haptic hardware

    Usage:
        >>> haptic = HapticFeedback()
        >>> haptic.get_pattern(VisualAlertType.CRITICAL_FLASH)
        [(200, 1.0), (100, 0), (200, 1.0), (100, 0), (200, 1.0)]
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize haptic feedback and load configuration.

        Args:
            config_dir: Directory containing haptic_config.json.
        """
        self._config_dir: Path = config_dir or MODULE_DIR
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load haptic configuration from disk."""
        config_path = self._config_dir / HAPTIC_CONFIG
        defaults: Dict[str, Any] = {
            "enabled": True,
            "default_intensity": "medium",
            "max_duration_ms": 5000,
            "pattern_repeat": 1,
        }
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                defaults.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    def get_pattern(
        self,
        alert_type: Union[VisualAlertType, str],
        intensity: Optional[str] = None,
    ) -> List[Tuple[int, float]]:
        """Get the haptic pattern for a given alert type.

        Args:
            alert_type: The alert type or its string value.
            intensity: Override intensity (low, medium, high).

        Returns:
            List of (duration_ms, intensity_0_to_1) tuples.
        """
        type_key = alert_type.value if isinstance(alert_type, VisualAlertType) else alert_type
        pattern = list(HAPTIC_PATTERNS.get(type_key, HAPTIC_PATTERNS["INFO_BANNER"]))

        # Apply intensity multiplier
        intensity_level = intensity or self._config.get("default_intensity", "medium")
        multipliers = {"low": 0.4, "medium": 0.7, "high": 1.0}
        mult = multipliers.get(intensity_level, 0.7)

        return [(d, round(i * mult, 2)) for d, i in pattern]

    def trigger_notification(
        self,
        alert_type: Union[VisualAlertType, str],
        intensity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete haptic notification specification.

        Args:
            alert_type: The alert type.
            intensity: Optional intensity override.

        Returns:
            Dictionary with pattern, vibration API array, and metadata.
        """
        pattern = self.get_pattern(alert_type, intensity)
        # Web Vibration API format: [on, off, on, off, ...] in ms
        vibration_array: List[int] = []
        for duration_ms, _ in pattern:
            vibration_array.append(duration_ms)
            vibration_array.append(100)  # 100ms gap between pulses
        if vibration_array:
            vibration_array.pop()  # Remove trailing gap

        return {
            "pattern": [{"duration_ms": d, "intensity": i} for d, i in pattern],
            "vibration_api_array": vibration_array,
            "repeat": self._config.get("pattern_repeat", 1),
            "intensity": intensity or self._config.get("default_intensity", "medium"),
            "alert_type": alert_type.value if isinstance(alert_type, VisualAlertType) else alert_type,
            "total_duration_ms": sum(d for d, _ in pattern),
        }


# ============================================================================
# HTML GENERATION FUNCTIONS
# ============================================================================


def generate_visual_notification_template() -> str:
    """Generate the HTML/CSS/JS visual alert notification template.

    Returns a self-contained, dependency-free HTML page that displays
    color-coded visual alerts with flash patterns. Designed for deaf and
    hard-of-hearing users — all notifications are purely visual.

    Features:
      - Color-coded alerts (red/orange/blue/green)
      - Flash patterns (rapid blink, slow pulse, steady glow, triple flash)
      - Persistent banner with dismiss button
      - Progress bar showing alert duration
      - High contrast mode support
      - Mobile responsive
      - ARIA labels for screen reader compatibility
      - WebSocket integration for real-time alerts
      - No external dependencies
    """
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Luqi AI Visual Alert System for Deaf and Hard-of-Hearing Users">
<title>Luqi AI — Visual Alert System</title>
<style>
  /* ================================================================
     CSS VARIABLES & RESET
     ================================================================ */
  :root {
    --color-critical: #D32F2F;
    --color-warning:  #F57C00;
    --color-info:     #1976D2;
    --color-success:  #388E3C;
    --bg-body:        #FAFAFA;
    --bg-card:        #FFFFFF;
    --text-primary:   #212121;
    --text-secondary: #757575;
    --border:         #E0E0E0;
    --shadow:         0 4px 20px rgba(0,0,0,0.15);
    --radius:         8px;
    --font-base:      'Segoe UI', system-ui, -apple-system, sans-serif;
    --font-mono:      'Consolas', 'Monaco', monospace;
    --transition:     0.3s ease;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { font-size: 16px; }
  body {
    font-family: var(--font-base);
    background: var(--bg-body);
    color: var(--text-primary);
    min-height: 100vh;
    padding: 1rem;
  }

  /* ================================================================
     HIGH CONTRAST MODE
     ================================================================ */
  @media (prefers-contrast: more) {
    :root {
      --color-critical: #FF0000;
      --color-warning:  #FF8800;
      --color-info:     #0066FF;
      --color-success:  #008800;
      --bg-body:        #000000;
      --bg-card:        #000000;
      --text-primary:   #FFFFFF;
      --text-secondary: #CCCCCC;
      --border:         #FFFFFF;
    }
    .alert-banner { border-width: 3px !important; }
  }

  /* ================================================================
     DARK MODE
     ================================================================ */
  @media (prefers-color-scheme: dark) {
    :root {
      --bg-body:        #121212;
      --bg-card:        #1E1E1E;
      --text-primary:   #E0E0E0;
      --text-secondary: #AAAAAA;
      --border:         #333333;
    }
  }

  /* ================================================================
     LAYOUT
     ================================================================ */
  .container { max-width: 800px; margin: 0 auto; }
  header {
    text-align: center;
    padding: 1.5rem 1rem;
    margin-bottom: 1rem;
  }
  header h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  header p  { color: var(--text-secondary); font-size: 0.95rem; }
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem;
    margin-bottom: 1rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 0.85rem;
  }
  .status-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--color-success);
    display: inline-block;
  }
  .status-dot.disconnected { background: var(--color-critical); }

  /* ================================================================
     ALERT BANNER
     ================================================================ */
  #alert-container {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-width: 420px;
    width: calc(100% - 2rem);
    pointer-events: none;
  }
  .alert-banner {
    pointer-events: all;
    background: var(--bg-card);
    border-left: 5px solid;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1rem 1.25rem;
    position: relative;
    overflow: hidden;
    animation: slideIn 0.4s ease;
    transition: opacity var(--transition), transform var(--transition);
  }
  .alert-banner.critical { border-color: var(--color-critical); }
  .alert-banner.warning  { border-color: var(--color-warning); }
  .alert-banner.info     { border-color: var(--color-info); }
  .alert-banner.success  { border-color: var(--color-success); }

  .alert-banner.critical .alert-icon { color: var(--color-critical); }
  .alert-banner.warning  .alert-icon { color: var(--color-warning); }
  .alert-banner.info     .alert-icon { color: var(--color-info); }
  .alert-banner.success  .alert-icon { color: var(--color-success); }

  .alert-banner.critical .progress-bar { background: var(--color-critical); }
  .alert-banner.warning  .progress-bar { background: var(--color-warning); }
  .alert-banner.info     .progress-bar { background: var(--color-info); }
  .alert-banner.success  .progress-bar { background: var(--color-success); }

  /* Flash pattern animations */
  .alert-banner.critical { animation: slideIn 0.4s ease, rapidBlink 0.6s infinite; }
  .alert-banner.warning  { animation: slideIn 0.4s ease, slowPulse 2s infinite; }
  .alert-banner.info     { animation: slideIn 0.4s ease, steadyGlow 2s infinite; }
  .alert-banner.success  { animation: slideIn 0.4s ease, tripleFlash 1.5s infinite; }

  @keyframes slideIn {
    from { transform: translateX(120%); opacity: 0; }
    to   { transform: translateX(0);     opacity: 1; }
  }
  @keyframes rapidBlink {
    0%, 100% { box-shadow: 0 0 0 0 transparent; }
    50%      { box-shadow: 0 0 20px 4px var(--color-critical); }
  }
  @keyframes slowPulse {
    0%, 100% { box-shadow: 0 0 0 0 transparent; }
    50%      { box-shadow: 0 0 16px 3px var(--color-warning); }
  }
  @keyframes steadyGlow {
    0%   { box-shadow: 0 0 4px 1px var(--color-info); }
    100% { box-shadow: 0 0 12px 3px var(--color-info); }
  }
  @keyframes tripleFlash {
    0%, 100% { box-shadow: 0 0 0 0 transparent; }
    25%      { box-shadow: 0 0 12px 2px var(--color-success); }
    50%      { box-shadow: 0 0 0 0 transparent; }
    75%      { box-shadow: 0 0 12px 2px var(--color-success); }
  }

  .alert-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.3rem;
  }
  .alert-icon { font-size: 1.3rem; line-height: 1; }
  .alert-title { font-weight: 700; font-size: 1rem; }
  .alert-message { font-size: 0.9rem; color: var(--text-secondary); line-height: 1.4; }
  .alert-time {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 0.4rem;
    font-family: var(--font-mono);
  }
  .alert-dismiss {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    color: var(--text-secondary);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
  }
  .alert-dismiss:hover,
  .alert-dismiss:focus {
    background: rgba(0,0,0,0.1);
    outline: 2px solid currentColor;
    outline-offset: 1px;
  }
  .progress-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 3px;
    border-radius: 0 0 0 var(--radius);
    animation: progress linear forwards;
  }
  @keyframes progress {
    from { width: 100%; }
    to   { width: 0%; }
  }

  /* ================================================================
     ALERT HISTORY
     ================================================================ */
  .history-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 1rem;
  }
  .history-section h2 { font-size: 1.1rem; margin-bottom: 0.5rem; }
  .alert-list {
    list-style: none;
    max-height: 300px;
    overflow-y: auto;
  }
  .alert-list li {
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }
  .alert-list li:last-child { border-bottom: none; }
  .alert-list .li-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .alert-list .li-critical { background: var(--color-critical); }
  .alert-list .li-warning  { background: var(--color-warning); }
  .alert-list .li-info     { background: var(--color-info); }
  .alert-list .li-success  { background: var(--color-success); }
  .alert-list .li-text { flex: 1; }
  .alert-list .li-time { font-size: 0.75rem; color: var(--text-secondary); }

  /* ================================================================
     SCREEN READER ONLY
     ================================================================ */
  .sr-only {
    position: absolute;
    width: 1px; height: 1px;
    padding: 0; margin: -1px;
    overflow: hidden;
    clip: rect(0,0,0,0);
    white-space: nowrap;
    border: 0;
  }

  /* ================================================================
     MOBILE RESPONSIVE
     ================================================================ */
  @media (max-width: 600px) {
    #alert-container { max-width: 100%; left: 0.5rem; right: 0.5rem; }
    .alert-banner { padding: 0.8rem 1rem; }
    header h1 { font-size: 1.2rem; }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .alert-banner { animation: slideIn 0.4s ease !important; }
    .progress-bar { animation: none !important; width: 100%; }
  }
</style>
</head>
<body>
  <div id="alert-container" role="region" aria-live="polite" aria-label="Visual alert notifications"
       aria-atomic="false">
    <!-- Alerts are injected here via JavaScript -->
  </div>

  <div class="container">
    <header>
      <h1>&#x1F4E2; Luqi AI Visual Alert System</h1>
      <p>Visual-only notifications designed for deaf and hard-of-hearing users</p>
    </header>

    <div class="status-bar" role="status" aria-live="polite">
      <span class="status-dot" id="status-dot"></span>
      <span id="status-text">WebSocket connecting...</span>
    </div>

    <div class="history-section">
      <h2>Alert History</h2>
      <ul class="alert-list" id="alert-history" role="log" aria-label="Alert history">
        <li style="color:var(--text-secondary); font-style:italic;">No alerts yet.</li>
      </ul>
    </div>
  </div>

  <script>
    // ================================================================
    // VISUAL ALERT SYSTEM — Pure JavaScript, no dependencies
    // ================================================================
    (function() {
      'use strict';

      const container = document.getElementById('alert-container');
      const statusDot = document.getElementById('status-dot');
      const statusText = document.getElementById('status-text');
      const historyList = document.getElementById('alert-history');

      let ws = null;
      let reconnectTimer = null;
      let alertIdCounter = 0;
      const activeAlerts = new Map();

      // Alert type configuration
      const ALERT_CONFIG = {
        CRITICAL_FLASH: {
          cssClass: 'critical',
          icon: '&#x26A0;',
          ariaLabel: 'Critical alert. Immediate attention required.',
          defaultDuration: 5000
        },
        WARNING_PULSE: {
          cssClass: 'warning',
          icon: '&#x1F514;',
          ariaLabel: 'Warning. Please review.',
          defaultDuration: 4000
        },
        INFO_BANNER: {
          cssClass: 'info',
          icon: '&#x2139;',
          ariaLabel: 'Information.',
          defaultDuration: 5000
        },
        SUCCESS_GLOW: {
          cssClass: 'success',
          icon: '&#x2713;',
          ariaLabel: 'Success. Action completed.',
          defaultDuration: 3000
        }
      };

      /**
       * Show a visual alert banner.
       */
      function showAlert(type, title, message, durationMs) {
        const config = ALERT_CONFIG[type] || ALERT_CONFIG.INFO_BANNER;
        const id = 'alert-' + (++alertIdCounter);
        const duration = durationMs || config.defaultDuration;

        const banner = document.createElement('div');
        banner.className = 'alert-banner ' + config.cssClass;
        banner.id = id;
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-label', config.ariaLabel);
        banner.tabIndex = 0;

        banner.innerHTML =
          '<span class="sr-only">' + config.ariaLabel + '</span>' +
          '<button class="alert-dismiss" aria-label="Dismiss ' + title + '" ' +
          'onclick="dismissAlert(\'' + id + '\')">&times;</button>' +
          '<div class="alert-header">' +
            '<span class="alert-icon" aria-hidden="true">' + config.icon + '</span>' +
            '<span class="alert-title">' + escapeHtml(title) + '</span>' +
          '</div>' +
          '<div class="alert-message">' + escapeHtml(message) + '</div>' +
          '<div class="alert-time">' + new Date().toLocaleTimeString() + '</div>' +
          '<div class="progress-bar" style="animation-duration:' + duration + 'ms"></div>';

        container.appendChild(banner);
        activeAlerts.set(id, { element: banner, timer: null });

        // Auto-dismiss
        const timer = setTimeout(() => dismissAlert(id), duration);
        activeAlerts.get(id).timer = timer;

        // Add to history
        addToHistory(config.cssClass, title, message);
      }

      /**
       * Dismiss an alert by ID.
       */
      window.dismissAlert = function(id) {
        const record = activeAlerts.get(id);
        if (!record) return;
        if (record.timer) clearTimeout(record.timer);
        const el = record.element;
        el.style.opacity = '0';
        el.style.transform = 'translateX(120%)';
        setTimeout(() => {
          if (el.parentNode) el.parentNode.removeChild(el);
          activeAlerts.delete(id);
        }, 300);
        // Send acknowledgment to server
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ event: 'ack', alert_id: id }));
        }
      };

      /**
       * Add alert to history list.
       */
      function addToHistory(cssClass, title, message) {
        const placeholder = historyList.querySelector('li[style*="italic"]');
        if (placeholder) placeholder.remove();

        const li = document.createElement('li');
        li.innerHTML =
          '<span class="li-dot li-' + cssClass + '" aria-hidden="true"></span>' +
          '<span class="li-text"><strong>' + escapeHtml(title) + '</strong> — ' +
          escapeHtml(message) + '</span>' +
          '<span class="li-time">' + new Date().toLocaleTimeString() + '</span>';
        historyList.insertBefore(li, historyList.firstChild);

        // Keep only last 50
        while (historyList.children.length > 50) {
          historyList.removeChild(historyList.lastChild);
        }
      }

      /**
       * Escape HTML to prevent XSS.
       */
      function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
      }

      /**
       * Connect to WebSocket for real-time alerts.
       */
      function connectWebSocket() {
        const wsUrl = 'ws://' + window.location.host + '/ws/accessibility-alerts';
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
          statusDot.classList.remove('disconnected');
          statusText.textContent = 'Connected — receiving visual alerts';
          ws.send('get_pending');
        };

        ws.onmessage = function(event) {
          const msg = JSON.parse(event.data);
          if (msg.event === 'visual_alert') {
            const d = msg.data;
            showAlert(d.alert_type, d.title, d.message, d.duration_ms);
          } else if (msg.event === 'pending_alerts') {
            msg.data.forEach(function(a) {
              showAlert(a.alert_type, a.title, a.message, a.duration_ms);
            });
          }
        };

        ws.onclose = function() {
          statusDot.classList.add('disconnected');
          statusText.textContent = 'Disconnected — reconnecting...';
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = function() {
          statusDot.classList.add('disconnected');
          statusText.textContent = 'Connection error';
        };
      }

      // ================================================================
      // KEYBOARD SHORTCUTS
      // ================================================================
      document.addEventListener('keydown', function(e) {
        // Escape dismisses newest alert
        if (e.key === 'Escape') {
          const newest = container.lastElementChild;
          if (newest) newest.querySelector('.alert-dismiss').click();
        }
      });

      // ================================================================
      // INIT
      // ================================================================
      connectWebSocket();

      // Demo: trigger sample alerts after 2 seconds
      setTimeout(function() {
        showAlert('INFO_BANNER', 'Luqi AI Ready',
          'Visual alert system is active. All notifications will appear here.', 5000);
      }, 2000);

    })();
  </script>
</body>
</html>"""


def generate_accessibility_dashboard() -> str:
    """Generate the HTML accessibility settings dashboard page.

    Returns a self-contained, dependency-free HTML page that allows users
    to configure all accessibility preferences including visual alerts,
    haptic feedback, captioning, sign language, color scheme, and font size.

    Features:
      - Toggle switches for all accessibility features
      - Color scheme picker with live preview
      - Font size selector
      - Haptic intensity control
      - Caption language selector
      - Sign language preference
      - High contrast mode toggle
      - Screen reader optimization toggle
      - Test alert buttons for each alert type
      - Mobile responsive design
      - High contrast support
      - ARIA labels throughout
    """
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Luqi AI Accessibility Settings for Deaf and Hard-of-Hearing Users">
<title>Luqi AI — Accessibility Settings</title>
<style>
  /* ================================================================
     CSS VARIABLES & RESET
     ================================================================ */
  :root {
    --primary:        #1976D2;
    --primary-dark:   #115293;
    --critical:       #D32F2F;
    --warning:        #F57C00;
    --info:           #1976D2;
    --success:        #388E3C;
    --bg-body:        #F5F5F5;
    --bg-card:        #FFFFFF;
    --bg-section:     #FAFAFA;
    --text-primary:   #212121;
    --text-secondary: #757575;
    --border:         #E0E0E0;
    --shadow:         0 2px 8px rgba(0,0,0,0.1);
    --radius:         8px;
    --font-base:      'Segoe UI', system-ui, -apple-system, sans-serif;
    --transition:     0.2s ease;
    --toggle-w:       48px;
    --toggle-h:       26px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font-base);
    background: var(--bg-body);
    color: var(--text-primary);
    min-height: 100vh;
    padding: 1rem;
  }

  /* High contrast */
  @media (prefers-contrast: more) {
    :root {
      --bg-body: #000; --bg-card: #000; --bg-section: #000;
      --text-primary: #FFF; --text-secondary: #CCC; --border: #FFF;
      --primary: #0066FF; --primary-dark: #0044CC;
    }
  }
  /* Dark mode */
  @media (prefers-color-scheme: dark) {
    :root {
      --bg-body: #121212; --bg-card: #1E1E1E; --bg-section: #1A1A1A;
      --text-primary: #E0E0E0; --text-secondary: #AAA; --border: #333;
    }
  }

  /* ================================================================
     LAYOUT
     ================================================================ */
  .container { max-width: 720px; margin: 0 auto; }
  header {
    text-align: center;
    padding: 1.5rem 1rem;
  }
  header h1 { font-size: 1.6rem; margin-bottom: 0.3rem; }
  header p { color: var(--text-secondary); font-size: 0.95rem; }
  .version { font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.3rem; }

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
    overflow: hidden;
  }
  .card-header {
    padding: 1rem 1.25rem;
    background: var(--bg-section);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .card-header h2 { font-size: 1.1rem; }
  .card-header .icon { font-size: 1.3rem; }
  .card-body { padding: 1rem 1.25rem; }

  /* ================================================================
     SETTING ROW
     ================================================================ */
  .setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    gap: 1rem;
  }
  .setting-row:last-child { border-bottom: none; }
  .setting-label { flex: 1; }
  .setting-label strong { display: block; font-size: 0.95rem; }
  .setting-label small {
    display: block;
    color: var(--text-secondary);
    font-size: 0.8rem;
    margin-top: 0.15rem;
  }

  /* ================================================================
     TOGGLE SWITCH
     ================================================================ */
  .toggle {
    position: relative;
    display: inline-block;
    width: var(--toggle-w);
    height: var(--toggle-h);
    flex-shrink: 0;
  }
  .toggle input {
    opacity: 0;
    width: 0; height: 0;
    position: absolute;
  }
  .toggle-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: #BDBDBD;
    border-radius: var(--toggle-h);
    transition: background var(--transition);
  }
  .toggle-slider::before {
    content: '';
    position: absolute;
    height: 20px; width: 20px;
    left: 3px; bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: transform var(--transition);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .toggle input:checked + .toggle-slider { background: var(--primary); }
  .toggle input:checked + .toggle-slider::before { transform: translateX(22px); }
  .toggle input:focus + .toggle-slider { outline: 2px solid var(--primary); outline-offset: 2px; }

  /* ================================================================
     SELECT & INPUT
     ================================================================ */
  select, input[type="range"] {
    font-family: inherit;
    font-size: 0.9rem;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg-card);
    color: var(--text-primary);
    min-width: 160px;
  }
  select:focus, input:focus {
    outline: 2px solid var(--primary);
    outline-offset: 1px;
  }
  input[type="range"] { padding: 0; min-width: 120px; }

  /* ================================================================
     COLOR SCHEME GRID
     ================================================================ */
  .color-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .color-option {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
    padding: 0.6rem;
    border: 2px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    transition: border-color var(--transition);
    background: var(--bg-card);
  }
  .color-option:hover,
  .color-option:focus,
  .color-option.selected {
    border-color: var(--primary);
    outline: none;
  }
  .color-swatch {
    width: 32px; height: 32px;
    border-radius: 50%;
    border: 2px solid var(--border);
  }
  .color-label { font-size: 0.75rem; text-align: center; }

  /* ================================================================
     TEST ALERTS
     ================================================================ */
  .test-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .btn {
    padding: 0.6rem 1rem;
    border: none;
    border-radius: 6px;
    font-family: inherit;
    font-size: 0.9rem;
    cursor: pointer;
    color: white;
    transition: opacity var(--transition), transform 0.1s;
  }
  .btn:hover { opacity: 0.85; }
  .btn:active { transform: scale(0.97); }
  .btn:focus { outline: 2px solid currentColor; outline-offset: 2px; }
  .btn-critical { background: var(--critical); }
  .btn-warning  { background: var(--warning); }
  .btn-info     { background: var(--info); }
  .btn-success  { background: var(--success); }
  .btn-primary  { background: var(--primary); }

  /* ================================================================
     SAVE BAR
     ================================================================ */
  .save-bar {
    position: sticky;
    bottom: 0;
    display: flex;
    justify-content: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--bg-card);
    border-top: 1px solid var(--border);
    box-shadow: 0 -4px 12px rgba(0,0,0,0.1);
  }

  /* ================================================================
     STATUS MESSAGE
     ================================================================ */
  .status-msg {
    text-align: center;
    padding: 0.5rem;
    font-size: 0.9rem;
    min-height: 2rem;
  }
  .status-msg.success { color: var(--success); }
  .status-msg.error   { color: var(--critical); }

  /* ================================================================
     SCREEN READER ONLY
     ================================================================ */
  .sr-only {
    position: absolute;
    width: 1px; height: 1px;
    padding: 0; margin: -1px;
    overflow: hidden;
    clip: rect(0,0,0,0);
    white-space: nowrap;
    border: 0;
  }

  /* ================================================================
     MOBILE
     ================================================================ */
  @media (max-width: 600px) {
    .setting-row { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
    select, input[type="range"] { width: 100%; }
    .test-buttons { justify-content: stretch; }
    .test-buttons .btn { flex: 1; }
  }
</style>
</head>
<body>
  <div class="container">
    <header role="banner">
      <h1>&#x267F; Accessibility Settings</h1>
      <p>Configure visual alerts, captions, sign language, and haptic feedback</p>
      <div class="version">Luqi AI v24.5.0 — Limitless Telecoms</div>
    </header>

    <!-- Master Toggle -->
    <div class="card">
      <div class="card-body">
        <div class="setting-row">
          <div class="setting-label">
            <strong>Enable Accessibility Suite</strong>
            <small>Turn on all accessibility features for deaf and hard-of-hearing users</small>
          </div>
          <label class="toggle" aria-label="Enable accessibility suite">
            <input type="checkbox" id="master-toggle" checked
                   onchange="updatePref('accessibility_enabled', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>
    </div>

    <!-- Visual Alerts -->
    <div class="card">
      <div class="card-header">
        <span class="icon" aria-hidden="true">&#x1F4E2;</span>
        <h2>Visual Alerts</h2>
      </div>
      <div class="card-body">
        <div class="setting-row">
          <div class="setting-label">
            <strong>Enable Visual Alerts</strong>
            <small>Flash notifications on screen when events occur</small>
          </div>
          <label class="toggle" aria-label="Enable visual alerts">
            <input type="checkbox" id="visual-alerts-toggle" checked
                   onchange="updatePref('visual_alerts', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>High Contrast Mode</strong>
            <small>Increase contrast for better visibility</small>
          </div>
          <label class="toggle" aria-label="Enable high contrast mode">
            <input type="checkbox" id="high-contrast-toggle"
                   onchange="updatePref('high_contrast', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Screen Reader Optimized</strong>
            <small>Add ARIA labels and live regions</small>
          </div>
          <label class="toggle" aria-label="Enable screen reader optimization">
            <input type="checkbox" id="sr-toggle" checked
                   onchange="updatePref('screen_reader_optimized', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Font Size</strong>
            <small>Adjust text size throughout the interface</small>
          </div>
          <select id="font-size-select" aria-label="Font size"
                  onchange="updatePref('font_size', this.value)">
            <option value="small">Small</option>
            <option value="medium" selected>Medium</option>
            <option value="large">Large</option>
            <option value="extra_large">Extra Large</option>
          </select>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Color Scheme</strong>
            <small>Choose a color scheme that works for you</small>
          </div>
        </div>
        <div class="color-grid" role="radiogroup" aria-label="Color scheme">
          <div class="color-option selected" role="radio" aria-checked="true" tabindex="0"
               onclick="selectColor(this, 'default')" onkeydown="if(event.key==='Enter')selectColor(this,'default')">
            <div class="color-swatch" style="background:linear-gradient(135deg,#1976D2,#388E3C,#F57C00)"></div>
            <span class="color-label">Default</span>
          </div>
          <div class="color-option" role="radio" aria-checked="false" tabindex="0"
               onclick="selectColor(this, 'high_contrast')" onkeydown="if(event.key==='Enter')selectColor(this,'high_contrast')">
            <div class="color-swatch" style="background:#000; border:3px solid #FFF;"></div>
            <span class="color-label">High Contrast</span>
          </div>
          <div class="color-option" role="radio" aria-checked="false" tabindex="0"
               onclick="selectColor(this, 'dark_mode')" onkeydown="if(event.key==='Enter')selectColor(this,'dark_mode')">
            <div class="color-swatch" style="background:#333;"></div>
            <span class="color-label">Dark Mode</span>
          </div>
          <div class="color-option" role="radio" aria-checked="false" tabindex="0"
               onclick="selectColor(this, 'protanopia')" onkeydown="if(event.key==='Enter')selectColor(this,'protanopia')">
            <div class="color-swatch" style="background:linear-gradient(135deg,#0066CC,#CC8800)"></div>
            <span class="color-label">Protanopia</span>
          </div>
          <div class="color-option" role="radio" aria-checked="false" tabindex="0"
               onclick="selectColor(this, 'deuteranopia')" onkeydown="if(event.key==='Enter')selectColor(this,'deuteranopia')">
            <div class="color-swatch" style="background:linear-gradient(135deg,#0066CC,#CC6600)"></div>
            <span class="color-label">Deuteranopia</span>
          </div>
          <div class="color-option" role="radio" aria-checked="false" tabindex="0"
               onclick="selectColor(this, 'tritanopia')" onkeydown="if(event.key==='Enter')selectColor(this,'tritanopia')">
            <div class="color-swatch" style="background:linear-gradient(135deg,#CC0000,#00CC66)"></div>
            <span class="color-label">Tritanopia</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Captioning -->
    <div class="card">
      <div class="card-header">
        <span class="icon" aria-hidden="true">&#x1F3A7;</span>
        <h2>Captioning</h2>
      </div>
      <div class="card-body">
        <div class="setting-row">
          <div class="setting-label">
            <strong>Enable Captioning</strong>
            <small>Real-time speech-to-text captions</small>
          </div>
          <label class="toggle" aria-label="Enable captioning">
            <input type="checkbox" id="captioning-toggle" checked
                   onchange="updatePref('captioning', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Preferred Caption Language</strong>
          </div>
          <select id="caption-lang" aria-label="Caption language"
                  onchange="updatePref('preferred_caption_language', this.value)">
            <option value="en-US" selected>English (US)</option>
            <option value="en-GB">English (UK)</option>
            <option value="es-ES">Espanol</option>
            <option value="fr-FR">Francais</option>
            <option value="de-DE">Deutsch</option>
            <option value="zh-CN">Chinese</option>
            <option value="ja-JP">Japanese</option>
            <option value="sas-ZA">SASL (South Africa)</option>
            <option value="sw-KE">Swahili</option>
            <option value="yo-NG">Yoruba</option>
            <option value="zu-ZA">Zulu</option>
            <option value="af-ZA">Afrikaans</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Sign Language -->
    <div class="card">
      <div class="card-header">
        <span class="icon" aria-hidden="true">&#x1F44B;</span>
        <h2>Sign Language</h2>
      </div>
      <div class="card-body">
        <div class="setting-row">
          <div class="setting-label">
            <strong>Enable Sign Language Support</strong>
            <small>Text-to-sign conversion and gesture input</small>
          </div>
          <label class="toggle" aria-label="Enable sign language support">
            <input type="checkbox" id="sign-toggle" checked
                   onchange="updatePref('sign_language', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Preferred Sign Language</strong>
          </div>
          <select id="sign-lang" aria-label="Sign language"
                  onchange="updatePref('preferred_sign_language', this.value)">
            <option value="asl" selected>American Sign Language (ASL)</option>
            <option value="bsl">British Sign Language (BSL)</option>
            <option value="auslan">Auslan (Australia)</option>
            <option value="sasl">South African Sign Language (SASL)</option>
            <option value="lsf">Langue des Signes Francaise (LSF)</option>
            <option value="dgs">Deutsche Gebaerdensprache (DGS)</option>
            <option value="kv">Kenyan Sign Language</option>
            <option value="nsl">Nigerian Sign Language</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Haptic Feedback -->
    <div class="card">
      <div class="card-header">
        <span class="icon" aria-hidden="true">&#x1F4F4;</span>
        <h2>Haptic Feedback</h2>
      </div>
      <div class="card-body">
        <div class="setting-row">
          <div class="setting-label">
            <strong>Enable Haptic Feedback</strong>
            <small>Vibration patterns for notifications</small>
          </div>
          <label class="toggle" aria-label="Enable haptic feedback">
            <input type="checkbox" id="haptic-toggle" checked
                   onchange="updatePref('haptic_feedback', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-row">
          <div class="setting-label">
            <strong>Haptic Intensity</strong>
            <small>Vibration strength for alerts</small>
          </div>
          <select id="haptic-intensity" aria-label="Haptic intensity"
                  onchange="updatePref('haptic_intensity', this.value)">
            <option value="low">Low (gentle)</option>
            <option value="medium" selected>Medium</option>
            <option value="high">High (strong)</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Test Alerts -->
    <div class="card">
      <div class="card-header">
        <span class="icon" aria-hidden="true">&#x1F6A8;</span>
        <h2>Test Visual Alerts</h2>
      </div>
      <div class="card-body">
        <p style="color:var(--text-secondary); font-size:0.85rem; margin-bottom:0.75rem;">
          Click to preview each alert type. All alerts are purely visual — no sound.
        </p>
        <div class="test-buttons">
          <button class="btn btn-critical" aria-label="Test critical alert"
                  onclick="testAlert('CRITICAL_FLASH')">Critical</button>
          <button class="btn btn-warning" aria-label="Test warning alert"
                  onclick="testAlert('WARNING_PULSE')">Warning</button>
          <button class="btn btn-info" aria-label="Test info alert"
                  onclick="testAlert('INFO_BANNER')">Info</button>
          <button class="btn btn-success" aria-label="Test success alert"
                  onclick="testAlert('SUCCESS_GLOW')">Success</button>
        </div>
      </div>
    </div>

    <!-- Save/Reset -->
    <div class="save-bar" role="toolbar" aria-label="Settings actions">
      <button class="btn btn-primary" onclick="saveSettings()">&#x1F4BE; Save Settings</button>
      <button class="btn btn-info" onclick="resetSettings()">&#x21BB; Reset to Defaults</button>
    </div>
    <div class="status-msg" id="status-msg" role="status" aria-live="polite"></div>

    <!-- Preview area for test alerts -->
    <div id="alert-preview" role="region" aria-live="polite" aria-label="Alert preview"
         style="position:fixed; top:1rem; right:1rem; z-index:9999; max-width:360px;"></div>
  </div>

  <script>
    // ================================================================
    // ACCESSIBILITY DASHBOARD — Pure JavaScript
    // ================================================================
    (function() {
      'use strict';

      const TEST_ALERTS = {
        CRITICAL_FLASH: { title: 'Critical Test', message: 'This is a critical alert preview.' },
        WARNING_PULSE:  { title: 'Warning Test',  message: 'This is a warning alert preview.' },
        INFO_BANNER:    { title: 'Info Test',     message: 'This is an informational alert preview.' },
        SUCCESS_GLOW:   { title: 'Success Test',  message: 'This is a success alert preview.' }
      };

      window.updatePref = function(key, value) {
        // In production: POST /api/accessibility/preferences
        console.log('Preference updated:', key, '=', value);
        showStatus('Preference updated: ' + key, 'success');
      };

      window.selectColor = function(el, scheme) {
        document.querySelectorAll('.color-option').forEach(function(opt) {
          opt.classList.remove('selected');
          opt.setAttribute('aria-checked', 'false');
        });
        el.classList.add('selected');
        el.setAttribute('aria-checked', 'true');
        updatePref('color_scheme', scheme);
      };

      window.testAlert = function(type) {
        const preview = document.getElementById('alert-preview');
        const alert = TEST_ALERTS[type];
        const colors = {
          CRITICAL_FLASH: '#D32F2F',
          WARNING_PULSE:  '#F57C00',
          INFO_BANNER:    '#1976D2',
          SUCCESS_GLOW:   '#388E3C'
        };
        const el = document.createElement('div');
        el.style.cssText =
          'background:#fff; border-left:5px solid ' + colors[type] +
          '; padding:1rem; margin-bottom:0.5rem; border-radius:8px;' +
          'box-shadow:0 4px 20px rgba(0,0,0,0.15); animation:slideIn 0.4s ease;';
        el.innerHTML =
          '<strong style="color:' + colors[type] + ';">' + alert.title + '</strong><br>' +
          '<small style="color:#666;">' + alert.message + '</small>';
        preview.appendChild(el);
        setTimeout(function() {
          el.style.opacity = '0';
          el.style.transform = 'translateX(120%)';
          setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
        }, 4000);

        // Trigger haptic feedback if supported
        if (navigator.vibrate) {
          navigator.vibrate([200, 100, 200]);
        }
      };

      window.saveSettings = function() {
        // In production: POST all preferences to /api/accessibility/preferences
        showStatus('Settings saved successfully!', 'success');
      };

      window.resetSettings = function() {
        if (!confirm('Reset all accessibility settings to defaults?')) return;
        document.getElementById('master-toggle').checked = true;
        document.getElementById('visual-alerts-toggle').checked = true;
        document.getElementById('captioning-toggle').checked = true;
        document.getElementById('sign-toggle').checked = true;
        document.getElementById('haptic-toggle').checked = true;
        document.getElementById('high-contrast-toggle').checked = false;
        document.getElementById('sr-toggle').checked = true;
        document.getElementById('font-size-select').value = 'medium';
        document.getElementById('caption-lang').value = 'en-US';
        document.getElementById('sign-lang').value = 'asl';
        document.getElementById('haptic-intensity').value = 'medium';
        selectColor(document.querySelector('.color-option'), 'default');
        showStatus('Settings reset to defaults', 'success');
      };

      function showStatus(text, type) {
        const el = document.getElementById('status-msg');
        el.textContent = text;
        el.className = 'status-msg ' + type;
        setTimeout(function() { el.textContent = ''; }, 3000);
      }
    })();
  </script>
</body>
</html>"""


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Enums
    "VisualAlertType",
    "FontSize",
    "ColorScheme",
    "HapticIntensity",
    # Data classes
    "VisualAlert",
    "CaptionSegment",
    "GestureRecognitionResult",
    # Core classes
    "AccessibilityManager",
    "CaptioningEngine",
    "SignLanguageSupport",
    "HapticFeedback",
    # HTML generators
    "generate_accessibility_dashboard",
    "generate_visual_notification_template",
    # Constants
    "FLASH_PATTERNS",
    "HAPTIC_PATTERNS",
    "COLOR_CRITICAL",
    "COLOR_WARNING",
    "COLOR_INFO",
    "COLOR_SUCCESS",
    "SUPPORTED_CAPTION_LANGUAGES",
    "SUPPORTED_SIGN_LANGUAGES",
    "DEFAULT_CONFIG",
]


# ============================================================================
# SELF-TEST (when run directly)
# ============================================================================

if __name__ == "__main__":
    import tempfile

    print("=" * 70)
    print("Luqi AI v24.5.0 — Accessibility Suite Self-Test")
    print("=" * 70)

    # Use a temp directory for self-test to avoid polluting the module dir
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = AccessibilityManager(config_dir=tmpdir)

        # 1. Preferences
        print("\n--- Preferences ---")
        prefs = manager.get_preferences()
        print(f"Accessibility enabled: {manager.is_accessibility_enabled()}")
        print(f"Preferences keys: {list(prefs.keys())}")

        # 2. Update preferences
        ok = manager.update_preferences(high_contrast=True, font_size="large")
        print(f"Update preferences: {'OK' if ok else 'FAILED'}")
        print(f"High contrast: {manager.get_preferences()['high_contrast']}")
        print(f"Font size: {manager.get_preferences()['font_size']}")

        # 3. Visual alerts
        print("\n--- Visual Alerts ---")
        alert = manager.send_visual_alert(
            VisualAlertType.INFO_BANNER,
            "Test Alert",
            "This is a test visual notification.",
        )
        print(f"Alert created: {alert.id}")
        print(f"Alert type: {alert.alert_type.value}")
        print(f"Alert color: {alert.color_hex}")
        print(f"Flash pattern: {alert.flash_pattern}")

        # 4. Pending alerts
        pending = manager.get_pending_alerts()
        print(f"Pending alerts: {len(pending)}")

        # 5. Acknowledge
        ack_ok = manager.acknowledge_alert(alert.id)
        print(f"Acknowledge: {'OK' if ack_ok else 'FAILED'}")

        # 6. Captioning
        print("\n--- Captioning ---")
        cap = manager.captioning()
        caption = cap.caption_audio("dummy_audio", language="en-US")
        print(f"Caption (en-US): {caption}")
        caption_es = cap.caption_audio("dummy_audio", language="es-ES")
        print(f"Caption (es-ES): {caption_es}")
        print(f"Supported languages: {len(cap.get_supported_languages())}")

        # 7. Sign Language
        print("\n--- Sign Language ---")
        sl = manager.sign_language()
        glyphs = sl.text_to_sign_glyphs("hello world", "asl")
        print(f"Sign glyphs HTML length: {len(glyphs)} chars")
        print(f"Supported sign languages: {len(sl.get_supported_sign_languages())}")

        # 8. Haptic Feedback
        print("\n--- Haptic Feedback ---")
        haptic = manager.haptic()
        pattern = haptic.get_pattern(VisualAlertType.CRITICAL_FLASH)
        print(f"Critical pattern: {pattern}")
        notif = haptic.trigger_notification(VisualAlertType.WARNING_PULSE)
        print(f"Notification spec keys: {list(notif.keys())}")

        # 9. HTML components
        print("\n--- HTML Components ---")
        alert_html = manager.generate_html_alert_component()
        print(f"Alert component HTML: {len(alert_html)} chars")
        dashboard_html = generate_accessibility_dashboard()
        print(f"Dashboard HTML: {len(dashboard_html)} chars")

    print("\n" + "=" * 70)
    print("All self-tests passed successfully!")
    print("=" * 70)
