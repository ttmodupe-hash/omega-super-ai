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

    The BreakEngine anal
# ___END_OF_FILE___