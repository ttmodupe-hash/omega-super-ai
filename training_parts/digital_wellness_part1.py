#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luqi AI v24.4.0 — Digital Wellness Module (Part 1 of 2)
=======================================================
Digital wellness tracking, screen time monitoring, posture reminders,
eye strain prevention, focus session management, and productivity analytics.

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# ============================================================================
# ENUMERATIONS
# ============================================================================

class WellnessCategory(str, Enum):
    """Categories of wellness metrics."""
    SCREEN_TIME = "screen_time"
    POSTURE = "posture"
    EYE_STRAIN = "eye_strain"
    FOCUS = "focus"
    BREAKS = "breaks"
    SLEEP = "sleep"
    PHYSICAL_ACTIVITY = "physical_activity"
    MENTAL_WELLNESS = "mental_wellness"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FocusStatus(str, Enum):
    """Focus session status."""
    IDLE = "idle"
    FOCUSING = "focusing"
    BREAK = "break"
    PAUSED = "paused"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class WellnessMetric:
    """A single wellness measurement."""
    id: str
    user_id: str
    category: WellnessCategory
    value: float
    unit: str
    recorded_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "manual"  # manual, sensor, api, inferred
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category.value,
            "value": self.value,
            "unit": self.unit,
            "recorded_at": self.recorded_at.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class ScreenTimeRecord:
    """Screen time tracking record."""
    id: str
    user_id: str
    application: str
    category: str  # browser, ide, communication, entertainment, etc.
    duration_minutes: float
    start_time: datetime
    end_time: Optional[datetime] = None
    idle_time_minutes: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "application": self.application,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "idle_time_minutes": self.idle_time_minutes,
        }


@dataclass
class PostureRecord:
    """Posture tracking record."""
    id: str
    user_id: str
    posture_score: float  # 0-100
    back_angle: float  # degrees
    neck_angle: float  # degrees
    screen_distance_inches: float
    seated_hours: float
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "posture_score": self.posture_score,
            "back_angle": self.back_angle,
            "neck_angle": self.neck_angle,
            "screen_distance_inches": self.screen_distance_inches,
            "seated_hours": self.seated_hours,
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass
class EyeStrainRecord:
    """Eye strain monitoring record."""
    id: str
    user_id: str
    eye_strain_score: float  # 0-100, higher = more strain
    blink_rate_per_min: float
    screen_brightness: float  # percentage
    ambient_light_lux: float
    blue_light_exposure_hours: float
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "eye_strain_score": self.eye_strain_score,
            "blink_rate_per_min": self.blink_rate_per_min,
            "screen_brightness": self.screen_brightness,
            "ambient_light_lux": self.ambient_light_lux,
            "blue_light_exposure_hours": self.blue_light_exposure_hours,
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass
class FocusSession:
    """Focus session tracking."""
    id: str
    user_id: str
    status: FocusStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    planned_duration_min: int = 25  # default Pomodoro
    actual_duration_min: float = 0.0
    interruptions: int = 0
    productivity_score: float = 0.0  # 0-100
    technique: str = "pomodoro"  # pomodoro, timebox, flow
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "planned_duration_min": self.planned_duration_min,
            "actual_duration_min": self.actual_duration_min,
            "interruptions": self.interruptions,
            "productivity_score": self.productivity_score,
            "technique": self.technique,
            "tags": self.tags,
        }


@dataclass
class BreakReminder:
    """Break reminder record."""
    id: str
    user_id: str
    reminder_type: str  # posture, eye, movement, hydration
    scheduled_at: datetime
    acknowledged_at: Optional[datetime] = None
    dismissed: bool = False
    snooze_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "reminder_type": self.reminder_type,
            "scheduled_at": self.scheduled_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "dismissed": self.dismissed,
            "snooze_count": self.snooze_count,
        }


@dataclass
class WellnessAlert:
    """Wellness alert/notification."""
    id: str
    user_id: str
    category: WellnessCategory
    level: AlertLevel
    message: str
    recommendation: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    dismissed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category.value,
            "level": self.level.value,
            "message": self.message,
            "recommendation": self.recommendation,
            "triggered_at": self.triggered_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "dismissed": self.dismissed,
        }


