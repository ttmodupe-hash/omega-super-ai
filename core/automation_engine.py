"""
OMEGA-LUQI Sovereign Digital Automation & RPA Kernel

Event-driven workflow executor: chains API/DB/calculation steps with 70%
autonomous execution, hard-freezing at the proven 30% gate when a step is
financially or administratively sensitive.

Safety architecture:
  - Every step endpoint passes the SSRF guard before any network call.
  - Critical steps (risk_profile=critical or payment endpoints) never execute;
    they register as gate tasks with completed history + remaining steps.
  - Step failures are isolated (pipeline stops) and optionally diagnosed by
    the self-healing agent (proposal only).
  - No third-party RPA licensing; all automation stays inside your network.
"""
import uuid
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .auth import LuqiAuthManager, UserSessionProfile
from .main_types import LuqiState, TaskStatus
from .state_store import get_state_store
from .ssrf_guard import assert_automation_url_allowed
from .pii_scrub import scrub_pii

automation_router = APIRouter(prefix="/v1/automation", tags=["Sovereign Digital Automation"])


from pydantic import BaseModel


class AutomationWorkflowSchema(BaseModel):
    workflow_name: str
    trigger_event: str                          # e.g. "new_tender_detected"
    target_action_steps: List[Dict[str, Any]]   # ordered microservice steps


class LuqiAutomationKernel:
    async def execute_autonomous_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one safe step through the SSRF-guarded async client."""
        action = step.get("action")
        endpoint = step.get("endpoint", "")
        payload = step.get("payload", {})

        if action not in ("GET", "POST"):
            return {"step": step.get("name"), "status": "skipped", "reason": "Unknown action protocol"}

        assert_automation_url_allowed(endpoint)  # SSRF guard - raises 400/403

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if action == "POST":
                    res = await client.post(endpoint, json=scrub_pii(payload) if isinstance(payload, str) else payload)
                    return {"step": step.get("name"), "status": "success", "code": res.status_code}
                res = await client.get(endpoint)
                return {"step": step.get("name"), "status": "success", "data": res.json()}
            except Exception as e:
                return {"step": step.get("name"), "status": "failed", "error": str(e)}


@automation_router.post("/trigger-workflow")
async def trigger_digital_automation_workflow(
    workflow: AutomationWorkflowSchema,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """70% autonomous pipeline with 30% gate interception on sensitive steps."""
    kernel = LuqiAutomationKernel()
    execution_history: List[Dict[str, Any]] = []

    for index, step in enumerate(workflow.target_action_steps):
        is_sensitive = (
            step.get("risk_profile") == "critical"
            or "payment" in step.get("endpoint", "").lower()
        )
        if is_sensitive:
            task = LuqiState(
                student_tier=current_user.tier,
                action_type="process_payment" if "payment" in step.get("endpoint", "").lower()
                            else "modify_api_limits",
                payload={
                    "item": f"Automation workflow halted: {workflow.workflow_name}",
                    "trigger": workflow.trigger_event,
                    "halted_step": step.get("name", f"step-{index}"),
                    "completed_steps_history": execution_history,
                    "remaining_steps": workflow.target_action_steps[index:],
                },
            )
            task.status = TaskStatus.PENDING_HUMAN_APPROVAL
            task.required_human_action = (
                f"Automation '{workflow.workflow_name}' frozen at sensitive step "
                f"'{step.get('name', index)}'. Release authorizes re-triggering the workflow."
            )
            get_state_store().set(task.task_id, task)
            from .notifications import notify_gate_lock
            notify_gate_lock(task)
            return {
                "execution_status": "LOCKED_AT_HUMAN_GATE",
                "gate_task_id": str(task.task_id),
                "completed_steps": execution_history,
                "message": "Automation pipeline frozen. Sensitive operation requires human release.",
            }

        result = await kernel.execute_autonomous_step(step)
        execution_history.append(result)
        if result["status"] == "failed":
            # Optional self-healing diagnosis (proposal only, never auto-patches)
            try:
                from .self_healing import diagnose_fault
                import asyncio
                asyncio.create_task(diagnose_fault(
                    "automation_engine",
                    f"Step {step.get('name')} failed: {result.get('error')}",
                ))
            except Exception:
                pass
            return {"execution_status": "failed_and_isolated", "failed_step": result, "history": execution_history}

    return {
        "execution_status": "completed",
        "workflow_name": workflow.workflow_name,
        "steps_executed": len(execution_history),
        "history": execution_history,
    }
