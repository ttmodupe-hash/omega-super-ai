"""
Consumer Shield — Telecom Bill Audit (BILL-AUDIT-1) — 2026-09-30

Deterministic anomaly detection over itemized telecom billing lines.

Origin: an external paste proposed this as a LangGraph + Celery + Redis
"enterprise workflow". House verdict (REJECT-5 precedent: never wrap a
five-line rule in a heavy agent framework):
  * The anomaly logic is deterministic arithmetic - it runs in microseconds,
    needs no LLM, no graph orchestrator, no message broker.
  * What the engine SHIPS instead: the same audit as a clean Consumer Shield
    module (sync endpoint below) plus async dispatch + polling + Postgres
    result persistence via core.async_jobs (JOBS-1).

Mission fit (standing founder directive): this protects people from real
South African billing abuse - out-of-bundle data charges on voice-only
lines, duplicate debits, and unauthorized charges - with an itemized,
explainable dispute report and honest escalation guidance.

Laws honoured:
  * Deterministic only - same bill in, same audit out. No LLM, no network.
  * Every anomaly names its rule and explains itself in one sentence.
  * Negative/impossible values are DATA-QUALITY flags, never counted as
    money owed.
  * Clean bills say so plainly; nothing is invented to look busy.
  * Disclaimer on every response: educational analysis, not legal advice.
"""
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/bill-audit", tags=["Consumer Shield - Bill Audit"])

RULES_VERSION = "1.0.0"

DISCLAIMER = (
    "Educational analysis only - this is NOT legal advice. Verify every charge "
    "against your contract, lodge the dispute with your provider in writing "
    "first, and escalate to ICASA only if the provider does not resolve it."
)
ESCALATION = {
    "step_1": "Lodge the dispute with your network provider in writing and keep the reference number.",
    "step_2": ("If unresolved, escalate to ICASA Consumer Affairs via icasa.org.za "
               "(verify the current contact details there - they can change)."),
    "step_3": "For premium-rated subscription content, also report to WASPA (waspa.org.za).",
}

_VALID_PLAN_TYPES = {"voice_only", "data_bundle", "mixed", "prepaid"}

# Voice-only plans should never carry data usage or data charges at all.
RULES = [
    {"id": "R1_VOICE_ONLY_DATA_CHARGE",
     "name": "Data charges on a voice-only plan",
     "explanation": "A voice-only line has no data bundle by definition - any data "
                    "usage or data charge on it is unauthorized out-of-bundle billing."},
    {"id": "R2_USER_FLAGGED_UNAUTHORIZED",
     "name": "Charge flagged as unauthorized by the account holder",
     "explanation": "The account holder marked this amount as not agreed to - it is "
                    "itemized for dispute regardless of plan type."},
    {"id": "R3_DUPLICATE_LINE",
     "name": "Duplicate charge on the same line",
     "explanation": "The same description and amount appears more than once for this "
                    "serial number - only the first occurrence is legitimate on its face."},
    {"id": "R4_IMPOSSIBLE_VALUES",
     "name": "Negative or impossible values (data-quality flag)",
     "explanation": "Negative usage or charge amounts indicate a broken export, not a "
                    "dispute - excluded from the disputed total."},
]
_RULE_BY_ID = {r["id"]: r for r in RULES}


class BillLine(BaseModel):
    serial_number: Optional[str] = Field(default=None, max_length=64)
    sn: Optional[str] = Field(default=None, max_length=64,
                              description="Alias for serial_number (accepts either).")
    phone_number: Optional[str] = Field(default=None, max_length=32)
    plan_type: str = Field(default="voice_only")
    data_usage_mb: float = Field(default=0.0)
    data_charge_zar: float = Field(default=0.0)
    unauthorized_charge_zar: float = Field(default=0.0,
        description="Amount the account holder disputes as not agreed to.")
    description: Optional[str] = Field(default=None, max_length=200)
    amount_zar: Optional[float] = Field(default=None,
        description="Line total, used with description for duplicate detection.")


class BillAuditRequest(BaseModel):
    lines: List[BillLine] = Field(min_length=1, max_length=10_000)


def _serial(line: Dict[str, Any]) -> str:
    sn = line.get("serial_number") or line.get("sn")
    return str(sn).strip() if sn else "UNKNOWN_SN"


