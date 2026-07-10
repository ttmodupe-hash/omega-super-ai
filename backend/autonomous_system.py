"""
Luqi AI v24.4.0 — Autonomous Multi-Agent Orchestrator
=======================================================
Master controller for the self-improving agent pipeline.

Coordinates:
  Agent 1 (HealthMonitor) -> Monitors system health
  Agent 2 (ResearchEngine) -> Researches improvements
  Agent 3 (SandboxValidator) -> Validates and deploys updates

Features:
  - Hierarchical agent coordination
  - Human-in-the-loop deployment (Option C)
  - Automatic escalation on critical failures
  - Configurable via /api/system/config

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple, Union

# ═══════════════════════════════════════════════════════════════════
# GRACEFUL IMPORTS — All modules wrapped in try/except
# ═══════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# ── Agent 1: HealthMonitor ────────────────────────────────────────
try:
    from backend.health_monitor import (
        ErrorTracker,
        HealthMonitor,
        register_health_endpoints,
    )

    _HEALTH_MONITOR_AVAILABLE = True
    logger.info("[AutonomousOrchestrator] HealthMonitor imported successfully")
except Exception as _e:
    logger.warning("[AutonomousOrchestrator] HealthMonitor unavailable: %s", _e)
    _HEALTH_MONITOR_AVAILABLE = False

    class _StubHealthMonitor:  # type: ignore[no-redef]
        """Stub HealthMonitor when backend.health_monitor is unavailable."""

        _instance: Optional["_StubHealthMonitor"] = None

        def __new__(cls) -> "_StubHealthMonitor":
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

        def __init__(self) -> None:
            if self._initialized:
                return
            self._initialized = True
            self._start_time = datetime.utcnow()
            logger.info("StubHealthMonitor initialized (degraded mode)")

        def get_health_report(self) -> dict:
            return {
                "status": "unknown",
                "version": "stub",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "HealthMonitor module not available — running in degraded mode",
                "uptime_seconds": round(
                    (datetime.utcnow() - self._start_time).total_seconds(), 1
                ),
            }

        def get_uptime_seconds(self) -> float:
            return (datetime.utcnow() - self._start_time).total_seconds()

        def record_endpoint_call(
            self, path: str, method: str, duration_ms: float, error: bool = False
        ) -> None:
            pass

    class _StubErrorTracker:  # type: ignore[no-redef]
        """Stub ErrorTracker when backend.health_monitor is unavailable."""

        _instance: Optional["_StubErrorTracker"] = None

        def __new__(cls) -> "_StubErrorTracker":
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

        def __init__(self) -> None:
            if self._initialized:
                return
            self._initialized = True
            self._errors: list = []

        def track_error(
            self,
            error: Exception,
            context: Optional[Dict[str, Any]] = None,
            severity: Optional[Any] = None,
        ) -> dict:
            err = {
                "id": f"err_{int(time.time())}",
                "timestamp": datetime.utcnow().isoformat(),
                "message": str(error),
                "severity": "critical",
            }
            self._errors.append(err)
            return err

        def get_errors(self, **kwargs: Any) -> list:
            return self._errors

        def get_error_summary(self, **kwargs: Any) -> dict:
            return {"total": len(self._errors), "by_severity": {"critical": 0}}

        def clear(self) -> None:
            self._errors.clear()

    def _stub_register_health_endpoints(app_or_router: Any) -> None:  # type: ignore[misc]
        logger.warning("register_health_endpoints: HealthMonitor not available")

    HealthMonitor = _StubHealthMonitor  # type: ignore[misc]
    ErrorTracker = _StubErrorTracker  # type: ignore[misc]
    register_health_endpoints = _stub_register_health_endpoints  # type: ignore[misc]

# ── Agent 2: ResearchEngine ───────────────────────────────────────
try:
    from backend.research_engine import ResearchEngine

    _RESEARCH_ENGINE_AVAILABLE = True
    logger.info("[AutonomousOrchestrator] ResearchEngine imported successfully")
except Exception as _e:
    logger.warning("[AutonomousOrchestrator] ResearchEngine unavailable: %s", _e)
    _RESEARCH_ENGINE_AVAILABLE = False

    class ResearchEngine:  # type: ignore[no-redef]
        """Stub ResearchEngine when backend.research_engine is unavailable."""

        def __init__(self) -> None:
            logger.info("StubResearchEngine initialized (degraded mode)")

        def run_research_cycle(self) -> List[Dict[str, Any]]:
            logger.warning("ResearchEngine.run_research_cycle: stub — no research performed")
            return []

        def get_status(self) -> dict:
            return {
                "status": "unavailable",
                "message": "ResearchEngine module not loaded",
                "last_cycle": None,
                "findings_count": 0,
            }

# ── Agent 3: SandboxValidator ─────────────────────────────────────
try:
    from backend.sandbox_validator import SandboxValidator

    _SANDBOX_VALIDATOR_AVAILABLE = True
    logger.info("[AutonomousOrchestrator] SandboxValidator imported successfully")
except Exception as _e:
    logger.warning("[AutonomousOrchestrator] SandboxValidator unavailable: %s", _e)
    _SANDBOX_VALIDATOR_AVAILABLE = False

    class SandboxValidator:  # type: ignore[no-redef]
        """Stub SandboxValidator when backend.sandbox_validator is unavailable."""

        def __init__(self) -> None:
            self._updates: Dict[str, dict] = {}
            logger.info("StubSandboxValidator initialized (degraded mode)")

        def submit_update(
            self, title: str, description: str, code: str, source: str
        ) -> dict:
            update_id = f"upd_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            self._updates[update_id] = {
                "id": update_id,
                "title": title,
                "description": description,
                "source": source,
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat(),
                "validated": False,
                "deployed": False,
                "message": "SandboxValidator not available — update stored but not validated",
            }
            logger.warning("SandboxValidator.submit_update: stub — update %s stored", update_id)
            return self._updates[update_id]

        def validate_update(self, update_id: str) -> dict:
            if update_id in self._updates:
                self._updates[update_id]["status"] = "needs_validation"
                self._updates[update_id]["message"] = "Validator unavailable — manual review required"
                return self._updates[update_id]
            return {"error": f"Update {update_id} not found"}

        def deploy_update(self, update_id: str) -> dict:
            if update_id in self._updates:
                self._updates[update_id]["status"] = "deployed"
                self._updates[update_id]["deployed_at"] = datetime.utcnow().isoformat()
                self._updates[update_id]["deployed"] = True
                return self._updates[update_id]
            return {"error": f"Update {update_id} not found"}

        def get_update(self, update_id: str) -> Optional[dict]:
            return self._updates.get(update_id)

        def get_all_updates(self) -> List[dict]:
            return list(self._updates.values())

        def get_status(self) -> dict:
            return {
                "status": "unavailable",
                "message": "SandboxValidator module not loaded",
                "pending_updates": len(self._updates),
                "validated_count": 0,
                "deployed_count": sum(1 for u in self._updates.values() if u.get("deployed")),
            }

# ── AlertSystem ───────────────────────────────────────────────────
try:
    from backend.alert_system import AlertSystem

    _ALERT_SYSTEM_AVAILABLE = True
    logger.info("[AutonomousOrchestrator] AlertSystem imported successfully")
except Exception as _e:
    logger.warning("[AutonomousOrchestrator] AlertSystem unavailable: %s", _e)
    _ALERT_SYSTEM_AVAILABLE = False

    class AlertSystem:  # type: ignore[no-redef]
        """Stub AlertSystem when backend.alert_system is unavailable."""

        def __init__(self) -> None:
            self._alerts: deque = deque(maxlen=1000)
            logger.info("StubAlertSystem initialized (degraded mode)")

        def send_alert(self, level: str, title: str, message: str, payload: Optional[dict] = None) -> dict:
            alert = {
                "id": f"alert_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                "level": level,
                "title": title,
                "message": message,
                "payload": payload or {},
                "timestamp": datetime.utcnow().isoformat(),
                "acknowledged": False,
                "acked_by": None,
                "acked_at": None,
            }
            self._alerts.append(alert)
            logger.critical("[ALERT — %s] %s: %s", level.upper(), title, message)
            return alert

        def get_alerts(self, acknowledged: Optional[bool] = None, limit: int = 100) -> List[dict]:
            alerts = list(self._alerts)
            if acknowledged is not None:
                alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
            return alerts[-limit:]

        def acknowledge_alert(self, alert_id: str, acked_by: str) -> bool:
            for alert in self._alerts:
                if alert["id"] == alert_id:
                    alert["acknowledged"] = True
                    alert["acked_by"] = acked_by
                    alert["acked_at"] = datetime.utcnow().isoformat()
                    return True
            return False

        def clear_acknowledged(self) -> int:
            cleared = sum(1 for a in self._alerts if a["acknowledged"])
            self._alerts = deque([a for a in self._alerts if not a["acknowledged"]], maxlen=1000)
            return cleared

# ── DeadMansSwitch ────────────────────────────────────────────────
try:
    from backend.dead_mans_switch import DeadMansSwitch

    _DMS_AVAILABLE = True
    logger.info("[AutonomousOrchestrator] DeadMansSwitch imported successfully")
except Exception as _e:
    logger.warning("[AutonomousOrchestrator] DeadMansSwitch unavailable: %s", _e)
    _DMS_AVAILABLE = False

    class DeadMansSwitch:  # type: ignore[no-redef]
        """Stub DeadMansSwitch when backend.dead_mans_switch is unavailable."""

        def __init__(self) -> None:
            logger.info("StubDeadMansSwitch initialized (degraded mode)")

        def trigger_rollback(self) -> dict:
            logger.critical("DeadMansSwitch.trigger_rollback: stub — rollback requested but DMS unavailable")
            return {
                "status": "failed",
                "message": "DeadMansSwitch not available — manual rollback required",
                "timestamp": datetime.utcnow().isoformat(),
            }

        def arm(self) -> None:
            logger.info("DeadMansSwitch.arm: stub")

        def disarm(self) -> None:
            logger.info("DeadMansSwitch.disarm: stub")

        def get_status(self) -> dict:
            return {
                "status": "unavailable",
                "message": "DeadMansSwitch module not loaded",
                "armed": False,
            }


# ═══════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════

class AgentRole(str, Enum):
    """Roles for agents in the autonomous pipeline."""

    HEALTH_MONITOR = "health_monitor"
    RESEARCHER = "researcher"
    VALIDATOR = "validator"


class SystemMode(str, Enum):
    """Operating modes for the autonomous orchestrator."""

    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    FULLY_AUTONOMOUS = "fully_autonomous"


@dataclass
class OrchestratorConfig:
    """Configuration for the AutonomousOrchestrator.

    Attributes:
        mode: Operating mode — HUMAN_IN_THE_LOOP requires human approval
            for deployments; FULLY_AUTONOMOUS enables auto-deploy.
        research_interval_hours: Hours between automatic research cycles.
        health_check_interval_seconds: Seconds between health checks.
        auto_deploy: Whether updates deploy automatically. Only True
            when mode is FULLY_AUTONOMOUS.
        max_stored_alerts: Maximum number of alerts to retain.
    """

    mode: SystemMode = SystemMode.HUMAN_IN_THE_LOOP
    research_interval_hours: int = 24
    health_check_interval_seconds: int = 30
    auto_deploy: bool = False
    max_stored_alerts: int = 1000

    def to_dict(self) -> dict:
        """Serialize config to a dictionary."""
        return {
            "mode": self.mode.value,
            "research_interval_hours": self.research_interval_hours,
            "health_check_interval_seconds": self.health_check_interval_seconds,
            "auto_deploy": self.auto_deploy,
            "max_stored_alerts": self.max_stored_alerts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrchestratorConfig":
        """Create config from a dictionary."""
        return cls(
            mode=SystemMode(data.get("mode", SystemMode.HUMAN_IN_THE_LOOP.value)),
            research_interval_hours=int(data.get("research_interval_hours", 24)),
            health_check_interval_seconds=int(data.get("health_check_interval_seconds", 30)),
            auto_deploy=bool(data.get("auto_deploy", False)),
            max_stored_alerts=int(data.get("max_stored_alerts", 1000)),
        )


@dataclass
class AgentStatus:
    """Status snapshot for a single agent."""

    role: AgentRole
    name: str
    available: bool
    status: str
    last_activity: Optional[str] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "name": self.name,
            "available": self.available,
            "status": self.status,
            "last_activity": self.last_activity,
            "details": self.details,
        }


# ═══════════════════════════════════════════════════════════════════
# AUTONOMOUS ORCHESTRATOR (Singleton)
# ═══════════════════════════════════════════════════════════════════

class AutonomousOrchestrator:
    """Master orchestrator for the autonomous multi-agent pipeline.

    Coordinates three specialized agents in a hierarchical flow:
      1. HealthMonitor — watches system health, detects anomalies
      2. ResearchEngine — investigates improvements and opportunities
      3. SandboxValidator — validates code updates and manages deployment

    Deployment requires human approval unless the system is configured
    in FULLY_AUTONOMOUS mode (not recommended for production).

    Singleton Pattern:
        Use create_orchestrator() factory or access via the module-level
        _orchestrator_instance variable.

    Example:
        orch = create_orchestrator()
        orch.initialize()
        status = orch.get_system_status()
    """

    _instance: Optional["AutonomousOrchestrator"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "AutonomousOrchestrator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # ── Configuration ─────────────────────────────────────────
        self._config = OrchestratorConfig()
        self._config_path: Optional[str] = None

        # ── Agents ────────────────────────────────────────────────
        self._health_monitor: Optional[Any] = None
        self._error_tracker: Optional[Any] = None
        self._research_engine: Optional[Any] = None
        self._sandbox_validator: Optional[Any] = None
        self._alert_system: Optional[Any] = None
        self._dead_mans_switch: Optional[Any] = None

        # ── State ─────────────────────────────────────────────────
        self._initialized_agents: bool = False
        self._last_health_check: Optional[datetime] = None
        self._last_research_cycle: Optional[datetime] = None
        self._research_findings: List[dict] = []
        self._pending_updates: Dict[str, dict] = {}
        self._deployment_history: deque = deque(maxlen=100)
        self._escalation_log: deque = deque(maxlen=500)
        self._system_start_time: datetime = datetime.utcnow()
        self._critical_failure_count: int = 0

        # ── Background task handles ───────────────────────────────
        self._health_task: Optional[asyncio.Task] = None
        self._research_task: Optional[asyncio.Task] = None

        logger.info(
            "AutonomousOrchestrator v24.4.0 initialized (mode=%s)",
            self._config.mode.value,
        )

    # ── Properties ──────────────────────────────────────────────────

    @property
    def config(self) -> OrchestratorConfig:
        """Current orchestrator configuration."""
        return self._config

    @property
    def health_monitor(self) -> Any:
        """HealthMonitor agent instance (or stub)."""
        return self._health_monitor

    @property
    def research_engine(self) -> Any:
        """ResearchEngine agent instance (or stub)."""
        return self._research_engine

    @property
    def sandbox_validator(self) -> Any:
        """SandboxValidator agent instance (or stub)."""
        return self._sandbox_validator

    # ── Initialization ──────────────────────────────────────────────

    def initialize(self) -> bool:
        """Set up all agents and prepare the orchestrator for operation.

        Creates instances of all three agents and supporting systems.
        Each agent is wrapped in try/except so partial failures still
        allow the system to operate in degraded mode.

        Returns:
            bool: True if at least the HealthMonitor is operational.
        """
        success = True

        # Agent 1: HealthMonitor (critical — must be present)
        try:
            self._health_monitor = HealthMonitor()
            self._error_tracker = getattr(
                self._health_monitor, "error_tracker", ErrorTracker()
            )
            logger.info("[Orchestrator] Agent 1 (HealthMonitor) ready")
        except Exception as e:
            logger.critical("[Orchestrator] Agent 1 (HealthMonitor) failed: %s", e)
            self._health_monitor = None
            self._error_tracker = None
            success = False

        # Agent 2: ResearchEngine
        try:
            self._research_engine = ResearchEngine()
            logger.info("[Orchestrator] Agent 2 (ResearchEngine) ready")
        except Exception as e:
            logger.error("[Orchestrator] Agent 2 (ResearchEngine) failed: %s", e)
            self._research_engine = None

        # Agent 3: SandboxValidator
        try:
            self._sandbox_validator = SandboxValidator()
            logger.info("[Orchestrator] Agent 3 (SandboxValidator) ready")
        except Exception as e:
            logger.error("[Orchestrator] Agent 3 (SandboxValidator) failed: %s", e)
            self._sandbox_validator = None

        # AlertSystem
        try:
            self._alert_system = AlertSystem()
            logger.info("[Orchestrator] AlertSystem ready")
        except Exception as e:
            logger.error("[Orchestrator] AlertSystem failed: %s", e)
            self._alert_system = None

        # DeadMansSwitch
        try:
            self._dead_mans_switch = DeadMansSwitch()
            logger.info("[Orchestrator] DeadMansSwitch ready")
        except Exception as e:
            logger.error("[Orchestrator] DeadMansSwitch failed: %s", e)
            self._dead_mans_switch = None

        self._initialized_agents = True
        logger.info(
            "[Orchestrator] Initialization complete (health=%s, research=%s, validator=%s)",
            self._health_monitor is not None,
            self._research_engine is not None,
            self._sandbox_validator is not None,
        )
        return success

    # ── Agent 1: Health Check ───────────────────────────────────────

    async def run_health_check(self) -> dict:
        """Execute a full health check via Agent 1 (HealthMonitor).

        Delegates to HealthMonitor.get_health_report(), then evaluates
        whether the results trigger escalation criteria.

        Returns:
            dict: Health report with orchestrator-level analysis appended.
        """
        self._last_health_check = datetime.utcnow()

        if self._health_monitor is None:
            return {
                "status": "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "HealthMonitor not available",
                "escalation_triggered": True,
                "orchestrator": self._get_orchestrator_meta(),
            }

        try:
            report = self._health_monitor.get_health_report()
        except Exception as e:
            logger.critical("[Orchestrator] Health check execution failed: %s", e)
            if self._error_tracker is not None:
                self._error_tracker.track_error(
                    e, context={"module": "orchestrator", "endpoint": "run_health_check"}
                )
            report = {"status": "error", "message": str(e)}

        # Evaluate escalation
        should_escalate = self._should_escalate(report)
        report["escalation_triggered"] = should_escalate
        report["orchestrator"] = self._get_orchestrator_meta()

        if should_escalate:
            self._critical_failure_count += 1
            await self._escalate_to_human(
                agent_name="HealthMonitor",
                error_payload={
                    "report": report,
                    "critical_failure_count": self._critical_failure_count,
                },
            )

        return report

    # ── Agent 2: Research Cycle ─────────────────────────────────────

    async def run_research_cycle(self) -> List[dict]:
        """Trigger a research/improvement cycle via Agent 2 (ResearchEngine).

        Delegates to ResearchEngine.run_research_cycle() and stores
        findings for human review.

        Returns:
            List[dict]: Research findings (empty list if unavailable).
        """
        self._last_research_cycle = datetime.utcnow()

        if self._research_engine is None:
            logger.warning("[Orchestrator] ResearchEngine not available — skipping cycle")
            return []

        try:
            if asyncio.iscoroutinefunction(self._research_engine.run_research_cycle):
                findings = await self._research_engine.run_research_cycle()
            else:
                loop = asyncio.get_event_loop()
                findings = await loop.run_in_executor(
                    None, self._research_engine.run_research_cycle
                )
        except Exception as e:
            logger.error("[Orchestrator] Research cycle failed: %s", e)
            if self._error_tracker is not None:
                self._error_tracker.track_error(
                    e, context={"module": "orchestrator", "endpoint": "run_research_cycle"}
                )
            findings = []

        # Enrich findings with metadata
        enriched: List[dict] = []
        for idx, finding in enumerate(findings):
            if not isinstance(finding, dict):
                finding = {"finding": str(finding)}
            finding["finding_id"] = f"find_{int(time.time())}_{idx}"
            finding["discovered_at"] = datetime.utcnow().isoformat()
            finding["reviewed"] = False
            enriched.append(finding)

        self._research_findings.extend(enriched)

        # Trim to reasonable size
        if len(self._research_findings) > 1000:
            self._research_findings = self._research_findings[-1000:]

        logger.info("[Orchestrator] Research cycle complete: %d findings", len(enriched))
        return enriched

    # ── Agent 3: Update Submission & Validation ─────────────────────

    async def submit_update(
        self,
        title: str,
        description: str,
        code: str,
        source: str,
    ) -> dict:
        """Submit a code update for validation via Agent 3 (SandboxValidator).

        The update flows: submitted -> validated -> [approved] -> deployed.
        Human approval is required unless in FULLY_AUTONOMOUS mode.

        Args:
            title: Short title for the update.
            description: Detailed description of changes.
            code: The code or patch to validate.
            source: Origin of the update (e.g., 'research_engine', 'manual').

        Returns:
            dict: Submission result with update_id and current status.
        """
        if self._sandbox_validator is None:
            update_id = f"upd_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            result = {
                "id": update_id,
                "title": title,
                "description": description,
                "source": source,
                "status": "pending_validator_unavailable",
                "submitted_at": datetime.utcnow().isoformat(),
                "message": "SandboxValidator not available — update queued for manual review",
            }
            self._pending_updates[update_id] = result
            logger.warning("[Orchestrator] Update %s queued (validator unavailable)", update_id)
            return result

        try:
            if asyncio.iscoroutinefunction(self._sandbox_validator.submit_update):
                result = await self._sandbox_validator.submit_update(
                    title, description, code, source
                )
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._sandbox_validator.submit_update(
                        title, description, code, source
                    ),
                )
        except Exception as e:
            logger.error("[Orchestrator] Update submission failed: %s", e)
            if self._error_tracker is not None:
                self._error_tracker.track_error(
                    e, context={"module": "orchestrator", "endpoint": "submit_update"}
                )
            return {
                "status": "error",
                "message": f"Submission failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Store in pending if we got a valid result
        if isinstance(result, dict) and "id" in result:
            self._pending_updates[result["id"]] = result

        # Auto-validate if in fully autonomous mode
        if self._config.mode == SystemMode.FULLY_AUTONOMOUS and self._config.auto_deploy:
            logger.info("[Orchestrator] Auto-deploy enabled — triggering validation")
            # Note: actual auto-deploy would call validate + deploy here
            # but for safety we still require explicit approval even in "auto" mode
            # unless the user explicitly configures dangerous_auto_deploy

        return result

    # ── Human-in-the-Loop: Approval & Deploy ────────────────────────

    async def approve_and_deploy(self, update_id: str, approved_by: str) -> bool:
        """Human approval gate + deployment.

        This is the critical human-in-the-loop checkpoint. An update must
        pass validation before it can be approved. After approval, the
        DeadMansSwitch is armed and the update is deployed.

        Args:
            update_id: ID of the update to approve and deploy.
            approved_by: Identifier of the human who approved the update.

        Returns:
            bool: True if deployment was successful.
        """
        logger.info(
            "[Orchestrator] Approval request for update %s by %s", update_id, approved_by
        )

        # Check validator availability
        if self._sandbox_validator is None:
            logger.error("[Orchestrator] Cannot deploy: SandboxValidator unavailable")
            return False

        # Retrieve update
        update = self._pending_updates.get(update_id)
        if update is None:
            try:
                if asyncio.iscoroutinefunction(self._sandbox_validator.get_update):
                    update = await self._sandbox_validator.get_update(update_id)
                else:
                    loop = asyncio.get_event_loop()
                    update = await loop.run_in_executor(
                        None, self._sandbox_validator.get_update, update_id
                    )
            except Exception as e:
                logger.error("[Orchestrator] Could not retrieve update %s: %s", update_id, e)
                return False

        if update is None:
            logger.error("[Orchestrator] Update %s not found", update_id)
            return False

        # Validate first
        try:
            if asyncio.iscoroutinefunction(self._sandbox_validator.validate_update):
                validation = await self._sandbox_validator.validate_update(update_id)
            else:
                loop = asyncio.get_event_loop()
                validation = await loop.run_in_executor(
                    None, self._sandbox_validator.validate_update, update_id
                )
        except Exception as e:
            logger.error("[Orchestrator] Validation failed for %s: %s", update_id, e)
            return False

        # Check validation result
        val_status = validation.get("status", "") if isinstance(validation, dict) else ""
        if val_status not in ("validated", "passed", "ready", "approved"):
            logger.warning(
                "[Orchestrator] Update %s not validated (status=%s) — cannot deploy",
                update_id,
                val_status,
            )
            return False

        # Arm DeadMansSwitch before deployment
        if self._dead_mans_switch is not None:
            try:
                self._dead_mans_switch.arm()
                logger.info("[Orchestrator] DeadMansSwitch armed before deployment")
            except Exception as e:
                logger.error("[Orchestrator] Failed to arm DeadMansSwitch: %s", e)
                # Continue anyway — deployment is the priority

        # Deploy
        try:
            if asyncio.iscoroutinefunction(self._sandbox_validator.deploy_update):
                deploy_result = await self._sandbox_validator.deploy_update(update_id)
            else:
                loop = asyncio.get_event_loop()
                deploy_result = await loop.run_in_executor(
                    None, self._sandbox_validator.deploy_update, update_id
                )
        except Exception as e:
            logger.critical("[Orchestrator] Deployment failed for %s: %s", update_id, e)
            if self._error_tracker is not None:
                self._error_tracker.track_error(
                    e,
                    context={
                        "module": "orchestrator",
                        "endpoint": "approve_and_deploy",
                        "update_id": update_id,
                    },
                )
            return False

        # Record deployment
        deploy_status = deploy_result.get("status", "") if isinstance(deploy_result, dict) else ""
        record = {
            "update_id": update_id,
            "approved_by": approved_by,
            "deployed_at": datetime.utcnow().isoformat(),
            "status": deploy_status,
            "validation_status": val_status,
        }
        self._deployment_history.append(record)

        # Disarm DMS on successful deployment
        if self._dead_mans_switch is not None and deploy_status in ("deployed", "success"):
            try:
                self._dead_mans_switch.disarm()
                logger.info("[Orchestrator] DeadMansSwitch disarmed after successful deployment")
            except Exception as e:
                logger.error("[Orchestrator] Failed to disarm DeadMansSwitch: %s", e)

        logger.info(
            "[Orchestrator] Update %s deployed by %s (status=%s)",
            update_id,
            approved_by,
            deploy_status,
        )
        return deploy_status in ("deployed", "success")

    # ── Emergency Rollback ──────────────────────────────────────────

    async def emergency_rollback(self) -> bool:
        """Trigger emergency rollback via DeadMansSwitch.

        This is the nuclear option — immediately rolls back the last
        deployed update and halts automatic operations.

        Returns:
            bool: True if rollback was triggered successfully.
        """
        logger.critical("[Orchestrator] EMERGENCY ROLLBACK TRIGGERED")

        if self._dead_mans_switch is None:
            logger.critical("[Orchestrator] DeadMansSwitch unavailable — cannot auto-rollback")
            await self._escalate_to_human(
                agent_name="DeadMansSwitch",
                error_payload={"message": "Emergency rollback requested but DMS unavailable"},
            )
            return False

        try:
            if asyncio.iscoroutinefunction(self._dead_mans_switch.trigger_rollback):
                result = await self._dead_mans_switch.trigger_rollback()
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self._dead_mans_switch.trigger_rollback
                )
        except Exception as e:
            logger.critical("[Orchestrator] Rollback execution failed: %s", e)
            return False

        # Log the rollback
        record = {
            "type": "rollback",
            "triggered_at": datetime.utcnow().isoformat(),
            "result": result if isinstance(result, dict) else {"status": str(result)},
        }
        self._deployment_history.append(record)

        # Halt auto-operations
        self._halt_background_tasks()

        # Escalate to human
        await self._escalate_to_human(
            agent_name="EmergencyRollback",
            error_payload={
                "message": "Emergency rollback was triggered",
                "rollback_result": result if isinstance(result, dict) else {"status": str(result)},
                "deployment_history": list(self._deployment_history)[-10:],
            },
        )

        return True

    # ── System Status ───────────────────────────────────────────────

    def get_system_status(self) -> dict:
        """Get comprehensive status of all agents and the orchestrator.

        Returns a complete snapshot including:
          - Orchestrator metadata (uptime, mode, version)
          - Agent 1: HealthMonitor status
          - Agent 2: ResearchEngine status
          - Agent 3: SandboxValidator status
          - AlertSystem summary
          - DeadMansSwitch status
          - Pending updates count
          - Recent deployment history
          - Escalation count

        Returns:
            dict: Complete system status dictionary.
        """
        agents: List[dict] = []

        # Agent 1: HealthMonitor
        if self._health_monitor is not None:
            try:
                hm_report = self._health_monitor.get_health_report()
                agents.append(
                    AgentStatus(
                        role=AgentRole.HEALTH_MONITOR,
                        name="HealthMonitor",
                        available=True,
                        status=hm_report.get("status", "unknown"),
                        last_activity=self._last_health_check.isoformat()
                        if self._last_health_check
                        else None,
                        details=hm_report,
                    ).to_dict()
                )
            except Exception as e:
                agents.append(
                    AgentStatus(
                        role=AgentRole.HEALTH_MONITOR,
                        name="HealthMonitor",
                        available=False,
                        status=f"error: {e}",
                    ).to_dict()
                )
        else:
            agents.append(
                AgentStatus(
                    role=AgentRole.HEALTH_MONITOR,
                    name="HealthMonitor",
                    available=False,
                    status="not_loaded",
                ).to_dict()
            )

        # Agent 2: ResearchEngine
        if self._research_engine is not None:
            try:
                re_status = self._research_engine.get_status()
                agents.append(
                    AgentStatus(
                        role=AgentRole.RESEARCHER,
                        name="ResearchEngine",
                        available=True,
                        status=re_status.get("status", "unknown"),
                        last_activity=self._last_research_cycle.isoformat()
                        if self._last_research_cycle
                        else None,
                        details=re_status,
                    ).to_dict()
                )
            except Exception as e:
                agents.append(
                    AgentStatus(
                        role=AgentRole.RESEARCHER,
                        name="ResearchEngine",
                        available=False,
                        status=f"error: {e}",
                    ).to_dict()
                )
        else:
            agents.append(
                AgentStatus(
                    role=AgentRole.RESEARCHER,
                    name="ResearchEngine",
                    available=False,
                    status="not_loaded",
                ).to_dict()
            )

        # Agent 3: SandboxValidator
        if self._sandbox_validator is not None:
            try:
                sv_status = self._sandbox_validator.get_status()
                agents.append(
                    AgentStatus(
                        role=AgentRole.VALIDATOR,
                        name="SandboxValidator",
                        available=True,
                        status=sv_status.get("status", "unknown"),
                        details=sv_status,
                    ).to_dict()
                )
            except Exception as e:
                agents.append(
                    AgentStatus(
                        role=AgentRole.VALIDATOR,
                        name="SandboxValidator",
                        available=False,
                        status=f"error: {e}",
                    ).to_dict()
                )
        else:
            agents.append(
                AgentStatus(
                    role=AgentRole.VALIDATOR,
                    name="SandboxValidator",
                    available=False,
                    status="not_loaded",
                ).to_dict()
            )

        # AlertSystem
        alert_summary: dict = {"available": False}
        if self._alert_system is not None:
            try:
                active = self._alert_system.get_alerts(acknowledged=False, limit=1000)
                total = self._alert_system.get_alerts(limit=1000)
                alert_summary = {
                    "available": True,
                    "active_unacknowledged": len(active),
                    "total_recent": len(total),
                }
            except Exception as e:
                alert_summary = {"available": True, "error": str(e)}

        # DeadMansSwitch
        dms_status: dict = {"available": False}
        if self._dead_mans_switch is not None:
            try:
                dms_status = {
                    "available": True,
                    **self._dead_mans_switch.get_status(),
                }
            except Exception as e:
                dms_status = {"available": True, "error": str(e)}

        return {
            "version": "24.4.0",
            "timestamp": datetime.utcnow().isoformat(),
            "orchestrator": self._get_orchestrator_meta(),
            "agents": agents,
            "alerts": alert_summary,
            "dead_mans_switch": dms_status,
            "pending_updates": len(self._pending_updates),
            "recent_deployments": list(self._deployment_history)[-10:],
            "escalations_24h": self._count_recent_escalations(hours=24),
            "critical_failures": self._critical_failure_count,
        }

    # ── Configuration Management ────────────────────────────────────

    def get_config(self) -> dict:
        """Get current orchestrator configuration.

        Returns:
            dict: Serialized OrchestratorConfig.
        """
        return self._config.to_dict()

    def update_config(self, **kwargs: Any) -> bool:
        """Update orchestrator configuration.

        Validates the new configuration and applies it. If mode is
        changed to HUMAN_IN_THE_LOOP, auto_deploy is forced to False.

        Args:
            **kwargs: Configuration key-value pairs to update.
                Supported keys: mode, research_interval_hours,
                health_check_interval_seconds, auto_deploy, max_stored_alerts.

        Returns:
            bool: True if the update was applied successfully.
        """
        try:
            # Build new config from current
            current = self._config.to_dict()
            current.update(kwargs)

            # Validate mode
            if "mode" in kwargs:
                mode_val = kwargs["mode"]
                if isinstance(mode_val, str):
                    mode_val = SystemMode(mode_val)
                # Force auto_deploy=False in human-in-the-loop mode
                if mode_val == SystemMode.HUMAN_IN_THE_LOOP:
                    current["auto_deploy"] = False

            new_config = OrchestratorConfig.from_dict(current)
            self._config = new_config

            logger.info("[Orchestrator] Configuration updated: %s", self._config.to_dict())
            return True
        except Exception as e:
            logger.error("[Orchestrator] Configuration update failed: %s", e)
            if self._error_tracker is not None:
                self._error_tracker.track_error(
                    e, context={"module": "orchestrator", "endpoint": "update_config"}
                )
            return False

    # ── Escalation Logic ────────────────────────────────────────────

    async def _escalate_to_human(
        self,
        agent_name: str,
        error_payload: dict,
    ) -> None:
        """Trigger a CRITICAL alert that requires human intervention.

        Sends an alert via AlertSystem and logs to the escalation queue.
        This method is called when automatic recovery is not possible.

        Args:
            agent_name: Name of the agent that triggered escalation.
            error_payload: Additional context about the error condition.
        """
        escalation = {
            "id": f"esc_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": error_payload,
            "resolved": False,
        }
        self._escalation_log.append(escalation)

        title = f"CRITICAL: {agent_name} requires human intervention"
        message = (
            f"Agent '{agent_name}' has triggered an escalation. "
            f"The autonomous system cannot recover automatically. "
            f"Review the error payload and take appropriate action."
        )

        # Send via AlertSystem
        if self._alert_system is not None:
            try:
                self._alert_system.send_alert(
                    level="critical",
                    title=title,
                    message=message,
                    payload={"agent": agent_name, **error_payload},
                )
            except Exception as e:
                logger.critical("[Orchestrator] AlertSystem failed during escalation: %s", e)

        logger.critical(
            "[ESCALATION] %s | %s | Escalations(24h): %d",
            agent_name,
            title,
            self._count_recent_escalations(hours=24),
        )

    def _should_escalate(self, health_report: dict) -> bool:
        """Determine if a health report should trigger human escalation.

        Escalation triggers:
        - Overall status is "unhealthy"
        - Critical error count exceeds threshold (5 in 1 hour)
        - HealthMonitor itself is not responding

        Args:
            health_report: The health report dictionary from HealthMonitor.

        Returns:
            bool: True if human escalation should be triggered.
        """
        if not isinstance(health_report, dict):
            return True  # Malformed report = escalate

        status = health_report.get("status", "unknown")
        if status == "unhealthy":
            return True

        # Check error summary
        errors = health_report.get("errors", {})
        if isinstance(errors, dict):
            critical_count = errors.get("critical", 0)
            if isinstance(critical_count, int) and critical_count >= 5:
                return True

        return False

    # ── Alert Management ────────────────────────────────────────────

    def get_active_alerts(
        self, acknowledged: Optional[bool] = None, limit: int = 100
    ) -> List[dict]:
        """Get active alerts from the AlertSystem.

        Args:
            acknowledged: Filter by acknowledged status. None returns all.
            limit: Maximum number of alerts to return.

        Returns:
            List[dict]: Active alerts.
        """
        if self._alert_system is None:
            # Fall back to escalation log
            alerts = list(self._escalation_log)
            if acknowledged is not None:
                alerts = [a for a in alerts if a.get("resolved") == acknowledged]
            return alerts[-limit:]

        try:
            return self._alert_system.get_alerts(acknowledged=acknowledged, limit=limit)
        except Exception as e:
            logger.error("[Orchestrator] Failed to get alerts: %s", e)
            return []

    def acknowledge_alert(self, alert_id: str, acked_by: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: ID of the alert to acknowledge.
            acked_by: Identifier of the person acknowledging.

        Returns:
            bool: True if the alert was acknowledged.
        """
        # Try escalation log first
        for esc in self._escalation_log:
            if esc["id"] == alert_id:
                esc["resolved"] = True
                esc["resolved_by"] = acked_by
                esc["resolved_at"] = datetime.utcnow().isoformat()
                return True

        # Try AlertSystem
        if self._alert_system is not None:
            try:
                return self._alert_system.acknowledge_alert(alert_id, acked_by)
            except Exception as e:
                logger.error("[Orchestrator] Failed to acknowledge alert %s: %s", alert_id, e)

        return False

    # ── FastAPI Endpoint Registration ───────────────────────────────

    def register_all_endpoints(self, app_or_router: Any) -> None:
        """Register ALL autonomous system endpoints on a FastAPI app/router.

        Registers 10 master endpoints:
          GET  /api/system/status           — Full system status
          GET  /api/system/config           — Current configuration
          POST /api/system/config           — Update configuration
          POST /api/system/health-check     — Trigger health check
          POST /api/system/research/run     — Trigger research cycle
          POST /api/system/submit-update    — Submit code for validation
          POST /api/system/approve-deploy/{id} — Human approval + deploy
          POST /api/system/rollback         — Emergency rollback
          GET  /api/system/alerts           — Active alerts
          POST /api/system/alerts/ack       — Acknowledge alert

        Also registers the health monitor's native endpoints.

        Args:
            app_or_router: FastAPI app or APIRouter instance.
        """
        from fastapi import HTTPException, Path, Request
        from fastapi.responses import JSONResponse

        logger.info("[Orchestrator] Registering autonomous system endpoints")

        # Also register the native health endpoints
        try:
            register_health_endpoints(app_or_router)
        except Exception as e:
            logger.warning("[Orchestrator] Could not register health endpoints: %s", e)

        # ── GET /api/system/status ────────────────────────────────
        @app_or_router.get("/api/system/status", tags=["Autonomous System"])
        async def api_system_status():
            """Get comprehensive system status for all agents."""
            try:
                status = self.get_system_status()
                return JSONResponse(status)
            except Exception as e:
                logger.error("Error getting system status: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── GET /api/system/config ────────────────────────────────
        @app_or_router.get("/api/system/config", tags=["Autonomous System"])
        async def api_system_config_get():
            """Get current orchestrator configuration."""
            try:
                return JSONResponse(self.get_config())
            except Exception as e:
                logger.error("Error getting config: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/config ───────────────────────────────
        @app_or_router.post("/api/system/config", tags=["Autonomous System"])
        async def api_system_config_post(request: Request):
            """Update orchestrator configuration.

            Request body: JSON object with config key-value pairs.
            Example: {"mode": "human_in_the_loop", "auto_deploy": false}
            """
            try:
                import json
                data = json.loads(await request.body())
                result = self.update_config(**data)
                return JSONResponse(
                    {"success": result, "config": self.get_config()}
                )
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            except Exception as e:
                logger.error("Error updating config: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/health-check ─────────────────────────
        @app_or_router.post("/api/system/health-check", tags=["Autonomous System"])
        async def api_system_health_check():
            """Trigger a full health check across all agents."""
            try:
                report = await self.run_health_check()
                return JSONResponse(report)
            except Exception as e:
                logger.error("Error running health check: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/research/run ─────────────────────────
        @app_or_router.post("/api/system/research/run", tags=["Autonomous System"])
        async def api_system_research_run():
            """Trigger a research cycle to find improvements."""
            try:
                findings = await self.run_research_cycle()
                return JSONResponse(
                    {
                        "status": "complete",
                        "findings_count": len(findings),
                        "findings": findings,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.error("Error running research cycle: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/submit-update ────────────────────────
        @app_or_router.post("/api/system/submit-update", tags=["Autonomous System"])
        async def api_system_submit_update(request: Request):
            """Submit a code update for validation.

            Request body:
                title: str — Update title
                description: str — Detailed description
                code: str — Code or patch to validate
                source: str — Origin of the update
            """
            try:
                import json
                data = json.loads(await request.body())
                result = await self.submit_update(
                    title=data.get("title", "Untitled"),
                    description=data.get("description", ""),
                    code=data.get("code", ""),
                    source=data.get("source", "manual"),
                )
                return JSONResponse(result)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            except Exception as e:
                logger.error("Error submitting update: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/approve-deploy/{id} ──────────────────
        @app_or_router.post(
            "/api/system/approve-deploy/{update_id}", tags=["Autonomous System"]
        )
        async def api_system_approve_deploy(update_id: str, request: Request):
            """Human approval gate — validate and deploy an update.

            Path parameter:
                update_id: ID of the update to approve and deploy

            Request body:
                approved_by: str — Identifier of the approver
            """
            try:
                import json
                body = json.loads(await request.body())
                approved_by = body.get("approved_by", "unknown")
                result = await self.approve_and_deploy(update_id, approved_by)
                return JSONResponse(
                    {
                        "success": result,
                        "update_id": update_id,
                        "approved_by": approved_by,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            except Exception as e:
                logger.error("Error approving/deploying update %s: %s", update_id, e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/rollback ─────────────────────────────
        @app_or_router.post("/api/system/rollback", tags=["Autonomous System"])
        async def api_system_rollback():
            """Trigger emergency rollback.

            WARNING: This immediately rolls back the last deployed update.
            Use only in critical failure scenarios.
            """
            try:
                result = await self.emergency_rollback()
                return JSONResponse(
                    {
                        "rollback_triggered": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.critical("Error during rollback: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── GET /api/system/alerts ────────────────────────────────
        @app_or_router.get("/api/system/alerts", tags=["Autonomous System"])
        async def api_system_alerts(acknowledged: Optional[bool] = None, limit: int = 100):
            """Get active alerts.

            Query parameters:
                acknowledged: Filter by acknowledged status (true/false)
                limit: Maximum number of alerts to return (default 100)
            """
            try:
                alerts = self.get_active_alerts(acknowledged=acknowledged, limit=limit)
                return JSONResponse(
                    {
                        "alerts": alerts,
                        "count": len(alerts),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.error("Error getting alerts: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/alerts/ack ───────────────────────────
        @app_or_router.post("/api/system/alerts/ack", tags=["Autonomous System"])
        async def api_system_alerts_ack(request: Request):
            """Acknowledge an alert.

            Request body:
                alert_id: str — ID of the alert to acknowledge
                acked_by: str — Identifier of the person acknowledging
            """
            try:
                import json
                data = json.loads(await request.body())
                alert_id = data.get("alert_id", "")
                acked_by = data.get("acked_by", "unknown")
                if not alert_id:
                    raise HTTPException(status_code=400, detail="alert_id is required")
                result = self.acknowledge_alert(alert_id, acked_by)
                return JSONResponse(
                    {
                        "success": result,
                        "alert_id": alert_id,
                        "acked_by": acked_by,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Error acknowledging alert: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        logger.info("[Orchestrator] All autonomous system endpoints registered")

    # ── Internal Helpers ────────────────────────────────────────────

    def _get_orchestrator_meta(self) -> dict:
        """Get orchestrator metadata for inclusion in responses.

        Returns:
            dict: Uptime, mode, version, initialization status.
        """
        return {
            "version": "24.4.0",
            "mode": self._config.mode.value,
            "auto_deploy": self._config.auto_deploy,
            "uptime_seconds": round(
                (datetime.utcnow() - self._system_start_time).total_seconds(), 1
            ),
            "initialized": self._initialized_agents,
            "agents_initialized": {
                "health_monitor": self._health_monitor is not None,
                "research_engine": self._research_engine is not None,
                "sandbox_validator": self._sandbox_validator is not None,
                "alert_system": self._alert_system is not None,
                "dead_mans_switch": self._dead_mans_switch is not None,
            },
        }

    def _count_recent_escalations(self, hours: int = 24) -> int:
        """Count escalations within the specified time window.

        Args:
            hours: Number of hours to look back.

        Returns:
            int: Number of escalations in the time window.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        count = 0
        for esc in self._escalation_log:
            try:
                esc_time = datetime.fromisoformat(esc["timestamp"])
                if esc_time >= cutoff:
                    count += 1
            except (ValueError, KeyError):
                continue
        return count

    def _halt_background_tasks(self) -> None:
        """Cancel all background tasks (health check, research)."""
        tasks_cancelled = 0
        for task_attr in ("_health_task", "_research_task"):
            task = getattr(self, task_attr, None)
            if task is not None and not task.done():
                task.cancel()
                tasks_cancelled += 1
                logger.info("[Orchestrator] Cancelled %s", task_attr)
        logger.info("[Orchestrator] Halted %d background tasks", tasks_cancelled)

    def __repr__(self) -> str:
        return (
            f"AutonomousOrchestrator("
            f"mode={self._config.mode.value}, "
            f"initialized={self._initialized_agents}, "
            f"uptime={self._get_orchestrator_meta()['uptime_seconds']}s)"
        )


# ═══════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[AutonomousOrchestrator] = None


def create_orchestrator() -> AutonomousOrchestrator:
    """Factory function to create or retrieve the AutonomousOrchestrator singleton.

    Returns the existing instance if one has already been created,
    otherwise creates and returns a new one.

    Returns:
        AutonomousOrchestrator: The singleton orchestrator instance.

    Example:
        orch = create_orchestrator()
        orch.initialize()
        status = orch.get_system_status()
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AutonomousOrchestrator()
    return _orchestrator_instance


# ═══════════════════════════════════════════════════════════════════
# STANDALONE CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════


def register_system_endpoints(app_or_router: Any) -> None:
    """Register all autonomous system endpoints on a FastAPI app/router.

    This is a standalone convenience function that creates the orchestrator,
    initializes it, and registers all endpoints. Use this in endpoint
    modules that import and register routes.

    Args:
        app_or_router: FastAPI app or APIRouter instance.

    Example:
        from backend.autonomous_system import register_system_endpoints
        register_system_endpoints(app)
    """
    orch = create_orchestrator()
    orch.initialize()
    orch.register_all_endpoints(app_or_router)