@dataclass
class DailyWellnessSummary:
    """Aggregated daily wellness report."""
    user_id: str
    date: str  # YYYY-MM-DD
    overall_score: float  # 0-100
    screen_time_total_min: float
    posture_score_avg: float
    eye_strain_avg: float
    focus_sessions_completed: int
    focus_sessions_total: int
    break_compliance_rate: float  # percentage
    alerts_triggered: int
    alerts_acknowledged: int
    top_applications: List[dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "date": self.date,
            "overall_score": self.overall_score,
            "screen_time_total_min": self.screen_time_total_min,
            "posture_score_avg": self.posture_score_avg,
            "eye_strain_avg": self.eye_strain_avg,
            "focus_sessions_completed": self.focus_sessions_completed,
            "focus_sessions_total": self.focus_sessions_total,
            "break_compliance_rate": self.break_compliance_rate,
            "alerts_triggered": self.alerts_triggered,
            "alerts_acknowledged": self.alerts_acknowledged,
            "top_applications": self.top_applications,
            "recommendations": self.recommendations,
        }


@dataclass
class WellnessSettings:
    """User wellness configuration."""
    user_id: str
    screen_time_goal_min: int = 360  # 6 hours
    break_interval_min: int = 30
    eye_strain_threshold_min: int = 20
    posture_reminder_enabled: bool = True
    focus_session_default_min: int = 25
    pomodoro_break_min: int = 5
    long_break_after_sessions: int = 4
    long_break_min: int = 15
    daily_focus_goal: int = 4
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "screen_time_goal_min": self.screen_time_goal_min,
            "break_interval_min": self.break_interval_min,
            "eye_strain_threshold_min": self.eye_strain_threshold_min,
            "posture_reminder_enabled": self.posture_reminder_enabled,
            "focus_session_default_min": self.focus_session_default_min,
            "pomodoro_break_min": self.pomodoro_break_min,
            "long_break_after_sessions": self.long_break_after_sessions,
            "long_break_min": self.long_break_min,
            "daily_focus_goal": self.daily_focus_goal,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class WellnessError(Exception):
    """Base exception for wellness module."""
    pass


class RecordNotFoundError(WellnessError):
    """Raised when a record is not found."""
    pass


class InvalidMetricError(WellnessError):
    """Raised when metric data is invalid."""
    pass


# ============================================================================
# IN-MEMORY DATA STORES
# ============================================================================

_metrics_db: Dict[str, WellnessMetric] = {}
_screen_time_db: Dict[str, ScreenTimeRecord] = {}
_posture_db: Dict[str, PostureRecord] = {}
_eye_strain_db: Dict[str, EyeStrainRecord] = {}
_focus_sessions_db: Dict[str, FocusSession] = {}
_break_reminders_db: Dict[str, BreakReminder] = {}
_alerts_db: Dict[str, WellnessAlert] = {}
_daily_summaries_db: Dict[str, DailyWellnessSummary] = {}
_settings_db: Dict[str, WellnessSettings] = {}


# ============================================================================
# CORE FUNCTIONS - METRICS
# ============================================================================

def record_metric(user_id: str, category: WellnessCategory, value: float,
                  unit: str, source: str = "manual", metadata: dict = None) -> dict:
    """Record a wellness metric for a user.

    Args:
        user_id: Unique user identifier.
        category: Wellness metric category.
        value: Numeric measurement value.
        unit: Unit of measurement.
        source: Data source (manual, sensor, api, inferred).
        metadata: Additional contextual data.

    Returns:
        dict: Recorded metric with ID and timestamp.

    Raises:
        InvalidMetricError: If value is invalid.
    """
    if value < 0:
        raise InvalidMetricError("Metric value cannot be negative")
    if not user_id:
        raise InvalidMetricError("user_id is required")

    metric = WellnessMetric(
        id=f"met_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        category=category,
        value=value,
        unit=unit,
        source=source,
        metadata=metadata or {},
    )
    _metrics_db[metric.id] = metric
    return metric.to_dict()


