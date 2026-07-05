#!/usr/bin/env python3
"""
Prometheus Prime — Deployment Manager

Handles safe deployment of code changes with canary, blue-green, and
immediate strategies.  Every deployment creates a backup, runs health
checks, and supports instant rollback.
"""

from __future__ import annotations

__all__ = [
    "DeploymentManager",
    "DeploymentStatus",
    "DeploymentRecord",
]

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("prometheus_prime.deployment")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEPLOY_DIR = Path(".prometheus_prime/deployments").resolve()
DEPLOY_LOG = DEPLOY_DIR / "deployments.jsonl"

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CANARY = "canary"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentRecord:
    """Immutable record of a single deployment attempt."""

    deploy_id: str
    strategy: Literal["immediate", "canary", "blue_green"]
    status: DeploymentStatus
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    files_deployed: list[str] = field(default_factory=list)
    backup_paths: dict[str, str] = field(default_factory=dict)
    health_checks: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ---------------------------------------------------------------------------
# DeploymentManager
# ---------------------------------------------------------------------------


class DeploymentManager:
    """Safe deployment with canary, blue-green, and immediate strategies.

    Usage::

        dm = DeploymentManager(project_root="/app/luqi")
        record = dm.deploy(files, strategy="canary")
        if record.status == DeploymentStatus.CANARY:
            time.sleep(300)  # monitor
            dm.promote(record.deploy_id)
    """

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.deploy_dir = Path(DEPLOY_DIR)
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._ensure_git_setup()

    # ------------------------------------------------------------------
    # 1. Deploy
    # ------------------------------------------------------------------

    def deploy(
        self,
        files: dict[str, str],
        strategy: Literal["immediate", "canary", "blue_green"] = "canary",
        rollout_percent: int = 10,
        health_check_url: str | None = None,
    ) -> DeploymentRecord:
        """Deploy *files* using the specified *strategy*.

        Parameters
        ----------
        files:
            Mapping ``{relative_path: source_code}``.
        strategy:
            ``immediate`` — write all files at once.
            ``canary`` — deploy to *rollout_percent* of traffic.
            ``blue_green`` — deploy to a parallel environment then swap.
        rollout_percent:
            Used only with ``canary`` strategy (1–100).
        health_check_url:
            Optional URL to ping after deployment for a health check.

        Returns
        -------
        DeploymentRecord
            Full record of the deployment attempt.
        """
        deploy_id = self._generate_deploy_id()
        record = DeploymentRecord(
            deploy_id=deploy_id,
            strategy=strategy,
            status=DeploymentStatus.IN_PROGRESS,
        )

        logger.info("Deployment %s starting — strategy=%s, files=%d",
                    deploy_id, strategy, len(files))

        try:
            if strategy == "immediate":
                self._deploy_immediate(files, record)
            elif strategy == "canary":
                self._deploy_canary(files, record, rollout_percent)
            elif strategy == "blue_green":
                self._deploy_blue_green(files, record)

            # Health check
            if health_check_url:
                self._health_check(health_check_url, record)

            record.status = DeploymentStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as exc:
            logger.exception("Deployment %s failed", deploy_id)
            record.status = DeploymentStatus.FAILED
            record.error_message = str(exc)
            self._rollback_files(record.backup_paths)

        self._persist_record(record)
        return record

    # ------------------------------------------------------------------
    # 2. Immediate deploy
    # ------------------------------------------------------------------

    def _deploy_immediate(
        self,
        files: dict[str, str],
        record: DeploymentRecord,
    ) -> None:
        """Deploy all files immediately with full backups."""
        for rel_path, source in files.items():
            abs_path = self.project_root / rel_path

            # Validate no path traversal
            try:
                abs_path.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                raise ValueError(f"Path traversal blocked: {{rel_path}}")

            # Backup
            if abs_path.exists():
                backup = self.deploy_dir / f"{{abs_path.name}}.{{record.deploy_id}}.bak"
                shutil.copy2(abs_path, backup)
                record.backup_paths[str(abs_path)] = str(backup)

            # Atomic write
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = abs_path.with_suffix(".tmp")
            tmp.write_text(source, encoding="utf-8")
            tmp.replace(abs_path)
            record.files_deployed.append(str(abs_path))

        logger.info("Immediate deploy %s — %d files written", record.deploy_id, len(files))

    # ------------------------------------------------------------------
    # 3. Canary deploy
    # ------------------------------------------------------------------

    def _deploy_canary(
        self,
        files: dict[str, str],
        record: DeploymentRecord,
        rollout_percent: int,
    ) -> None:
        """Deploy to a fraction of the codebase (simulated via feature-flag).

        In a real system this would update a feature-flag service (e.g.,
        LaunchDarkly, Unleash) to route *rollout_percent* of traffic to
        the new code.  Here we write files to a canary sub-directory and
        create a feature-flag manifest.
        """
        canary_dir = self.deploy_dir / "canary" / record.deploy_id
        canary_dir.mkdir(parents=True, exist_ok=True)

        # Write files to canary directory
        for rel_path, source in files.items():
            canary_file = canary_dir / rel_path.replace("/", "_")
            canary_file.write_text(source, encoding="utf-8")
            record.files_deployed.append(str(canary_file))

        # Create feature-flag manifest
        manifest = {
            "deploy_id": record.deploy_id,
            "rollout_percent": rollout_percent,
            "canary_dir": str(canary_dir),
            "files": list(files.keys()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (canary_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Back up originals
        for rel_path in files:
            abs_path = self.project_root / rel_path
            if abs_path.exists():
                backup = self.deploy_dir / f"{{abs_path.name}}.{{record.deploy_id}}.bak"
                shutil.copy2(abs_path, backup)
                record.backup_paths[str(abs_path)] = str(backup)

        record.status = DeploymentStatus.CANARY
        logger.info("Canary deploy %s — %d%% rollout, files in %s",
                    record.deploy_id, rollout_percent, canary_dir)

    # ------------------------------------------------------------------
    # 4. Blue-green deploy
    # ------------------------------------------------------------------

    def _deploy_blue_green(
        self,
        files: dict[str, str],
        record: DeploymentRecord,
    ) -> None:
        """Deploy to a parallel 'green' environment, leaving 'blue' running.

        The green environment is created under ``.prometheus_prime/deployments/green/``.
        After health checks pass, a ``swap`` command promotes green to live.
        """
        green_dir = self.deploy_dir / "green" / record.deploy_id
        green_dir.mkdir(parents=True, exist_ok=True)

        # Copy current project to green
        if self.project_root.exists():
            for item in self.project_root.rglob("*"):
                if item.is_file() and ".prometheus_prime" not in str(item):
                    rel = item.relative_to(self.project_root)
                    dest = green_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

        # Overlay new files on green
        for rel_path, source in files.items():
            dest = green_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source, encoding="utf-8")
            record.files_deployed.append(str(dest))

        # Create swap manifest
        manifest = {
            "deploy_id": record.deploy_id,
            "green_dir": str(green_dir),
            "blue_dir": str(self.project_root),
            "files": list(files.keys()),
            "status": "green_ready",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (green_dir / "swap_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        record.status = DeploymentStatus.MONITORING
        logger.info("Blue-green deploy %s — green environment ready at %s", record.deploy_id, green_dir)

    # ------------------------------------------------------------------
    # 5. Promote / rollback
    # ------------------------------------------------------------------

    def promote(self, deploy_id: str) -> DeploymentRecord | None:
        """Promote a canary or blue-green deployment to full rollout.

        For canary: copies canary files to the live project.
        For blue-green: swaps the green environment to live.

        Returns the updated record or ``None`` if not found.
        """
        record = self._load_record(deploy_id)
        if record is None:
            return None

        if record.strategy == "canary":
            return self._promote_canary(record)
        elif record.strategy == "blue_green":
            return self._promote_blue_green(record)

        # Immediate is already live
        record.status = DeploymentStatus.COMPLETED
        self._persist_record(record)
        return record

    def _promote_canary(self, record: DeploymentRecord) -> DeploymentRecord:
        canary_dir = self.deploy_dir / "canary" / record.deploy_id
        manifest_path = canary_dir / "manifest.json"
        if not manifest_path.exists():
            record.status = DeploymentStatus.FAILED
            record.error_message = "Canary manifest not found"
            self._persist_record(record)
            return record

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Copy canary files to live
        for rel_path in manifest.get("files", []):
            canary_file = canary_dir / rel_path.replace("/", "_")
            live_path = self.project_root / rel_path
            if canary_file.exists():
                live_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = live_path.with_suffix(".tmp")
                shutil.copy2(canary_file, tmp)
                tmp.replace(live_path)

        record.status = DeploymentStatus.COMPLETED
        record.completed_at = datetime.now(timezone.utc).isoformat()
        self._persist_record(record)
        logger.info("Canary %s promoted to full rollout", record.deploy_id)
        return record

    def _promote_blue_green(self, record: DeploymentRecord) -> DeploymentRecord:
        green_dir = self.deploy_dir / "green" / record.deploy_id
        manifest_path = green_dir / "swap_manifest.json"
        if not manifest_path.exists():
            record.status = DeploymentStatus.FAILED
            record.error_message = "Swap manifest not found"
            self._persist_record(record)
            return record

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Swap: green becomes blue
        swap_marker = self.deploy_dir / "active_deployment.txt"
        swap_marker.write_text(str(green_dir), encoding="utf-8")

        manifest["status"] = "swapped"
        (green_dir / "swap_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        record.status = DeploymentStatus.COMPLETED
        record.completed_at = datetime.now(timezone.utc).isoformat()
        self._persist_record(record)
        logger.info("Blue-green %s swapped — green is now live", record.deploy_id)
        return record

    def rollback(self, deploy_id: str) -> DeploymentRecord | None:
        """Instant rollback to pre-deployment state.

        Restores all files from their backups and marks the deployment as
        ``ROLLED_BACK``.

        Returns the updated record or ``None`` if not found.
        """
        record = self._load_record(deploy_id)
        if record is None:
            return None

        logger.info("Rolling back deployment %s ...", deploy_id)
        self._rollback_files(record.backup_paths)

        record.status = DeploymentStatus.ROLLED_BACK
        record.completed_at = datetime.now(timezone.utc).isoformat()
        self._persist_record(record)
        logger.info("Deployment %s rolled back successfully", deploy_id)
        return record

    @staticmethod
    def _rollback_files(backup_paths: dict[str, str]) -> None:
        """Restore files from their backups."""
        for live_path_str, backup_path_str in backup_paths.items():
            backup = Path(backup_path_str)
            live = Path(live_path_str)
            if backup.exists():
                live.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, live)
                logger.debug("Restored %s from %s", live, backup)

    # ------------------------------------------------------------------
    # 6. Health checks
    # ------------------------------------------------------------------

    def _health_check(self, url: str, record: DeploymentRecord) -> None:
        """Ping *url* and record the result."""
        import urllib.request

        check: dict[str, Any] = {"url": url, "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                check["status_code"] = resp.status
                check["passed"] = resp.status < 400
        except Exception as exc:
            check["passed"] = False
            check["error"] = str(exc)

        record.health_checks.append(check)
        logger.info("Health check %s — passed=%s", url, check.get("passed"))

    # ------------------------------------------------------------------
    # 7. History & queries
    # ------------------------------------------------------------------

    def get_deployment_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent deployment records."""
        if not DEPLOY_LOG.exists():
            return []

        records: list[dict[str, Any]] = []
        with open(DEPLOY_LOG, "r", encoding="utf-8") as fh:
            for line in reversed(fh.readlines()):
                if line.strip():
                    records.append(json.loads(line))
                if len(records) >= limit:
                    break
        return records

    def get_deployment(self, deploy_id: str) -> dict[str, Any] | None:
        """Return a single deployment record by ID."""
        if not DEPLOY_LOG.exists():
            return None
        with open(DEPLOY_LOG, "r", encoding="utf-8") as fh:
            for line in fh:
                record = json.loads(line)
                if record.get("deploy_id") == deploy_id:
                    return record
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_deploy_id() -> str:
        return f"d-{{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}}-{{uuid.uuid4().hex[:8]}}"

    def _persist_record(self, record: DeploymentRecord) -> None:
        DEPLOY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEPLOY_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), default=str) + "\\n")

    def _load_record(self, deploy_id: str) -> DeploymentRecord | None:
        data = self.get_deployment(deploy_id)
        if data is None:
            return None
        return DeploymentRecord(
            deploy_id=data["deploy_id"],
            strategy=data["strategy"],
            status=DeploymentStatus(data.get("status", "pending")),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            files_deployed=data.get("files_deployed", []),
            backup_paths=data.get("backup_paths", {}),
            health_checks=data.get("health_checks", []),
            error_message=data.get("error_message", ""),
        )

    def _ensure_git_setup(self) -> None:
        """Ensure the project root has a Git repo for tracking deployments."""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=self.project_root,
                    capture_output=True,
                    check=True,
                )
                logger.info("Git repo initialised at %s", self.project_root)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.debug("Git not available; skipping git setup")
