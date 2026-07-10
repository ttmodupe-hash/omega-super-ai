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
            description=activity["description"],
            benefit=activity["benefit"],
            message=message,
            fatigue_score=fatigue_score,
        )


# ---------------------------------------------------------------------------
# Eye Strain Tracker (20-20-20 Rule)
# ---------------------------------------------------------------------------


class EyeStrainTracker:
    """Tracks compliance with the 20-20-20 rule for eye strain prevention.

    Every 20 minutes of screen time, users should look at something 20 feet
    away for 20 seconds. This class tracks reminders and compliance.
    """

    def __init__(self) -> None:
        """Initialize the eye strain tracker."""
        self._lock = threading.Lock()
        self._last_eye_break: Dict[str, datetime] = {}
        self._compliance_streak: Dict[str, int] = defaultdict(int)
        self._total_reminders: Dict[str, int] = defaultdict(int)
        self._compliance_count: Dict[str, int] = defaultdict(int)

    def record_screen_time(
        self, user_id: str, duration_ms: int
    ) -> bool:
        """Record screen time and check if an eye break is due.

        Args:
            user_id: The user identifier.
            duration_ms: Screen time duration in milliseconds.

        Returns:
            True if an eye break reminder should be shown.
        """
        with self._lock:
            now = datetime.utcnow()
            last = self._last_eye_break.get(user_id)

            if last is None:
                self._last_eye_break[user_id] = now
                return False

            minutes_since = (now - last).total_seconds() / 60.0

            if minutes_since >= Constants.EYE_BREAK_INTERVAL_MINUTES:
                self._total_reminders[user_id] += 1
                return True

            return False

    def record_compliance(self, user_id: str) -> None:
        """Record that the user took an eye break.

        Args:
            user_id: The user who took the break.
        """
        with self._lock:
            self._last_eye_break[user_id] = datetime.utcnow()
            self._compliance_streak[user_id] += 1
            self._compliance_count[user_id] += 1

    def get_compliance_rate(self, user_id: str) -> float:
        """Get the eye break compliance rate.

        Args:
            user_id: The user to query.

        Returns:
            Float between 0.0 and 1.0.
        """
        with self._lock:
            total = max(self._total_reminders.get(user_id, 0), 1)
            compliant = self._compliance_count.get(user_id, 0)
            return min(compliant / total, 1.0)

    def get_streak(self, user_id: str) -> int:
        """Get the current eye break compliance streak.

        Args:
            user_id: The user to query.

        Returns:
            Number of consecutive compliant breaks.
        """
        with self._lock:
            return self._compliance_streak.get(user_id, 0)

    def reset_streak(self, user_id: str) -> None:
        """Reset the compliance streak (called when user misses a break).

        Args:
            user_id: The user whose streak to reset.
        """
        with self._lock:
            self._compliance_streak[user_id] = 0

    def get_reminder_message(self, user_id: str) -> str:
        """Get a gentle reminder message for the 20-20-20 rule.

        Args:
            user_id: The user to address.

        Returns:
            Gentle, encouraging reminder message.
        """
        streak = self.get_streak(user_id)
        if streak >= 5:
            return (
                f"Amazing! You have a {streak}-break streak. "
                "Time for another 20-20-20: look 20 feet away for 20 seconds!"
            )
        elif streak >= 3:
            return (
                f"Great job! {streak} breaks in a row. "
                "Look at something 20 feet away for 20 seconds."
            )
        else:
            return (
                "Friendly reminder: look at something about 20 feet away "
                "for 20 seconds. Your eyes will thank you!"
            )


# ---------------------------------------------------------------------------
# Focus Mode Manager
# ---------------------------------------------------------------------------


