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
    "profile": CognitiveLoad.LOW.value,
    "settings": CognitiveLoad.LOW.value,
    "notifications": CognitiveLoad.LOW.value,
    # Medium cognitive load
    "research": CognitiveLoad.MEDIUM.value,
    "search": CognitiveLoad.MEDIUM.value,
    "file_analysis": CognitiveLoad.MEDIUM.value,
    "document": CognitiveLoad.MEDIUM.value,
    "studying": CognitiveLoad.MEDIUM.value,
    "learning": CognitiveLoad.MEDIUM.value,
    "planning": CognitiveLoad.MEDIUM.value,
    "writing": CognitiveLoad.MEDIUM.value,
    "note_taking": CognitiveLoad.MEDIUM.value,
    "review": CognitiveLoad.MEDIUM.value,
    # High cognitive load
    "deep_work": CognitiveLoad.HIGH.value,
    "coding": CognitiveLoad.HIGH.value,
    "programming": CognitiveLoad.HIGH.value,
    "problem_solving": CognitiveLoad.HIGH.value,
    "analysis": CognitiveLoad.HIGH.value,
    "design": CognitiveLoad.HIGH.value,
    "modeling": CognitiveLoad.HIGH.value,
    "debugging": CognitiveLoad.HIGH.value,
    "testing": CognitiveLoad.HIGH.value,
}

COGNITIVE_LOAD_MULTIPLIERS: Dict[str, float] = {
    CognitiveLoad.LOW.value: 1.0,
    CognitiveLoad.MEDIUM.value: 1.5,
    CognitiveLoad.HIGH.value: 2.5,
}


# ---------------------------------------------------------------------------
# Wellness Tips Database
# ---------------------------------------------------------------------------


