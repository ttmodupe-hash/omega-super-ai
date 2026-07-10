class SessionTracker:
    """Tracks user activities and provides rolling window analysis.

    The SessionTracker records each activity with its cognitive load and
    provides aggregate metrics over various time windows. It maintains a
    bounded history to prevent unbounded memory growth.
    """

    def __init__(self) -> None:
        """Initialize the session tracker."""
        self._lock = threading.Lock()
        self._activities: Dict[str, Deque[ActivityRecord]] = defaultdict(
            lambda: deque(maxlen=Constants.MAX_ACTIVITY_HISTORY)
        )
        self._last_activity_time: Dict[str, datetime] = {}
        self._current_session_start: Dict[str, datetime] = {}
        self._breaks_taken: Dict[str, int] = defaultdict(int)
        self._breaks_suggested: Dict[str, int] = defaultdict(int)
        self._last_break_time: Dict[str, datetime] = {}

    def track(
        self,
        user_id: str,
        feature: str,
        duration_ms: int,
        cognitive_load: Optional[str] = None,
    ) -> None:
        """Record a user activity.

        Args:
            user_id: Unique identifier for the user.
            feature: The feature or page the user was interacting with.
            duration_ms: Duration of the activity in milliseconds.
            cognitive_load: Optional cognitive load override. If not provided,
                the system looks up the feature's default load classification.

        Raises:
            ValueError: If duration_ms is negative or feature is empty.
        """
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        if not feature:
            raise ValueError("feature must not be empty")

        load = cognitive_load or FEATURE_COGNITIVE_LOAD.get(
            feature, CognitiveLoad.MEDIUM.value
        )

        record = ActivityRecord(
            feature=feature,
            duration_ms=duration_ms,
            cognitive_load=load,
        )

        with self._lock:
            self._activities[user_id].append(record)

            now = datetime.utcnow()

            # Check if this is a continuation of the current session
            # or the start of a new one
            last_time = self._last_activity_time.get(user_id)
            if last_time is not None:
                gap_minutes = (now - last_time).total_seconds() / 60.0
                if gap_minutes > 10:
                    # Session break - count this as an implicit break taken
                    self._breaks_taken[user_id] += 1
                    self._current_session_start[user_id] = now
                    self._last_break_time[user_id] = now
            else:
                self._current_session_start[user_id] = now

            self._last_activity_time[user_id] = now

        logger.debug(
            "Tracked activity for user %s: feature=%s duration=%d load=%s",
            user_id,
            feature,
            duration_ms,
            load,
        )

    def get_activities(
        self,
        user_id: str,
        window_minutes: int = 60,
    ) -> List[ActivityRecord]:
        """Get activities within a rolling time window.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            List of ActivityRecord objects within the window.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        with self._lock:
            history = self._activities.get(user_id, deque())
            return [a for a in history if a.timestamp >= cutoff]

    def get_screen_time_minutes(
        self,
        user_id: str,
        window_minutes: int = 1440,
    ) -> int:
        """Get total screen time in minutes for a time window.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes (default 24h).

        Returns:
            Total screen time in minutes.
        """
        activities = self.get_activities(user_id, window_minutes)
        total_ms = sum(a.duration_ms for a in activities)
        return int(total_ms / 60000)

    def get_feature_breakdown(
        self,
        user_id: str,
        window_minutes: int = 1440,
    ) -> Dict[str, int]:
        """Get screen time breakdown by feature.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Dictionary mapping feature names to minutes.
        """
        activities = self.get_activities(user_id, window_minutes)
        feature_ms: Dict[str, int] = defaultdict(int)
        for a in activities:
            feature_ms[a.feature] += a.duration_ms
        return {
            f: int(ms / 60000) for f, ms in feature_ms.items()
        }

    def get_current_session_minutes(self, user_id: str) -> int:
        """Get the length of the current continuous session in minutes.

        Args:
            user_id: The user to query.

        Returns:
            Current session length in minutes, or 0 if no active session.
        """
        with self._lock:
            start = self._current_session_start.get(user_id)
            if start is None:
                return 0
            return int((datetime.utcnow() - start).total_seconds() / 60.0)

    def get_average_cognitive_load(
        self,
        user_id: str,
        window_minutes: int = 60,
    ) -> float:
        """Get the average cognitive load multiplier for recent activities.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Average cognitive load multiplier (1.0-2.5).
        """
        activities = self.get_activities(user_id, window_minutes)
        if not activities:
            return 1.0
        total = sum(
            COGNITIVE_LOAD_MULTIPLIERS.get(a.cognitive_load, 1.5)
            for a in activities
        )
        return total / len(activities)

    def get_interaction_frequency(
        self,
        user_id: str,
        window_minutes: int = 30,
    ) -> float:
        """Get interaction frequency (activities per hour).

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Average activities per hour.
        """
        activities = self.get_activities(user_id, window_minutes)
        if not activities or window_minutes <= 0:
            return 0.0
        return len(activities) / (window_minutes / 60.0)

    def get_peak_hours(
        self,
        user_id: str,
        window_minutes: int = 1440,
    ) -> List[int]:
        """Get the hours with highest usage.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            List of hour integers (0-23) sorted by usage, top 5.
        """
        activities = self.get_activities(user_id, window_minutes)
        hour_usage: Dict[int, int] = defaultdict(int)
        for a in activities:
            hour = a.timestamp.hour
            hour_usage[hour] += a.duration_ms

        sorted_hours = sorted(
            hour_usage.items(), key=lambda x: x[1], reverse=True
        )
        return [h for h, _ in sorted_hours[:5]]

    def record_break_taken(self, user_id: str) -> None:
        """Record that the user took a break.

        Args:
            user_id: The user who took a break.
        """
        with self._lock:
            self._breaks_taken[user_id] += 1
            self._last_break_time[user_id] = datetime.utcnow()

    def record_break_suggested(self, user_id: str) -> None:
        """Record that a break was suggested to the user.

        Args:
            user_id: The user who received the suggestion.
        """
        with self._lock:
            self._breaks_suggested[user_id] += 1

    def get_break_compliance_rate(self, user_id: str) -> float:
        """Get the break compliance rate.

        Args:
            user_id: The user to query.

        Returns:
            Float between 0.0 and 1.0 representing compliance.
        """
        with self._lock:
            suggested = max(self._breaks_suggested.get(user_id, 0), 1)
            taken = self._breaks_taken.get(user_id, 0)
            return min(taken / suggested, 1.0)

    def get_last_break_minutes_ago(self, user_id: str) -> int:
        """Get minutes since the user's last break.

        Args:
            user_id: The user to query.

        Returns:
            Minutes since last break, or a large number if never.
        """
        with self._lock:
            last = self._last_break_time.get(user_id)
            if last is None:
                return 9999
            return int((datetime.utcnow() - last).total_seconds() / 60.0)

    def get_average_session_minutes(
        self,
        user_id: str,
        window_minutes: int = 1440,
    ) -> float:
        """Get the average session length in minutes.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Average session length in minutes.
        """
        activities = self.get_activities(user_id, window_minutes)
        if not activities:
            return 0.0

        # Group activities into sessions (gaps > 10 minutes)
        sessions: List[int] = []
        current_session_ms = 0
        prev_time: Optional[datetime] = None

        for a in activities:
            if prev_time is not None:
                gap = (a.timestamp - prev_time).total_seconds()
                if gap > 600:  # 10 minutes
                    sessions.append(current_session_ms)
                    current_session_ms = 0
            current_session_ms += a.duration_ms
            prev_time = a.timestamp

        if current_session_ms > 0:
            sessions.append(current_session_ms)

        if not sessions:
            return 0.0

        avg_ms = statistics.mean(sessions)
        return avg_ms / 60000.0

    def get_longest_session_minutes(
        self,
        user_id: str,
        window_minutes: int = 1440,
    ) -> int:
        """Get the longest single session in minutes.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Longest session length in minutes.
        """
        activities = self.get_activities(user_id, window_minutes)
        if not activities:
            return 0

        longest_ms = 0
        current_session_ms = 0
        prev_time: Optional[datetime] = None

        for a in activities:
            if prev_time is not None:
                gap = (a.timestamp - prev_time).total_seconds()
                if gap > 600:
                    longest_ms = max(longest_ms, current_session_ms)
                    current_session_ms = 0
            current_session_ms += a.duration_ms
            prev_time = a.timestamp

        longest_ms = max(longest_ms, current_session_ms)
        return int(longest_ms / 60000)

    def clear_user_data(self, user_id: str) -> None:
        """Clear all data for a user.

        Args:
            user_id: The user whose data to clear.
        """
        with self._lock:
            self._activities.pop(user_id, None)
            self._last_activity_time.pop(user_id, None)
            self._current_session_start.pop(user_id, None)
            self._breaks_taken.pop(user_id, None)
            self._breaks_suggested.pop(user_id, None)
            self._last_break_time.pop(user_id, None)


# ---------------------------------------------------------------------------
# Fatigue Calculator
# ---------------------------------------------------------------------------


class FatigueCalculator:
    """Calculates a composite digital fatigue score (0-100).

    The fatigue score is a weighted combination of:
    - Screen time (30%): Longer screen time = higher fatigue
    - Cognitive load (25%): More intense tasks = faster fatigue
    - Session length (20%): Longer without breaks = higher fatigue
    - Time of day (15%): Late night = fatigue accumulates faster
    - Interaction frequency (10%): Rapid switching = cognitive drain
    """

    # Score thresholds for interpretation
    THRESHOLDS: ClassVar[Dict[str, Tuple[int, int]]] = {
        FatigueLevel.FRESH.value: (0, Constants.FATIGUE_FRESH),
        FatigueLevel.MILD.value: (
            Constants.FATIGUE_FRESH + 1,
            Constants.FATIGUE_MILD,
        ),
        FatigueLevel.MODERATE.value: (
            Constants.FATIGUE_MILD + 1,
            Constants.FATIGUE_MODERATE,
        ),
        FatigueLevel.HIGH.value: (
            Constants.FATIGUE_MODERATE + 1,
            Constants.FATIGUE_HIGH,
        ),
        FatigueLevel.CRITICAL.value: (
            Constants.FATIGUE_HIGH + 1,
            Constants.FATIGUE_CRITICAL,
        ),
    }

    @classmethod
    def calculate(
        cls,
        screen_time_minutes: int,
        avg_cognitive_load: float,
        current_session_minutes: int,
        last_break_minutes_ago: int,
        interaction_frequency: float,
    ) -> int:
        """Calculate the composite fatigue score.

        Args:
            screen_time_minutes: Total screen time in recent period.
            avg_cognitive_load: Average cognitive load multiplier (1.0-2.5).
            current_session_minutes: Current continuous session length.
            last_break_minutes_ago: Minutes since last break.
            interaction_frequency: Activities per hour.

        Returns:
            Integer fatigue score between 0 and 100.
        """
        # 1. Screen time component (0-100)
        screen_component = cls._screen_time_score(screen_time_minutes)

        # 2. Cognitive load component (0-100)
        cognitive_component = cls._cognitive_load_score(avg_cognitive_load)

        # 3. Session length component (0-100)
        session_component = cls._session_length_score(
            current_session_minutes, last_break_minutes_ago
        )

        # 4. Time of day component (0-100)
        time_component = cls._time_of_day_score()

        # 5. Interaction frequency component (0-100)
        freq_component = cls._interaction_frequency_score(interaction_frequency)

        # Weighted composite
        score = (
            screen_component * Constants.WEIGHT_SCREEN_TIME
            + cognitive_component * Constants.WEIGHT_COGNITIVE_LOAD
            + session_component * Constants.WEIGHT_SESSION_LENGTH
            + time_component * Constants.WEIGHT_TIME_OF_DAY
            + freq_component * Constants.WEIGHT_INTERACTION_FREQ
        )

        return int(round(max(0.0, min(100.0, score))))

    @classmethod
    def _screen_time_score(cls, minutes: int) -> float:
        """Calculate screen time fatigue component.

        Score increases non-linearly with screen time:
        - 0-60 min: minimal fatigue
        - 60-240 min: moderate increase
        - 240+ min: steep increase

        Args:
            minutes: Screen time in minutes.

        Returns:
            Score between 0 and 100.
        """
        if minutes <= 60:
            return minutes * 0.2  # 0-12
        elif minutes <= 240:
            return 12 + (minutes - 60) * 0.35  # 12-75
        else:
            return min(75 + (minutes - 240) * 0.25, 100.0)

    @classmethod
    def _cognitive_load_score(cls, avg_load: float) -> float:
        """Calculate cognitive load fatigue component.

        Args:
            avg_load: Average cognitive load multiplier (1.0-2.5).

        Returns:
            Score between 0 and 100.
        """
        # Map 1.0-2.5 to 0-100
        normalized = (avg_load - 1.0) / 1.5
        return min(normalized * 100.0, 100.0)

    @classmethod
    def _session_length_score(
        cls, session_minutes: int, last_break_minutes_ago: int
    ) -> float:
        """Calculate session length fatigue component.

        Args:
            session_minutes: Current session length in minutes.
            last_break_minutes_ago: Minutes since last break.

        Returns:
            Score between 0 and 100.
        """
        # Score based on the longer of current session or time since break
        effective_minutes = max(session_minutes, last_break_minutes_ago)

        if effective_minutes <= 30:
            return effective_minutes * 0.5  # 0-15
        elif effective_minutes <= 120:
            return 15 + (effective_minutes - 30) * 0.5  # 15-60
        else:
            return min(60 + (effective_minutes - 120) * 0.5, 100.0)

    @classmethod
    def _time_of_day_score(cls) -> float:
        """Calculate time-of-day fatigue component.

        Fatigue accumulates faster late at night. Score peaks between
        2 AM and 4 AM, and is lowest mid-morning.

        Returns:
            Score between 0 and 100.
        """
        hour = datetime.utcnow().hour

        # Lowest fatigue at 10 AM (hour 10), highest at 3 AM (hour 3)
        # Use a sinusoidal model shifted to peak at 3 AM
        # Convert hour to angle (0-23 mapped to 0-2pi)
        angle = (hour / 24.0) * 2 * math.pi
        # Shift so peak is at 3 AM (3/24 * 2pi = pi/4)
        shift = (3 / 24.0) * 2 * math.pi
        # Cosine peaks at 0, so shift to make it peak at 3 AM
        score = 50 + 50 * math.cos(angle - shift)

        return max(0.0, min(100.0, score))

    @classmethod
    def _interaction_frequency_score(cls, freq_per_hour: float) -> float:
        """Calculate interaction frequency fatigue component.

        Rapid context switching is cognitively draining.

        Args:
            freq_per_hour: Number of activities per hour.

        Returns:
            Score between 0 and 100.
        """
        # 0-20 activities/hour is normal, 20-60 is elevated, 60+ is extreme
        if freq_per_hour <= 20:
            return freq_per_hour * 1.5  # 0-30
        elif freq_per_hour <= 60:
            return 30 + (freq_per_hour - 20) * 1.75  # 30-100
        else:
            return 100.0

    @classmethod
    def interpret_score(cls, score: int) -> str:
        """Convert a numeric fatigue score to a human-readable level.

        Args:
            score: Fatigue score (0-100).

        Returns:
            Human-readable fatigue level string.
        """
        for level, (low, high) in cls.THRESHOLDS.items():
            if low <= score <= high:
                return level
        return FatigueLevel.CRITICAL.value

    @classmethod
    def get_status_message(cls, score: int) -> str:
        """Get a gentle, positive status message for a fatigue score.

        Args:
            score: Fatigue score (0-100).

        Returns:
            Gentle, encouraging message.
        """
        messages = {
            FatigueLevel.FRESH.value: (
                "You are feeling great! Your energy is optimal for focused work."
            ),
            FatigueLevel.MILD.value: (
                "You are doing well. A micro-break soon would help you stay refreshed."
            ),
            FatigueLevel.MODERATE.value: (
                "You have been working hard. A short break would do wonders for your focus."
            ),
            FatigueLevel.HIGH.value: (
                "Your mind deserves a rest. A proper break will help you come back stronger."
            ),
            FatigueLevel.CRITICAL.value: (
                "You have been at it for a while. Your well-being comes first. "
                "Please take a meaningful break."
            ),
        }
        level = cls.interpret_score(score)
        return messages.get(
            level, "Listen to your body and take breaks when you need them."
        )


# ---------------------------------------------------------------------------
# Break Engine
# ---------------------------------------------------------------------------


class BreakEngine:
    """Generates personalized break suggestions based on user state.

    The BreakEngine analyzes the user's current fatigue score, recent activity
    patterns, and break history to recommend the most appropriate type of
    break with a gentle, positive message.
    """

    MICRO_BREAK_ACTIVITIES: ClassVar[List[Dict[str, str]]] = [
        {
            "title": "Eye Rest",
            "description": "Close your eyes gently and take 5 slow, deep breaths. Let your eye muscles fully relax.",
            "benefit": "Closing your eyes for just 20 seconds reduces eye strain by allowing your ciliary muscles to reset their focus.",
        },
        {
            "title": "Gentle Neck Rolls",
            "description": "Slowly roll your head in a circle: drop chin to chest, roll to the right shoulder, back, then left. Repeat 3 times each direction.",
            "benefit": "Neck rolls release tension in the cervical spine and improve blood flow to the brain, reducing headaches.",
        },
        {
            "title": "Shoulder Shrugs",
            "description": "Lift both shoulders up toward your ears, hold for 3 seconds, then let them drop. Repeat 5 times.",
            "benefit": "Shoulder shrugs release upper body tension that builds from forward posture during screen work.",
        },
        {
            "title": "Finger and Wrist Stretch",
            "description": "Extend your arms forward, spread your fingers wide, then make a fist. Rotate your wrists 5 times each direction.",
            "benefit": "These movements prevent repetitive strain injury and improve circulation to your hands and forearms.",
        },
        {
            "title": "Deep Breathing Reset",
            "description": "Place one hand on your belly. Inhale deeply through your nose for 4 counts, feeling your belly rise. Exhale slowly for 6 counts. Repeat 5 times.",
            "benefit": "Deep diaphragmatic breathing activates your parasympathetic nervous system, reducing stress in under 60 seconds.",
        },
        {
            "title": "Desk Stretch",
            "description": "Interlace your fingers and reach your arms overhead with palms up. Stretch tall, hold for 10 seconds, then gently lean side to side.",
            "benefit": "Overhead stretching decompresses the spine and counteracts the compressive effects of sitting.",
        },
        {
            "title": "Palming",
            "description": "Rub your palms together to warm them, then gently cup them over your closed eyes. Relax for 20-30 seconds.",
            "benefit": "The warmth and darkness help relax the eye muscles and stimulate tear production, relieving dry eyes.",
        },
        {
            "title": "Ankle Circles",
            "description": "Lift one foot slightly off the ground and rotate your ankle 10 times in each direction. Switch feet.",
            "benefit": "Ankle circles improve lower leg circulation and help prevent blood pooling from prolonged sitting.",
        },
        {
            "title": "Jaw Relaxation",
            "description": "Let your jaw hang loose, gently massage your jaw muscles in small circles, then open and close your mouth slowly 5 times.",
            "benefit": "Many people unconsciously clench their jaw while focusing. This release reduces tension headaches.",
        },
        {
            "title": "Gentle Spinal Twist",
            "description": "Sit tall, place your right hand on your left knee, and gently twist your torso to the left. Hold for 10 seconds, then switch sides.",
            "benefit": "Spinal twists relieve tension in the lower back and improve spinal mobility after sitting.",
        },
    ]

    SHORT_BREAK_ACTIVITIES: ClassVar[List[Dict[str, str]]] = [
        {
            "title": "Take a Walk",
            "description": "Step away from your screen and walk around your space, or step outside if possible. Notice the sights and sounds around you.",
            "benefit": "Walking increases blood flow to the brain, boosts creative thinking by 60%, and counteracts the effects of prolonged sitting.",
        },
        {
            "title": "Hydration Break",
            "description": "Drink a full glass of water slowly. Pay attention to the sensation of hydration.",
            "benefit": "Even mild dehydration impairs cognitive performance. A glass of water restores focus and energy.",
        },
        {
            "title": "Mindful Minute",
            "description": "Find a comfortable position, close your eyes, and focus entirely on your breath for one minute. When your mind wanders, gently return to your breath.",
            "benefit": "Just one minute of mindfulness reduces cortisol levels and resets your attention for better focus when you return.",
        },
        {
            "title": "Look at Nature",
            "description": "Find a window and look at natural scenery for a few minutes. If no window is available, look at images of nature.",
            "benefit": "Viewing nature reduces mental fatigue and restores directed attention capacity, a phenomenon known as Attention Restoration Theory.",
        },
        {
            "title": "Quick Tidy",
            "description": "Spend a few minutes tidying your immediate workspace. Clear away clutter, organize papers, and wipe down your desk.",
            "benefit": "A clean workspace reduces cognitive overload and creates a sense of calm and control.",
        },
        {
            "title": "Snack Smart",
            "description": "Have a healthy snack like a handful of nuts, a piece of fruit, or some dark chocolate. Eat mindfully, savoring each bite.",
            "benefit": "Nutrient-dense snacks stabilize blood sugar and provide sustained energy without the crash of sugary options.",
        },
        {
            "title": "Connect with Someone",
            "description": "Send a quick message, make a brief call, or have a short chat with a colleague, friend, or family member.",
            "benefit": "Social connection releases oxytocin, which reduces stress and boosts mood and motivation.",
        },
        {
            "title": "Eye Exercise Routine",
            "description": "Practice the 20-20-20 rule: look at something 20 feet away for 20 seconds. Then do 10 slow eye rolls in each direction.",
            "benefit": "These exercises relax the ciliary muscles responsible for focusing and reduce eye strain significantly.",
        },
        {
            "title": "Listen to Music",
            "description": "Put on a favorite song and listen actively. If you feel like it, move or dance to the music.",
            "benefit": "Music activates multiple brain regions associated with pleasure and can reduce stress hormones within minutes.",
        },
        {
            "title": "Gratitude Pause",
            "description": "Write down or mentally list three things you are grateful for right now. They can be big or small.",
            "benefit": "Gratitude practice has been shown to increase happiness, reduce stress, and improve overall well-being.",
        },
    ]

    LONG_BREAK_ACTIVITIES: ClassVar[List[Dict[str, str]]] = [
        {
            "title": "Go for a Real Walk",
            "description": "Leave your workspace and go for a 15-30 minute walk outside. Leave your phone behind or in your pocket.",
            "benefit": "Walking in nature reduces cortisol, improves mood, and provides cardiovascular benefits. It also gives your brain space for creative insights.",
        },
        {
            "title": "Have a Proper Meal",
            "description": "Step away from all screens and enjoy a nutritious meal. Eat slowly, savoring each bite without distractions.",
            "benefit": "Mindful eating improves digestion, nutrient absorption, and satisfaction. The break from screens allows your brain to rest.",
        },
        {
            "title": "Power Nap",
            "description": "Lie down in a quiet, dark space and set an alarm for 10-20 minutes. Close your eyes and relax.",
            "benefit": "NASA research found that a 10-20 minute nap improves alertness and performance by 34% without causing grogginess.",
        },
        {
            "title": "Physical Exercise",
            "description": "Do a workout: yoga, stretching, bodyweight exercises, or whatever movement you enjoy. Even 15 minutes makes a difference.",
            "benefit": "Exercise releases endorphins, reduces stress, and improves cognitive function. The benefits last for hours afterward.",
        },
        {
            "title": "Meditation Session",
            "description": "Sit comfortably, close your eyes, and practice meditation for 15-20 minutes. Focus on your breath or use a guided meditation app.",
            "benefit": "Regular meditation reduces anxiety, improves focus, and actually changes brain structure in positive ways (neuroplasticity).",
        },
        {
            "title": "Social Connection",
            "description": "Meet a friend for coffee, have a meal with family, or call someone you care about for a real conversation.",
            "benefit": "Meaningful social interaction is one of the strongest predictors of happiness and longevity.",
        },
        {
            "title": "Creative Activity",
            "description": "Engage in a creative hobby: drawing, playing music, writing, crafting, cooking, or anything that lets you express yourself.",
            "benefit": "Creative activities engage different brain networks than analytical work, providing genuine cognitive rest and renewal.",
        },
        {
            "title": "Take a Shower",
            "description": "A warm shower relaxes tense muscles and provides a mental reset. Many people have their best ideas in the shower.",
            "benefit": "The warm water increases blood flow, relaxes muscles, and the sensory deprivation allows your default mode network to generate creative insights.",
        },
    ]

    SESSION_END_ACTIVITIES: ClassVar[List[Dict[str, str]]] = [
        {
            "title": "Wind-Down Routine",
            "description": "Begin your evening wind-down: dim the lights, put away screens, and engage in calming activities like reading or gentle stretching.",
            "benefit": "A consistent wind-down routine signals to your brain that it is time to sleep, improving both sleep quality and how quickly you fall asleep.",
        },
        {
            "title": "Gentle Evening Stretch",
            "description": "Do a series of gentle stretches focusing on areas that feel tense. Move slowly and breathe deeply into each stretch.",
            "benefit": "Gentle stretching in the evening releases physical tension accumulated during the day and promotes relaxation.",
        },
        {
            "title": "Journal Reflection",
            "description": "Spend 10 minutes writing about your day: what went well, what you learned, and what you are looking forward to tomorrow.",
            "benefit": "Evening journaling processes the day's experiences, reduces rumination, and creates mental closure for better sleep.",
        },
        {
            "title": "Reading Time",
            "description": "Read a physical book or e-ink device for pleasure. Choose something light and enjoyable, not work-related.",
            "benefit": "Reading fiction or light non-fiction reduces stress by 68% (more than listening to music or taking a walk) and prepares the mind for sleep.",
        },
    ]

    GENTLE_MESSAGES: ClassVar[Dict[str, List[str]]] = {
        BreakType.MICRO.value: [
            "A tiny reset for a big refresh. Take 20 seconds just for you.",
            "Your eyes will thank you for this quick pause.",
            "A little stretch goes a long way. Care to try?",
            "Quick pause, big difference. You have earned 20 seconds.",
        ],
        BreakType.SHORT.value: [
            "You have been doing amazing work. A short break will help you keep that momentum.",
            "Your brain has been working hard. It deserves a few minutes of rest.",
            "A quick break now means better focus when you return. Want to give it a try?",
            "Step away for just a few minutes. You will come back even stronger.",
        ],
        BreakType.LONG.value: [
            "You have put in serious work today. Your mind and body will thank you for a proper break.",
            "Rest is not a reward for finishing work; it is part of the process. Time to recharge.",
            "A longer break now will make the rest of your day more productive and enjoyable.",
            "You have earned this. Step away, recharge, and return when you are ready.",
        ],
        BreakType.SESSION_END.value: [
            "The day is winding down. Your well-being is the top priority now.",
            "Rest is productive too. Time to let your mind and body recover.",
            "You have done enough for today. Let yourself relax and prepare for restful sleep.",
        ],
    }

    @classmethod
    def get_suggestion(
        cls,
        fatigue_score: int,
        current_session_minutes: int,
        last_break_minutes_ago: int,
        wind_down_active: bool = False,
    ) -> BreakSuggestion:
        """Generate a personalized break suggestion.

        Args:
            fatigue_score: Current fatigue score (0-100).
            current_session_minutes: Current session length in minutes.
            last_break_minutes_ago: Minutes since last break.
            wind_down_active: Whether wind-down mode is active.

        Returns:
            A BreakSuggestion tailored to the user's current state.
        """
        if wind_down_active:
            break_type = BreakType.SESSION_END.value
            activity = random.choice(cls.SESSION_END_ACTIVITIES)
            duration = random.choice([300, 600, 900])
        elif fatigue_score >= Constants.FATIGUE_HIGH:
            break_type = BreakType.LONG.value
            activity = random.choice(cls.LONG_BREAK_ACTIVITIES)
            duration = random.choice([600, 900, 1200, 1800])
        elif fatigue_score >= Constants.FATIGUE_MODERATE:
            break_type = BreakType.SHORT.value
            activity = random.choice(cls.SHORT_BREAK_ACTIVITIES)
            duration = random.choice([180, 240, 300, 360])
        elif current_session_minutes >= Constants.MICRO_BREAK_INTERVAL:
            break_type = BreakType.MICRO.value
            activity = random.choice(cls.MICRO_BREAK_ACTIVITIES)
            duration = random.choice([20, 30])
        else:
            break_type = BreakType.MICRO.value
            activity = random.choice(cls.MICRO_BREAK_ACTIVITIES)
            duration = 20

        message = random.choice(
            cls.GENTLE_MESSAGES.get(break_type, cls.GENTLE_MESSAGES[BreakType.MICRO.value])
        )

        return BreakSuggestion(
            break_type=break_type,
            duration_seconds=duration,
            title=activity["title"],
            description=activity["description"]
# ___END_OF_FILE___