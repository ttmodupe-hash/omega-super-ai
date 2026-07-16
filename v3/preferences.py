"""User Preferences Persistence for Luqi-AI.

Stores user settings in ~/.omega_ai/preferences.json with thread-safe
file locking, atomic writes, and type validation.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "default_country": "South Africa",
    "risk_tolerance": "moderate",
    "preferred_language": "en",
    "currency": "ZAR",
    "power_cost_per_kwh": 0.15,
    "max_history": 6,
}

_PREFERENCE_TYPES: Dict[str, tuple] = {
    "default_country": (str,),
    "risk_tolerance": (str,),
    "preferred_language": (str,),
    "currency": (str,),
    "power_cost_per_kwh": (int, float),
    "max_history": (int,),
}


def _get_preferences_dir() -> Path:
    return Path.home() / ".omega_ai"


def _get_preferences_path() -> Path:
    return _get_preferences_dir() / "preferences.json"


class UserPreferences:
    """Thread-safe user preferences manager with persistent JSON storage."""

    _lock = threading.Lock()

    def __init__(self) -> None:
        self._prefs: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        prefs_path = _get_preferences_path()
        if not prefs_path.exists():
            logger.debug("Preferences file not found; creating defaults.")
            self._prefs = dict(DEFAULT_PREFERENCES)
            self.save()
            return
        try:
            with prefs_path.open("r", encoding="utf-8") as fh:
                try:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
                except ImportError:
                    pass
                data = json.load(fh)
                try:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except ImportError:
                    pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read preferences (%s); using defaults.", exc)
            self._prefs = dict(DEFAULT_PREFERENCES)
            self.save()
            return

        merged = dict(DEFAULT_PREFERENCES)
        if isinstance(data, dict):
            for key, value in data.items():
                if key in _PREFERENCE_TYPES:
                    expected = _PREFERENCE_TYPES[key]
                    if isinstance(value, expected):
                        merged[key] = value
                    else:
                        logger.warning("Preference '%s' has wrong type; using default.", key)
                else:
                    merged[key] = value
        self._prefs = merged
        self.save()

    def save(self) -> None:
        with self._lock:
            prefs_dir = _get_preferences_dir()
            prefs_dir.mkdir(parents=True, exist_ok=True)
            prefs_path = _get_preferences_path()
            tmp_path = prefs_path.with_suffix(".tmp")
            try:
                with tmp_path.open("w", encoding="utf-8") as fh:
                    try:
                        import fcntl
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                    except ImportError:
                        pass
                    json.dump(self._prefs, fh, indent=2, ensure_ascii=False)
                    fh.flush()
                    os.fsync(fh.fileno())
                    try:
                        import fcntl
                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                    except ImportError:
                        pass
                os.replace(str(tmp_path), str(prefs_path))
            except OSError as exc:
                logger.error("Failed to save preferences: %s", exc)
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise

    def get(self, key: str, default: Any = None) -> Any:
        return self._prefs.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in _PREFERENCE_TYPES:
                expected = _PREFERENCE_TYPES[key]
                if not isinstance(value, expected):
                    if expected == (int, float) and isinstance(value, (int, float)):
                        pass
                    elif expected == (int,) and isinstance(value, float) and value.is_integer():
                        value = int(value)
                    else:
                        raise TypeError(
                            f"Preference '{key}' expects "
                            f"{' or '.join(t.__name__ for t in expected)}, "
                            f"got {type(value).__name__}"
                        )
            self._prefs[key] = value
            self.save()

    def reset(self) -> None:
        with self._lock:
            self._prefs = dict(DEFAULT_PREFERENCES)
            self.save()

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._prefs)