class FocusModeManager:
    """Manages focus mode and Pomodoro timer functionality.

    Focus mode provides a distraction-free environment with integrated
    Pomodoro timing. Users can select from preset work/break intervals
    or customize their own.
    """

    PRESETS: ClassVar[Dict[str, Tuple[int, int]]] = {
        "classic": Constants.POMODORO_CLASSIC,
        "long": Constants.POMODORO_LONG,
        "short": Constants.POMODORO_SHORT,
    }

    def __init__(self) -> None:
        """Initialize the focus mode manager."""
        self._lock = threading.Lock()
        self._focus_state: Dict[str, str] = {}
        self._pomodoro_phase: Dict[str, str] = {}
        self._pomodoro_preset: Dict[str, str] = {}
        self._phase_start_time: Dict[str, datetime] = {}
        self._sessions_completed: Dict[str, int] = defaultdict(int)
        self._daily_goal: Dict[str, int] = defaultdict(lambda: 8)

    def toggle_focus(self, user_id: str, enabled: bool) -> None:
        """Toggle focus mode for a user.

        Args:
            user_id: The user to toggle focus mode for.
            enabled: Whether to enable or disable focus mode.
        """
        with self._lock:
            if enabled:
                self._focus_state[user_id] = FocusModeState.ACTIVE.value
                self._pomodoro_phase[user_id] = PomodoroPhase.IDLE.value
                self._phase_start_time[user_id] = datetime.utcnow()
            else:
                self._focus_state[user_id] = FocusModeState.INACTIVE.value
                self._pomodoro_phase[user_id] = PomodoroPhase.IDLE.value

        logger.info(
            "Focus mode %s for user %s",
            "enabled" if enabled else "disabled",
            user_id,
        )

    def start_pomodoro(
        self, user_id: str, preset: str = "classic"
    ) -> None:
        """Start a Pomodoro session.

        Args:
            user_id: The user to start the session for.
            preset: Pomodoro preset name (classic, long, short).

        Raises:
            ValueError: If the preset is not recognized.
        """
        if preset not in self.PRESETS:
            raise ValueError(
                f"Unknown preset: {preset}. Available: {list(self.PRESETS.keys())}"
            )

        with self._lock:
            self._focus_state[user_id] = FocusModeState.ACTIVE.value
            self._pomodoro_phase[user_id] = PomodoroPhase.WORK.value
            self._pomodoro_preset[user_id] = preset
            self._phase_start_time[user_id] = datetime.utcnow()

        logger.info(
            "Pomodoro started for user %s with preset %s", user_id, preset
        )

    def stop_pomodoro(self, user_id: str) -> None:
        """Stop the current Pomodoro session.

        Args:
            user_id: The user to stop the session for.
        """
        with self._lock:
            self._pomodoro_phase[user_id] = PomodoroPhase.IDLE.value
            self._focus_state[user_id] = FocusModeState.INACTIVE.value

    def get_status(self, user_id: str) -> FocusStatus:
        """Get the current focus mode status.

        Args:
            user_id: The user to query.

        Returns:
            FocusStatus with current state and timer information.
        """
        with self._lock:
            state = self._focus_state.get(
                user_id, FocusModeState.INACTIVE.value
            )
            phase = self._pomodoro_phase.get(
                user_id, PomodoroPhase.IDLE.value
            )
            preset_name = self._pomodoro_preset.get(user_id, "classic")
            work_min, break_min = self.PRESETS.get(
                preset_name, Constants.POMODORO_CLASSIC
            )
            start_time = self._phase_start_time.get(user_id)
            sessions = self._sessions_completed.get(user_id, 0)
            goal = self._daily_goal.get(user_id, 8)

        if start_time is not None and phase != PomodoroPhase.IDLE.value:
            elapsed = int(
                (datetime.utcnow() - start_time).total_seconds()
            )
            if phase == PomodoroPhase.WORK.value:
                remaining = max(work_min * 60 - elapsed, 0)
            else:
                remaining = max(break_min * 60 - elapsed, 0)
        else:
            elapsed = 0
            remaining = work_min * 60 if phase == PomodoroPhase.IDLE.value else 0

        return FocusStatus(
            state=state,
            pomodoro_phase=phase,
            pomodoro_work_minutes=work_min,
            pomodoro_break_minutes=break_min,
            elapsed_seconds=elapsed,
            remaining_seconds=remaining,
            sessions_completed=sessions,
            daily_goal=goal,
        )

    def set_daily_goal(self, user_id: str, goal: int) -> None:
        """Set the daily Pomodoro session goal.

        Args:
            user_id: The user to set the goal for.
            goal: Number of sessions per day.

        Raises:
            ValueError: If goal is not positive.
        """
        if goal < 1:
            raise ValueError("Daily goal must be at least 1")
        with self._lock:
            self._daily_goal[user_id] = goal

    def complete_session(self, user_id: str) -> None:
        """Record a completed Pomodoro session.

        Args:
            user_id: The user who completed a session.
        """
        with self._lock:
            self._sessions_completed[user_id] += 1
            # Switch to break phase
            self._pomodoro_phase[user_id] = PomodoroPhase.BREAK.value
            self._phase_start_time[user_id] = datetime.utcnow()

    def complete_break(self, user_id: str) -> None:
        """Record a completed break and return to work.

        Args:
            user_id: The user who completed a break.
        """
        with self._lock:
            self._pomodoro_phase[user_id] = PomodoroPhase.WORK.value
            self._phase_start_time[user_id] = datetime.utcnow()

    def is_focus_active(self, user_id: str) -> bool:
        """Check if focus mode is currently active.

        Args:
            user_id: The user to check.

        Returns:
            True if focus mode is active.
        """
        with self._lock:
            return (
                self._focus_state.get(user_id)
                == FocusModeState.ACTIVE.value
            )