def get_user_metrics(user_id: str, category: WellnessCategory = None,
                     since: datetime = None, limit: int = 100) -> list:
    """Get wellness metrics for a user with optional filtering.

    Args:
        user_id: User identifier.
        category: Optional category filter.
        since: Optional datetime filter.
        limit: Maximum results to return.

    Returns:
        list: Filtered wellness metrics.
    """
    results = []
    for metric in _metrics_db.values():
        if metric.user_id != user_id:
            continue
        if category and metric.category != category:
            continue
        if since and metric.recorded_at < since:
            continue
        results.append(metric.to_dict())
    return sorted(results, key=lambda x: x["recorded_at"], reverse=True)[:limit]


# ============================================================================
# CORE FUNCTIONS - SCREEN TIME
# ============================================================================

def record_screen_time(user_id: str, application: str, category: str,
                       duration_minutes: float, idle_time_minutes: float = 0) -> dict:
    """Record screen time for an application.

    Args:
        user_id: User identifier.
        application: Application name.
        category: App category (browser, ide, etc.).
        duration_minutes: Time spent in minutes.
        idle_time_minutes: Idle time within session.

    Returns:
        dict: Screen time record.
    """
    record = ScreenTimeRecord(
        id=f"st_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        application=application,
        category=category,
        duration_minutes=duration_minutes,
        start_time=datetime.utcnow() - timedelta(minutes=duration_minutes),
        idle_time_minutes=idle_time_minutes,
    )
    _screen_time_db[record.id] = record
    return record.to_dict()


def get_daily_screen_time(user_id: str, date_str: str = None) -> dict:
    """Get aggregated daily screen time breakdown.

    Args:
        user_id: User identifier.
        date_str: Date in YYYY-MM-DD format (defaults to today).

    Returns:
        dict: Screen time summary with app breakdown.
    """
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    app_times = defaultdict(float)
    category_times = defaultdict(float)
    total = 0.0

    for record in _screen_time_db.values():
        if record.user_id != user_id:
            continue
        record_date = record.start_time.strftime("%Y-%m-%d")
        if record_date != date_str:
            continue
        active_time = record.duration_minutes - record.idle_time_minutes
        app_times[record.application] += active_time
        category_times[record.category] += active_time
        total += active_time

    top_apps = sorted(
        [{"app": k, "minutes": round(v, 1)} for k, v in app_times.items()],
        key=lambda x: x["minutes"],
        reverse=True,
    )[:10]

    return {
        "user_id": user_id,
        "date": date_str,
        "total_active_minutes": round(total, 1),
        "total_hours": round(total / 60, 1),
        "by_application": top_apps,
        "by_category": {k: round(v, 1) for k, v in category_times.items()},
    }


# ============================================================================
# CORE FUNCTIONS - POSTURE
# ============================================================================

def record_posture(user_id: str, posture_score: float, back_angle: float,
                   neck_angle: float, screen_distance_inches: float,
                   seated_hours: float) -> dict:
    """Record a posture measurement.

    Args:
        user_id: User identifier.
        posture_score: Overall posture score 0-100.
        back_angle: Back angle in degrees.
        neck_angle: Neck angle in degrees.
        screen_distance_inches: Distance from screen in inches.
        seated_hours: Hours spent seated.

    Returns:
        dict: Posture record with alerts if needed.
    """
    record = PostureRecord(
        id=f"pos_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        posture_score=max(0, min(100, posture_score)),
        back_angle=back_angle,
        neck_angle=neck_angle,
        screen_distance_inches=screen_distance_inches,
        seated_hours=seated_hours,
    )
    _posture_db[record.id] = record

    # Generate alerts for poor posture
    alerts = []
    if posture_score < 50:
        alert = _create_alert(
            user_id, WellnessCategory.POSTURE, AlertLevel.CRITICAL,
            "Poor posture detected! Your back angle indicates slouching.",
            "Sit up straight, align your ears with shoulders, and adjust your chair."
        )
        alerts.append(alert.to_dict())
    elif posture_score < 70:
        alert = _create_alert(
            user_id, WellnessCategory.POSTURE, AlertLevel.WARNING,
            "Posture needs improvement. Take a moment to adjust.",
            "Check that your screen is at eye level and feet are flat on the floor."
        )
        alerts.append(alert.to_dict())

    result = record.to_dict()
    if alerts:
        result["alerts"] = alerts
    return result


