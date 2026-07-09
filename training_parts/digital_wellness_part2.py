#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luqi AI v24.4.0 — Digital Wellness Module (Part 2 of 2)
=======================================================
Part 2 contains API endpoint functions and integration helpers.
This file is meant to be concatenated with part 1 to form the complete module.

Usage:
    from digital_wellness import (
        record_screen_time, get_daily_screen_time,
        record_posture, get_posture_trends,
        record_eye_strain, record_metric,
        start_focus_session, end_focus_session, get_focus_stats,
        schedule_break_reminder, acknowledge_break_reminder, get_break_compliance,
        get_user_alerts, acknowledge_alert,
        generate_daily_summary, get_daily_summary,
        get_wellness_settings, update_wellness_settings,
        get_overall_wellness_score, get_wellness_tips,
        WellnessCategory, AlertLevel, FocusStatus,
    )

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Import from part 1 (when files are merged)
# from .digital_wellness import (
#     _screen_time_db, _posture_db, _eye_strain_db, _focus_sessions_db,
#     _break_reminders_db, _alerts_db, _daily_summaries_db, _settings_db,
#     _metrics_db, _get_or_create_settings, _create_alert, _score_to_grade,
#     ScreenTimeRecord, PostureRecord, EyeStrainRecord, FocusSession,
#     BreakReminder, WellnessAlert, DailyWellnessSummary,
#     WellnessCategory, AlertLevel, FocusStatus,
#     WellnessError, RecordNotFoundError, InvalidMetricError,
#     WELLNESS_TIPS
# )


# ============================================================================
# API ENDPOINT FUNCTIONS
# ============================================================================

def api_record_screen_time(user_id: str, data: dict) -> dict:
    """API wrapper for recording screen time.

    Args:
        user_id: User identifier.
        data: Request data with application, category, duration_minutes.

    Returns:
        dict: Recorded screen time with ID.
    """
    from . import digital_wellness as dw
    return dw.record_screen_time(
        user_id=user_id,
        application=data.get("application", "unknown"),
        category=data.get("category", "other"),
        duration_minutes=float(data.get("duration_minutes", 0)),
        idle_time_minutes=float(data.get("idle_time_minutes", 0)),
    )


def api_get_screen_time_summary(user_id: str, date_str: str = None) -> dict:
    """API wrapper for getting daily screen time summary.

    Args:
        user_id: User identifier.
        date_str: Optional date override.

    Returns:
        dict: Screen time summary.
    """
    from . import digital_wellness as dw
    return dw.get_daily_screen_time(user_id, date_str)


def api_record_posture(user_id: str, data: dict) -> dict:
    """API wrapper for recording posture.

    Args:
        user_id: User identifier.
        data: Posture measurement data.

    Returns:
        dict: Posture record with any alerts.
    """
    from . import digital_wellness as dw
    return dw.record_posture(
        user_id=user_id,
        posture_score=float(data.get("posture_score", 70)),
        back_angle=float(data.get("back_angle", 90)),
        neck_angle=float(data.get("neck_angle", 45)),
        screen_distance_inches=float(data.get("screen_distance_inches", 20)),
        seated_hours=float(data.get("seated_hours", 0)),
    )


def api_record_eye_strain(user_id: str, data: dict) -> dict:
    """API wrapper for recording eye strain.

    Args:
        user_id: User identifier.
        data: Eye strain measurement data.

    Returns:
        dict: Eye strain record with alerts.
    """
    from . import digital_wellness as dw
    return dw.record_eye_strain(
        user_id=user_id,
        eye_strain_score=float(data.get("eye_strain_score", 30)),
        blink_rate_per_min=float(data.get("blink_rate_per_min", 15)),
        screen_brightness=float(data.get("screen_brightness", 70)),
        ambient_light_lux=float(data.get("ambient_light_lux", 300)),
        blue_light_exposure_hours=float(data.get("blue_light_exposure_hours", 4)),
    )


def api_start_focus(user_id: str, data: dict = None) -> dict:
    """API wrapper to start a focus session.

    Args:
        user_id: User identifier.
        data: Optional session configuration.

    Returns:
        dict: Session details.
    """
    from . import digital_wellness as dw
    data = data or {}
    return dw.start_focus_session(
        user_id=user_id,
        planned_duration_min=int(data.get("planned_duration_min", 25)),
        technique=data.get("technique", "pomodoro"),
        tags=data.get("tags", []),
    )


