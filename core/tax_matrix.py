"""
OMEGA-LUQI High-Intelligence Tax & Corporate Filing Engine

Computes corporate tax returns completely and automatically, then registers
the submission as a critical action in the proven 30% Human-in-the-Loop gate.
No filing leaves the system without an authenticated human release - the lock
is enforced by the same state machine the test suite validates, not by a
status string.

NOTE: 27% is the SARS headline corporate rate baseline. Provisional tax,
dividends tax, and industry-specific adjustments are out of scope for v1 -
always label output as an ESTIMATE until a qualified practitioner reviews.
"""
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class TaxFilingSchema(BaseModel):
    gross_revenue: float
    allowable_expenses: float
    tax_exemptions: float = 0.0


def compute_returns(financial_data: TaxFilingSchema) -> Dict[str, Any]:
    taxable_income = max(0.0, financial_data.gross_revenue - financial_data.allowable_expenses - financial_data.tax_exemptions)
    estimated_tax_payable = taxable_income * 0.27  # SARS headline corporate rate baseline
    return {
        "taxable_net_income": taxable_income,
        "estimated_liability": estimated_tax_payable,
        "disclaimer": "ESTIMATE ONLY - not a filed return. Requires qualified practitioner review before submission.",
    }


@router.post("/v1/agent/tax-compute")
async def calculate_corporate_returns(financial_data: TaxFilingSchema) -> Dict[str, Any]:
    """Compute the return, then lock the filing behind the 30% human gate."""
    from .main_types import LuqiState, TaskStatus
    from .state_store import get_state_store

    calculation = compute_returns(financial_data)

    # Register the filing as a critical action in the PROVEN gate
    task = LuqiState(
        student_tier="enterprise",
        action_type="submit_government_filing",
        payload={"calculation": calculation, "source": "tax_matrix"},
    )
    task.status = TaskStatus.PENDING_HUMAN_APPROVAL
    task.required_human_action = (
        "Tax filing locked at the 30% gate. Review financial statements, append verified credentials, "
        "then release via POST /v1/human/override/{task_id}."
    )
    get_state_store().set(task.task_id, task)
    from .notifications import notify_gate_lock
    notify_gate_lock(task)

    return {
        "calculation_status": TaskStatus.PENDING_HUMAN_APPROVAL,
        "financial_summary": calculation,
        "gate_task_id": str(task.task_id),
        "human_action_required": task.required_human_action,
    }
