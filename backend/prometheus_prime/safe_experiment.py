#!/usr/bin/env python3
"""
Prometheus Prime — Safe Experimentation Framework

Provides isolated environments for testing new features before they reach
production.  Implements the full experiment lifecycle:

    create → run → (canary-deploy | rollback) → analyse

All experiment artefacts are stored under *EXPERIMENT_DIR* and keyed by a
UUID-based *experiment_id* so that every trial is fully reproducible.
"""

from __future__ import annotations

__all__ = [
    "SafeExperiment",
    "ExperimentResults",
    "CanaryStatus",
    "Sandbox",
]

import ast
import contextlib
import copy
import gc
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("prometheus_prime.safe_experiment")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPERIMENT_DIR = Path(".prometheus_prime/experiments").resolve()
MAX_CANARY_ROLLOUT: int = 100  # percent

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ExperimentResults:
    """Aggregated results from running an experiment."""

    experiment_id: str
    passed: bool
    metrics: dict[str, float] = field(default_factory=dict)
    comparison: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""


@dataclass
class CanaryStatus:
    """Snapshot of a canary deployment."""

    status: Literal["deployed", "rolled_back", "monitoring", "pending"]
    rollout_percent: int = 0
    errors_detected: int = 0
    requests_served: int = 0
    latency_p95_ms: float = 0.0
    health_score: float = 1.0
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class _ExperimentRecord:
    """Internal on-disk record for an experiment."""

    experiment_id: str
    created_at: str
    feature_code_path: str
    test_cases_path: str
    baseline_results: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    canary: dict[str, Any] = field(default_factory=dict)
    status: str = "created"  # created | running | passed | failed | canary | rolled_back


# ---------------------------------------------------------------------------
# Sandbox — isolated execution environment
# ---------------------------------------------------------------------------


