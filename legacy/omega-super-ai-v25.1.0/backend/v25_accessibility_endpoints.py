"""
Luqi AI v24.5.0 — Accessibility Endpoints for Deaf & Hard-of-Hearing Users
===========================================================================

Registers all accessibility endpoints with the shared FastAPI app.

Endpoints:
  - GET  /api/accessibility/status         — Current settings
  - POST /api/accessibility/preferences    — Update preferences
  - GET  /api/accessibility/alerts         — Pending visual alerts
  - POST /api/accessibility/alerts/ack     — Acknowledge alert
  - GET  /api/accessibility/captioning/supported — Supported languages
  - POST /api/accessibility/caption        — Caption audio
  - GET  /api/accessibility/sign-languages — Supported sign languages
  - POST /api/accessibility/text-to-sign   — Convert text to sign glyphs
  - GET  /api/accessibility/haptic-patterns — Available patterns
  - GET  /api/accessibility/dashboard      — HTML settings page
  - WS   /ws/accessibility-alerts          — Real-time visual alert stream

Part of Luqi AI v24.5.0 by Limitless Telecoms — Accessible AI for Everyone
"""

try:
    from backend.router import app
except ImportError:
    app = None

try:
    from backend.accessibility_deaf import (
        AccessibilityManager,
        CaptioningEngine,
        SignLanguageSupport,
        HapticFeedback,
        generate_accessibility_dashboard,
    )
    _ACCESS_AVAILABLE = True
except ImportError as _e:
    _ACCESS_AVAILABLE = False

if _ACCESS_AVAILABLE and app is not None:
    manager = AccessibilityManager()
    manager.register_endpoints(app)