def get_posture_trends(user_id: str, days: int = 7) -> list:
    """Get posture score trends over time.

    Args:
        user_id: User identifier.
        days: Number of days to look back.

    Returns:
        list: Daily average posture scores.
    """
    since = datetime.utcnow() - timedelta(days=days)
    daily_scores = defaultdict(list)

    for record in _posture_db.values():
        if record.user_id != user_id or record.recorded_at < since:
            continue
        date_key = record.recorded_at.strftime("%Y-%m-%d")
        daily_scores[date_key].append(record.posture_score)

    return [
        {
            "date": date_key,
            "avg_score": round(sum(scores) / len(scores), 1),
            "min_score": round(min(scores), 1),
            "max_score": round(max(scores), 1),
            "readings": len(scores),
        }
        for date_key, scores in sorted(daily_scores.items())
    ]


# ============================================================================
# CORE FUNCTIONS - EYE STRAIN
# ============================================================================

def record_eye_strain(user_id: str, eye_strain_score: float,
                      blink_rate_per_min: float, screen_brightness: float,
                      ambient_light_lux: float, blue_light_exposure_hours: float) -> dict:
    """Record eye strain measurement.

    Args:
        user_id: User identifier.
        eye_strain_score: Strain score 0-100.
        blink_rate_per_min: Blinks per minute.
        screen_brightness: Screen brightness percentage.
        ambient_light_lux: Ambient light in lux.
        blue_light_exposure_hours: Hours of blue light exposure.

    Returns:
        dict: Eye strain record with alerts.
    """
    record = EyeStrainRecord(
        id=f"eye_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        eye_strain_score=max(0, min(100, eye_strain_score)),
        blink_rate_per_min=blink_rate_per_min,
        screen_brightness=screen_brightness,
        ambient_light_lux=ambient_light_lux,
        blue_light_exposure_hours=blue_light_exposure_hours,
    )
    _eye_strain_db[record.id] = record

    alerts = []
    if eye_strain_score > 75:
        alert = _create_alert(
            user_id, WellnessCategory.EYE_STRAIN, AlertLevel.CRITICAL,
            "High eye strain detected! Take a break immediately.",
            "Apply the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds."
        )
        alerts.append(alert.to_dict())
    elif eye_strain_score > 50:
        alert = _create_alert(
            user_id, WellnessCategory.EYE_STRAIN, AlertLevel.WARNING,
            "Moderate eye strain detected.",
            "Blink deliberately, adjust screen brightness, and consider blue light filter."
        )
        alerts.append(alert.to_dict())

    result = record.to_dict()
    if alerts:
        result["alerts"] = alerts
    return result


# ============================================================================
# CORE FUNCTIONS - FOCUS SESSIONS
# ============================================================================

def start_focus_session(user_id: str, planned_duration_min: int = 25,
                        technique: str = "pomodoro", tags: list = None) -> dict:
    """Start a new focus session.

    Args:
        user_id: User identifier.
        planned_duration_min: Planned session duration.
        technique: Focus technique (pomodoro, timebox, flow).
        tags: Session tags/labels.

    Returns:
        dict: Session details.
    """
    # End any active session first
    _end_active_session(user_id)

    session = FocusSession(
        id=f"foc_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        status=FocusStatus.FOCUSING,
        start_time=datetime.utcnow(),
        planned_duration_min=planned_duration_min,
        technique=technique,
        tags=tags or [],
    )
    _focus_sessions_db[session.id] = session
    return session.to_dict()