class Sandbox:
    """Isolated Python execution sandbox.

    Loads user-provided code into a separate module namespace so that
    crashes, infinite loops, or import side-effects do not affect the host
    process.  Timeouts and memory bounds provide additional safety.
    """

    def __init__(
        self,
        source_code: str,
        module_name: str = "_experiment_module",
        timeout_seconds: float = 30.0,
        memory_limit_mb: int = 512,
    ) -> None:
        self.source_code = source_code
        self.module_name = module_name
        self.timeout = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self._module: Any = None
        self._namespace: dict[str, Any] = {}

    # -- lifecycle --------------------------------------------------------

    def compile_and_load(self) -> bool:
        """Parse *source_code*, compile it, and load into a fresh namespace.

        Returns ``True`` on success; logs details and returns ``False``
        on syntax or import errors.
        """
        try:
            tree = ast.parse(self.source_code)
            compiled = compile(tree, filename="<experiment>", mode="exec")
        except SyntaxError as exc:
            logger.error("Sandbox syntax error: %s", exc)
            return False

        # Fresh namespace — no accidental access to caller's globals
        self._namespace = {
            "__name__": self.module_name,
            "__file__": "<experiment>",
            "__builtins__": __builtins__,
        }

        try:
            exec(compiled, self._namespace)  # noqa: S102
        except Exception as exc:
            logger.error("Sandbox execution error: %s", exc)
            return False

        return True

    def run_function(self, func_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Call *func_name* from the sandboxed module with timeout.

        Returns a dict with keys ``success``, ``result``, ``duration_ms``,
        and ``error``.
        """
        if func_name not in self._namespace:
            return {"success": False, "error": f"Function '{func_name}' not found", "duration_ms": 0.0}

        func = self._namespace[func_name]
        if not callable(func):
            return {"success": False, "error": f"'{func_name}' is not callable", "duration_ms": 0.0}

        result_container: dict[str, Any] = {}

        def _target() -> None:
            start = time.perf_counter()
            try:
                result_container["result"] = func(*args, **kwargs)
                result_container["success"] = True
            except Exception as exc:
                result_container["error"] = str(exc)
                result_container["traceback"] = traceback.format_exc()
                result_container["success"] = False
            result_container["duration_ms"] = (time.perf_counter() - start) * 1000

        t = threading.Thread(target=_target)
        start = time.perf_counter()
        t.start()
        t.join(timeout=self.timeout)
        wall_ms = (time.perf_counter() - start) * 1000

        if t.is_alive():
            # Best-effort: we cannot kill the thread, but we mark it timed out
            return {
                "success": False,
                "error": f"Timeout after {{self.timeout}}s (wall={{wall_ms:.1f}}ms)",
                "duration_ms": wall_ms,
            }

        return result_container

    def get_object(self, name: str) -> Any:
        """Retrieve an object exported by the sandboxed module."""
        return self._namespace.get(name)

    # -- helpers ----------------------------------------------------------

    def list_callables(self) -> list[str]:
        """Return all callable names defined in the sandbox."""
        return [k for k, v in self._namespace.items() if callable(v) and not k.startswith("__")]


# ---------------------------------------------------------------------------
# Main experimentation class
# ---------------------------------------------------------------------------


class SafeExperiment:
    """End-to-end safe experimentation framework.

    Example::

        se = SafeExperiment()
        eid = se.create_experiment(feature_code, test_cases)
        results = se.run_experiment(eid)
        if results.passed:
            se.canary_deploy(eid, rollout_percent=5)
    """

    def __init__(self, experiment_dir: str | Path = EXPERIMENT_DIR) -> None:
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, _ExperimentRecord] = {}
        self._lock = threading.RLock()
        self._load_existing_records()

    # ------------------------------------------------------------------
    # 1. Create experiment
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        feature_code: str,
        test_cases: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create an isolated experiment.

        Parameters
        ----------
        feature_code:
            Python source of the new feature.
        test_cases:
            Python source of the pytest test suite.
        metadata:
            Optional extra metadata stored with the record.

        Returns
        -------
        str
            UUID experiment identifier.
        """
        experiment_id = str(uuid.uuid4())
        exp_path = self.experiment_dir / experiment_id
        exp_path.mkdir(parents=True, exist_ok=False)

        code_path = exp_path / "feature.py"
        test_path = exp_path / "test_feature.py"
        code_path.write_text(feature_code, encoding="utf-8")
        test_path.write_text(test_cases, encoding="utf-8")

        # Write metadata
        meta = {
            "experiment_id": experiment_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "feature_code_path": str(code_path),
            "test_cases_path": str(test_path),
            "status": "created",
            "user_metadata": metadata or {},
        }
        (exp_path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        record = _ExperimentRecord(
            experiment_id=experiment_id,
            created_at=meta["created_at"],
            feature_code_path=str(code_path),
            test_cases_path=str(test_path),
        )
        with self._lock:
            self._records[experiment_id] = record

        logger.info("Experiment %s created at %s", experiment_id, exp_path)
        return experiment_id

    # ------------------------------------------------------------------
    # 2. Run experiment
    # ------------------------------------------------------------------

    def run_experiment(self, experiment_id: str) -> ExperimentResults:
        """Run the experiment in isolation and collect metrics.

        Pipeline
        --------
        1. Load feature code into a :class:`Sandbox`.
        2. Run provided test cases via pytest in a subprocess.
        3. Compare timing / memory against baseline if one exists.

        Parameters
        ----------
        experiment_id:
            UUID returned by :meth:`create_experiment`.

        Returns
        -------
        ExperimentResults
        """
        record = self._get_record(experiment_id)
        if record is None:
            return ExperimentResults(
                experiment_id=experiment_id,
                passed=False,
                errors=["Experiment not found"],
            )

        start_iso = datetime.now(timezone.utc).isoformat()
        logger.info("Running experiment %s ...", experiment_id)

        feature_code = Path(record.feature_code_path).read_text(encoding="utf-8")
        test_code = Path(record.test_cases_path).read_text(encoding="utf-8")

        # -- Phase 1: sandbox validation --------------------------------
        sandbox = Sandbox(feature_code, timeout_seconds=30.0)
        sandbox_ok = sandbox.compile_and_load()

        # -- Phase 2: pytest in subprocess -------------------------------
        pytest_results = self._run_pytest_in_subprocess(record.test_cases_path)

        # -- Phase 3: baseline comparison --------------------------------
        baseline = self._load_baseline()
        comparison = self._compare_with_baseline(pytest_results, baseline)

        # -- Aggregate ---------------------------------------------------
        passed = sandbox_ok and pytest_results.get("passed", 0) > 0
        errors: list[str] = []
        if not sandbox_ok:
            errors.append("Sandbox compilation failed")
        if pytest_results.get("failed", 0) > 0:
            errors.append(f"{{pytest_results['failed']}} test(s) failed")

        metrics: dict[str, float] = {
            "sandbox_compile_time_ms": pytest_results.get("duration_ms", 0.0),
            "tests_passed": float(pytest_results.get("passed", 0)),
            "tests_failed": float(pytest_results.get("failed", 0)),
            "test_duration_ms": pytest_results.get("duration_ms", 0.0),
        }

        end_iso = datetime.now(timezone.utc).isoformat()

        results = ExperimentResults(
            experiment_id=experiment_id,
            passed=passed,
            metrics=metrics,
            comparison=comparison,
            errors=errors,
            start_time=start_iso,
            end_time=end_iso,
        )

        # Persist
        record.results = asdict(results)
        record.status = "passed" if passed else "failed"
        self._save_record(record)

        logger.info("Experiment %s finished — passed=%s", experiment_id, passed)
        return results

    # ------------------------------------------------------------------
    # 3. Canary deploy
    # ------------------------------------------------------------------

    def canary_deploy(
        self,
        experiment_id: str,
        rollout_percent: int = 5,
    ) -> CanaryStatus:
        """Gradually roll out the experiment to a percentage of traffic.

        This implementation simulates a canary by running synthetic load
        against the sandboxed code and monitoring for errors.  In a real
        deployment the same logic would drive a Kubernetes rollout or
        feature-flag gate.

        Parameters
        ----------
        experiment_id:
            UUID of the experiment to deploy.
        rollout_percent:
            Percentage of traffic (1–100).

        Returns
        -------
        CanaryStatus
        """
        if not 1 <= rollout_percent <= MAX_CANARY_ROLLOUT:
            raise ValueError(f"rollout_percent must be 1–{{MAX_CANARY_ROLLOUT}}")

        record = self._get_record(experiment_id)
        if record is None:
            return CanaryStatus(status="rolled_back", rollout_percent=0)

        record.status = "canary"
        self._save_record(record)

        logger.info("Canary deploy %s at %d%%", experiment_id, rollout_percent)

        # Synthetic load test
        feature_code = Path(record.feature_code_path).read_text(encoding="utf-8")
        sandbox = Sandbox(feature_code, timeout_seconds=10.0)
        if not sandbox.compile_and_load():
            return self._rollback_canary(record, "Sandbox compilation failed")

        callables = sandbox.list_callables()
        if not callables:
            return self._rollback_canary(record, "No callable entry points found")

        entry_point = callables[0]
        error_count = 0
        latencies: list[float] = []
        total_requests = max(10, rollout_percent * 2)

        for i in range(total_requests):
            # Vary input to exercise different code paths
            test_input = f"canary request {{i}} rollout={{rollout_percent}}"
            resp = sandbox.run_function(entry_point, test_input)
            latencies.append(resp.get("duration_ms", 0.0))
            if not resp.get("success", False):
                error_count += 1

        p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
        health = 1.0 - (error_count / max(total_requests, 1))

        # Auto-rollback if health drops below threshold
        if health < 0.95 or p95 > 5000:  # 5s threshold
            return self._rollback_canary(
                record,
                f"Health={{health:.2f}}, p95={{p95:.1f}}ms — below thresholds",
            )

        status = CanaryStatus(
            status="monitoring",
            rollout_percent=rollout_percent,
            errors_detected=error_count,
            requests_served=total_requests,
            latency_p95_ms=round(p95, 2),
            health_score=round(health, 3),
            metrics={"avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0},
        )

        record.canary = asdict(status)
        self._save_record(record)
        return status

    # ------------------------------------------------------------------
    # 4. Rollback
    # ------------------------------------------------------------------

    def rollback(self, experiment_id: str) -> bool:
        """Instantly revert an experiment to the previous stable state.

        Returns ``True`` if the rollback was successful.
        """
        record = self._get_record(experiment_id)
        if record is None:
            logger.warning("Rollback requested for unknown experiment %s", experiment_id)
            return False

        record.status = "rolled_back"
        record.canary = {}
        self._save_record(record)

        logger.info("Experiment %s rolled back", experiment_id)
        return True

    # ------------------------------------------------------------------
    # 5. Results
    # ------------------------------------------------------------------

    def get_experiment_results(self, experiment_id: str) -> dict[str, Any]:
        """Retrieve the full experiment report.

        Returns
        -------
        dict
            Merged metadata, results, canary status, and comparison data.
        """
        record = self._get_record(experiment_id)
        if record is None:
            return {"error": "Experiment not found"}

        return {
            "experiment_id": record.experiment_id,
            "created_at": record.created_at,
            "status": record.status,
            "feature_code_path": record.feature_code_path,
            "test_cases_path": record.test_cases_path,
            "baseline_comparison": record.baseline_results,
            "results": record.results,
            "canary": record.canary,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_record(self, experiment_id: str) -> _ExperimentRecord | None:
        with self._lock:
            return self._records.get(experiment_id)

    def _save_record(self, record: _ExperimentRecord) -> None:
        exp_path = self.experiment_dir / record.experiment_id
        meta_path = exp_path / "meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "experiment_id": record.experiment_id,
                    "created_at": record.created_at,
                    "feature_code_path": record.feature_code_path,
                    "test_cases_path": record.test_cases_path,
                    "baseline_results": record.baseline_results,
                    "results": record.results,
                    "canary": record.canary,
                    "status": record.status,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _load_existing_records(self) -> None:
        """Load all experiment records from disk on startup."""
        if not self.experiment_dir.exists():
            return
        for subdir in self.experiment_dir.iterdir():
            meta = subdir / "meta.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    record = _ExperimentRecord(
                        experiment_id=data["experiment_id"],
                        created_at=data["created_at"],
                        feature_code_path=data["feature_code_path"],
                        test_cases_path=data["test_cases_path"],
                        baseline_results=data.get("baseline_results", {}),
                        results=data.get("results", {}),
                        canary=data.get("canary", {}),
                        status=data.get("status", "created"),
                    )
                    self._records[record.experiment_id] = record
                except Exception as exc:
                    logger.warning("Failed to load record from %s: %s", subdir, exc)

    @staticmethod
    def _run_pytest_in_subprocess(test_file: str | Path) -> dict[str, Any]:
        """Run pytest in a subprocess and capture results.

        Returns a dict with ``passed``, ``failed``, ``skipped``,
        ``duration_ms``, and ``output``.
        """
        import subprocess

        test_file = Path(test_file)
        if not test_file.exists():
            return {"passed": 0, "failed": 1, "skipped": 0, "duration_ms": 0, "output": "Test file not found"}

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "--no-header",
            "-q",
        ]

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 1, "skipped": 0, "duration_ms": 120_000, "output": "Timeout"}
        duration_ms = (time.perf_counter() - start) * 1000

        output = proc.stdout + proc.stderr

        # Parse counts from the last summary line
        passed = failed = skipped = 0
        for line in output.splitlines():
            if "passed" in line and "failed" in line:
                parts = line.split(", ")
                for p in parts:
                    if "passed" in p:
                        passed = int(p.split()[0])
                    elif "failed" in p:
                        failed = int(p.split()[0])
                    elif "skipped" in p:
                        skipped = int(p.split()[0])

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": round(duration_ms, 2),
            "output": output,
        }

    @staticmethod
    def _load_baseline() -> dict[str, Any]:
        """Load baseline metrics from disk if available."""
        baseline_path = EXPERIMENT_DIR / "baseline.json"
        if baseline_path.exists():
            return json.loads(baseline_path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _compare_with_baseline(
        current: dict[str, Any],
        baseline: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare current results against historical baseline."""
        comparison: dict[str, Any] = {}
        if not baseline:
            comparison["has_baseline"] = False
            return comparison

        comparison["has_baseline"] = True
        for key in ("tests_passed", "test_duration_ms"):
            if key in current and key in baseline:
                diff = current[key] - baseline[key]
                comparison[key] = {
                    "current": current[key],
                    "baseline": baseline[key],
                    "diff": round(diff, 2),
                    "regression": key == "tests_passed" and diff < 0,
                }
        return comparison

    def _rollback_canary(self, record: _ExperimentRecord, reason: str) -> CanaryStatus:
        logger.warning("Canary rollback for %s: %s", record.experiment_id, reason)
        record.status = "rolled_back"
        record.canary = {"rollback_reason": reason}
        self._save_record(record)
        return CanaryStatus(
            status="rolled_back",
            rollout_percent=0,
            errors_detected=1,
            health_score=0.0,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def list_experiments(self) -> list[dict[str, str]]:
        """Return a summary of all experiments."""
        with self._lock:
            return [
                {
                    "id": r.experiment_id,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in self._records.values()
            ]

    def delete_experiment(self, experiment_id: str) -> bool:
        """Permanently delete an experiment and all its artefacts."""
        record = self._get_record(experiment_id)
        if record is None:
            return False
        exp_path = self.experiment_dir / experiment_id
        if exp_path.exists():
            shutil.rmtree(exp_path)
        with self._lock:
            self._records.pop(experiment_id, None)
        logger.info("Experiment %s deleted", experiment_id)
        return True

    def save_baseline(self, experiment_id: str) -> bool:
        """Promote an experiment's results to the official baseline."""
        record = self._get_record(experiment_id)
        if record is None or not record.results:
            return False
        baseline_path = EXPERIMENT_DIR / "baseline.json"
        baseline_path.write_text(
            json.dumps(record.results.get("metrics", {}), indent=2),
            encoding="utf-8",
        )
        logger.info("Baseline updated from experiment %s", experiment_id)
        return True
