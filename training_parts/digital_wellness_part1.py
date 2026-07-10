"""Luqi AI v24 -- Digital Wellness & Fatigue Prevention System

Promotes healthy digital habits through gentle, non-intrusive awareness:
- Session time tracking with smart break reminders
- Digital fatigue score calculation (cognitive load estimation)
- Eye strain prevention (20-20-20 rule)
- Mindfulness break suggestions
- Usage analytics and patterns
- Focus mode (distraction-free)
- Wind-down mode (before sleep)
- Wellness tips engine
- Screen time goals and limits
- Posture and movement reminders
- Information diet (content quality scoring)
- Notification batching recommendations

The system is designed to be HELPFUL, not annoying. Reminders are:
- Gentle and positive (never scolding)
- Contextually aware (not during critical tasks)
- Adaptive (learns user's patterns)
- Optional (user can customize or disable)

Usage:
    from backend.digital_wellness import wellness_engine

    # Track page view
    wellness_engine.track_activity(user_id, "chat", duration_ms=120000)

    # Get wellness status
    status = wellness_engine.get_status(user_id)

    # Get next break suggestion
    suggestion = wellness_engine.get_break_suggestion(user_id)

Architecture:
    The system is composed of several subsystems that work together:

    1. SessionTracker: Records and categorizes user activities
    2. FatigueCalculator: Computes a composite fatigue score (0-100)
    3. BreakEngine: Generates personalized break recommendations
    4. EyeStrainTracker: Implements the 20-20-20 rule
    5. FocusModeManager: Handles Pomodoro and distraction-free mode
    6. WindDownManager: Evening wind-down and sleep hygiene
    7. UsageAnalytics: Aggregates usage patterns and trends
    8. ScreenTimeGoals: Tracks progress against user-defined limits
    9. WellnessTipsEngine: Curates and serves contextual tips
    10. WellnessEngine: Orchestrates all subsystems (singleton)

All subsystems are designed to be stateless with respect to the global
application state; per-user data is stored in memory using a lightweight
cache with TTL eviction to prevent unbounded growth.

Author: Luqi AI Engineering Team
Version: 24.0.0
License: Proprietary
"""

from __future__ import annotations

import enum
import json
import logging
import math
import random
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, ClassVar, Deque, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------

