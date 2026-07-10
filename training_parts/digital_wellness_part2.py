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

        avg_ms = statistics.mean
# ___END_OF_FILE___