def end_focus_session(user_id: str, session_id: str = None) -> dict:
    """End an active focus session.

    Args:
        user_id: User identifier.
        session_id: Specific session ID (ends most recent if not provided).

    Returns:
        dict: Completed session summary.
    """
    session = None
    if session_id:
        session = _focus_sessions_db.get(session_id)
    else:
        # Find most recent active session
        active = [
            s for s in _focus_sessions_db.values()
            if s.user_id == user_id and s.status == FocusStatus.FOCUSING
        ]
        if active:
            session = max(active, key=lambda s: s.start_time)

    if not session:
        raise RecordNotFoundError("No active focus session found")

    session.end_time = datetime.utcnow()
    session.actual_duration_min = (session.end_time - session.start_time).total_seconds() / 60
    session.status = FocusStatus.IDLE

    # Calculate productivity score
    planned = session.planned_duration_min
    actual = session.actual_duration_min
    if actual >= planned * 0.8 and session.interruptions <= 2:
        session.productivity_score = 90 + min(10, (planned - session.interruptions * 5))
    elif actual >= planned * 0.5:
        session.productivity_score = 60 + (actual / planned) * 30
    else:
        session.productivity_score = max(10, (actual / planned) * 60)

    return session.to_dict()


def get_focus_sessions(user_id: str, since: datetime = None, limit: int = 50) -> list:
    """Get focus session history for a user.

    Args:
        user_id: User identifier.
        since: Filter by date.
        limit: Maximum results.

    Returns:
        list: Focus session records.
    """
    results = []
    for session in _focus_sessions_db.values():
        if session.user_id != user_id:
            continue
        if since and session.start_time < since:
            continue
        results.append(session.to_dict())
    return sorted(results, key=lambda x: x["start_time"], reverse=True)[:limit]


def get_focus_stats(user_id: str, days: int = 7) -> dict:
    """Get focus statistics for a time period.

    Args:
        user_id: User identifier.
        days: Number of days to analyze.

    Returns:
        dict: Focus statistics summary.
    """
    since = datetime.utcnow() - timedelta(days=days)
    sessions = [
        s for s in _focus_sessions_db.values()
        if s.user_id == user_id and s.start_time >= since
    ]

    completed = [s for s in sessions if s.end_time is not None]
    total_planned = sum(s.planned_duration_min for s in completed)
    total_actual = sum(s.actual_duration_min for s in completed)
    avg_productivity = sum(s.productivity_score for s in completed) / len(completed) if completed else 0

    return {
        "user_id": user_id,
        "period_days": days,
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "total_focus_hours": round(total_actual / 60, 1),
        "avg_session_min": round(total_actual / len(completed), 1) if completed else 0,
        "avg_productivity_score": round(avg_productivity, 1),
        "total_interruptions": sum(s.interruptions for s in sessions),
        "completion_rate": round(len(completed) / max(len(sessions), 1) * 100, 1),
    }


def _end_active_session(user_id: str) -> None:
    """End any currently active focus session for user."""
    for session in _focus_sessions_db.values():
        if session.user_id == user_id and session.status == FocusStatus.FOCUSING:
            session.status = FocusStatus.IDLE
            session.end_time = datetime.utcnow()
            session.actual_duration_min = (
                session.end_time - session.start_time
            ).total_seconds() / 60


# ============================================================================
# CORE FUNCTIONS - BREAK REMINDERS
# ============================================================================

def schedule_break_reminder(user_id: str, reminder_type: str,
                            scheduled_at: datetime = None) -> dict:
    """Schedule a break reminder.

    Args:
        user_id: User identifier.
        reminder_type: Type of break (posture, eye, movement, hydration).
        scheduled_at: When to trigger (defaults to now + interval).

    Returns:
        dict: Reminder record.
    """
    if scheduled_at is None:
        settings = _get_or_create_settings(user_id)
        scheduled_at = datetime.utcnow() + timedelta(minutes=settings.break_interval_min)

    reminder = BreakReminder(
        id=f"brk_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        reminder_type=reminder_type,
        scheduled_at=scheduled_at,
    )
    _break_reminders_db[reminder.id] = reminder
    return reminder.to_dict()


def acknowledge_break_reminder(reminder_id: str) -> dict:
    """Mark a break reminder as acknowledged.

    Args:
        reminder_id: Reminder identifier.

    Returns:
        dict: Updated reminder.
    """
    if reminder_id not in _break_reminders_db:
        raise RecordNotFoundError(f"Reminder '{reminder_id}' not found")

    reminder = _break_reminders_db[reminder_id]
    reminder.acknowledged_at = datetime.utcnow()
    return reminder.to_dict()