def api_end_focus(user_id: str, session_id: str = None) -> dict:
    """API wrapper to end a focus session.

    Args:
        user_id: User identifier.
        session_id: Optional specific session ID.

    Returns:
        dict: Completed session summary.
    """
    from . import digital_wellness as dw
    return dw.end_focus_session(user_id, session_id)


def api_get_focus_history(user_id: str, days: int = 7) -> dict:
    """API wrapper for focus history and stats.

    Args:
        user_id: User identifier.
        days: Number of days to analyze.

    Returns:
        dict: Focus sessions and statistics.
    """
    from . import digital_wellness as dw
    since = datetime.utcnow() - timedelta(days=days)
    sessions = dw.get_focus_sessions(user_id, since=since)
    stats = dw.get_focus_stats(user_id, days=days)
    return {
        "sessions": sessions,
        "statistics": stats,
    }


def api_schedule_break(user_id: str, data: dict) -> dict:
    """API wrapper for scheduling break reminders.

    Args:
        user_id: User identifier.
        data: Break configuration.

    Returns:
        dict: Scheduled reminder.
    """
    from . import digital_wellness as dw
    scheduled_at = None
    if "minutes_from_now" in data:
        scheduled_at = datetime.utcnow() + timedelta(minutes=int(data["minutes_from_now"]))
    return dw.schedule_break_reminder(
        user_id=user_id,
        reminder_type=data.get("reminder_type", "movement"),
        scheduled_at=scheduled_at,
    )


def api_acknowledge_break(reminder_id: str) -> dict:
    """API wrapper to acknowledge a break reminder.

    Args:
        reminder_id: Reminder identifier.

    Returns:
        dict: Updated reminder.
    """
    from . import digital_wellness as dw
    return dw.acknowledge_break_reminder(reminder_id)


def api_get_breaks_status(user_id: str) -> dict:
    """API wrapper for break compliance status.

    Args:
        user_id: User identifier.

    Returns:
        dict: Break compliance data.
    """
    from . import digital_wellness as dw
    return dw.get_break_compliance(user_id, days=1)


def api_get_alerts(user_id: str, category: str = None, level: str = None) -> list:
    """API wrapper for getting wellness alerts.

    Args:
        user_id: User identifier.
        category: Optional category filter.
        level: Optional severity filter.

    Returns:
        list: Wellness alerts.
    """
    from . import digital_wellness as dw
    cat_enum = None
    if category:
        try:
            cat_enum = dw.WellnessCategory(category)
        except ValueError:
            pass
    level_enum = None
    if level:
        try:
            level_enum = dw.AlertLevel(level)
        except ValueError:
            pass
    return dw.get_user_alerts(user_id, category=cat_enum, level=level_enum)


def api_acknowledge_alert(alert_id: str) -> dict:
    """API wrapper to acknowledge an alert.

    Args:
        alert_id: Alert identifier.

    Returns:
        dict: Updated alert.
    """
    from . import digital_wellness as dw
    return dw.acknowledge_alert(alert_id)


def api_get_daily_summary(user_id: str, date_str: str = None) -> dict:
    """API wrapper for daily wellness summary.

    Args:
        user_id: User identifier.
        date_str: Optional date override.

    Returns:
        dict: Daily summary.
    """
    from . import digital_wellness as dw
    return dw.get_daily_summary(user_id, date_str)


def api_get_wellness_score(user_id: str) -> dict:
    """API wrapper for overall wellness score.

    Args:
        user_id: User identifier.

    Returns:
        dict: Overall wellness with breakdown.
    """
    from . import digital_wellness as dw
    return dw.get_overall_wellness_score(user_id)


def api_get_settings(user_id: str) -> dict:
    """API wrapper for getting wellness settings.

    Args:
        user_id: User identifier.

    Returns:
        dict: Current settings.
    """
    from . import digital_wellness as dw
    return dw.get_wellness_settings(user_id)


def api_update_settings(user_id: str, data: dict) -> dict:
    """API wrapper for updating wellness settings.

    Args:
        user_id: User identifier.
        data: Settings to update.

    Returns:
        dict: Updated settings.
    """
    from . import digital_wellness as dw
    return dw.update_wellness_settings(user_id, **data)