logger = logging.getLogger("luqi.wellness")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class Constants:
    """Wellness system configuration constants."""

    # Fatigue score thresholds
    FATIGUE_FRESH: int = 30
    FATIGUE_MILD: int = 50
    FATIGUE_MODERATE: int = 70
    FATIGUE_HIGH: int = 85
    FATIGUE_CRITICAL: int = 100

    # Break intervals (in minutes of continuous screen time)
    MICRO_BREAK_INTERVAL: int = 20
    SHORT_BREAK_INTERVAL: int = 60
    LONG_BREAK_INTERVAL: int = 240

    # 20-20-20 rule
    EYE_BREAK_INTERVAL_MINUTES: int = 20
    EYE_BREAK_DISTANCE_FEET: int = 20
    EYE_BREAK_DURATION_SECONDS: int = 20

    # Focus mode Pomodoro presets (work/break in minutes)
    POMODORO_CLASSIC: Tuple[int, int] = (25, 5)
    POMODORO_LONG: Tuple[int, int] = (50, 10)
    POMODORO_SHORT: Tuple[int, int] = (15, 3)

    # Wind-down defaults
    WIND_DOWN_START_HOUR: int = 21  # 9 PM
    WIND_DOWN_END_HOUR: int = 7  # 7 AM

    # Screen time goal defaults (in minutes)
    DEFAULT_DAILY_LIMIT_MINUTES: int = 480  # 8 hours
    DEFAULT_SINGLE_SESSION_LIMIT_MINUTES: int = 120  # 2 hours

    # Cache TTL for user data (in seconds)
    USER_DATA_TTL_SECONDS: int = 86400  # 24 hours

    # Maximum activity history entries per user
    MAX_ACTIVITY_HISTORY: int = 10000

    # Maximum tip history entries per user
    MAX_TIP_HISTORY: int = 500

    # Rolling analysis windows (in minutes)
    ROLLING_WINDOW_SHORT: int = 30
    ROLLING_WINDOW_MEDIUM: int = 60
    ROLLING_WINDOW_LONG: int = 240

    # Fatigue score calculation weights
    WEIGHT_SCREEN_TIME: float = 0.30
    WEIGHT_COGNITIVE_LOAD: float = 0.25
    WEIGHT_SESSION_LENGTH: float = 0.20
    WEIGHT_TIME_OF_DAY: float = 0.15
    WEIGHT_INTERACTION_FREQ: float = 0.10


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CognitiveLoad(str, enum.Enum):
    """Cognitive load classification for activities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FatigueLevel(str, enum.Enum):
    """Human-readable fatigue levels."""

    FRESH = "fresh"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class BreakType(str, enum.Enum):
    """Types of breaks recommended by the system."""

    MICRO = "micro"
    SHORT = "short"
    LONG = "long"
    SESSION_END = "session_end"


class TipCategory(str, enum.Enum):
    """Wellness tip categories."""

    EYE_HEALTH = "eye_health"
    POSTURE = "posture"
    MENTAL_CLARITY = "mental_clarity"
    SLEEP = "sleep"
    HYDRATION = "hydration"
    MOVEMENT = "movement"
    STRESS = "stress"
    SOCIAL = "social"


class FocusModeState(str, enum.Enum):
    """States for the focus mode manager."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class PomodoroPhase(str, enum.Enum):
    """Phases of a Pomodoro cycle."""

    WORK = "work"
    BREAK = "break"
    IDLE = "idle"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class ActivityRecord:
    """A single user activity record.

    Attributes:
        feature: The feature or page the user was interacting with.
        duration_ms: Duration of the activity in milliseconds.
        cognitive_load: Estimated cognitive load of the activity.
        timestamp: When the activity started.
    """

    feature: str
    duration_ms: int
    cognitive_load: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "feature": self.feature,
            "duration_ms": self.duration_ms,
            "cognitive_load": self.cognitive_load,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WellnessStatus:
    """Current wellness status for a user.

    Attributes:
        fatigue_score: Composite fatigue score (0-100).
        fatigue_level: Human-readable fatigue level.
        screen_time_minutes: Total screen time today in minutes.
        current_session_minutes: Current continuous session length in minutes.
        last_break_minutes_ago: Minutes since last break.
        eye_strain_compliance: 20-20-20 compliance rate (0.0-1.0).
        break_suggested: Whether a break is currently recommended.
        break_urgency: Urgency of break recommendation (0-3).
        message: Gentle status message for the user.
        next_break_estimate_minutes: Estimated minutes until next break needed.
        wind_down_active: Whether wind-down mode is currently active.
        focus_mode_active: Whether focus mode is currently active.
    """

    fatigue_score: int
    fatigue_level: str
    screen_time_minutes: int
    current_session_minutes: int
    last_break_minutes_ago: int
    eye_strain_compliance: float
    break_suggested: bool
    break_urgency: int
    message: str
    next_break_estimate_minutes: int
    wind_down_active: bool
    focus_mode_active: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class BreakSuggestion:
    """A personalized break suggestion.

    Attributes:
        break_type: Type of break (micro, short, long, session_end).
        duration_seconds: Recommended duration in seconds.
        title: Short, friendly title for the break activity.
        description: What to do during the break.
        benefit: Science-backed explanation of why this helps.
        message: Gentle notification message.
        fatigue_score: Current fatigue score when suggestion was made.
    """

    break_type: str
    duration_seconds: int
    title: str
    description: str
    benefit: str
    message: str
    fatigue_score: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class WellnessTip:
    """A contextual wellness tip.

    Attributes:
        category: Tip category.
        title: Short tip title.
        content: Full tip content.
        action_item: Optional actionable step.
        source: Scientific source or general recommendation.
    """

    category: str
    title: str
    content: str
    action_item: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class ScreenTimeGoals:
    """User-defined screen time goals.

    Attributes:
        daily_limit_minutes: Total daily screen time limit.
        single_session_limit_minutes: Max minutes per continuous session.
        break_reminder_interval_minutes: Minutes between break reminders.
        eye_break_enabled: Whether 20-20-20 reminders are enabled.
        wind_down_enabled: Whether wind-down mode is enabled.
        wind_down_start_hour: Hour to start wind-down (24h format).
        focus_mode_default_preset: Default Pomodoro preset name.
    """

    daily_limit_minutes: int = Constants.DEFAULT_DAILY_LIMIT_MINUTES
    single_session_limit_minutes: int = (
        Constants.DEFAULT_SINGLE_SESSION_LIMIT_MINUTES
    )
    break_reminder_interval_minutes: int = Constants.SHORT_BREAK_INTERVAL
    eye_break_enabled: bool = True
    wind_down_enabled: bool = True
    wind_down_start_hour: int = Constants.WIND_DOWN_START_HOUR
    focus_mode_default_preset: str = "classic"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class FocusStatus:
    """Current focus mode status.

    Attributes:
        state: Current focus mode state.
        pomodoro_phase: Current Pomodoro phase.
        pomodoro_work_minutes: Work interval in minutes.
        pomodoro_break_minutes: Break interval in minutes.
        elapsed_seconds: Seconds elapsed in current phase.
        remaining_seconds: Seconds remaining in current phase.
        sessions_completed: Number of completed Pomodoro sessions today.
        daily_goal: Daily Pomodoro session goal.
    """

    state: str
    pomodoro_phase: str
    pomodoro_work_minutes: int
    pomodoro_break_minutes: int
    elapsed_seconds: int
    remaining_seconds: int
    sessions_completed: int
    daily_goal: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class UsageReport:
    """Usage analytics report.

    Attributes:
        period: Report period (today, weekly, monthly).
        total_screen_time_minutes: Total screen time in period.
        feature_breakdown: Screen time per feature.
        peak_hours: Hours with highest usage.
        average_session_minutes: Average session length.
        longest_session_minutes: Longest single session.
        breaks_taken: Number of breaks taken.
        breaks_suggested: Number of breaks suggested.
        break_compliance_rate: Break compliance rate (0.0-1.0).
        average_fatigue_score: Average fatigue score.
        fatigue_trend: Fatigue score trend description.
        insights: Personalized insights.
    """

    period: str
    total_screen_time_minutes: int
    feature_breakdown: Dict[str, int]
    peak_hours: List[int]
    average_session_minutes: float
    longest_session_minutes: int
    breaks_taken: int
    breaks_suggested: int
    break_compliance_rate: float
    average_fatigue_score: float
    fatigue_trend: str
    insights: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "period": self.period,
            "total_screen_time_minutes": self.total_screen_time_minutes,
            "feature_breakdown": self.feature_breakdown,
            "peak_hours": self.peak_hours,
            "average_session_minutes": self.average_session_minutes,
            "longest_session_minutes": self.longest_session_minutes,
            "breaks_taken": self.breaks_taken,
            "breaks_suggested": self.breaks_suggested,
            "break_compliance_rate": self.break_compliance_rate,
            "average_fatigue_score": self.average_fatigue_score,
            "fatigue_trend": self.fatigue_trend,
            "insights": self.insights,
        }