class WellnessTipsDatabase:
    """Curated wellness tips with contextual selection capabilities.

    This class maintains a comprehensive database of science-backed wellness
    tips organized by category. Tips are selected contextually based on the
    user's current state, time of day, activity type, and viewing history
    to ensure relevance and avoid repetition.
    """

    _tips: ClassVar[List[WellnessTip]] = []
    _initialized: ClassVar[bool] = False
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _initialize(cls) -> None:
        """Lazily initialize the tips database with 200+ curated tips."""
        with cls._lock:
            if cls._initialized:
                return
            cls._tips = cls._load_all_tips()
            cls._initialized = True
            logger.info(
                "WellnessTipsDatabase initialized with %d tips", len(cls._tips)
            )

    @classmethod
    def get_all_tips(cls) -> List[WellnessTip]:
        """Get all wellness tips."""
        if not cls._initialized:
            cls._initialize()
        return list(cls._tips)

    @classmethod
    def get_tips_by_category(cls, category: str) -> List[WellnessTip]:
        """Get all tips in a specific category."""
        if not cls._initialized:
            cls._initialize()
        return [t for t in cls._tips if t.category == category]

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all available tip category names."""
        if not cls._initialized:
            cls._initialize()
        return sorted({t.category for t in cls._tips})

    @classmethod
    def select_contextual_tip(
        cls,
        fatigue_score: int,
        current_activity: str = "",
        tip_history: Optional[List[str]] = None,
        preferred_category: Optional[str] = None,
    ) -> WellnessTip:
        """Select a wellness tip based on current context."""
        if not cls._initialized:
            cls._initialize()

        history = tip_history or []

        if preferred_category:
            candidates = cls.get_tips_by_category(preferred_category)
        else:
            category = cls._select_category(fatigue_score, current_activity)
            candidates = cls.get_tips_by_category(category)

        if not candidates:
            candidates = cls._tips

        fresh_candidates = [t for t in candidates if t.title not in history]
        if not fresh_candidates:
            fresh_candidates = candidates

        return random.choice(fresh_candidates)

    @classmethod
    def _select_category(cls, fatigue_score: int, activity: str) -> str:
        """Select the most relevant category based on context."""
        hour = datetime.utcnow().hour

        if hour >= 21 or hour < 6:
            return TipCategory.SLEEP.value

        if fatigue_score > 70:
            weights = {
                TipCategory.MOVEMENT.value: 0.30,
                TipCategory.MENTAL_CLARITY.value: 0.25,
                TipCategory.STRESS.value: 0.20,
                TipCategory.EYE_HEALTH.value: 0.15,
                TipCategory.HYDRATION.value: 0.10,
            }
            return random.choices(
                list(weights.keys()), weights=list(weights.values())
            )[0]

        if fatigue_score > 40:
            weights = {
                TipCategory.EYE_HEALTH.value: 0.25,
                TipCategory.POSTURE.value: 0.25,
                TipCategory.HYDRATION.value: 0.20,
                TipCategory.MOVEMENT.value: 0.15,
                TipCategory.MENTAL_CLARITY.value: 0.15,
            }
            return random.choices(
                list(weights.keys()), weights=list(weights.values())
            )[0]

        load = FEATURE_COGNITIVE_LOAD.get(activity, CognitiveLoad.MEDIUM.value)
        if load == CognitiveLoad.HIGH.value:
            weights = {
                TipCategory.MENTAL_CLARITY.value: 0.30,
                TipCategory.MOVEMENT.value: 0.25,
                TipCategory.POSTURE.value: 0.20,
                TipCategory.STRESS.value: 0.15,
                TipCategory.HYDRATION.value: 0.10,
            }
            return random.choices(
                list(weights.keys()), weights=list(weights.values())
            )[0]

        weights = {
            TipCategory.EYE_HEALTH.value: 0.20,
            TipCategory.POSTURE.value: 0.15,
            TipCategory.HYDRATION.value: 0.15,
            TipCategory.MOVEMENT.value: 0.15,
            TipCategory.MENTAL_CLARITY.value: 0.15,
            TipCategory.SOCIAL.value: 0.10,
            TipCategory.SLEEP.value: 0.10,
        }
        return random.choices(
            list(weights.keys()), weights=list(weights.values())
        )[0]

    @classmethod
    def _load_all_tips(cls) -> List[WellnessTip]:
        """Load the complete curated tips database (200+ tips)."""
        tips: List[WellnessTip] = []

        # EYE HEALTH (25 tips)
        tips.extend([
            WellnessTip(TipCategory.EYE_HEALTH.value, "The 20-20-20 Rule",
                "Every 20 minutes, look at something 20 feet away for at least 20 seconds. This simple habit reduces eye strain by allowing your eye muscles to relax and reset their focus point.",
                "Set a timer for 20 minutes and practice looking out a window at a distant object.", "American Optometric Association"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Blink More Often",
                "When staring at screens, we blink up to 60% less frequently, which leads to dry, irritated eyes. Conscious blinking helps spread tears evenly across the eye surface.",
                "Try blinking 10 times slowly right now, then set a reminder to do this every 15 minutes.", "American Academy of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Adjust Screen Brightness",
                "Your screen should match the brightness of your surrounding environment. A screen that is too bright or too dim forces your eyes to work harder to adjust.",
                "Match your screen brightness to the ambient light level in your room right now.", "Occupational Health Psychology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Increase Text Size",
                "Squinting to read small text causes eye strain and can lead to headaches. Increasing your default font size or zoom level reduces the effort your eyes expend.",
                "Increase your browser or application zoom level by 10%.", "Ergonomic Design Principles"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Use the Right Screen Distance",
                "Position your screen about an arm's length away (20-26 inches) with the top of the screen at or slightly below eye level.",
                "Check that your screen is at least 20 inches from your face and the top is at or below eye level.", "OSHA Ergonomics Guidelines"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Reduce Blue Light in Evening",
                "Blue light from screens can suppress melatonin production by up to 50%, making it harder to fall asleep. Most devices have a built-in blue light filter.",
                "Enable your device's blue light filter or night mode now.", "Harvard Medical School Sleep Research"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Follow the 10-15-20 Blink Exercise",
                "Every 20 minutes, close your eyes for 10 seconds, then blink 15 times rapidly. This exercise fully re-lubricates your eyes.",
                "Try the 10-15-20 blink exercise right now.", "Dry Eye Foundation"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Use Artificial Tears",
                "If you experience persistent dry eyes during screen use, over-the-counter lubricating eye drops can provide relief.",
                "Consider keeping preservative-free artificial tears at your desk.", "American Academy of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Take Visual Breaks with Palming",
                "Palming is a relaxation technique where you cover your closed eyes with your palms for 30-60 seconds. The warmth and darkness help relax the eye muscles.",
                "Try palming: rub your hands together to warm them, then gently cup them over your closed eyes for 30 seconds.", "Bates Method Research"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Reduce Screen Glare",
                "Glare from windows or overhead lights forces your eyes to work harder. Position your screen perpendicular to windows.",
                "Check your screen for reflections and reposition or adjust blinds to reduce glare.", "Vision Council of America"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Practice Eye Rolling Exercises",
                "Gentle eye rolling exercises help strengthen the extraocular muscles and improve blood circulation around the eyes.",
                "Roll your eyes in a slow circle 5 times in each direction.", "Vision Therapy Research"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Eat Eye-Friendly Foods",
                "Foods rich in omega-3s (salmon, walnuts), lutein (spinach, kale), vitamin C (citrus), and vitamin E (almonds) support long-term eye health.",
                "Add one eye-healthy food to your next meal or snack.", "American Optometric Association Nutrition Council"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Use Proper Lighting",
                "The lighting in your workspace should be about half as bright as typical office lighting. Avoid working in complete darkness.",
                "Turn on a soft ambient light source if you are working in a dark room.", "Illuminating Engineering Society"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Get Regular Eye Exams",
                "Adults who use screens extensively should have comprehensive eye exams every 1-2 years. Uncorrected vision problems cause significantly more strain.",
                "Schedule an eye exam if it has been more than 2 years since your last one.", "American Optometric Association"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Try the Focus Flexing Exercise",
                "Alternate your focus between a nearby object (your thumb) and a distant object (20+ feet away) for 10-15 cycles.",
                "Practice focus flexing: alternate focus between your thumb and a distant object 10 times.", "Clinical and Experimental Optometry"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Consider Computer Glasses",
                "Specialized computer glasses with anti-reflective coating and blue light filtering can reduce eye strain for heavy screen users.",
                "Ask your optometrist about computer glasses at your next eye exam.", "American Academy of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Take Eye Health Breaks Outside",
                "Looking at natural scenery, especially greenery at varying distances, provides the best possible exercise for your eye muscles.",
                "If possible, spend 5 minutes looking at natural scenery outside.", "Environmental Psychology Research"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Reduce Peripheral Screen Clutter",
                "Multiple monitors and cluttered screen edges force your eyes to constantly scan wide areas. Organizing your workspace helps your eyes focus.",
                "Close unnecessary windows and organize your desktop to reduce visual clutter.", "Human Factors and Ergonomics Society"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Stay Hydrated for Eye Moisture",
                "Proper hydration is essential for maintaining adequate tear production. Dehydration can exacerbate dry eye symptoms.",
                "Drink a full glass of water right now.", "National Eye Institute"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Use Dark Mode Wisely",
                "Dark mode can reduce eye strain in low-light environments but may increase strain in bright conditions.",
                "Switch your device to the theme that matches your current lighting conditions.", "Human-Computer Interaction Research"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Warm Compress for Eye Relief",
                "A warm compress over closed eyes for 5-10 minutes can help unclog meibomian glands, improving tear film quality.",
                "Try a warm compress over your eyes for 5 minutes during your next break.", "British Journal of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Follow the 1-2-10 Reading Rule",
                "For optimal eye comfort: hold phones 1 foot away, tablets 2 feet away, and desktop monitors 10 feet (or arm's length) away.",
                "Check the distance of each screen you use against the 1-2-10 rule.", "American Academy of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Practice Figure-Eight Eye Exercise",
                "Imagine a large figure-eight about 10 feet in front of you. Trace it slowly with your eyes for 30 seconds each direction.",
                "Trace an imaginary figure-eight with your eyes for 30 seconds.", "Vision Therapy Techniques"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Minimize Airflow to Eyes",
                "Direct airflow from fans, air conditioning vents, or heaters can accelerate tear evaporation and cause dry eyes.",
                "Check if any vents or fans are blowing directly at your face and redirect them.", "American Academy of Ophthalmology"),
            WellnessTip(TipCategory.EYE_HEALTH.value, "Consider Lutein Supplements",
                "Lutein and zeaxanthin are carotenoids that accumulate in the retina and may help filter harmful blue light.",
                "Include more leafy greens in your diet or discuss supplements with your doctor.", "National Institutes of Health"),
        ])

        # POSTURE & ERGONOMICS (25 tips)
        tips.extend([
            WellnessTip(TipCategory.POSTURE.value, "Align Your Monitor Properly",
                "The top of your monitor should be at or slightly below eye level. This encourages a neutral neck position and reduces strain.",
                "Adjust your monitor so the top edge is at or just below eye level.", "OSHA Computer Workstation Guidelines"),
            WellnessTip(TipCategory.POSTURE.value, "Support Your Lower Back",
                "Use a chair with adequate lumbar support or place a small pillow at the curve of your lower back.",
                "Check that your lower back is supported and adjust your chair or add a cushion.", "Canadian Centre for Occupational Health and Safety"),
            WellnessTip(TipCategory.POSTURE.value, "Keep Feet Flat on the Floor",
                "Your feet should rest flat on the floor with knees at a 90-100 degree angle. If your feet do not reach, use a footrest.",
                "Ensure both feet are flat on the floor while sitting.", "Ergonomic Design Standards"),
            WellnessTip(TipCategory.POSTURE.value, "Position Keyboard and Mouse Correctly",
                "Keep your keyboard and mouse at elbow height so your arms form a roughly 90-degree angle.",
                "Adjust your keyboard and mouse so your elbows are at 90 degrees when using them.", "Occupational Safety and Health Administration"),
            WellnessTip(TipCategory.POSTURE.value, "Avoid Forward Head Posture",
                "For every inch your head moves forward, the effective weight on your neck increases by about 10 pounds.",
                "Do a quick posture check: are your ears directly above your shoulders?", "Spine Research Institute"),
            WellnessTip(TipCategory.POSTURE.value, "Take Standing Breaks",
                "Standing for just 2-3 minutes every 30 minutes can significantly reduce the health risks associated with prolonged sitting.",
                "Stand up and stretch for 2 minutes right now.", "British Journal of Sports Medicine"),
            WellnessTip(TipCategory.POSTURE.value, "Use a Sit-Stand Desk",
                "Alternating between sitting and standing throughout the day can reduce lower back pain by up to 32%.",
                "If you have a sit-stand desk, switch to standing for the next 30 minutes.", "Centers for Disease Control and Prevention"),
            WellnessTip(TipCategory.POSTURE.value, "Keep Shoulders Relaxed",
                "Many people unconsciously raise their shoulders while typing or using a mouse. Periodically check that your shoulders are relaxed.",
                "Roll your shoulders backward 5 times, then let them settle in a relaxed position.", "Physical Therapy Research"),
            WellnessTip(TipCategory.POSTURE.value, "Avoid Crossing Legs",
                "Crossing your legs while sitting can lead to poor posture, reduced circulation, and uneven pressure on your hips.",
                "Uncross your legs if they are crossed right now.", "Mayo Clinic Ergonomics"),
            WellnessTip(TipCategory.POSTURE.value, "Stretch Your Hip Flexors",
                "Sitting for extended periods tightens the hip flexor muscles, which can pull your pelvis into an anterior tilt and cause lower back pain.",
                "Do a standing hip flexor stretch for 30 seconds each side.", "Journal of Orthopaedic & Sports Physical Therapy"),
            WellnessTip(TipCategory.POSTURE.value, "Keep Wrists Neutral",
                "Your wrists should remain in a straight, neutral position when typing. Avoid bending them up, down, or to the sides.",
                "Check your wrist position: they should be straight, not bent, while typing.", "National Institute of Neurological Disorders and Stroke"),
            WellnessTip(TipCategory.POSTURE.value, "Do the Brugger Relief Position",
                "Sit at the edge of your chair, arch your lower back slightly, open your chest, and rotate your arms outward with thumbs pointing back. Hold for 10 seconds.",
                "Try the Brugger relief position for 10 seconds right now.", "European Journal of Applied Physiology"),
            WellnessTip(TipCategory.POSTURE.value, "Adjust Chair Armrests",
                "Armrests should support your forearms without raising your shoulders. Adjust them so your shoulders remain relaxed.",
                "Adjust your armrests so your shoulders stay relaxed while your forearms are supported.", "Human Factors and Ergonomics Society"),
            WellnessTip(TipCategory.POSTURE.value, "Stretch Your Neck Regularly",
                "Gentle neck stretches can relieve tension and prevent stiffness. Slowly tilt your head toward each shoulder.",
                "Do gentle neck stretches: tilt side to side, then rotate slowly. Hold each for 15 seconds.", "American Physical Therapy Association"),
            WellnessTip(TipCategory.POSTURE.value, "Use a Document Holder",
                "If you frequently reference physical documents, use a document holder positioned at the same height and distance as your monitor.",
                "If you use physical documents, position them at the same height as your screen.", "Occupational Health Psychology"),
            WellnessTip(TipCategory.POSTURE.value, "Take Walking Meetings",
                "Whenever possible, take one-on-one meetings while walking. This breaks up sedentary time and can boost creative thinking by up to 60%.",
                "Suggest a walking meeting for your next one-on-one conversation.", "Stanford University Creativity Research"),
            WellnessTip(TipCategory.POSTURE.value, "Strengthen Your Core",
                "A strong core supports proper posture and reduces strain on your back. Simple exercises like planks and bridges help immensely.",
                "Do a 30-second plank during your next break to engage your core muscles.", "Journal of Strength and Conditioning Research"),
            WellnessTip(TipCategory.POSTURE.value, "Position Your Phone at Eye Level",
                "Looking down at your phone places up to 60 pounds of pressure on your neck. Bring your phone up to eye level.",
                "When using your phone next, bring it up to eye level instead of looking down.", "Surgical Technology International"),
            WellnessTip(TipCategory.POSTURE.value, "Use a Headset for Calls",
                "Cradling a phone between your ear and shoulder while typing causes significant neck strain. Use a headset instead.",
                "Switch to a headset or earbuds for your next phone call.", "Occupational Health Journal"),
            WellnessTip(TipCategory.POSTURE.value, "Do Seated Spinal Twists",
                "A seated spinal twist helps release tension in the lower back and improves spinal mobility.",
                "Do a seated spinal twist for 15 seconds on each side.", "Yoga Journal / Physical Therapy Integration"),
            WellnessTip(TipCategory.POSTURE.value, "Maintain Elbow Angle",
                "Your elbows should stay close to your body at approximately a 90-degree angle when typing.",
                "Check that your elbows are at 90 degrees and close to your body.", "Ergonomic Workplace Design"),
            WellnessTip(TipCategory.POSTURE.value, "Stretch Chest Muscles",
                "Hours of forward-facing computer work can tighten chest muscles and round the shoulders.",
                "Do a doorway chest stretch: place your forearms on the door frame and lean forward gently for 20 seconds.", "Journal of Bodywork and Movement Therapies"),
            WellnessTip(TipCategory.POSTURE.value, "Take Micro-Movement Breaks",
                "Even tiny movements like shifting your position, rolling your ankles, or stretching your fingers help prevent stiffness.",
                "Do a quick full-body micro-stretch: roll your ankles, stretch your fingers, and shift your sitting position.", "Applied Ergonomics Research"),
            WellnessTip(TipCategory.POSTURE.value, "Keep Hips Level",
                "When sitting, your hips should be level and your weight distributed evenly on both sides.",
                "Check that your weight is evenly distributed on both hips.", "Physical Medicine and Rehabilitation"),
            WellnessTip(TipCategory.POSTURE.value, "Do the Wall Angel Exercise",
                "Stand with your back against a wall, arms bent at 90 degrees. Slowly slide your arms up and down while keeping contact.",
                "Try 10 wall angels during your next break to open your shoulders.", "Corrective Exercise Research"),
        ])

        # MENTAL CLARITY (25 tips)
        tips.extend([
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Practice the 4-7-8 Breathing Technique",
                "Inhale for 4 counts, hold for 7 counts, exhale for 8 counts. This activates the parasympathetic nervous system.",
                "Do three cycles of 4-7-8 breathing right now.", "Harvard Medical School"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use the Two-Minute Rule",
                "If a task takes less than two minutes, do it immediately. This prevents small tasks from accumulating and creating mental clutter.",
                "Identify one small task you have been putting off and complete it now.", "Getting Things Done by David Allen"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Try Box Breathing",
                "Box breathing (4-4-4-4) is used by Navy SEALs to stay calm under pressure. Inhale 4, hold 4, exhale 4, hold 4.",
                "Practice box breathing for one minute.", "Journal of Neurophysiology"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take a Mindful Minute",
                "Set a timer for 60 seconds and focus entirely on your breath. When your mind wanders, gently bring it back.",
                "Take a mindful minute: close your eyes and focus only on your breathing for 60 seconds.", "Journal of Cognitive Enhancement"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use the Pomodoro Technique",
                "Work in focused 25-minute intervals followed by 5-minute breaks. After 4 cycles, take a longer 15-30 minute break.",
                "Start a 25-minute focused work session now, planning a 5-minute break after.", "Cirillo (Pomodoro Technique Creator)"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Declutter Your Digital Workspace",
                "A cluttered desktop and too many open tabs create cognitive overload. Close unused applications and browser tabs.",
                "Close 5 browser tabs or applications you are not actively using.", "Cognitive Load Theory Research"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Practice Single-Tasking",
                "Multitasking can reduce productivity by up to 40% and increase errors. Focus on one task at a time.",
                "Pick one task and commit to focusing only on it for the next 15 minutes.", "American Psychological Association"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take a Brain Dump Break",
                "When your mind feels overwhelmed, spend 2 minutes writing down every thought and task without organizing.",
                "Spend 2 minutes writing down everything on your mind right now.", "Bullet Journal Method Research"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use the 5-4-3-2-1 Grounding Technique",
                "When mentally scattered, name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, and 1 you taste.",
                "Do the 5-4-3-2-1 grounding exercise right now.", "Anxiety and Depression Association of America"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take a Power Nap",
                "A 10-20 minute nap can improve alertness, memory, and cognitive performance without causing grogginess.",
                "If possible, take a 10-20 minute power nap during your next break.", "NASA Fatigue Countermeasures Study"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Stay Hydrated for Brain Function",
                "Even mild dehydration (1-2% of body weight) can impair cognitive performance, memory, and mood.",
                "Drink a full glass of water right now.", "Journal of Nutrition"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Try the Feynman Technique",
                "Explain a complex concept in simple terms as if teaching a beginner. This identifies gaps in your understanding.",
                "Pick a concept you are learning and explain it out loud in the simplest terms possible.", "Richard Feynman Learning Method"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take Nature Brain Breaks",
                "Even 5 minutes in nature or looking at natural scenery can reduce mental fatigue and restore directed attention.",
                "Look out a window at natural scenery for 2 minutes, or step outside briefly.", "Environmental Psychology Research (Kaplan, 1995)"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use Binaural Beats for Focus",
                "Binaural beats in the alpha (8-13 Hz) and beta (13-30 Hz) ranges may enhance focus and cognitive performance.",
                "Try playing alpha or beta binaural beats at low volume during your next focused work session.", "Frontiers in Psychiatry"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use the Rule of Three",
                "At the start of each day, identify the three most important tasks. Focusing on just three priorities prevents overwhelm.",
                "Write down the three most important things you want to accomplish today.", "Productivity Research (Chris Bailey)"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take a Digital Sabbath",
                "Designate regular periods to completely disconnect from all screens. This allows your brain to recover from constant stimulation.",
                "Schedule a 2-hour screen-free block for later today or this week.", "Digital Minimalism by Cal Newport"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use Mental Models",
                "Mental models like inversion, first principles, and second-order thinking improve decision quality.",
                "Apply inversion to a current challenge: ask yourself what would guarantee failure, then avoid those actions.", "The Great Mental Models by Shane Parrish"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Eat Brain-Boosting Foods",
                "Foods rich in omega-3s (fatty fish), antioxidants (berries), flavonoids (dark chocolate), and choline (eggs) support cognitive function.",
                "Include one brain-boosting food in your next snack.", "Harvard Health Nutrition"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Practice Interleaved Learning",
                "Instead of focusing on one skill for hours, alternate between related topics. This strengthens neural pathways more effectively.",
                "If studying or practicing multiple skills, switch between them every 20-30 minutes.", "Journal of Educational Psychology"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use the Zeigarnik Effect",
                "Your brain remembers incomplete tasks better than completed ones. Start a challenging task to engage this effect.",
                "Spend 5 minutes starting a challenging task, then take a break and let your mind process it.", "Zeigarnik (1927) / Memory Research"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Try Alternate Nostril Breathing",
                "This yogic breathing technique (Nadi Shodhana) balances the left and right hemispheres of the brain.",
                "Try alternate nostril breathing for 2 minutes.", "International Journal of Yoga"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Review Your Day",
                "Spend 5 minutes at the end of each day reviewing what you accomplished, what you learned, and what you are grateful for.",
                "Write down three things you accomplished today and one thing you are grateful for.", "Positive Psychology Research (Seligman, 2005)"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Chunk Information",
                "Break complex information into smaller, meaningful chunks (3-7 items). Your working memory can only hold about 4 chunks at once.",
                "Take a complex task or topic you are working on and break it into 3-5 smaller chunks.", "Cognitive Psychology (Miller's Law, 1956)"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Use Spaced Repetition",
                "Review information at increasing intervals (1 day, 3 days, 1 week, 2 weeks). This leverages the spacing effect.",
                "If learning something new, schedule a review session for tomorrow.", "Ebbinghaus Forgetting Curve Research"),
            WellnessTip(TipCategory.MENTAL_CLARITY.value, "Take a Shower Thought Break",
                "Mild distractions like showering or walking allow your brain's default mode network to make creative connections.",
                "Take a brief walk or do a simple household task to let your mind wander creatively.", "Journal of Experimental Psychology"),
        ])

        # SLEEP HYGIENE (25 tips)
        tips.extend([
            WellnessTip(TipCategory.SLEEP.value, "Maintain a Consistent Sleep Schedule",
                "Going to bed and waking up at the same time every day regulates your circadian rhythm.",
                "Set a bedtime alarm for tonight and commit to being in bed at that time.", "American Academy of Sleep Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Create a Wind-Down Routine",
                "A 30-60 minute wind-down routine signals to your body that it is time to sleep. Avoid screens during this time.",
                "Plan a 30-minute wind-down routine for tonight with at least one non-screen activity.", "Sleep Foundation"),
            WellnessTip(TipCategory.SLEEP.value, "Keep Your Bedroom Cool",
                "The ideal bedroom temperature for sleep is between 60-67 degrees Fahrenheit (15-19 Celsius).",
                "Adjust your thermostat or open a window to cool your bedroom before bed.", "National Sleep Foundation"),
            WellnessTip(TipCategory.SLEEP.value, "Avoid Screens 1 Hour Before Bed",
                "Blue light from screens suppresses melatonin production, making it harder to fall asleep.",
                "Set a screen curfew for 1 hour before your planned bedtime tonight.", "Harvard Medical School"),
            WellnessTip(TipCategory.SLEEP.value, "Use Your Bed Only for Sleep",
                "Your brain creates associations with your environment. Using your bed for work makes it harder to drift off.",
                "If you work or watch content in bed, commit to moving those activities elsewhere.", "Cognitive Behavioral Therapy for Insomnia (CBT-I)"),
            WellnessTip(TipCategory.SLEEP.value, "Limit Caffeine After Noon",
                "Caffeine has a half-life of 5-6 hours. Half the caffeine from your 2 PM coffee is still in your system at 8 PM.",
                "Switch to decaffeinated beverages or herbal tea after noon today.", "Journal of Clinical Sleep Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Try Progressive Muscle Relaxation",
                "PMR involves tensing and then relaxing each muscle group from toes to head. This reduces physical tension.",
                "Try PMR tonight: tense each muscle group for 5 seconds, then relax for 10 seconds, starting from your toes.", "Behavior Research and Therapy"),
            WellnessTip(TipCategory.SLEEP.value, "Keep Your Room Dark",
                "Even small amounts of light can suppress melatonin production and disrupt sleep quality.",
                "Check your bedroom for light sources and eliminate or cover them before bed.", "Journal of Biological Rhythms"),
            WellnessTip(TipCategory.SLEEP.value, "Avoid Alcohol Before Bed",
                "While alcohol may help you fall asleep faster, it significantly reduces REM sleep quality.",
                "If you drink alcohol, finish your last drink at least 3 hours before bedtime.", "Alcoholism: Clinical and Experimental Research"),
            WellnessTip(TipCategory.SLEEP.value, "Exercise Regularly, But Not Right Before Bed",
                "Regular exercise improves sleep quality but vigorous exercise within 2 hours of bedtime can be stimulating.",
                "Schedule your exercise for morning or afternoon rather than evening.", "Advances in Preventive Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Try a Body Scan Meditation",
                "A body scan meditation involves mentally scanning your body from head to toe, noticing sensations without judgment.",
                "Try a 5-minute body scan meditation using a guided audio track before bed tonight.", "JAMA Internal Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Expose Yourself to Morning Light",
                "Natural light exposure within the first hour of waking helps regulate your circadian rhythm.",
                "Spend 10 minutes outside or by a sunny window within the first hour of waking tomorrow.", "Sleep Medicine Reviews"),
            WellnessTip(TipCategory.SLEEP.value, "Limit Naps to 20 Minutes",
                "Long naps or late-day napping can interfere with nighttime sleep. Keep naps to 10-20 minutes before 3 PM.",
                "If you nap today, set an alarm for exactly 20 minutes.", "Sleep Foundation"),
            WellnessTip(TipCategory.SLEEP.value, "Avoid Heavy Meals Before Bed",
                "Eating a large meal within 2-3 hours of bedtime can cause discomfort, acid reflux, and disrupted sleep.",
                "Finish your last meal at least 3 hours before bedtime tonight.", "International Journal of Environmental Research and Public Health"),
            WellnessTip(TipCategory.SLEEP.value, "Use White Noise",
                "White noise or consistent ambient sound masks disruptive noises and creates a consistent auditory environment.",
                "Try a white noise app or fan tonight to mask ambient sounds while sleeping.", "Archives of Disease in Childhood"),
            WellnessTip(TipCategory.SLEEP.value, "Write a Worry List Before Bed",
                "If racing thoughts keep you awake, spend 5 minutes before bed writing down all your concerns and tomorrow's to-do list.",
                "Write down your top 3 concerns and tomorrow's priorities before getting into bed tonight.", "Behavioral Sleep Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Try the Military Sleep Method",
                "Relax your face, drop your shoulders, exhale and relax your chest, then relax your legs. Imagine a calming scene for 10 seconds.",
                "Practice the military sleep method tonight: relax face, shoulders, chest, legs, then visualize a calm scene.", "Sharon Ackerman, 'Relax and Win'"),
            WellnessTip(TipCategory.SLEEP.value, "Invest in Quality Bedding",
                "Your mattress, pillows, and bedding significantly impact sleep quality. A supportive mattress aligns your spine.",
                "Assess your mattress and pillow: are they supportive and comfortable? Consider replacing if over 7-8 years old.", "National Sleep Foundation"),
            WellnessTip(TipCategory.SLEEP.value, "Avoid the Snooze Button",
                "Hitting snooze fragments your sleep and starts a new sleep cycle that you cannot complete, causing sleep inertia.",
                "Place your alarm across the room tonight so you have to get up to turn it off.", "Journal of Sleep Research"),
            WellnessTip(TipCategory.SLEEP.value, "Take a Warm Bath Before Bed",
                "A warm bath 1-2 hours before bed raises your body temperature slightly. The subsequent drop signals your body it is time to sleep.",
                "Take a warm bath or shower 1-2 hours before bed tonight.", "Sleep Medicine Reviews"),
            WellnessTip(TipCategory.SLEEP.value, "Try Magnesium for Sleep",
                "Magnesium plays a role in regulating melatonin and GABA, which promotes relaxation. Many people are mildly deficient.",
                "Consider adding magnesium-rich foods (nuts, seeds, leafy greens) to your diet.", "Journal of Research in Medical Sciences"),
            WellnessTip(TipCategory.SLEEP.value, "Keep Pets Out of the Bedroom",
                "While comforting, pets can disrupt sleep with movement, noise, and allergens.",
                "If pet-related sleep disruption is an issue, consider transitioning your pet to sleep outside your bedroom.", "Mayo Clinic Sleep Center"),
            WellnessTip(TipCategory.SLEEP.value, "Use Aromatherapy",
                "Lavender scent has been shown to lower heart rate and blood pressure, promoting relaxation.",
                "Try lavender essential oil in a diffuser or on your pillow tonight.", "Journal of Alternative and Complementary Medicine"),
            WellnessTip(TipCategory.SLEEP.value, "Understand Your Chronotype",
                "Everyone has a natural sleep-wake preference (chronotype). Understanding yours helps you schedule your day optimally.",
                "Reflect on when you naturally feel most alert and schedule demanding tasks during those hours.", "The Power of When by Dr. Michael Breus"),
            WellnessTip(TipCategory.SLEEP.value, "Try Paradoxical Intention",
                "If you struggle with sleep anxiety, try paradoxical intention: instead of trying to fall asleep, try to stay awake with your eyes closed.",
                "If you cannot fall asleep, try paradoxical intention: tell yourself to stay awake and see what happens.", "Cognitive Behavioral Therapy for Insomnia"),
        ])

        # HYDRATION & NUTRITION (25 tips)
        tips.extend([
            WellnessTip(TipCategory.HYDRATION.value, "Drink Water First Thing",
                "After 7-8 hours of sleep, your body is dehydrated. Drinking water immediately upon waking jumpstarts your metabolism.",
                "Place a glass of water by your bed tonight and drink it first thing in the morning.", "Journal of Biological Chemistry"),
            WellnessTip(TipCategory.HYDRATION.value, "Use the Urine Color Test",
                "A simple way to check hydration: pale yellow urine indicates good hydration, while dark yellow suggests you need more water.",
                "Check your urine color now. If it is darker than pale yellow, drink a glass of water.", "European Journal of Clinical Nutrition"),
            WellnessTip(TipCategory.HYDRATION.value, "Eat Water-Rich Foods",
                "Cucumbers (96% water), watermelon (92%), strawberries (91%), and lettuce (96%) contribute significantly to daily hydration.",
                "Add a water-rich food like cucumber or watermelon to your next meal or snack.", "USDA Food Composition Database"),
            WellnessTip(TipCategory.HYDRATION.value, "Set Hydration Reminders",
                "Setting gentle reminders every hour helps maintain consistent hydration, which is better than drinking large amounts infrequently.",
                "Set a recurring hourly reminder to take a few sips of water.", "European Food Safety Authority"),
            WellnessTip(TipCategory.HYDRATION.value, "Drink Before You Feel Thirsty",
                "Thirst is a lagging indicator of dehydration. By the time you feel thirsty, you may already be 1-2% dehydrated.",
                "Take a sip of water now, even if you do not feel thirsty.", "Journal of the American College of Nutrition"),
            WellnessTip(TipCategory.HYDRATION.value, "Limit Sugary Drinks",
                "Sugary beverages cause blood sugar spikes followed by crashes that affect energy and focus.",
                "Replace one sugary drink today with water or unsweetened herbal tea.", "American Heart Association"),
            WellnessTip(TipCategory.HYDRATION.value, "Carry a Water Bottle",
                "Having water visibly available makes you significantly more likely to drink regularly.",
                "Fill a water bottle and place it within arm's reach right now.", "Behavioral Nutrition Research"),
            WellnessTip(TipCategory.HYDRATION.value, "Balance Electrolytes",
                "For intense activity, plain water may not be sufficient. Electrolytes are essential for nerve function and muscle contraction.",
                "If you exercised intensely today, consider adding an electrolyte source to your water.", "Sports Medicine Research"),
            WellnessTip(TipCategory.HYDRATION.value, "Drink Herbal Tea",
                "Herbal teas like chamomile, peppermint, and ginger provide hydration along with additional health benefits.",
                "Try a cup of herbal tea during your next break.", "Journal of Traditional and Complementary Medicine"),
            WellnessTip(TipCategory.HYDRATION.value, "Monitor Caffeine Intake",
                "While moderate caffeine (up to 400mg/day) is safe, excessive caffeine can cause dehydration, anxiety, and sleep disruption.",
                "Count your caffeine servings today. Aim to stay at or below 400mg.", "FDA Caffeine Guidelines"),
            WellnessTip(TipCategory.HYDRATION.value, "Eat a Protein-Rich Breakfast",
                "A breakfast with 20-30g of protein stabilizes blood sugar, reduces cravings, and improves sustained energy.",
                "Include a protein source in your breakfast tomorrow morning.", "American Journal of Clinical Nutrition"),
            WellnessTip(TipCategory.HYDRATION.value, "Choose Complex Carbohydrates",
                "Complex carbs (whole grains, oats, quinoa) provide sustained energy without the blood sugar spikes of simple sugars.",
                "Replace a refined grain with a whole grain option at your next meal.", "Harvard T.H. Chan School of Public Health"),
            WellnessTip(TipCategory.HYDRATION.value, "Include Healthy Fats",
                "Healthy fats from avocados, nuts, olive oil, and fatty fish support brain function, hormone production, and nutrient absorption.",
                "Add a source of healthy fat to one meal today.", "American Heart Association"),
            WellnessTip(TipCategory.HYDRATION.value, "Eat the Rainbow",
                "Different colored fruits and vegetables contain different phytonutrients. Eating a variety ensures a broad spectrum of nutrients.",
                "Aim to include at least 3 different colors of fruits or vegetables in your meals today.", "USDA Dietary Guidelines"),
            WellnessTip(TipCategory.HYDRATION.value, "Practice Mindful Eating",
                "Eating without distractions improves digestion, portion awareness, and meal satisfaction.",
                "Eat your next meal without any screens and focus on the flavors and textures.", "Harvard Health Publishing"),
            WellnessTip(TipCategory.HYDRATION.value, "Limit Processed Foods",
                "Highly processed foods often contain excess sodium, added sugars, and unhealthy fats that cause energy crashes.",
                "Replace one processed snack today with a whole food alternative.", "British Medical Journal"),
            WellnessTip(TipCategory.HYDRATION.value, "Stay Hydrated During Exercise",
                "Dehydration during exercise impairs performance and increases injury risk.",
                "If you exercise today, drink water 30 minutes before, during, and after.", "American College of Sports Medicine"),
            WellnessTip(TipCategory.HYDRATION.value, "Consider Fermented Foods",
                "Fermented foods like yogurt, kefir, sauerkraut contain probiotics that support gut health.",
                "Include one fermented food in your diet today or this week.", "Nutrition Reviews"),
            WellnessTip(TipCategory.HYDRATION.value, "Plan Healthy Snacks",
                "Having healthy snacks readily available prevents reaching for less nutritious options when hungry.",
                "Prepare a healthy snack to have ready for when hunger strikes later.", "Appetite Journal"),
            WellnessTip(TipCategory.HYDRATION.value, "Limit Alcohol and Stay Hydrated",
                "Alcohol is a diuretic that promotes fluid loss. For every alcoholic drink, have a glass of water.",
                "If you drink alcohol, alternate each drink with a full glass of water.", "National Institute on Alcohol Abuse and Alcoholism"),
            WellnessTip(TipCategory.HYDRATION.value, "Drink Warm Water in the Morning",
                "Warm water in the morning can aid digestion, improve circulation, and help flush toxins.",
                "Try a cup of warm water with lemon tomorrow morning.", "Traditional Medicine / Integrative Health"),
            WellnessTip(TipCategory.HYDRATION.value, "Track Your Water Intake",
                "Using a water tracking app or marking a bottle with time goals can significantly increase water consumption.",
                "Mark your water bottle with hourly drinking goals or use a hydration tracking app.", "Health Psychology Research"),
            WellnessTip(TipCategory.HYDRATION.value, "Eat Mindfully",
                "Chewing thoroughly and eating slowly improves digestion, nutrient absorption, and satisfaction.",
                "At your next meal, aim to chew each bite at least 15-20 times.", "Journal of the Academy of Nutrition and Dietetics"),
            WellnessTip(TipCategory.HYDRATION.value, "Choose Green Tea for Focus",
                "Green tea contains L-theanine, an amino acid that promotes calm alertness and works synergistically with caffeine.",
                "Try green tea instead of coffee for your next caffeine boost.", "Nutritional Neuroscience"),
            WellnessTip(TipCategory.HYDRATION.value, "Stay Hydrated for Joint Health",
                "Cartilage in your joints is about 80% water. Staying well-hydrated helps maintain joint lubrication.",
                "Take a moment to drink water and then do a few gentle joint rotations.", "Orthopedic Research"),
        ])

        # MOVEMENT & EXERCISE (25 tips)
        tips.extend([
            WellnessTip(TipCategory.MOVEMENT.value, "Take a 5-Minute Walk Every Hour",
                "A 5-minute walk every hour offsets the health risks of prolonged sitting and improves circulation.",
                "Stand up and take a 5-minute walk right now, even if it is just around your space.", "British Journal of Sports Medicine"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Desk Stretches",
                "Simple desk stretches for your neck, shoulders, wrists, and back can be done without leaving your chair.",
                "Do a full-body desk stretch: neck rolls, shoulder shrugs, wrist circles, and a seated spinal twist.", "Occupational Health and Safety"),
            WellnessTip(TipCategory.MOVEMENT.value, "Take the Stairs",
                "Taking stairs instead of elevators adds significant physical activity without requiring extra time.",
                "Take the stairs instead of the elevator for the rest of the day.", "Preventive Medicine Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do a 7-Minute Workout",
                "A high-intensity 7-minute bodyweight workout can provide significant fitness benefits.",
                "Do a 7-minute workout: jumping jacks, wall sit, push-ups, crunches, step-ups, squats, tricep dips, plank, high knees, lunges, side plank.", "American College of Sports Medicine"),
            WellnessTip(TipCategory.MOVEMENT.value, "Practice Standing Meetings",
                "Standing meetings tend to be shorter and more efficient. Standing also burns more calories.",
                "Stand up for your next phone call or virtual meeting.", "Harvard Business Review"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Calf Raises",
                "Calf raises can be done anywhere and help prevent blood from pooling in your lower legs during long sitting periods.",
                "Do 20 calf raises right now: rise onto your toes, hold for 2 seconds, then lower slowly.", "Journal of Applied Physiology"),
            WellnessTip(TipCategory.MOVEMENT.value, "Take Walking Breaks",
                "A 10-minute walk provides both physical activity and mental refreshment. Walking boosts creative output by 60%.",
                "Take a 10-minute walk outside or around your building.", "Stanford University Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Chair Squats",
                "Chair squats are a safe way to build leg strength. Stand up from your chair, then lower yourself back down slowly.",
                "Do 10 slow chair squats right now.", "Strength and Conditioning Journal"),
            WellnessTip(TipCategory.MOVEMENT.value, "Stretch Your Hip Flexors",
                "Sitting tightens hip flexors, which can pull your pelvis forward and cause lower back pain.",
                "Do a kneeling hip flexor stretch for 30 seconds on each side.", "Journal of Orthopaedic & Sports Physical Therapy"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Wrist and Finger Exercises",
                "Typing and mouse use can lead to repetitive strain injuries. Regular exercises keep your hands healthy.",
                "Do wrist circles (10 each direction) and finger spreads (10 times) right now.", "Journal of Hand Therapy"),
            WellnessTip(TipCategory.MOVEMENT.value, "Practice Desk Yoga",
                "Desk yoga combines gentle stretches and breathing exercises that can be done at your workstation.",
                "Try seated cat-cow: place hands on knees, arch your back on inhale, round on exhale. Repeat 10 times.", "International Journal of Yoga"),
            WellnessTip(TipCategory.MOVEMENT.value, "Take Movement Snacks",
                "Movement snacks are short bursts of physical activity (1-2 minutes) scattered throughout the day.",
                "Do a 2-minute movement snack: marching, arm circles, side steps, gentle jumping jacks.", "Exercise and Sport Sciences Reviews"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Planks for Core Strength",
                "A strong core supports good posture and prevents back pain. Start with 20 seconds and work up to 60.",
                "Hold a plank position for 30 seconds right now, keeping your body in a straight line.", "Journal of Strength and Conditioning Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Walk After Meals",
                "A 10-15 minute walk after eating helps regulate blood sugar, aids digestion, and provides gentle movement.",
                "Take a 10-minute walk after your next meal.", "Diabetes Care Journal"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Ankle Circles",
                "Ankle circles improve circulation in the lower legs and help prevent blood pooling during long periods of sitting.",
                "Do 10 ankle circles in each direction for each foot right now.", "Circulation Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Stretch Your Hamstrings",
                "Tight hamstrings from prolonged sitting can contribute to lower back pain.",
                "Do a seated hamstring stretch: extend one leg straight, reach toward your toes, hold 30 seconds each side.", "Spine Research Journal"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Push-Ups Anywhere",
                "Push-ups are one of the most efficient upper body exercises, requiring no equipment.",
                "Do as many push-ups as you can (wall, knee, or full) right now.", "American Council on Exercise"),
            WellnessTip(TipCategory.MOVEMENT.value, "Take Stretching Breaks",
                "A 2-minute full-body stretch every hour prevents muscle stiffness and provides a mental reset.",
                "Do a 2-minute full-body stretch, paying extra attention to any areas that feel tight.", "Applied Ergonomics"),
            WellnessTip(TipCategory.MOVEMENT.value, "Dance to a Song",
                "Dancing for the length of one song (3-4 minutes) is a joyful way to get your heart rate up and release endorphins.",
                "Play one of your favorite songs and dance to it right now.", "Dance Movement Therapy Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Lunges",
                "Lunges strengthen the legs, glutes, and core while improving balance and hip flexibility.",
                "Do 10 walking lunges or stationary lunges on each leg.", "Journal of Strength and Conditioning Research"),
            WellnessTip(TipCategory.MOVEMENT.value, "Practice Deep Squats",
                "Deep squats maintain hip and ankle mobility that is often lost from prolonged sitting.",
                "Do 5 deep squats, holding the bottom position for 5 seconds each time.", "Journal of Orthopaedic & Sports Physical Therapy"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Arm Circles",
                "Arm circles loosen the shoulders and upper back, which often become tense during computer work.",
                "Do 10 arm circles forward and 10 backward with each arm.", "Physical Therapy in Sport"),
            WellnessTip(TipCategory.MOVEMENT.value, "Take a Brisk Walk",
                "Brisk walking (where you can talk but not sing) provides moderate-intensity cardiovascular exercise.",
                "Take a 15-minute brisk walk, maintaining a pace where you can talk but not sing.", "Centers for Disease Control and Prevention"),
            WellnessTip(TipCategory.MOVEMENT.value, "Do Shoulder Blade Squeezes",
                "Squeeze your shoulder blades together and hold for 5 seconds, repeat 10 times. This strengthens upper back muscles.",
                "Do 10 shoulder blade squeezes, holding each for 5 seconds.", "Journal of Bodywork and Movement Therapies"),
            WellnessTip(TipCategory.MOVEMENT.value, "Stand on One Leg",
                "Single-leg balance exercises strengthen stabilizing muscles and improve proprioception.",
                "Stand on one leg for 30 seconds, then switch. Use a wall for support if needed.", "Balance and Posture Research"),
        ])

        # STRESS MANAGEMENT (25 tips)
        tips.extend([
            WellnessTip(TipCategory.STRESS.value, "Practice Diaphragmatic Breathing",
                "Breathe deeply into your belly rather than shallowly into your chest. This activates the relaxation response.",
                "Practice 5 deep belly breaths right now, with a slow 4-second inhale and 6-second exhale.", "Harvard Medical School"),
            WellnessTip(TipCategory.STRESS.value, "Try the 5-5-5 Grounding Technique",
                "Name 5 things you can see, 5 things you can hear, and 5 things you can feel. This pulls you into the present moment.",
                "Do the 5-5-5 grounding exercise right now.", "Dialectical Behavior Therapy"),
            WellnessTip(TipCategory.STRESS.value, "Write in a Gratitude Journal",
                "Writing down 3 things you are grateful for each day trains your brain to notice the positive.",
                "Write down 3 things you are grateful for right now.", "Journal of Personality and Social Psychology (Emmons, 2003)"),
            WellnessTip(TipCategory.STRESS.value, "Try Guided Meditation",
                "Guided meditations provide structured relaxation, especially helpful for beginners.",
                "Try a 5-minute guided meditation using a free app or online video.", "JAMA Internal Medicine"),
            WellnessTip(TipCategory.STRESS.value, "Use Positive Self-Talk",
                "The way you talk to yourself matters. Replace harsh self-criticism with compassionate, encouraging language.",
                "Replace one negative thought you have had today with a supportive, encouraging alternative.", "Cognitive Behavioral Therapy Research"),
            WellnessTip(TipCategory.STRESS.value, "Create a Relaxation Playlist",
                "Music has a powerful effect on the nervous system. Listening for just 10 minutes can reduce cortisol levels.",
                "Start creating a relaxation playlist with 5 songs that make you feel calm.", "Psychology of Music Journal"),
            WellnessTip(TipCategory.STRESS.value, "Practice the STOP Technique",
                "When feeling overwhelmed, STOP: Stop, Take a breath, Observe, Proceed mindfully. This creates a pause.",
                "Practice STOP right now: Stop, Take a breath, Observe, Proceed with awareness.", "Mindfulness-Based Stress Reduction (MBSR)"),
            WellnessTip(TipCategory.STRESS.value, "Set Boundaries with Technology",
                "Constant connectivity creates chronic low-level stress. Establish tech-free times and zones.",
                "Choose one tech-free time block for today and stick to it.", "Digital Wellness Research"),
            WellnessTip(TipCategory.STRESS.value, "Try Acupressure for Stress Relief",
                "Pressing the point between your thumb and index finger (LI4) for 2-3 minutes can help relieve tension.",
                "Apply gentle pressure to the webbing between your thumb and index finger for 2 minutes on each hand.", "Journal of Acupuncture and Meridian Studies"),
            WellnessTip(TipCategory.STRESS.value, "Practice Emotional Labeling",
                "Simply naming your emotions reduces their intensity. This is called affect labeling and engages the prefrontal cortex.",
                "Name the primary emotion you are feeling right now without judgment.", "Psychological Science (Lieberman et al., 2007)"),
            WellnessTip(TipCategory.STRESS.value, "Create a Worry Time",
                "Instead of worrying throughout the day, schedule a specific 15-minute 'worry time' to contain anxiety.",
                "Schedule a 15-minute worry time for later today and write down any worries that come up before then.", "Cognitive Behavioral Therapy for Anxiety"),
            WellnessTip(TipCategory.STRESS.value, "Use Aromatherapy for Calm",
                "Scents like lavender, chamomile, bergamot, and sandalwood have been shown to reduce anxiety and promote relaxation.",
                "Use a calming essential oil or scent in your workspace during your next break.", "Complementary Therapies in Medicine"),
            WellnessTip(TipCategory.STRESS.value, "Try Tense and Release",
                "Systematically tense each muscle group for 5 seconds, then release for 10 seconds, from toes to head.",
                "Do a quick tense-and-release cycle: tense your whole body for 5 seconds, then release completely.", "Behavior Research and Therapy"),
            WellnessTip(TipCategory.STRESS.value, "Connect with Nature",
                "Spending even 20 minutes in nature significantly reduces cortisol levels.",
                "Step outside for 5 minutes, or look at nature imagery if going outside is not possible.", "Frontiers in Psychology"),
            WellnessTip(TipCategory.STRESS.value, "Practice Self-Compassion",
                "Treat yourself with the same kindness you would offer a good friend. Self-compassion reduces anxiety and increases resilience.",
                "Say one kind, supportive thing to yourself right now.", "Kristin Neff Self-Compassion Research"),
            WellnessTip(TipCategory.STRESS.value, "Try Journaling for Stress Relief",
                "Writing about your thoughts and feelings for 15-20 minutes can reduce stress and improve immune function.",
                "Spend 5 minutes writing freely about what is on your mind right now.", "Journal of Consulting and Clinical Psychology (Pennebaker, 1997)"),
            WellnessTip(TipCategory.STRESS.value, "Use Visualization Techniques",
                "Visualization involves imagining a peaceful, calming scene in detail. This triggers real relaxation responses.",
                "Close your eyes for 1 minute and vividly imagine your favorite peaceful place.", "Applied Psychophysiology and Biofeedback"),
            WellnessTip(TipCategory.STRESS.value, "Try Laughter Therapy",
                "Laughter reduces stress hormones, releases endorphins, and boosts immune function. Even simulated laughter helps.",
                "Watch a funny video or recall a humorous memory to bring genuine laughter.", "Alternative Therapies in Health and Medicine"),
            WellnessTip(TipCategory.STRESS.value, "Practice the RAIN Technique",
                "RAIN is a mindfulness technique: Recognize, Allow, Investigate with kindness, Nurture with self-compassion.",
                "Apply RAIN to a current challenge: Recognize, Allow, Investigate, Nurture.", "Mindfulness Meditation Research (Tara Brach)"),
            WellnessTip(TipCategory.STRESS.value, "Create a Calming Ritual",
                "A personal calming ritual, like making tea or lighting a candle, signals to your nervous system that it is safe to relax.",
                "Create or perform one calming ritual right now.", "Behavioral Psychology Research"),
            WellnessTip(TipCategory.STRESS.value, "Try Reframing",
                "Reframing involves looking at a stressful situation from a different perspective. Ask what you can learn from it.",
                "Reframe one current stressor by asking: What can I learn from this situation?", "Cognitive Behavioral Therapy"),
            WellnessTip(TipCategory.STRESS.value, "Use Cold Water for Calm",
                "Splashing cold water on your face triggers the mammalian dive reflex, which slows your heart rate.",
                "Splash cold water on your face or hold an ice cube for 30 seconds.", "Psychophysiology Research"),
            WellnessTip(TipCategory.STRESS.value, "Practice Acceptance",
                "Some stress comes from fighting reality. Acceptance means acknowledging what is true so you can respond effectively.",
                "Identify one thing you are resisting right now and practice accepting it as it is.", "Acceptance and Commitment Therapy (ACT)"),
            WellnessTip(TipCategory.STRESS.value, "Try Paced Breathing",
                "Paced breathing at about 6 breaths per minute optimizes heart rate variability and promotes calm alertness.",
                "Practice paced breathing: inhale for 4 counts, exhale for 6 counts. Continue for 1 minute.", "Heart Rate Variability Research"),
            WellnessTip(TipCategory.STRESS.value, "Create a Support System",
                "Social support is one of the strongest predictors of resilience. Cultivate relationships you can rely on.",
                "Reach out to one person you care about today, just to connect.", "Social Support and Health Research (Cohen & Wills, 1985)"),
        ])

        # SOCIAL CONNECTION (25 tips)
        tips.extend([
            WellnessTip(TipCategory.SOCIAL.value, "Call Someone You Care About",
                "Hearing a loved one's voice activates oxytocin release, reducing stress and promoting bonding.",
                "Call or voice message someone you care about right now, even for just 5 minutes.", "Psychoneuroendocrinology Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Active Listening",
                "Active listening means giving someone your full attention and asking thoughtful questions.",
                "In your next conversation, focus entirely on listening rather than planning your response.", "Journal of Applied Communication Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Express Appreciation",
                "Expressing gratitude to others strengthens relationships and increases happiness for both giver and receiver.",
                "Send a message of appreciation to someone who has helped you recently.", "Journal of Personality and Social Psychology"),
            WellnessTip(TipCategory.SOCIAL.value, "Schedule Regular Check-Ins",
                "Regular, predictable contact with friends and family provides a sense of security and belonging.",
                "Schedule a recurring weekly or bi-weekly check-in with a friend or family member.", "Relationship Science Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Join a Community",
                "Being part of a community provides belonging and support. In-person connection is ideal.",
                "Research one local or online community related to your interests and consider joining.", "Social Capital Research (Putnam, 2000)"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Vulnerability",
                "Sharing your authentic self, including struggles, deepens relationships and builds trust.",
                "Share one genuine thought or feeling with someone you trust today.", "Brene Brown Vulnerability Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Help Someone Else",
                "Acts of kindness trigger the release of dopamine and oxytocin, improving your own well-being.",
                "Do one small act of kindness for someone today.", "Journal of Social Psychology"),
            WellnessTip(TipCategory.SOCIAL.value, "Have a Meaningful Conversation",
                "Deep, meaningful conversations are more satisfying than small talk. Ask open-ended questions about values and dreams.",
                "Start a conversation with a question like 'What has been the highlight of your week?'", "Psychological Science"),
            WellnessTip(TipCategory.SOCIAL.value, "Eat Meals with Others",
                "Shared meals are one of the most universal forms of social bonding. Eating with others improves digestion.",
                "Arrange to share at least one meal with someone this week.", "Public Health Nutrition Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Send a Handwritten Note",
                "In the digital age, a handwritten note carries special weight and shows thoughtfulness.",
                "Write a short handwritten note to someone you appreciate and mail it this week.", "Positive Psychology Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Empathy",
                "Empathy is the ability to understand and share the feelings of another. Practice by imagining yourself in their situation.",
                "In your next interaction, make a conscious effort to understand the other person's perspective.", "Empathy Research (Decety & Ickes)"),
            WellnessTip(TipCategory.SOCIAL.value, "Celebrate Others' Successes",
                "Genuinely celebrating others' achievements strengthens bonds and increases your own happiness.",
                "Reach out to congratulate someone on a recent achievement, no matter how small.", "Journal of Personality and Social Psychology"),
            WellnessTip(TipCategory.SOCIAL.value, "Create Shared Experiences",
                "Shared experiences, especially novel ones, create stronger bonds than material exchanges.",
                "Plan a shared experience with someone: try a new restaurant, take a class, or explore together.", "Experience Psychology Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Be Present in Conversations",
                "Put away your phone and give your full attention. Being fully present signals respect and care.",
                "In your next conversation, put your phone away and give your complete attention.", "Mindfulness in Relationships Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Forgiveness",
                "Holding grudges harms your own well-being more than the other person's. Forgiveness releases the burden of resentment.",
                "Consider one grudge you are holding and explore what it would feel like to release it.", "Journal of Behavioral Medicine"),
            WellnessTip(TipCategory.SOCIAL.value, "Volunteer Your Time",
                "Volunteering provides a sense of purpose, expands your social network, and improves mental health.",
                "Research local volunteer opportunities and sign up for one that interests you.", "Journal of Health and Social Behavior"),
            WellnessTip(TipCategory.SOCIAL.value, "Reconnect with Old Friends",
                "Rekindling old friendships can be deeply rewarding. Shared history provides a strong foundation.",
                "Send a message to an old friend you have not spoken to in a while.", "Longitudinal Friendship Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Healthy Conflict Resolution",
                "Healthy resolution involves using 'I' statements, focusing on the issue rather than the person.",
                "Reflect on a current conflict and reframe your perspective using 'I' statements.", "Conflict Resolution Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Set Healthy Boundaries",
                "Healthy boundaries are essential for maintaining energy and well-being in relationships.",
                "Identify one area where you need a boundary and practice stating it clearly and kindly.", "Boundaries Research (Cloud & Townsend)"),
            WellnessTip(TipCategory.SOCIAL.value, "Show Physical Affection",
                "Appropriate physical touch releases oxytocin and reduces cortisol. Even a brief hug can significantly reduce stress.",
                "If appropriate and welcome, share a hug or pat on the back with someone you care about.", "Psychological Science"),
            WellnessTip(TipCategory.SOCIAL.value, "Be a Good Neighbor",
                "Simple neighborly gestures build community cohesion and increase your own sense of belonging.",
                "Do one neighborly act today: greet a neighbor, offer help, or share something.", "Community Psychology Research"),
            WellnessTip(TipCategory.SOCIAL.value, "Listen to Understand, Not to Reply",
                "Most people listen with the intent to reply rather than to understand. Practice listening with curiosity.",
                "In your next conversation, focus entirely on understanding the other person before responding.", "Active Listening Research (Rogers & Farson)"),
            WellnessTip(TipCategory.SOCIAL.value, "Create a Ritual with Loved Ones",
                "Shared rituals like weekly dinners or morning walks provide predictable connection points that strengthen relationships.",
                "Propose a recurring ritual with someone you care about.", "Family Rituals Research (Fiese et al., 2002)"),
            WellnessTip(TipCategory.SOCIAL.value, "Express Love in Others' Languages",
                "People receive love differently: words of affirmation, acts of service, gifts, quality time, or physical touch.",
                "Identify the love language of someone close to you and express care in that way today.", "The 5 Love Languages by Gary Chapman"),
            WellnessTip(TipCategory.SOCIAL.value, "Practice Digital Connection Mindfully",
                "While digital tools enable connection, they can create shallow interactions. Use video calls over text when possible.",
                "Replace one text-based interaction today with a video call or voice message.", "Digital Communication Research"),
        ])

        return tips


# ---------------------------------------------------------------------------
# Session Tracker
# ---------------------------------------------------------------------------