def api_get_tips(category: str = None, count: int = 3) -> list:
    """API wrapper for wellness tips.

    Args:
        category: Optional category filter.
        count: Number of tips.

    Returns:
        list: Wellness tips.
    """
    from . import digital_wellness as dw
    cat_enum = None
    if category:
        try:
            cat_enum = dw.WellnessCategory(category)
        except ValueError:
            pass
    return dw.get_wellness_tips(category=cat_enum, count=count)


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def batch_record_metrics(user_id: str, metrics: list) -> list:
    """Record multiple wellness metrics in a batch.

    Args:
        user_id: User identifier.
        metrics: List of metric dicts with category, value, unit.

    Returns:
        list: Recorded metrics.
    """
    from . import digital_wellness as dw
    results = []
    for metric in metrics:
        try:
            result = dw.record_metric(
                user_id=user_id,
                category=dw.WellnessCategory(metric["category"]),
                value=float(metric["value"]),
                unit=metric.get("unit", "count"),
                source=metric.get("source", "api"),
                metadata=metric.get("metadata", {}),
            )
            results.append({"success": True, "data": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    return results


def get_weekly_report(user_id: str) -> dict:
    """Generate comprehensive weekly wellness report.

    Args:
        user_id: User identifier.

    Returns:
        dict: Weekly wellness report.
    """
    from . import digital_wellness as dw
    today = datetime.utcnow()
    daily_summaries = []

    for i in range(7):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            summary = dw.get_daily_summary(user_id, date_str)
            daily_summaries.append(summary)
        except Exception:
            pass

    if not daily_summaries:
        return {
            "user_id": user_id,
            "period": "last_7_days",
            "message": "No wellness data recorded yet.",
            "recommendations": ["Start tracking your wellness metrics today!"],
        }

    avg_score = sum(s["overall_score"] for s in daily_summaries) / len(daily_summaries)
    total_screen = sum(s["screen_time_total_min"] for s in daily_summaries)
    avg_posture = sum(s["posture_score_avg"] for s in daily_summaries) / len(daily_summaries)
    total_focus = sum(s["focus_sessions_completed"] for s in daily_summaries)
    avg_break = sum(s["break_compliance_rate"] for s in daily_summaries) / len(daily_summaries)

    return {
        "user_id": user_id,
        "period": "last_7_days",
        "days_with_data": len(daily_summaries),
        "average_overall_score": round(avg_score, 1),
        "total_screen_time_hours": round(total_screen / 60, 1),
        "average_posture_score": round(avg_posture, 1),
        "total_focus_sessions": total_focus,
        "average_break_compliance": round(avg_break, 1),
        "daily_breakdown": daily_summaries,
        "recommendations": _generate_weekly_recommendations(avg_score, avg_posture, avg_break),
    }


def _generate_weekly_recommendations(score: float, posture: float, breaks: float) -> list:
    """Generate weekly recommendations based on averages."""
    recs = []
    if score < 60:
        recs.append("Your overall wellness score needs attention. Focus on consistent break schedules.")
    elif score < 80:
        recs.append("Good progress! Small improvements in posture and breaks will boost your score.")
    else:
        recs.append("Excellent wellness habits! Keep maintaining your routine.")

    if posture < 60:
        recs.append("Posture is a concern. Consider ergonomic equipment and posture reminders.")
    if breaks < 50:
        recs.append("Break compliance is low. Set up automated reminders to take regular breaks.")
    if not recs:
        recs.append("You're doing great! Continue your current wellness practices.")
    return recs


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def sync_with_security_training(user_id: str) -> dict:
    """Sync wellness data with security training progress.

    Args:
        user_id: User identifier.

    Returns:
        dict: Combined wellness and training status.
    """
    from . import digital_wellness as dw

    wellness = dw.get_overall_wellness_score(user_id)
    daily = dw.get_daily_summary(user_id)
    focus = dw.get_focus_stats(user_id)

    return {
        "user_id": user_id,
        "wellness_score": wellness.get("overall_score", 0),
        "grade": wellness.get("grade", "N/A"),
        "screen_time_hours": round(daily.get("screen_time_total_min", 0) / 60, 1),
        "focus_sessions_today": daily.get("focus_sessions_completed", 0),
        "focus_hours_7d": focus.get("total_focus_hours", 0),
        "productivity_score": focus.get("avg_productivity_score", 0),
        "break_compliance": daily.get("break_compliance_rate", 0),
        "recommendations": daily.get("recommendations", []),
        "synced_at": datetime.utcnow().isoformat(),
    }


def get_dashboard_data(user_id: str) -> dict:
    """Get all data needed for the wellness dashboard.

    Args:
        user_id: User identifier.

    Returns:
        dict: Complete dashboard dataset.
    """
    from . import digital_wellness as dw

    return {
        "wellness_score": dw.get_overall_wellness_score(user_id),
        "daily_summary": dw.get_daily_summary(user_id),
        "screen_time": dw.get_daily_screen_time(user_id),
        "focus_stats": dw.get_focus_stats(user_id, days=7),
        "break_compliance": dw.get_break_compliance(user_id, days=7),
        "posture_trends": dw.get_posture_trends(user_id, days=7),
        "alerts": dw.get_user_alerts(user_id, limit=10),
        "tips": dw.get_wellness_tips(count=3),
        "settings": dw.get_wellness_settings(user_id),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# FASTAPI ROUTER SETUP (if using FastAPI)
# ============================================================================

def create_wellness_router():
    """Create FastAPI router for wellness endpoints.

    Returns:
        APIRouter: Configured router with all wellness endpoints.

    Example:
        from fastapi import FastAPI
        from digital_wellness_endpoints import create_wellness_router

        app = FastAPI()
        app.include_router(create_wellness_router(), prefix="/api/wellness")
    """
    try:
        from fastapi import APIRouter, HTTPException, Depends
        from pydantic import BaseModel, Field
    except ImportError:
        raise ImportError("FastAPI and Pydantic required. Install: pip install fastapi pydantic")

    router = APIRouter()

    class ScreenTimeRequest(BaseModel):
        application: str = Field(..., min_length=1)
        category: str = "other"
        duration_minutes: float = Field(..., gt=0)
        idle_time_minutes: float = 0

    class PostureRequest(BaseModel):
        posture_score: float = Field(..., ge=0, le=100)
        back_angle: float = 90.0
        neck_angle: float = 45.0
        screen_distance_inches: float = 20.0
        seated_hours: float = 0.0

    class EyeStrainRequest(BaseModel):
        eye_strain_score: float = Field(..., ge=0, le=100)
        blink_rate_per_min: float = 15.0
        screen_brightness: float = 70.0
        ambient_light_lux: float = 300.0
        blue_light_exposure_hours: float = 4.0

    class FocusStartRequest(BaseModel):
        planned_duration_min: int = 25
        technique: str = "pomodoro"
        tags: list = []

    class BreakScheduleRequest(BaseModel):
        reminder_type: str = "movement"
        minutes_from_now: int = 30

    class SettingsUpdateRequest(BaseModel):
        screen_time_goal_min: Optional[int] = None
        break_interval_min: Optional[int] = None
        eye_strain_threshold_min: Optional[int] = None
        posture_reminder_enabled: Optional[bool] = None
        focus_session_default_min: Optional[int] = None
        daily_focus_goal: Optional[int] = None

    @router.post("/screen-time")
    def record_screen_time_endpoint(user_id: str, request: ScreenTimeRequest):
        from . import digital_wellness as dw
        try:
            return dw.record_screen_time(user_id, **request.dict())
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/screen-time")
    def get_screen_time_endpoint(user_id: str, date: str = None):
        from . import digital_wellness as dw
        return dw.get_daily_screen_time(user_id, date)

    @router.post("/posture")
    def record_posture_endpoint(user_id: str, request: PostureRequest):
        from . import digital_wellness as dw
        try:
            return dw.record_posture(user_id, **request.dict())
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/eye-strain")
    def record_eye_strain_endpoint(user_id: str, request: EyeStrainRequest):
        from . import digital_wellness as dw
        try:
            return dw.record_eye_strain(user_id, **request.dict())
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/focus/start")
    def start_focus_endpoint(user_id: str, request: FocusStartRequest = None):
        from . import digital_wellness as dw
        req_data = request.dict() if request else {}
        return dw.start_focus_session(user_id, **req_data)

    @router.post("/focus/end")
    def end_focus_endpoint(user_id: str, session_id: str = None):
        from . import digital_wellness as dw
        try:
            return dw.end_focus_session(user_id, session_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/focus/history")
    def get_focus_history_endpoint(user_id: str, days: int = 7):
        from . import digital_wellness as dw
        return {
            "sessions": dw.get_focus_sessions(user_id),
            "statistics": dw.get_focus_stats(user_id, days=days),
        }

    @router.post("/breaks/schedule")
    def schedule_break_endpoint(user_id: str, request: BreakScheduleRequest):
        from . import digital_wellness as dw
        scheduled_at = datetime.utcnow() + timedelta(minutes=request.minutes_from_now)
        return dw.schedule_break_reminder(user_id, request.reminder_type, scheduled_at)

    @router.post("/breaks/{reminder_id}/acknowledge")
    def acknowledge_break_endpoint(reminder_id: str):
        from . import digital_wellness as dw
        try:
            return dw.acknowledge_break_reminder(reminder_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/breaks/compliance")
    def get_break_compliance_endpoint(user_id: str, days: int = 7):
        from . import digital_wellness as dw
        return dw.get_break_compliance(user_id, days=days)

    @router.get("/alerts")
    def get_alerts_endpoint(user_id: str, category: str = None, level: str = None):
        from . import digital_wellness as dw
        cat = None
        if category:
            try:
                cat = dw.WellnessCategory(category)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        lvl = None
        if level:
            try:
                lvl = dw.AlertLevel(level)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
        return dw.get_user_alerts(user_id, category=cat, level=lvl)

    @router.post("/alerts/{alert_id}/acknowledge")
    def acknowledge_alert_endpoint(alert_id: str):
        from . import digital_wellness as dw
        try:
            return dw.acknowledge_alert(alert_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/daily-summary")
    def get_daily_summary_endpoint(user_id: str, date: str = None):
        from . import digital_wellness as dw
        return dw.get_daily_summary(user_id, date)

    @router.get("/score")
    def get_wellness_score_endpoint(user_id: str):
        from . import digital_wellness as dw
        return dw.get_overall_wellness_score(user_id)

    @router.get("/settings")
    def get_settings_endpoint(user_id: str):
        from . import digital_wellness as dw
        return dw.get_wellness_settings(user_id)

    @router.put("/settings")
    def update_settings_endpoint(user_id: str, request: SettingsUpdateRequest):
        from . import digital_wellness as dw
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        return dw.update_wellness_settings(user_id, **update_data)

    @router.get("/tips")
    def get_tips_endpoint(category: str = None, count: int = 3):
        from . import digital_wellness as dw
        cat = None
        if category:
            try:
                cat = dw.WellnessCategory(category)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        return dw.get_wellness_tips(category=cat, count=count)

    @router.get("/dashboard")
    def get_dashboard_endpoint(user_id: str):
        return get_dashboard_data(user_id)

    @router.get("/weekly-report")
    def get_weekly_report_endpoint(user_id: str):
        return get_weekly_report(user_id)

    return router


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Data models
    "WellnessMetric", "ScreenTimeRecord", "PostureRecord", "EyeStrainRecord",
    "FocusSession", "BreakReminder", "WellnessAlert", "DailyWellnessSummary",
    "WellnessSettings", "WellnessCategory", "AlertLevel", "FocusStatus",
    # Exceptions
    "WellnessError", "RecordNotFoundError", "InvalidMetricError",
    # Core functions
    "record_metric", "get_user_metrics",
    "record_screen_time", "get_daily_screen_time",
    "record_posture", "get_posture_trends",
    "record_eye_strain",
    "start_focus_session", "end_focus_session", "get_focus_sessions", "get_focus_stats",
    "schedule_break_reminder", "acknowledge_break_reminder", "get_break_compliance",
    "get_user_alerts", "acknowledge_alert",
    "generate_daily_summary", "get_daily_summary",
    "get_wellness_settings", "update_wellness_settings",
    "get_overall_wellness_score", "get_wellness_tips",
    # API wrappers
    "api_record_screen_time", "api_get_screen_time_summary",
    "api_record_posture", "api_record_eye_strain",
    "api_start_focus", "api_end_focus", "api_get_focus_history",
    "api_schedule_break", "api_acknowledge_break", "api_get_breaks_status",
    "api_get_alerts", "api_acknowledge_alert",
    "api_get_daily_summary", "api_get_wellness_score",
    "api_get_settings", "api_update_settings", "api_get_tips",
    # Batch and reports
    "batch_record_metrics", "get_weekly_report",
    # Integration
    "sync_with_security_training", "get_dashboard_data",
    "create_wellness_router",
]