# ---------------------------------------------------------------------------
# Wind-Down Mode Manager
# ---------------------------------------------------------------------------


class WindDownManager:
    """Manages wind-down mode for evening sleep hygiene.

    Wind-down mode activates during configurable evening hours and provides
    gentle nudges toward restful activities and away from stimulating screen use.
    """

    def __init__(self) -> None:
        """Initialize the wind-down manager."""
        self._user_start_hours: Dict[str, int] = {}
        self._user_enabled: Dict[str, bool] = {}

    def is_active(
        self,
        user_id: str,
        default_start_hour: int = Constants.WIND_DOWN_START_HOUR,
    ) -> bool:
        """Check if wind-down mode should be active.

        Wind-down is active from the start hour until the end hour
        (default 9 PM to 7 AM).

        Args:
            user_id: The user to check.
            default_start_hour: Default start hour if user has not set one.

        Returns:
            True if wind-down mode is active.
        """
        enabled = self._user_enabled.get(user_id, True)
        if not enabled:
            return False

        start_hour = self._user_start_hours.get(user_id, default_start_hour)
        current_hour = datetime.utcnow().hour

        # Wind-down is active from start_hour through midnight until end_hour
        if start_hour <= current_hour or current_hour < Constants.WIND_DOWN_END_HOUR:
            return True
        return False

    def set_start_hour(self, user_id: str, hour: int) -> None:
        """Set the wind-down start hour for a user.

        Args:
            user_id: The user to configure.
            hour: Start hour in 24-hour format (0-23).

        Raises:
            ValueError: If hour is not in valid range.
        """
        if not 0 <= hour <= 23:
            raise ValueError("Hour must be between 0 and 23")
        self._user_start_hours[user_id] = hour

    def set_enabled(self, user_id: str, enabled: bool) -> None:
        """Enable or disable wind-down mode.

        Args:
            user_id: The user to configure.
            enabled: Whether wind-down mode is enabled.
        """
        self._user_enabled[user_id] = enabled

    def get_suggestions(self) -> List[str]:
        """Get wind-down activity suggestions.

        Returns:
            List of calming activity suggestions.
        """
        return [
            "Read a physical book or e-ink device",
            "Practice gentle stretching or yoga",
            "Listen to calming music or a sleep podcast",
            "Do a meditation or breathing exercise",
            "Write in a journal",
            "Take a warm bath or shower",
            "Prepare for tomorrow to reduce morning stress",
            "Dim the lights in your environment",
            "Do a body scan relaxation exercise",
            "Sip herbal tea like chamomile or peppermint",
        ]

    def get_tip(self) -> str:
        """Get a wind-down specific tip.

        Returns:
            A sleep hygiene tip appropriate for wind-down hours.
        """
        tips = [
            "The blue light from screens can delay melatonin production by up to 3 hours. Consider switching to non-screen activities.",
            "A consistent bedtime routine signals your brain to prepare for sleep. Try to go to bed at the same time each night.",
            "Your bedroom should be cool (60-67F), dark, and quiet for optimal sleep conditions.",
            "Avoid caffeine for at least 6 hours before bedtime. It has a half-life of 5-6 hours.",
            "A warm bath 1-2 hours before bed helps your body temperature drop, which signals sleepiness.",
        ]
        return random.choice(tips)


# ---------------------------------------------------------------------------
# Screen Time Goals Manager
# ---------------------------------------------------------------------------