def get_break_compliance(user_id: str, days: int = 7) -> dict:
    """Calculate break reminder compliance rate.

    Args:
        user_id: User identifier.
        days: Days to analyze.

    Returns:
        dict: Compliance statistics.
    """
    since = datetime.utcnow() - timedelta(days=days)
    reminders = [
        r for r in _break_reminders_db.values()
        if r.user_id == user_id and r.scheduled_at >= since
    ]

    total = len(reminders)
    acknowledged = sum(1 for r in reminders if r.acknowledged_at is not None)
    dismissed = sum(1 for r in reminders if r.dismissed)
    snoozed = sum(r.snooze_count for r in reminders)

    return {
        "user_id": user_id,
        "period_days": days,
        "total_reminders": total,
        "acknowledged": acknowledged,
        "dismissed": dismissed,
        "total_snoozes": snoozed,
        "compliance_rate": round(acknowledged / max(total, 1) * 100, 1),
    }


# ============================================================================
# CORE FUNCTIONS - ALERTS
# ============================================================================

def _create_alert(user_id: str, category: WellnessCategory, level: AlertLevel,
                  message: str, recommendation: str) -> WellnessAlert:
    """Internal: Create and store a wellness alert."""
    alert = WellnessAlert(
        id=f"alr_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        category=category,
        level=level,
        message=message,
        recommendation=recommendation,
    )
    _alerts_db[alert.id] = alert
    return alert


def get_user_alerts(user_id: str, category: WellnessCategory = None,
                    level: AlertLevel = None, acknowledged_only: bool = False,
                    limit: int = 50) -> list:
    """Get wellness alerts for a user.

    Args:
        user_id: User identifier.
        category: Optional category filter.
        level: Optional severity filter.
        acknowledged_only: Only show acknowledged alerts.
        limit: Maximum results.

    Returns:
        list: Wellness alerts.
    """
    results = []
    for alert in _alerts_db.values():
        if alert.user_id != user_id:
            continue
        if category and alert.category != category:
            continue
        if level and alert.level != level:
            continue
        if acknowledged_only and alert.acknowledged_at is None:
            continue
        results.append(alert.to_dict())
    return sorted(results, key=lambda x: x["triggered_at"], reverse=True)[:limit]


def acknowledge_alert(alert_id: str) -> dict:
    """Acknowledge a wellness alert.

    Args:
        alert_id: Alert identifier.

    Returns:
        dict: Updated alert.
    """
    if alert_id not in _alerts_db:
        raise RecordNotFoundError(f"Alert '{alert_id}' not found")

    alert = _alerts_db[alert_id]
    alert.acknowledged_at = datetime.utcnow()
    return alert.to_dict()


# ============================================================================
# CORE FUNCTIONS - DAILY SUMMARIES
# ============================================================================