@dataclass
class WellnessPreferences:
    """User wellness preferences for personalization.

    Attributes:
        break_notifications_enabled: Whether break notifications are enabled.
        eye_break_notifications_enabled: Whether eye break notifications are enabled.
        tip_notifications_enabled: Whether wellness tip notifications are enabled.
        focus_mode_sound_enabled: Whether focus mode uses sounds.
        wind_down_auto_enabled: Whether wind-down starts automatically.
        posture_reminders_enabled: Whether posture reminders are enabled.
        movement_reminders_enabled: Whether movement reminders are enabled.
        notification_tone: Preferred notification tone style.
        tip_frequency: How often to show tips (low, medium, high).
    """

    break_notifications_enabled: bool = True
    eye_break_notifications_enabled: bool = True
    tip_notifications_enabled: bool = True
    focus_mode_sound_enabled: bool = False
    wind_down_auto_enabled: bool = True
    posture_reminders_enabled: bool = True
    movement_reminders_enabled: bool = True
    notification_tone: str = "gentle"
    tip_frequency: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Feature Cognitive Load Mapping
# ---------------------------------------------------------------------------

FEATURE_COGNITIVE_LOAD: Dict[str, str] = {
    # Low cognitive load
    "chat": CognitiveLoad.LOW.value,
    "messaging": CognitiveLoad.LOW.value,
    "reading": CognitiveLoad.LOW.value,
    "browse": CognitiveLoad.LOW.value,
    "browsing": CognitiveLoad.LOW.value,
    "dashboard": CognitiveLoad.LOW.value,
    "profile": Cognitive
# ___END_OF_FILE___