class ScreenTimeGoalsManager:
    """Manages user-defined screen time goals and tracks progress.

    Provides gentle warnings when users approach their limits and
    celebrates healthy habits.
    """

    def __init__(self, session_tracker: SessionTracker) -> None:
        """Initialize the goals manager.

        Args:
            session_tracker: The session tracker for querying usage.
        """
        self._tracker = session_tracker
        self._lock = threading.Lock()
        self._goals: Dict[str, ScreenTimeGoals] = {}
        self._warning_sent: Dict[str, Dict[str, bool]] = defaultdict(
            lambda: {"50": False, "80": False, "100": False}
        )

    def set_goals(self, user_id: str, goals: ScreenTimeGoals) -> None:
        """Set screen time goals for a user.

        Args:
            user_id: The user to set goals for.
            goals: ScreenTimeGoals object with desired limits.
        """
        with self._lock:
            self._goals[user_id] = goals
            # Reset warning flags
            self._warning_sent[user_id] = {
                "50": False,
                "80": False,
                "100": False,
            }

    def get_goals(self, user_id: str) -> ScreenTimeGoals:
        """Get current screen time goals for a user.

        Args:
            user_id: The user to query.

        Returns:
            ScreenTimeGoals object (returns defaults if not set).
        """
        with self._lock:
            goals = self._goals.get(user_id)
            if goals is None:
                goals = ScreenTimeGoals()
                self._goals[user_id] = goals
            return goals

    def check_progress(self, user_id: str) -> Dict[str, Any]:
        """Check progress against screen time goals.

        Args:
            user_id: The user to check.

        Returns:
            Dictionary with progress information and any warnings.
        """
        goals = self.get_goals(user_id)
        used_minutes = self._tracker.get_screen_time_minutes(
            user_id, window_minutes=1440
        )
        limit = goals.daily_limit_minutes

        if limit <= 0:
            percentage = 0.0
        else:
            percentage = (used_minutes / limit) * 100.0

        warnings: List[str] = []

        with self._lock:
            warning_flags = self._warning_sent.get(user_id, {})

            if percentage >= 100 and not warning_flags.get("100"):
                warnings.append(
                    "You have reached your daily screen time goal. "
                    "Great job being mindful of your usage today!"
                )
                warning_flags["100"] = True
            elif percentage >= 80 and not warning_flags.get("80"):
                warnings.append(
                    "You are at 80% of your daily screen time goal. "
                    "Consider taking a longer break or winding down soon."
                )
                warning_flags["80"] = True
            elif percentage >= 50 and not warning_flags.get("50"):
                warnings.append(
                    "You are at 50% of your daily screen time goal. "
                    "You are using your time mindfully. Keep it up!"
                )
                warning_flags["50"] = True

        return {
            "used_minutes": used_minutes,
            "limit_minutes": limit,
            "percentage": round(percentage, 1),
            "remaining_minutes": max(limit - used_minutes, 0),
            "warnings": warnings,
        }

    def reset_daily_warnings(self, user_id: str) -> None:
        """Reset warning flags for a new day.

        Args:
            user_id: The user to reset.
        """
        with self._lock:
            self._warning_sent[user_id] = {
                "50": False,
                "80": False,
                "100": False,
            }


# ---------------------------------------------------------------------------
# Wellness Tips Engine
# ---------------------------------------------------------------------------


