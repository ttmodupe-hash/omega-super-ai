#!/usrenv/bin python3
"""Luqi AI v24 -- Digital Wellness API Endpoints

REST endpoints for the Digital Wellness & Fatigue Prevention System.
Provides: activity tracking, fatigue scoring, break suggestions, wellness tips,
usage analytics, focus mode, Pomodoro timer, screen time goals, and insights.

Endpoints: 18 total
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger("luqi.wellness.api")


def _success_response(data: Any, message: str = "") -> Dict[str, Any]:
    """Standardized success response envelope."""
    return {"success": True, "message": message, "data": data}


def _error_response(message: str, code: str = "wellness_error", status_code: int = 400) -> JSONResponse:
    """Standardized error response envelope."""
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


# ═══════════════════════════════════════════════════════════════════
# Activity Tracking
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/wellness/track")
async def wellness_track_activity(request: Request) -> JSONResponse:
    """Track user activity for wellness analysis.

    Body: {"user_id": str, "feature": str, "duration_ms": int, "cognitive_load": str}
    """
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")
        feature = body.get("feature", "general")
        duration_ms = int(body.get("duration_ms", 0))
        cognitive_load = body.get("cognitive_load", "medium")

        from backend.digital_wellness import wellness_engine
        wellness_engine.track_activity(user_id, feature, duration_ms, cognitive_load)

        return JSONResponse(content=_success_response(None, "Activity tracked"))
    except Exception as exc:
        logger.error("Wellness track error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Wellness Status & Fatigue Score
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/status")
async def wellness_status(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get current wellness status including fatigue score and recommendations."""
    try:
        from backend.digital_wellness import wellness_engine
        status = wellness_engine.get_status(user_id)
        return JSONResponse(content=_success_response(status.to_dict()))
    except Exception as exc:
        logger.error("Wellness status error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness")
async def wellness_root() -> JSONResponse:
    """List all available wellness endpoints."""
    endpoints = [
        {"method": "POST", "path": "/api/wellness/track", "description": "Track user activity"},
        {"method": "GET", "path": "/api/wellness/status", "description": "Get wellness status & fatigue score"},
        {"method": "GET", "path": "/api/wellness/break", "description": "Get break suggestion"},
        {"method": "POST", "path": "/api/wellness/break/record", "description": "Record a break was taken"},
        {"method": "GET", "path": "/api/wellness/tip", "description": "Get contextual wellness tip"},
        {"method": "GET", "path": "/api/wellness/tips/all", "description": "List wellness tip categories"},
        {"method": "GET", "path": "/api/wellness/usage", "description": "Get usage report"},
        {"method": "POST", "path": "/api/wellness/goals", "description": "Set screen time goals"},
        {"method": "GET", "path": "/api/wellness/goals", "description": "Get current goals"},
        {"method": "POST", "path": "/api/wellness/focus", "description": "Toggle focus mode"},
        {"method": "GET", "path": "/api/wellness/focus", "description": "Get focus mode status"},
        {"method": "POST", "path": "/api/wellness/focus/pomodoro", "description": "Control Pomodoro timer"},
        {"method": "POST", "path": "/api/wellness/preferences", "description": "Update preferences"},
        {"method": "GET", "path": "/api/wellness/preferences", "description": "Get preferences"},
        {"method": "GET", "path": "/api/wellness/insights", "description": "Get personalized insights"},
        {"method": "GET", "path": "/api/wellness/wind-down", "description": "Get wind-down status"},
        {"method": "POST", "path": "/api/wellness/eye-break/record", "description": "Record 20-20-20 completion"},
        {"method": "GET", "path": "/api/wellness/self-test", "description": "Run self-tests"},
    ]
    return JSONResponse(content=_success_response(endpoints, "Digital Wellness API v24.3.0"))


