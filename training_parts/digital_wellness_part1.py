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

    FRESH = "fres
# ___END_OF_FILE___