class WellnessTipsEngine:
    """Serves contextual wellness tips based on user state.

    Uses the WellnessTipsDatabase to select tips that are relevant to the
    user's current fatigue level, activity, and tip history.
    """

    def __init__(self) -> None:
        """Initialize the tips engine."""
        self._lock = threading.Lock()
        self._tip_history: Dict[str, Deque[str]] = defaultdict(
            lambda: deque(maxlen=Constants.MAX_TIP_HISTORY)
        )

    def get_tip(
        self,
        user_id: str,
        fatigue_score: int = 50,
        current_activity: str = "",
        category: Optional[str] = None,
    ) -> WellnessTip:
        """Get a contextual wellness tip.

        Args:
            user_id: The user to get a tip for.
            fatigue_score: Current fatigue score.
            current_activity: Current activity type.
            category: Optional preferred category.

        Returns:
            A contextually selected WellnessTip.
        """
        with self._lock:
            history = list(self._tip_history.get(user_id, deque()))

        tip = WellnessTipsDatabase.select_contextual_tip(
            fatigue_score=fatigue_score,
            current_activity=current_activity,
            tip_history=history,
            preferred_category=category,
        )

        with self._lock:
            self._tip_history[user_id].append(tip.title)

        return tip

    def get_categories(self) -> List[str]:
        """Get all available tip categories.

        Returns:
            List of category name strings.
        """
        return WellnessTipsDatabase.get_categories()

    def get_tips_by_category(self, category: str) -> List[WellnessTip]:
        """Get all tips in a specific category.

        Args:
            category: Category to filter by.

        Returns:
            List of WellnessTip objects.
        """
        return WellnessTipsDatabase.get_tips_by_category(category)

    def clear_history(self, user_id: str) -> None:
        """Clear tip history for a user.

        Args:
            user_id: The user whose history to clear.
        """
        with self._lock:
            self._tip_history.pop(user_id, None)


# ---------------------------------------------------------------------------
# Usage Analytics
# ---------------------------------------------------------------------------