# ═══════════════════════════════════════════════════════════════════
# Break Suggestions
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/break")
async def wellness_break_suggestion(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get a personalized break suggestion based on current fatigue level."""
    try:
        from backend.digital_wellness import wellness_engine
        suggestion = wellness_engine.get_break_suggestion(user_id)
        return JSONResponse(content=_success_response(suggestion.to_dict()))
    except Exception as exc:
        logger.error("Break suggestion error: %s", exc)
        return _error_response(str(exc))


@app.post("/api/wellness/break/record")
async def wellness_record_break(request: Request) -> JSONResponse:
    """Record that a user took a break."""
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")
        break_type = body.get("break_type", "short")
        duration_seconds = int(body.get("duration_seconds", 300))

        from backend.digital_wellness import wellness_engine
        wellness_engine.record_break(user_id, break_type, duration_seconds)

        return JSONResponse(content=_success_response(None, "Break recorded. Great job taking care of yourself!"))
    except Exception as exc:
        logger.error("Record break error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Wellness Tips
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/tip")
async def wellness_tip(
    user_id: str = Query("anonymous"),
    category: Optional[str] = Query(None),
) -> JSONResponse:
    """Get a contextual wellness tip. Optionally filter by category."""
    try:
        from backend.digital_wellness import wellness_engine
        tip = wellness_engine.get_wellness_tip(user_id, category)
        return JSONResponse(content=_success_response(tip.to_dict()))
    except Exception as exc:
        logger.error("Wellness tip error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness/tips/all")
async def wellness_tip_categories() -> JSONResponse:
    """List all wellness tip categories with counts."""
    try:
        from backend.digital_wellness import wellness_engine
        categories = wellness_engine.get_tip_categories()
        return JSONResponse(content=_success_response(categories))
    except Exception as exc:
        logger.error("Tip categories error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Usage Analytics
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/usage")
async def wellness_usage(
    user_id: str = Query("anonymous"),
    period: str = Query("today"),
) -> JSONResponse:
    """Get usage analytics for a time period (today, week, month)."""
    try:
        from backend.digital_wellness import wellness_engine
        report = wellness_engine.get_usage_report(user_id, period)
        return JSONResponse(content=_success_response(report.to_dict()))
    except Exception as exc:
        logger.error("Usage report error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Screen Time Goals
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/wellness/goals")
async def wellness_set_goals(request: Request) -> JSONResponse:
    """Set screen time goals.

    Body: {"user_id": str, "daily_limit_minutes": int, "break_reminders": bool,
           "focus_sessions_per_day": int, "eye_break_reminders": bool}
    """
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")

        from backend.digital_wellness import wellness_engine, ScreenTimeGoals
        goals = ScreenTimeGoals(
            daily_limit_minutes=body.get("daily_limit_minutes", 480),
            break_reminders=body.get("break_reminders", True),
            focus_sessions_per_day=body.get("focus_sessions_per_day", 4),
            eye_break_reminders=body.get("eye_break_reminders", True),
        )
        wellness_engine.set_goals(user_id, goals)

        return JSONResponse(content=_success_response(None, "Goals saved"))
    except Exception as exc:
        logger.error("Set goals error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness/goals")
async def wellness_get_goals(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get current screen time goals."""
    try:
        from backend.digital_wellness import wellness_engine
        goals = wellness_engine.get_goals(user_id)
        return JSONResponse(content=_success_response(goals.to_dict() if goals else None))
    except Exception as exc:
        logger.error("Get goals error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Focus Mode
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/wellness/focus")
async def wellness_focus_toggle(request: Request) -> JSONResponse:
    """Toggle focus mode on/off.

    Body: {"user_id": str, "enabled": bool, "session_goal": str}
    """
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")
        enabled = bool(body.get("enabled", False))
        session_goal = body.get("session_goal", "")

        from backend.digital_wellness import wellness_engine
        wellness_engine.toggle_focus_mode(user_id, enabled, session_goal)

        status = "enabled" if enabled else "disabled"
        return JSONResponse(content=_success_response(None, f"Focus mode {status}"))
    except Exception as exc:
        logger.error("Focus toggle error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness/focus")
async def wellness_focus_status(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get focus mode status and Pomodoro timer state."""
    try:
        from backend.digital_wellness import wellness_engine
        status = wellness_engine.get_focus_status(user_id)
        return JSONResponse(content=_success_response(status.to_dict()))
    except Exception as exc:
        logger.error("Focus status error: %s", exc)
        return _error_response(str(exc))


@app.post("/api/wellness/focus/pomodoro")
async def wellness_pomodoro(request: Request) -> JSONResponse:
    """Control the Pomodoro timer.

    Body: {"user_id": str, "action": str}
    Actions: "start", "pause", "reset", "skip"
    """
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")
        action = body.get("action", "")

        from backend.digital_wellness import wellness_engine
        result = wellness_engine.control_pomodoro(user_id, action)

        return JSONResponse(content=_success_response(result.to_dict()))
    except Exception as exc:
        logger.error("Pomodoro error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Preferences
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/wellness/preferences")
async def wellness_set_preferences(request: Request) -> JSONResponse:
    """Update wellness preferences.

    Body: {"user_id": str, "break_sound_enabled": bool,
           "browser_notifications": bool, "wind_down_hour": int,
           "reminder_frequency": str}
    """
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")

        from backend.digital_wellness import wellness_engine, WellnessPreferences
        prefs = WellnessPreferences(
            break_sound_enabled=body.get("break_sound_enabled", True),
            browser_notifications=body.get("browser_notifications", True),
            wind_down_hour=body.get("wind_down_hour", 21),
            reminder_frequency=body.get("reminder_frequency", "normal"),
        )
        wellness_engine.set_preferences(user_id, prefs)

        return JSONResponse(content=_success_response(None, "Preferences saved"))
    except Exception as exc:
        logger.error("Set preferences error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness/preferences")
async def wellness_get_preferences(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get current wellness preferences."""
    try:
        from backend.digital_wellness import wellness_engine
        prefs = wellness_engine.get_preferences(user_id)
        return JSONResponse(content=_success_response(prefs.to_dict()))
    except Exception as exc:
        logger.error("Get preferences error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Insights & Wind-Down
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/insights")
async def wellness_insights(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get personalized wellness insights and recommendations."""
    try:
        from backend.digital_wellness import wellness_engine
        insights = wellness_engine.get_insights(user_id)
        return JSONResponse(content=_success_response(insights))
    except Exception as exc:
        logger.error("Insights error: %s", exc)
        return _error_response(str(exc))


@app.get("/api/wellness/wind-down")
async def wellness_wind_down(
    user_id: str = Query("anonymous"),
) -> JSONResponse:
    """Get wind-down mode status and sleep hygiene suggestions."""
    try:
        from backend.digital_wellness import wellness_engine
        status = wellness_engine.get_wind_down_status(user_id)
        return JSONResponse(content=_success_response(status.to_dict()))
    except Exception as exc:
        logger.error("Wind-down error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Eye Break Tracking
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/wellness/eye-break/record")
async def wellness_record_eye_break(request: Request) -> JSONResponse:
    """Record completion of a 20-20-20 eye break."""
    try:
        body = json.loads(await request.body())
        user_id = body.get("user_id", "anonymous")

        from backend.digital_wellness import wellness_engine
        streak = wellness_engine.record_eye_break(user_id)

        return JSONResponse(content=_success_response(
            {"streak": streak},
            f"Great job! 20-20-20 streak: {streak} {'🔥' if streak >= 5 else ''}"
        ))
    except Exception as exc:
        logger.error("Eye break record error: %s", exc)
        return _error_response(str(exc))


# ═══════════════════════════════════════════════════════════════════
# Self-Test
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/wellness/self-test")
async def wellness_self_test() -> JSONResponse:
    """Run validation self-tests for the wellness system."""
    try:
        from backend.digital_wellness import wellness_engine
        results = wellness_engine.self_test()
        return JSONResponse(content=_success_response(results))
    except Exception as exc:
        logger.error("Self-test error: %s", exc)
        return _error_response(str(exc))


logger.info("v24.3.0 Digital Wellness endpoints loaded: 18 endpoints")