def generate_daily_summary(user_id: str, date_str: str = None) -> dict:
    """Generate comprehensive daily wellness summary.

    Args:
        user_id: User identifier.
        date_str: Date in YYYY-MM-DD format (defaults to today).

    Returns:
        dict: Daily wellness summary with recommendations.
    """
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Aggregate screen time
    screen_data = get_daily_screen_time(user_id, date_str)
    total_screen = screen_data["total_active_minutes"]

    # Aggregate posture
    posture_records = [
        r for r in _posture_db.values()
        if r.user_id == user_id and r.recorded_at.strftime("%Y-%m-%d") == date_str
    ]
    avg_posture = sum(r.posture_score for r in posture_records) / len(posture_records) if posture_records else 75.0

    # Aggregate eye strain
    eye_records = [
        r for r in _eye_strain_db.values()
        if r.user_id == user_id and r.recorded_at.strftime("%Y-%m-%d") == date_str
    ]
    avg_eye_strain = sum(r.eye_strain_score for r in eye_records) / len(eye_records) if eye_records else 30.0

    # Focus sessions
    day_start = datetime.strptime(date_str, "%Y-%m-%d")
    day_end = day_start + timedelta(days=1)
    sessions = [
        s for s in _focus_sessions_db.values()
        if s.user_id == user_id and day_start <= s.start_time < day_end
    ]
    completed_focus = sum(1 for s in sessions if s.end_time is not None)

    # Break compliance
    break_data = get_break_compliance(user_id)

    # Alerts
    day_alerts = [
        a for a in _alerts_db.values()
        if a.user_id == user_id and a.triggered_at.strftime("%Y-%m-%d") == date_str
    ]
    acknowledged_alerts = sum(1 for a in day_alerts if a.acknowledged_at is not None)

    # Calculate overall score
    screen_score = max(0, 100 - (total_screen / 360) * 30)  # Penalty > 6 hours
    posture_component = avg_posture * 0.25
    eye_component = max(0, 100 - avg_eye_strain) * 0.25
    focus_component = min(100, completed_focus * 25)
    break_component = break_data["compliance_rate"]

    overall = round(
        (screen_score * 0.2 + posture_component + eye_component +
         focus_component * 0.15 + break_component * 0.15), 1
    )
    overall = max(0, min(100, overall))

    # Generate recommendations
    recommendations = []
    if total_screen > 480:
        recommendations.append("Screen time exceeds 8 hours. Consider taking more frequent breaks.")
    if avg_posture < 60:
        recommendations.append("Posture needs attention. Try ergonomic adjustments.")
    if avg_eye_strain > 50:
        recommendations.append("High eye strain detected. Apply the 20-20-20 rule regularly.")
    if completed_focus < 2:
        recommendations.append("Few focus sessions today. Try Pomodoro technique for better productivity.")
    if break_data["compliance_rate"] < 50:
        recommendations.append("Low break compliance. Set up reminders to maintain wellness.")
    if not recommendations:
        recommendations.append("Great job! Your digital wellness is on track today.")

    summary = DailyWellnessSummary(
        user_id=user_id,
        date=date_str,
        overall_score=overall,
        screen_time_total_min=total_screen,
        posture_score_avg=round(avg_posture, 1),
        eye_strain_avg=round(avg_eye_strain, 1),
        focus_sessions_completed=completed_focus,
        focus_sessions_total=len(sessions),
        break_compliance_rate=break_data["compliance_rate"],
        alerts_triggered=len(day_alerts),
        alerts_acknowledged=acknowledged_alerts,
        top_applications=screen_data["by_application"][:5],
        recommendations=recommendations,
    )
    _daily_summaries_db[f"{user_id}:{date_str}"] = summary
    return summary.to_dict()


def get_daily_summary(user_id: str, date_str: str = None) -> dict:
    """Get a previously generated daily summary.

    Args:
        user_id: User identifier.
        date_str: Date in YYYY-MM-DD format.

    Returns:
        dict: Daily summary (generates if not exists).
    """
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    key = f"{user_id}:{date_str}"
    if key not in _daily_summaries_db:
        return generate_daily_summary(user_id, date_str)
    return _daily_summaries_db[key].to_dict()


# ============================================================================
# CORE FUNCTIONS - SETTINGS
# ============================================================================

def _get_or_create_settings(user_id: str) -> WellnessSettings:
    """Get or create wellness settings for user."""
    if user_id not in _settings_db:
        _settings_db[user_id] = WellnessSettings(user_id=user_id)
    return _settings_db[user_id]


def get_wellness_settings(user_id: str) -> dict:
    """Get user's wellness settings."""
    settings = _get_or_create_settings(user_id)
    return settings.to_dict()


def update_wellness_settings(user_id: str, **kwargs) -> dict:
    """Update wellness settings.

    Args:
        user_id: User identifier.
        **kwargs: Settings to update.

    Returns:
        dict: Updated settings.
    """
    settings = _get_or_create_settings(user_id)

    allowed_fields = [
        "screen_time_goal_min", "break_interval_min", "eye_strain_threshold_min",
        "posture_reminder_enabled", "focus_session_default_min",
        "pomodoro_break_min", "long_break_after_sessions", "long_break_min",
        "daily_focus_goal",
    ]

    for field in allowed_fields:
        if field in kwargs:
            setattr(settings, field, kwargs[field])

    settings.updated_at = datetime.utcnow()
    return settings.to_dict()