class UsageAnalytics:
    """Aggregates usage patterns and generates insights.

    Provides daily, weekly, and monthly reports with personalized insights
    based on usage patterns, fatigue trends, and break compliance.
    """

    def __init__(
        self,
        session_tracker: SessionTracker,
        fatigue_calculator: FatigueCalculator,
    ) -> None:
        """Initialize usage analytics.

        Args:
            session_tracker: The session tracker for activity data.
            fatigue_calculator: The fatigue calculator for scoring.
        """
        self._tracker = session_tracker
        self._fatigue_calc = fatigue_calculator
        self._fatigue_history: Dict[str, Deque[Tuple[datetime, int]]] = (
            defaultdict(lambda: deque(maxlen=1000))
        )

    def record_fatigue_score(self, user_id: str, score: int) -> None:
        """Record a fatigue score for trend analysis.

        Args:
            user_id: The user identifier.
            score: The fatigue score (0-100).
        """
        self._fatigue_history[user_id].append((datetime.utcnow(), score))

    def generate_report(
        self,
        user_id: str,
        period: str = "today",
    ) -> UsageReport:
        """Generate a usage analytics report.

        Args:
            user_id: The user to generate the report for.
            period: Report period (today, weekly, monthly).

        Returns:
            UsageReport with analytics and insights.

        Raises:
            ValueError: If period is not recognized.
        """
        if period == "today":
            window_minutes = 1440
        elif period == "weekly":
            window_minutes = 10080
        elif period == "monthly":
            window_minutes = 43200
        else:
            raise ValueError(
                f"Unknown period: {period}. Use 'today', 'weekly', or 'monthly'."
            )

        total_minutes = self._tracker.get_screen_time_minutes(
            user_id, window_minutes
        )
        feature_breakdown = self._tracker.get_feature_breakdown(
            user_id, window_minutes
        )
        peak_hours = self._tracker.get_peak_hours(user_id, window_minutes)
        avg_session = self._tracker.get_average_session_minutes(
            user_id, window_minutes
        )
        longest_session = self._tracker.get_longest_session_minutes(
            user_id, window_minutes
        )
        breaks_taken = self._tracker._breaks_taken.get(user_id, 0)
        breaks_suggested = self._tracker._breaks_suggested.get(user_id, 0)
        compliance_rate = self._tracker.get_break_compliance_rate(user_id)
        avg_fatigue = self._get_average_fatigue(user_id, window_minutes)
        fatigue_trend = self._analyze_fatigue_trend(user_id)
        insights = self._generate_insights(
            user_id,
            total_minutes,
            avg_session,
            compliance_rate,
            avg_fatigue,
            feature_breakdown,
        )

        return UsageReport(
            period=period,
            total_screen_time_minutes=total_minutes,
            feature_breakdown=feature_breakdown,
            peak_hours=peak_hours,
            average_session_minutes=round(avg_session, 1),
            longest_session_minutes=longest_session,
            breaks_taken=breaks_taken,
            breaks_suggested=breaks_suggested,
            break_compliance_rate=round(compliance_rate, 2),
            average_fatigue_score=round(avg_fatigue, 1),
            fatigue_trend=fatigue_trend,
            insights=insights,
        )

    def _get_average_fatigue(
        self, user_id: str, window_minutes: int
    ) -> float:
        """Get average fatigue score over a time window.

        Args:
            user_id: The user to query.
            window_minutes: Lookback window in minutes.

        Returns:
            Average fatigue score.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        scores = [
            s for t, s in self._fatigue_history.get(user_id, deque())
            if t >= cutoff
        ]
        if not scores:
            return 25.0
        return statistics.mean(scores)

    def _analyze_fatigue_trend(self, user_id: str) -> str:
        """Analyze fatigue score trend.

        Args:
            user_id: The user to analyze.

        Returns:
            Human-readable trend description.
        """
        history = list(self._fatigue_history.get(user_id, deque()))
        if len(history) < 5:
            return "insufficient_data"

        # Compare first half vs second half
        mid = len(history) // 2
        first_half = [s for _, s in history[:mid]]
        second_half = [s for _, s in history[mid:]]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        diff = second_avg - first_avg
        if diff < -10:
            return "improving"
        elif diff < -5:
            return "slightly_improving"
        elif diff > 10:
            return "worsening"
        elif diff > 5:
            return "slightly_worsening"
        else:
            return "stable"

    def _generate_insights(
        self,
        user_id: str,
        total_minutes: int,
        avg_session: float,
        compliance_rate: float,
        avg_fatigue: float,
        feature_breakdown: Dict[str, int],
    ) -> List[str]:
        """Generate personalized insights based on usage patterns.

        Args:
            user_id: The user to generate insights for.
            total_minutes: Total screen time in minutes.
            avg_session: Average session length in minutes.
            compliance_rate: Break compliance rate.
            avg_fatigue: Average fatigue score.
            feature_breakdown: Screen time by feature.

        Returns:
            List of insight strings.
        """
        insights: List[str] = []

        # Screen time insights
        hours = total_minutes / 60.0
        if hours > 10:
            insights.append(
                f"Your screen time is {hours:.1f} hours. Consider setting a daily limit and scheduling more offline activities."
            )
        elif hours > 6:
            insights.append(
                f"Your screen time is {hours:.1f} hours, which is within a typical range. Keep listening to your body's signals."
            )
        elif hours > 0:
            insights.append(
                f"Your screen time is {hours:.1f} hours. Great balance between digital engagement and rest!"
            )

        # Session length insights
        if avg_session > 90:
            insights.append(
                f"Your average session length is {avg_session:.0f} minutes. Try taking breaks every 60 minutes to maintain focus and reduce fatigue."
            )
        elif avg_session > 45:
            insights.append(
                f"Your average session length is {avg_session:.0f} minutes. You are doing well at maintaining focused work periods."
            )
        elif avg_session > 0:
            insights.append(
                f"Your average session length is {avg_session:.0f} minutes. Great job taking regular breaks!"
            )

        # Break compliance insights
        if compliance_rate < 0.3:
            insights.append(
                f"Your break compliance is {compliance_rate:.0%}. Taking even short breaks can significantly improve your well-being and productivity."
            )
        elif compliance_rate < 0.6:
            insights.append(
                f"Your break compliance is {compliance_rate:.0%}. You are doing okay, but there is room for improvement. Your future self will thank you!"
            )
        elif compliance_rate >= 0.6:
            insights.append(
                f"Your break compliance is {compliance_rate:.0%}. Excellent job prioritizing your well-being!"
            )

        # Fatigue insights
        if avg_fatigue > 60:
            insights.append(
                f"Your average fatigue score is {avg_fatigue:.0f}. Consider incorporating more breaks, hydration, and movement into your routine."
            )
        elif avg_fatigue > 40:
            insights.append(
                f"Your average fatigue score is {avg_fatigue:.0f}. You are managing well, but watch for signs of increasing fatigue."
            )
        else:
            insights.append(
                f"Your average fatigue score is {avg_fatigue:.0f}. You are maintaining excellent energy levels!"
            )

        # Feature insights
        if feature_breakdown:
            top_feature = max(feature_breakdown, key=feature_breakdown.get)
            top_minutes = feature_breakdown[top_feature]
            insights.append(
                f"Your most-used feature is '{top_feature}' ({top_minutes} minutes). Make sure you are balancing this with other activities."
            )

        return insights


# ---------------------------------------------------------------------------
# User Preferences Manager
# ---------------------------------------------------------------------------


class UserPreferencesManager:
    """Manages per-user wellness preferences.

    Stores and retrieves user preferences for wellness feature customization.
    """

    def __init__(self) -> None:
        """Initialize the preferences manager."""
        self._lock = threading.Lock()
        self._preferences: Dict[str, WellnessPreferences] = {}

    def get_preferences(self, user_id: str) -> WellnessPreferences:
        """Get wellness preferences for a user.

        Args:
            user_id: The user to query.

        Returns:
            WellnessPreferences object (returns defaults if not set).
        """
        with self._lock:
            prefs = self._preferences.get(user_id)
            if prefs is None:
                prefs = WellnessPreferences()
                self._preferences[user_id] = prefs
            return prefs

    def update_preferences(
        self, user_id: str, updates: Dict[str, Any]
    ) -> WellnessPreferences:
        """Update wellness preferences for a user.

        Args:
            user_id: The user to update.
            updates: Dictionary of preference fields to update.

        Returns:
            Updated WellnessPreferences object.
        """
        with self._lock:
            prefs = self._preferences.get(user_id, WellnessPreferences())
            for key, value in updates.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)
            self._preferences[user_id] = prefs
            return prefs

    def reset_preferences(self, user_id: str) -> None:
        """Reset preferences to defaults.

        Args:
            user_id: The user whose preferences to reset.
        """
        with self._lock:
            self._preferences[user_id] = WellnessPreferences()


# ---------------------------------------------------------------------------
# Main Wellness Engine
# ---------------------------------------------------------------------------


class WellnessEngine:
    """Central wellness engine that orchestrates all subsystems.

    The WellnessEngine is the primary interface for the digital wellness
    system. It coordinates the session tracker, fatigue calculator, break
    engine, eye strain tracker, focus mode, wind-down mode, usage analytics,
    screen time goals, and wellness tips engine.

    This class is designed to be used as a singleton via the
    ``wellness_engine`` module-level instance.
    """

    def __init__(self) -> None:
        """Initialize the wellness engine and all subsystems."""
        logger.info("Initializing WellnessEngine...")

        self._session_tracker = SessionTracker()
        self._fatigue_calculator = FatigueCalculator()
        self._break_engine = BreakEngine()
        self._eye_tracker = EyeStrainTracker()
        self._focus_manager = FocusModeManager()
        self._wind_down_manager = WindDownManager()
        self._goals_manager = ScreenTimeGoalsManager(self._session_tracker)
        self._tips_engine = WellnessTipsEngine()
        self._usage_analytics = UsageAnalytics(
            self._session_tracker, self._fatigue_calculator
        )
        self._preferences_manager = UserPreferencesManager()

        # Ensure tips database is initialized
        WellnessTipsDatabase._initialize()

        logger.info("WellnessEngine initialized successfully")

    # =====================================================================
    # Public API
    # =====================================================================

    def track_activity(
        self,
        user_id: str,
        feature: str,
        duration_ms: int,
        cognitive_load: Optional[str] = None,
    ) -> None:
        """Track user activity for wellness analysis.

        Args:
            user_id: Unique identifier for the user.
            feature: The feature or page the user was interacting with.
            duration_ms: Duration of the activity in milliseconds.
            cognitive_load: Optional cognitive load override (low, medium, high).

        Raises:
            ValueError: If duration_ms is negative or feature is empty.
        """
        self._session_tracker.track(
            user_id, feature, duration_ms, cognitive_load
        )
        # Check if eye break is due
        self._eye_tracker.record_screen_time(user_id, duration_ms)

        logger.debug(
            "Activity tracked: user=%s feature=%s duration=%dms",
            user_id,
            feature,
            duration_ms,
        )

    def get_status(self, user_id: str) -> WellnessStatus:
        """Get current wellness status including fatigue score.

        Args:
            user_id: The user to get status for.

        Returns:
            WellnessStatus with current state information.
        """
        # Gather metrics
        screen_time_4h = self._session_tracker.get_screen_time_minutes(
            user_id, window_minutes=Constants.ROLLING_WINDOW_LONG
        )
        screen_time_today = self._session_tracker.get_screen_time_minutes(
            user_id, window_minutes=1440
        )
        current_session = self._session_tracker.get_current_session_minutes(
            user_id
        )
        last_break = self._session_tracker.get_last_break_minutes_ago(user_id)
        avg_cognitive_load = (
            self._session_tracker.get_average_cognitive_load(user_id)
        )
        interaction_freq = (
            self._session_tracker.get_interaction_frequency(user_id)
        )
        eye_compliance = self._eye_tracker.get_compliance_rate(user_id)

        # Calculate fatigue score
        fatigue_score = self._fatigue_calculator.calculate(
            screen_time_minutes=screen_time_4h,
            avg_cognitive_load=avg_cognitive_load,
            current_session_minutes=current_session,
            last_break_minutes_ago=last_break,
            interaction_frequency=interaction_freq,
        )

        # Record for trend analysis
        self._usage_analytics.record_fatigue_score(user_id, fatigue_score)

        # Determine fatigue level and messages
        fatigue_level = self._fatigue_calculator.interpret_score(fatigue_score)
        message = self._fatigue_calculator.get_status_message(fatigue_score)

        # Determine break urgency
        break_suggested = fatigue_score >= Constants.FATIGUE_FRESH
        if fatigue_score >= Constants.FATIGUE_HIGH:
            break_urgency = 3
        elif fatigue_score >= Constants.FATIGUE_MODERATE:
            break_urgency = 2
        elif fatigue_score >= Constants.FATIGUE_FRESH:
            break_urgency = 1
        else:
            break_urgency = 0

        # Estimate next break
        if fatigue_score >= Constants.FATIGUE_HIGH:
            next_break_estimate = 0
        elif fatigue_score >= Constants.FATIGUE_MODERATE:
            next_break_estimate = max(
                0, Constants.MICRO_BREAK_INTERVAL - (current_session % Constants.MICRO_BREAK_INTERVAL)
           )
        else:
            next_break_estimate = max(
                0, Constants.SHORT_BREAK_INTERVAL - current_session
            )

        # Check wind-down and focus
        wind_down = self._wind_down_manager.is_active(user_id)
        focus_active = self._focus_manager.is_focus_active(user_id)

        return WellnessStatus(
            fatigue_score=fatigue_score,
            fatigue_level=fatigue_level,
            screen_time_minutes=screen_time_today,
            current_session_minutes=current_session,
            last_break_minutes_ago=last_break,
            eye_strain_compliance=round(eye_compliance, 2),
            break_suggested=break_suggested,
            break_urgency=break_urgency,
            message=message,
            next_break_estimate_minutes=next_break_estimate,
            wind_down_active=wind_down,
            focus_mode_active=focus_active,
        )

    def get_break_suggestion(self, user_id: str) -> BreakSuggestion:
        """Get personalized break suggestion.

        Args:
            user_id: The user to get a suggestion for.

        Returns:
            BreakSuggestion tailored to the user's current state.
        """
        status = self.get_status(user_id)
        suggestion = self._break_engine.get_suggestion(
            fatigue_score=status.fatigue_score,
            current_session_minutes=status.current_session_minutes,
            last_break_minutes_ago=status.last_break_minutes_ago,
            wind_down_active=status.wind_down_active,
        )
        self._session_tracker.record_break_suggested(user_id)
        return suggestion

    def record_break_taken(self, user_id: str) -> None:
        """Record that a user took a break.

        Args:
            user_id: The user who took a break.
        """
        self._session_tracker.record_break_taken(user_id)

    def get_wellness_tip(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> WellnessTip:
        """Get a contextual wellness tip.

        Args:
            user_id: The user to get a tip for.
            category: Optional preferred tip category.

        Returns:
            A contextually selected WellnessTip.
        """
        status = self.get_status(user_id)
        return self._tips_engine.get_tip(
            user_id=user_id,
            fatigue_score=status.fatigue_score,
            category=category,
        )

    def get_usage_report(
        self, user_id: str, period: str = "today"
    ) -> UsageReport:
        """Get usage analytics for a time period.

        Args:
            user_id: The user to get the report for.
            period: Report period (today, weekly, monthly).

        Returns:
            UsageReport with analytics and insights.
        """
        return self._usage_analytics.generate_report(user_id, period)

    def set_goals(self, user_id: str, goals: ScreenTimeGoals) -> None:
        """Set screen time goals.

        Args:
            user_id: The user t
# ___END_OF_FILE___