#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — Dead Man's Switch
====================================
Process watchdog with automatic rollback.

Features:
  - Watches main process via PID
  - Automatic rollback on crash within prove-alive window
  - Keeps last 5 known-good versions as backups (circular buffer)
  - Restart after rollback via subprocess
  - Sends CRITICAL alert on rollback via AlertSystem

Architecture:
    The DeadMansSwitch is a singleton that runs a background watchdog
    thread. After a code swap, the orchestrator must call prove_alive()
    within ``PROVE_ALIVE_WINDOW_SECONDS`` (default 10). If the watched
    PID dies before that window expires, the switch considers the update
    bad and rolls back to the last known-good backup.

Backup Strategy:
    Backups are stored in ``./backups/luqi-ai-backup-N/`` where N is
    1-5 in a circular fashion. Each backup is a recursive copy of the
    ``backend/`` directory (excluding the backups/ dir itself and any
    __pycache__ / .git artefacts).

Critical Invariants:
    - This module NEVER modifies its own source file.
    - This module has NO external runtime dependencies beyond stdlib.
    - It imports AlertSystem optionally; rollback works even if that
      import fails.

Environment Variables:
    BACKUP_DIR: Root directory for backups (default: ./backups)
    BACKEND_DIR: Directory to back up / restore (default: ./backend)
    PROVE_ALIVE_WINDOW_SECONDS: Seconds to wait for prove_alive
                                (default: 10)
    RESTART_COMMAND: Shell command to restart the service
                     (default: "python -m backend.main")

Usage:
    >>> from dead_mans_switch import DeadMansSwitch, start_watchdog
    >>> dms = DeadMansSwitch()
    >>> dms.create_backup("v24.4.1")
    >>> dms.watch_process(os.getpid())
    >>> # After successful code swap:
    >>> dms.prove_alive()
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.dead_mans_switch")

# ---------------------------------------------------------------------------
# Optional AlertSystem import — if it fails, we log to stderr only.
# ---------------------------------------------------------------------------
try:
    from alert_system import AlertSystem, AlertSeverity  # type: ignore[import]

    _HAS_ALERT_SYSTEM = True
