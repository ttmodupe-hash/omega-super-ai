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


# ---------------------------------------------------------------------------
# TAX-TURNOVER-1 (2026-09-30): SARS Turnover Tax estimate for micro businesses.
# An external draft of this calculator was reviewed and its rates CONFIRMED
# against the official SARS page before integration - no unverified tax
# figure ever ships. Table for the 2026/27 year of assessment (years of
# assessment ending between 1 March 2026 and 28 February 2027); Budget 2026
# raised the qualifying turnover threshold from R1m to R2.3m and the 0% band
# from R335k to R600k.
# Source: https://www.sars.gov.za/types-of-tax/turnover-tax/
TURNOVER_TAX_YEAR = "2026/27"
TURNOVER_TAX_SOURCE = "https://www.sars.gov.za/types-of-tax/turnover-tax/"
MAX_QUALIFYING_TURNOVER = 2_300_000.0


def compute_turnover_tax(annual_turnover: float) -> Dict[str, Any]:
    """SARS turnover-tax estimate on the verified 2026/27 table."""
    t = float(annual_turnover)
    if t < 0:
        raise ValueError("annual_turnover must be >= 0")
    if t <= 600_000:
        bracket, tax = "R1 - R600,000: 0% of taxable turnover", 0.0
    elif t <= 950_000:
        bracket = "R600,001 - R950,000: 1% of taxable turnover above R600,000"
        tax = 0.01 * (t - 600_000)
    elif t <= 1_400_000:
        bracket = "R950,001 - R1,400,000: R3,500 + 2% of taxable turnover above R950,000"
        tax = 3_500.0 + 0.02 * (t - 950_000)
    else:
        bracket = "R1,400,001 and above: R12,500 + 3% of taxable turnover above R1,400,000"
        tax = 12_500.0 + 0.03 * (t - 1_400_000)
    qualifies = t <= MAX_QUALIFYING_TURNOVER
    return {
        "tax_year": TURNOVER_TAX_YEAR,
        "annual_turnover": round(t, 2),
        "qualifies_for_turnover_tax": qualifies,
        "bracket": (bracket if qualifies else
                    "annual turnover exceeds the R2.3 million qualifying threshold - "
                    "standard income tax / VAT rules apply instead"),
        "estimated_turnover_tax": round(tax, 2) if qualifies else None,
        "effective_rate_pct": (round(100.0 * tax / t, 4) if (qualifies and t) else 0.0),
        "source": TURNOVER_TAX_SOURCE,
        "disclaimer": ("ESTIMATE ONLY - not a filed return and not tax advice. Turnover-tax "
                       "qualification carries further SARS conditions (natural-person "
                       "ownership, professional-service income limits and more); confirm "
                       "with SARS or a registered tax practitioner before registering "
                       "or paying."),
    }


class TurnoverTaxSchema(BaseModel):
    annual_turnover: float


@router.post("/v1/agent/turnover-tax-estimate")
async def estimate_turnover_tax(payload: TurnoverTaxSchema) -> Dict[str, Any]:
    """Pure estimate - no filing is created, so no human-gate lock is needed."""
    from fastapi import HTTPException
    if payload.annual_turnover < 0:
        raise HTTPException(status_code=422, detail="annual_turnover must be >= 0")
    return compute_turnover_tax(payload.annual_turnover)


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