def audit_lines(raw_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure deterministic audit. Accepts plain dicts (async path) or
    model_dump() output (API path); returns the full audit payload."""
    anomalies: List[Dict[str, Any]] = []
    data_quality_flags: List[Dict[str, Any]] = []
    seen_signatures: Dict[str, int] = {}
    total_disputed = 0.0

    for raw in raw_lines:
        line = BillLine(**{k: v for k, v in raw.items() if k in BillLine.model_fields})
        serial = _serial(raw)
        plan = line.plan_type if line.plan_type in _VALID_PLAN_TYPES else "voice_only"

        # R4 first: impossible values are data-quality issues, not disputes.
        if line.data_usage_mb < 0 or line.data_charge_zar < 0 or line.unauthorized_charge_zar < 0:
            data_quality_flags.append({
                "rule_id": "R4_IMPOSSIBLE_VALUES", "serial_number": serial,
                "issue": _RULE_BY_ID["R4_IMPOSSIBLE_VALUES"]["name"],
                "explanation": _RULE_BY_ID["R4_IMPOSSIBLE_VALUES"]["explanation"]})
            continue  # never dispute money on a broken row

        # R1: voice-only line carrying data usage/charges.
        if plan == "voice_only" and (line.data_usage_mb > 0 or line.data_charge_zar > 0):
            amount = max(line.data_charge_zar, 0.0)
            anomalies.append({
                "rule_id": "R1_VOICE_ONLY_DATA_CHARGE", "serial_number": serial,
                "phone_number": line.phone_number,
                "issue": _RULE_BY_ID["R1_VOICE_ONLY_DATA_CHARGE"]["name"],
                "disputed_amount_zar": round(amount, 2),
                "detail": f"{line.data_usage_mb} MB billed at R {amount:,.2f} on a voice-only profile",
                "explanation": _RULE_BY_ID["R1_VOICE_ONLY_DATA_CHARGE"]["explanation"]})
            total_disputed += amount

        # R2: account-holder-flagged unauthorized amount (any plan).
        if line.unauthorized_charge_zar > 0:
            anomalies.append({
                "rule_id": "R2_USER_FLAGGED_UNAUTHORIZED", "serial_number": serial,
                "phone_number": line.phone_number,
                "issue": _RULE_BY_ID["R2_USER_FLAGGED_UNAUTHORIZED"]["name"],
                "disputed_amount_zar": round(line.unauthorized_charge_zar, 2),
                "detail": f"R {line.unauthorized_charge_zar:,.2f} flagged by the account holder",
                "explanation": _RULE_BY_ID["R2_USER_FLAGGED_UNAUTHORIZED"]["explanation"]})
            total_disputed += line.unauthorized_charge_zar

        # R3: duplicate (serial + description + amount) beyond the first occurrence.
        if line.description and line.amount_zar is not None:
            sig = f"{serial}|{line.description.strip().lower()}|{round(line.amount_zar, 2)}"
            seen_signatures[sig] = seen_signatures.get(sig, 0) + 1
            if seen_signatures[sig] > 1:
                anomalies.append({
                    "rule_id": "R3_DUPLICATE_LINE", "serial_number": serial,
                    "phone_number": line.phone_number,
                    "issue": _RULE_BY_ID["R3_DUPLICATE_LINE"]["name"],
                    "disputed_amount_zar": round(line.amount_zar, 2),
                    "detail": (f"'{line.description}' R {line.amount_zar:,.2f} appears "
                               f"{seen_signatures[sig]} times on this line"),
                    "explanation": _RULE_BY_ID["R3_DUPLICATE_LINE"]["explanation"]})
                total_disputed += line.amount_zar

    total_disputed = round(total_disputed, 2)
    report = _render_report(len(raw_lines), anomalies, data_quality_flags, total_disputed)
    return {
        "rules_version": RULES_VERSION,
        "audited_lines": len(raw_lines),
        "anomaly_count": len(anomalies),
        "total_disputed_zar": total_disputed,
        "anomalies": anomalies,
        "data_quality_flags": data_quality_flags,
        "clean": not anomalies,
        "verdict": ("No anomalies detected by the current rule set - this bill is clean "
                    "against rules " + ", ".join(r["id"] for r in RULES) + ".")
                   if not anomalies else
                   f"{len(anomalies)} anomaly(ies) found, R {total_disputed:,.2f} in disputed charges.",
        "report": report,
        "next_steps": ESCALATION if anomalies else None,
        "disclaimer": DISCLAIMER,
    }


def _render_report(n_lines: int, anomalies: List[Dict[str, Any]],
                   flags: List[Dict[str, Any]], total: float) -> str:
    out = [
        "=" * 50,
        "LUQI-AI CONSUMER SHIELD - BILL RECONCILIATION REPORT",
        "=" * 50,
        f"Audited lines        : {n_lines}",
        f"Flagged anomalies    : {len(anomalies)}",
        f"Data-quality flags   : {len(flags)}",
        f"Total disputed       : R {total:,.2f}",
        "-" * 50,
    ]
    if anomalies:
        out.append("ITEMIZED ANOMALIES (keyed by serial number):")
        for a in anomalies:
            out.append(
                f"- [{a['rule_id']}] Serial {a['serial_number']}"
                + (f" | Line {a['phone_number']}" if a.get("phone_number") else "")
                + f" | Dispute: R {a['disputed_amount_zar']:,.2f}"
                + f"\n    {a['detail']}")
    else:
        out.append("No anomalies - nothing itemized.")
    if flags:
        out.append("DATA-QUALITY FLAGS (not counted in the disputed total):")
        for f in flags:
            out.append(f"- [{f['rule_id']}] Serial {f['serial_number']} | {f['issue']}")
    return "\n".join(out)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/rules")
async def list_rules() -> Dict[str, Any]:
    """The explainable rule catalogue - public and defensive by design."""
    return {"rules_version": RULES_VERSION, "rules": RULES,
            "valid_plan_types": sorted(_VALID_PLAN_TYPES),
            "note": "Deterministic rules only - every anomaly names its rule.",
            "disclaimer": DISCLAIMER}


@router.post("")
async def bill_audit(req: BillAuditRequest) -> Dict[str, Any]:
    """Synchronous audit - instant, deterministic, stateless (like scam-check).
    For the trackable 202 + polling variant, use POST /v1/jobs/bill-audit."""
    return audit_lines([line.model_dump() for line in req.lines])