except Exception:
    _HAS_ALERT_SYSTEM = False
    logger.warning(
        "AlertSystem not available — rollback alerts will be stderr-only"
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_BACKUPS: int = 5
DEFAULT_PROVE_ALIVE_WINDOW: int = 10  # seconds
DEFAULT_RESTART_COMMAND: str = "python -m backend.main"


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------
class WatchdogState(str, Enum):
    """Lifecycle states of the watchdog."""

    IDLE = "IDLE"
    WATCHING = "WATCHING"
    WAITING_FOR_PROOF = "WAITING_FOR_PROOF"
    ROLLING_BACK = "ROLLING_BACK"
    SHUTDOWN = "SHUTDOWN"


# ---------------------------------------------------------------------------
# DeadMansSwitch (Singleton)
# ---------------------------------------------------------------------------
class DeadMansSwitch:
    """Process watchdog with automatic rollback to last known-good backup.

    The switch maintains a circular buffer of up to ``MAX_BACKUPS``
    numbered snapshots of the backend directory. After a code update,
    the orchestrator calls :meth:`prove_alive` to confirm the new code
    is stable. If the watched PID dies before proof is received, the
    switch automatically restores the most recent backup and restarts.

    This class is a singleton so that multiple callers (e.g. the main
    orchestrator and the HTTP health handler) share the same state.

    Example::

        >>> dms = DeadMansSwitch()
        >>> dms.create_backup("v24.4.1-before-swap")
        >>> dms.watch_process(os.getpid())
        >>> # ... code swap happens ...
        >>> dms.prove_alive()   # must be called within 10s
    """

    _instance: Optional["DeadMansSwitch"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "DeadMansSwitch":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Directories
        self._backup_dir: Path = Path(
            os.environ.get("BACKUP_DIR", "./backups")
        ).resolve()
        self._backend_dir: Path = Path(
            os.environ.get("BACKEND_DIR", "./backend")
        ).resolve()
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        # Prove-alive configuration
        self._prove_alive_window: int = int(
            os.environ.get(
                "PROVE_ALIVE_WINDOW_SECONDS",
                str(DEFAULT_PROVE_ALIVE_WINDOW),
            )
        )
        self._restart_command: str = os.environ.get(
            "RESTART_COMMAND", DEFAULT_RESTART_COMMAND
        )

        # State
        self._state: WatchdogState = WatchdogState.IDLE
        self._state_lock: threading.Lock = threading.Lock()
        self._proof_received: threading.Event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._shutdown_event: threading.Event = threading.Event()

        # PID under watch
        self._watched_pid: Optional[int] = None

        # Metadata persisted alongside backups
        self._metadata_path: Path = self._backup_dir / "backup-metadata.json"
        self._metadata: Dict[str, Any] = self._load_metadata()

        self._initialized = True
        logger.info(
            "DeadMansSwitch initialised — backup_dir=%s backend_dir=%s window=%ds",
            self._backup_dir,
            self._backend_dir,
            self._prove_alive_window,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_backup(self, version_label: str = "") -> Path:
        """Create a numbered backup of the backend directory.

        Backups are stored in a circular fashion:
        ``backups/luqi-ai-backup-1/`` … ``backups/luqi-ai-backup-5/``.
        The oldest backup is overwritten when the buffer wraps around.

        Args:
            version_label: Optional human-readable label (e.g. ``"v24.4.1"``).

        Returns:
            Path to the newly created backup directory.
        """
        slot = self._next_backup_slot()
        backup_path = self._backup_dir / f"luqi-ai-backup-{slot}"

        # Remove previous content in this slot
        if backup_path.exists():
            shutil.rmtree(backup_path, ignore_errors=True)

        # Copy backend directory, excluding sensitive paths
        self._copy_tree(self._backend_dir, backup_path)

        # Write slot metadata
        meta_entry = {
            "slot": slot,
            "version_label": version_label,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "backend_dir": str(self._backend_dir),
            "backup_path": str(backup_path),
        }
        self._metadata[f"slot_{slot}"] = meta_entry
        self._save_metadata()

        logger.info(
            "Backup created in slot %d at %s (label=%s)",
            slot,
            backup_path,
            version_label,
        )
        return backup_path

    def prove_alive(self) -> None:
        """Signal that the current code version is healthy.

        Must be called within ``PROVE_ALIVE_WINDOW_SECONDS`` after a
        code swap. Sets an internal event that stops the rollback timer.
        """
        with self._state_lock:
            if self._state == WatchdogState.WAITING_FOR_PROOF:
                self._proof_received.set()
                self._state = WatchdogState.WATCHING
                logger.info("prove_alive received — rollback cancelled")
            else:
                logger.debug(
                    "prove_alive called but state is %s (ignored)",
                    self._state.value,
                )

    def watch_process(self, pid: int) -> None:
        """Start the background watchdog thread monitoring *pid*.

        The thread polls the process every 2 seconds. If the process
        disappears while the switch is ``WAITING_FOR_PROOF``, a
        rollback is triggered automatically.

        Args:
            pid: Process ID to watch.
        """
        with self._state_lock:
            if self._state == WatchdogState.SHUTDOWN:
                logger.warning("Watchdog is shutdown — refusing to watch PID %d", pid)
                return

            self._watched_pid = pid
            self._state = WatchdogState.WATCHING

        if (
            self._watchdog_thread is not None
            and self._watchdog_thread.is_alive()
        ):
            logger.info("Watchdog thread already running")
            return

        self._shutdown_event.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="DeadMansSwitch-Watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()
        logger.info("Watchdog started for PID %d", pid)

    def rollback(self) -> bool:
        """Restore the last known-good backup and restart the service.

        This method is thread-safe and idempotent — if a rollback is
        already in progress it returns immediately.

        Returns:
            ``True`` if rollback succeeded, ``False`` otherwise.
        """
        with self._state_lock:
            if self._state == WatchdogState.ROLLING_BACK:
                logger.warning("Rollback already in progress")
                return False
            self._state = WatchdogState.ROLLING_BACK

        logger.critical("ROLLBACK INITIATED — restoring last known-good backup")

        last_backup = self._get_last_backup_path()
        if last_backup is None:
            logger.error("No backup available for rollback — aborting")
            with self._state_lock:
                self._state = WatchdogState.WATCHING
            return False

        try:
            # 1. Stop watching so we don't trigger another rollback
            self._shutdown_event.set()

            # 2. Replace backend directory with backup content
            self._restore_backup(last_backup)

            # 3. Send CRITICAL alert
            self._send_rollback_alert(last_backup)

            # 4. Restart the service
            self._restart_service()

            logger.critical("Rollback completed successfully from %s", last_backup)
            return True

        except Exception as exc:
            logger.critical(
                "Rollback failed: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            with self._state_lock:
                self._state = WatchdogState.WATCHING
            return False

    def get_backups(self) -> List[Dict[str, Any]]:
        """List available backups with metadata.

        Returns:
            List of backup metadata dictionaries, most recent first.
        """
        backups: List[Dict[str, Any]] = []
        for slot in range(1, MAX_BACKUPS + 1):
            meta = self._metadata.get(f"slot_{slot}")
            backup_path = self._backup_dir / f"luqi-ai-backup-{slot}"
            if meta and backup_path.exists():
                backups.append(
                    {
                        "slot": slot,
                        "path": str(backup_path),
                        "version_label": meta.get("version_label", ""),
                        "created_at": meta.get("created_at", ""),
                        "exists": True,
                    }
                )
            elif backup_path.exists():
                # Fallback if metadata missing but directory exists
                backups.append(
                    {
                        "slot": slot,
                        "path": str(backup_path),
                        "version_label": "unknown",
                        "created_at": "",
                        "exists": True,
                    }
                )
        # Sort by slot descending (higher slot = more recent in circular buffer)
        backups.sort(key=lambda b: b["slot"], reverse=True)
        return backups

    def is_rollback_available(self) -> bool:
        """Return ``True`` if at least one backup exists for rollback."""
        return self._get_last_backup_path() is not None

    def cleanup_old_backups(self, keep: int = MAX_BACKUPS) -> int:
        """Remove old backups, keeping only the most recent *keep*.

        Args:
            keep: Number of backups to retain (default 5).

        Returns:
            Number of backups removed.
        """
        backups = self.get_backups()
        to_remove = backups[keep:]
        removed = 0
        for entry in to_remove:
            path = Path(entry["path"])
            try:
                shutil.rmtree(path, ignore_errors=True)
                # Clean metadata
                self._metadata.pop(f"slot_{entry['slot']}", None)
                removed += 1
                logger.info("Cleaned old backup: %s", path)
            except Exception as exc:
                logger.error("Failed to remove backup %s: %s", path, exc)
        self._save_metadata()
        return removed

    # ------------------------------------------------------------------
    # Internal: Watchdog loop
    # ------------------------------------------------------------------

    def _watchdog_loop(self) -> None:
        """Background thread that polls the watched PID.

        The loop runs until shutdown_event is set or the thread is
        joined. It transitions through states:

            WATCHING → WAITING_FOR_PROOF (on code swap hint)
            WAITING_FOR_PROOF → ROLLING_BACK (if PID dies before proof)
            WAITING_FOR_PROOF → WATCHING (if prove_alive received)
        """
        logger.debug("Watchdog loop started")
        poll_interval: float = 2.0

        while not self._shutdown_event.is_set():
            time.sleep(poll_interval)

            with self._state_lock:
                state = self._state
                pid = self._watched_pid

            if state == WatchdogState.SHUTDOWN:
                break

            if pid is None:
                continue

            # Check if process is still alive
            if not self._is_process_alive(pid):
                logger.critical(
                    "Watched PID %d has died (state=%s)",
                    pid,
                    state.value,
                )
                if state == WatchdogState.WAITING_FOR_PROOF:
                    # Code swap failed — rollback!
                    logger.critical(
                        "Process died during prove-alive window — triggering rollback"
                    )
                    self.rollback()
                    break
                else:
                    # Process died outside of code-swap window — just log
                    logger.error(
                        "Watched PID %d died outside prove-alive window", pid
                    )
                    with self._state_lock:
                        self._state = WatchdogState.IDLE
                    break

        logger.debug("Watchdog loop exited")

    # ------------------------------------------------------------------
    # Internal: Process health check
    # ------------------------------------------------------------------

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Return ``True`` if *pid* is currently running.

        Uses ``os.kill(pid, 0)`` which raises OSError if the process
        does not exist. This is POSIX-compatible.

        Args:
            pid: Process ID to check.
        """
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    # ------------------------------------------------------------------
    # Internal: Backup / restore helpers
    # ------------------------------------------------------------------

    def _next_backup_slot(self) -> int:
        """Determine the next slot number in the circular buffer.

        Returns:
            Integer 1-5 representing the next backup slot.
        """
        existing = self.get_backups()
        if not existing:
            return 1
        # Find highest slot, wrap around
        highest = max(b["slot"] for b in existing)
        next_slot = highest + 1
        if next_slot > MAX_BACKUPS:
            next_slot = 1
        return next_slot

    def _get_last_backup_path(self) -> Optional[Path]:
        """Return the path to the most recent backup, or ``None``."""
        backups = self.get_backups()
        if not backups:
            return None
        # Most recent = highest slot number that exists
        for entry in backups:
            path = Path(entry["path"])
            if path.exists():
                return path
        return None

    def _copy_tree(self, src: Path, dst: Path) -> None:
        """Recursively copy *src* directory to *dst*, excluding artefacts.

        Excludes:
            - ``backups/`` directory (prevents recursive backup loops)
            - ``__pycache__`` directories
            - ``.git`` directories
            - ``*.pyc`` files

        Args:
            src: Source directory.
            dst: Destination directory.
        """
        EXCLUDE_DIRS = {"backups", "__pycache__", ".git", ".pytest_cache", ".mypy_cache"}
        EXCLUDE_SUFFIXES = {".pyc", ".pyo"}

        dst.mkdir(parents=True, exist_ok=True)

        for item in src.rglob("*"):
            # Skip excluded directories
            if any(part in EXCLUDE_DIRS for part in item.parts):
                continue
            if item.suffix in EXCLUDE_SUFFIXES:
                continue

            rel_path = item.relative_to(src)
            dst_path = dst / rel_path

            if item.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst_path)

    def _restore_backup(self, backup_path: Path) -> None:
        """Replace the backend directory with the contents of *backup_path*.

        This operation is done atomically where possible:
        1. Rename current backend to backend.bak
        2. Copy backup to backend/
        3. Remove backend.bak on success, restore it on failure

        Args:
            backup_path: Path to the backup directory to restore from.
        """
        backend_bak = self._backend_dir.parent / "backend.bak"

        # Remove stale backup temp
        if backend_bak.exists():
            shutil.rmtree(backend_bak, ignore_errors=True)

        try:
            # Step 1: rename current backend out of the way
            self._backend_dir.rename(backend_bak)
            logger.info("Renamed current backend to %s", backend_bak)

            # Step 2: copy backup into place
            self._copy_tree(backup_path, self._backend_dir)
            logger.info("Restored backend from %s", backup_path)

            # Step 3: clean up backup temp on success
            shutil.rmtree(backend_bak, ignore_errors=True)

        except Exception:
            # Attempt to restore original backend on failure
            logger.critical(
                "Restore failed — attempting to recover original backend\n%s",
                traceback.format_exc(),
            )
            if backend_bak.exists():
                if self._backend_dir.exists():
                    shutil.rmtree(self._backend_dir, ignore_errors=True)
                backend_bak.rename(self._backend_dir)
            raise

    # ------------------------------------------------------------------
    # Internal: Restart
    # ------------------------------------------------------------------

    def _restart_service(self) -> None:
        """Restart the Luqi AI service via subprocess.

        Uses ``subprocess.Popen`` to spawn a new process and then
        exits the current one so the new process can take over.
        """
        logger.critical(
            "Restarting service with command: %s", self._restart_command
        )
        try:
            # Detached process so it survives our exit
            subprocess.Popen(
                self._restart_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            logger.info("Restart subprocess launched — exiting current process")
            # Give the new process a moment to start
            time.sleep(1)
            sys.exit(0)
        except Exception as exc:
            logger.critical("Failed to restart service: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Internal: Alert on rollback
    # ------------------------------------------------------------------

    def _send_rollback_alert(self, backup_path: Path) -> None:
        """Send a CRITICAL alert that a rollback has occurred.

        Uses AlertSystem if available, otherwise logs to stderr.

        Args:
            backup_path: The backup that was restored.
        """
        message = (
            f"Automatic rollback executed.\n"
            f"Restored from: {backup_path}\n"
            f"Backend dir: {self._backend_dir}\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}"
        )

        if _HAS_ALERT_SYSTEM:
            try:
                alert_sys = AlertSystem()
                alert_sys.trigger_critical_alert(
                    agent_name="DeadMansSwitch",
                    error_payload={
                        "event": "ROLLBACK_EXECUTED",
                        "backup_path": str(backup_path),
                        "backend_dir": str(self._backend_dir),
                    },
                    details=message,
                )
            except Exception as exc:
                logger.error("Failed to send rollback alert: %s", exc)
        else:
            logger.critical("ROLLBACK ALERT (no AlertSystem): %s", message)

    # ------------------------------------------------------------------
    # Internal: Metadata persistence
    # ------------------------------------------------------------------

    def _load_metadata(self) -> Dict[str, Any]:
        """Load backup metadata from JSON file.

        Returns:
            Metadata dictionary, or empty dict if file doesn't exist.
        """
        if self._metadata_path.exists():
            try:
                with open(self._metadata_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load backup metadata: %s", exc)
        return {}

    def _save_metadata(self) -> None:
        """Persist backup metadata to JSON file (best-effort)."""
        try:
            with open(self._metadata_path, "w", encoding="utf-8") as fh:
                json.dump(self._metadata, fh, indent=2, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
        except Exception as exc:
            logger.error("Failed to save backup metadata: %s", exc)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Gracefully stop the watchdog thread and clean up."""
        with self._state_lock:
            self._state = WatchdogState.SHUTDOWN
        self._shutdown_event.set()
        self._proof_received.set()  # Unblock any waiting threads
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=5.0)
        logger.info("DeadMansSwitch shutdown complete")


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def start_watchdog(pid: Optional[int] = None) -> DeadMansSwitch:
    """Create and start the DeadMansSwitch watchdog.

    Args:
        pid: Process ID to watch. Defaults to the parent process ID.

    Returns:
        The configured and running DeadMansSwitch singleton.
    """
    if pid is None:
        pid = os.getpid()
    dms = DeadMansSwitch()
    dms.watch_process(pid)
    return dms


def create_emergency_backup(version_label: str = "emergency") -> Path:
    """Create an emergency backup immediately.

    This is a convenience wrapper for one-off backup creation without
    needing to manage the DeadMansSwitch lifecycle.

    Args:
        version_label: Label for the backup (default ``"emergency"``).

    Returns:
        Path to the created backup directory.
    """
    dms = DeadMansSwitch()
    return dms.create_backup(version_label)
