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

        Return
# ___END_OF_FILE___