# ============================================================================
# CORE FUNCTIONS - OVERALL WELLNESS SCORE
# ============================================================================

def get_overall_wellness_score(user_id: str) -> dict:
    """Calculate comprehensive wellness score.

    Args:
        user_id: User identifier.

    Returns:
        dict: Overall wellness with breakdown.
    """
    # Get latest daily summary
    today_summary = get_daily_summary(user_id)

    # Get focus stats (last 7 days)
    focus_stats = get_focus_stats(user_id, days=7)

    # Get break compliance
    break_stats = get_break_compliance(user_id, days=7)

    # Get posture trends
    posture_trends = get_posture_trends(user_id, days=7)
    avg_posture = sum(p["avg_score"] for p in posture_trends) / len(posture_trends) if posture_trends else 75

    # Component scores
    screen = max(0, min(100, 100 - (today_summary["screen_time_total_min"] / 480) * 25))
    posture = max(0, min(100, avg_posture))
    eye = max(0, min(100, 100 - today_summary["eye_strain_avg"]))
    focus = max(0, min(100, focus_stats["avg_productivity_score"]))
    breaks = break_stats["compliance_rate"]

    # Weighted overall
    overall = round(
        screen * 0.20 + posture * 0.25 + eye * 0.20 +
        focus * 0.15 + breaks * 0.20, 1
    )

    return {
        "user_id": user_id,
        "overall_score": overall,
        "grade": _score_to_grade(overall),
        "breakdown": {
            "screen_time": {"score": round(screen, 1), "weight": 0.20},
            "posture": {"score": round(posture, 1), "weight": 0.25},
            "eye_health": {"score": round(eye, 1), "weight": 0.20},
            "focus_productivity": {"score": round(focus, 1), "weight": 0.15},
            "break_compliance": {"score": round(breaks, 1), "weight": 0.20},
        },
        "focus_stats_7d": focus_stats,
        "break_compliance_7d": break_stats,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


# ============================================================================
# TIPS AND RECOMMENDATIONS
# ============================================================================

WELLNESS_TIPS = {
    WellnessCategory.SCREEN_TIME: [
        "Set app time limits for social media and entertainment apps.",
        "Use grayscale mode on your phone to reduce dopamine hits.",
        "Keep devices out of the bedroom for better sleep quality.",
        "Schedule 'no-screen' blocks during your most productive hours.",
    ],
    WellnessCategory.POSTURE: [
        "Position your screen at arm's length and eye level.",
        "Use an external keyboard and laptop stand for better ergonomics.",
        "Set a timer to check your posture every 15 minutes.",
        "Consider a standing desk or desk converter for variety.",
    ],
    WellnessCategory.EYE_STRAIN: [
        "Follow the 20-20-20 rule: Every 20 min, look 20 feet away for 20 seconds.",
        "Blink deliberately when working on screens.",
        "Adjust screen brightness to match ambient lighting.",
        "Use artificial tears if you experience dry eyes.",
    ],
    WellnessCategory.FOCUS: [
        "Try the Pomodoro Technique: 25 min work, 5 min break.",
        "Use website blockers during focus sessions.",
        "Turn off non-essential notifications.",
        "Create a dedicated workspace free from distractions.",
    ],
    WellnessCategory.BREAKS: [
        "Set hourly reminders to stand and stretch.",
        "Use break time for short walks or hydration.",
        "Practice deep breathing exercises during breaks.",
        "Step outside for natural light exposure.",
    ],
}


def get_wellness_tips(category: WellnessCategory = None, count: int = 3) -> list:
    """Get wellness tips by category.

    Args:
        category: Optional category filter.
        count: Number of tips to return.

    Returns:
        list: Wellness tips.
    """
    import random

    if category:
        tips = WELLNESS_TIPS.get(category, [])
        return random.sample(tips, min(count, len(tips)))

    all_tips = []
    for cat, tips in WELLNESS_TIPS.items():
        all_tips.extend([{"category": cat.value, "tip": t} for t in tips])
    random.shuffle(all_tips)
    return all_tips[:count]


# ============================================================================
# INIT
# ============================================================================

# Pre-populate with sample tips accessible via API
