"""
Financial Literacy & Scam Protection skill — UNIFY-13 (luqi-ai #62)

One unified capability replacing the disconnected v25-era modules
(financial_literacy.py, investment_mining.py, loan_mastery.py):

- GET  /v1/finlit/topics            — education topic index
- GET  /v1/finlit/topics/{topic_id} — full lesson content (with disclaimer)
- GET  /v1/finlit/scam-patterns     — versioned scam-pattern catalogue
- POST /v1/finlit/scam-check        — deterministic scam-pattern analysis of text

Design rules (house law):
- Deterministic detection only — no LLM call, works fully offline, no DB.
- The scam-pattern list is versioned in the repo: core/data/scam_patterns.json.
  Any pattern change must bump its `version` field.
- EVERY response carries the education-not-advice disclaimer. No exceptions.
- ZA-focused examples (FSCA, NCR/NCA, SARS, stokvels) per the standing user
  directive: "help people make [money] and avoid scams, understand finance,
  importance to invest".
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/finlit", tags=["financial-literacy"])

DISCLAIMER = (
    "Educational information only — this is NOT financial advice. "
    "Consult an FSCA-licensed financial advisor before making financial decisions."
)
REPORT_LINE = (
    "Report suspected fraud: FSCA (0800 110 443), SAFPS (011 867 2234), "
    "your bank's fraud line, and SAPS (10111)."
)

_PATTERNS_FILE = Path(__file__).resolve().parent / "data" / "scam_patterns.json"

# Severity-weighted risk bands (sum of matched pattern severities, plus repeat-hit bonus)
_RISK_BANDS = ((0, "none"), (3, "low"), (7, "medium"), (12, "high"))  # >12 -> critical


# ── Pattern catalogue (versioned, repo-resident) ─────────────────────────

@lru_cache(maxsize=1)
def _load_patterns() -> Dict[str, Any]:
    """Load the versioned scam-pattern catalogue. Fail-closed: a skill that
    cannot load its detection catalogue must not serve scam checks."""
    if not _PATTERNS_FILE.exists():
        raise RuntimeError(f"scam pattern catalogue missing: {_PATTERNS_FILE}")
    data = json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("patterns"):
        raise RuntimeError("scam pattern catalogue is malformed (needs version + patterns)")
    return data


def _compile(indicator: str) -> re.Pattern:
    # Phrase match, case-insensitive, tolerant of extra internal whitespace.
    return re.compile(r"\b" + r"\s+".join(map(re.escape, indicator.split())) + r"\b", re.I)


# ── Education content (real, ZA-focused) ─────────────────────────────────

TOPICS: List[Dict[str, Any]] = [
    {
        "id": "budgeting-basics",
        "title": "Budgeting: telling your money where to go",
        "minutes": 15,
        "content": (
            "A budget is a plan you make BEFORE the money arrives.\n\n"
            "1. Start with NET income — what actually lands in your account.\n"
            "2. List fixed needs (rent, transport, food, electricity, airtime) first.\n"
            "3. Pay yourself first: move savings the day you are paid, even 10%. "
            "Saving 'what is left over' means saving nothing.\n"
            "4. What remains is for wants — and when it is finished, it is finished.\n\n"
            "Track every rand for one month. Most people find a leak (takeaways, "
            "unused subscriptions, bank fees) worth 5–15% of their income."
        ),
    },
    {
        "id": "emergency-fund",
        "title": "The emergency fund: your first financial shield",
        "minutes": 10,
        "content": (
            "Before investing anything, build an emergency fund — 1 month of essential "
            "expenses first, then grow toward 3–6 months.\n\n"
            "Why first? Because without it, every shock (funeral, job loss, broken car) "
            "forces you into expensive debt — mashonisas charge 30–50% per month, which "
            "destroys any investment gains.\n\n"
            "Where to keep it: a separate savings account or money-market account that "
            "earns interest but can be reached within a day or two. NOT in investments "
            "that can drop in value, and NOT in your everyday account where it leaks away."
        ),
    },
    {
        "id": "understanding-debt",
        "title": "Debt: the tool that cuts both ways",
        "minutes": 15,
        "content": (
            "Debt is expensive fuel. Used for an asset that grows or earns (education, "
            "a home, tools for a business) it can build wealth. Used for consumption "
            "(clothes, phones, holidays) it transfers your future income to a lender.\n\n"
            "Know your rights (South Africa):\n"
            "- Credit providers must be registered with the NCR (check ncr.org.za).\n"
            "- Upfront fees before a loan pays out are ILLEGAL under the National Credit Act.\n"
            "- In duplum: interest owed can never exceed the outstanding capital.\n"
            "- Debt review is a legal, regulated way out of over-indebtedness — far better "
            "than ignoring it or borrowing from loan sharks.\n\n"
            "Kill debt in order of interest rate (usually: store cards and mashonisa first, "
            "then credit cards, then personal loans, home/car last)."
        ),
    },
    {
        "id": "investing-basics",
        "title": "Investing basics: how money actually grows",
        "minutes": 20,
        "content": (
            "Investing is owning assets that produce value — not betting on tips.\n\n"
            "Core truths:\n"
            "- COMPOUND GROWTH: returns earn returns. R500/month at 10% per year becomes "
            "about R102 000 in 10 years and over R1 million in 30 years. Time is the "
            "ingredient, not timing.\n"
            "- RISK AND RETURN ARE LINKED: anything promising 10%+ per MONTH with 'no risk' "
            "is a scam — that is 3x per year, which no legitimate investment can guarantee.\n"
            "- DIVERSIFY: never put everything in one company, one asset, or one scheme.\n\n"
            "Legitimate SA starting points: Tax-Free Savings Accounts (TFSA, up to "
            "R36 000/year, all growth tax-free), low-cost unit trusts and ETFs, and "
            "retirement annuities (tax-deductible). All are available from FSCA-regulated "
            "providers — always verify the provider's licence at fsca.co.za."
        ),
    },
    {
        "id": "compound-growth",
        "title": "Compound growth: the eighth wonder, in numbers",
        "minutes": 10,
        "content": (
            "Compound growth means your returns start earning their own returns.\n\n"
            "R10 000 at 10% per year:\n"
            "- After 10 years: ~R25 900\n"
            "- After 20 years: ~R67 300\n"
            "- After 30 years: ~R174 500\n\n"
            "Notice the acceleration — the last decade adds more than the first two combined. "
            "This is why starting at 25 beats starting at 35 even with the same monthly amount, "
            "and why scammers exploit the reverse: 'guaranteed 30% per month' sounds like "
            "compound magic but is mathematically unsustainable (R1 000 would become "
            "R23 million in 3 years — if it were real, they would not need your money)."
        ),
    },
    {
        "id": "scam-self-defence",
        "title": "Scam self-defence: the five rules",
        "minutes": 10,
        "content": (
            "Five rules that stop almost every scam:\n\n"
            "1. GUARANTEED RETURNS DO NOT EXIST. Any promise of fixed high returns is fraud.\n"
            "2. NEVER share OTPs, PINs, or passwords — not with 'the bank', 'SARS', or 'police'. "
            "Real institutions never ask.\n"
            "3. NEVER pay to receive money — release fees, withdrawal taxes, admin fees, "
            "training fees. Paying to get paid is the scam's signature.\n"
            "4. URGENCY IS A WEAPON. 'Act now or lose it' exists to stop you thinking. "
            "Real opportunities survive a 48-hour pause.\n"
            "5. VERIFY INDEPENDENTLY. Look up the official number or site yourself — never "
            "use contact details from the message. Check FSCA (investments) and NCR (loans) "
            "registrations.\n\n"
            + REPORT_LINE
        ),
    },
]
_TOPIC_INDEX = {t["id"]: t for t in TOPICS}


# ── Schemas ──────────────────────────────────────────────────────────────

class ScamCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    context: Optional[str] = Field(
        default=None, max_length=200,
        description="Optional hint, e.g. 'whatsapp message', 'email', 'phone call'.",
    )


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/topics")
async def list_topics() -> Dict[str, Any]:
    """Index of financial-literacy education topics."""
    return {
        "topics": [
            {"id": t["id"], "title": t["title"], "minutes": t["minutes"]} for t in TOPICS
        ],
        "disclaimer": DISCLAIMER,
    }


@router.get("/topics/{topic_id}")
async def topic_detail(topic_id: str) -> Dict[str, Any]:
    """Full lesson content for one topic. Always carries the disclaimer."""
    topic = _TOPIC_INDEX.get(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found.")
    return {**topic, "disclaimer": DISCLAIMER}


@router.get("/scam-patterns")
async def scam_patterns() -> Dict[str, Any]:
    """The versioned scam-detection catalogue (defensive content — public by design)."""
    data = _load_patterns()
    return {
        "version": data["version"],
        "updated": data["updated"],
        "patterns": [
            {k: p[k] for k in ("id", "name", "category", "severity", "description", "sa_example", "advice")}
            for p in data["patterns"]
        ],
        "report_line": REPORT_LINE,
        "disclaimer": DISCLAIMER,
    }


@router.post("/scam-check")
async def scam_check(req: ScamCheckRequest) -> Dict[str, Any]:
    """Deterministic scam-pattern analysis. No LLM, no storage, fully offline.

    Scoring: sum of matched pattern severities + 1 per extra hit beyond the
    first in each pattern. Bands: 0 none / 1-3 low / 4-7 medium / 8-12 high /
    13+ critical.
    """
    data = _load_patterns()
    matches = []
    score = 0
    for p in data["patterns"]:
        hits = 0
        hit_terms = []
        for ind in p["indicators"]:
            found = _compile(ind).findall(req.text)
            if found:
                hits += len(found)
                hit_terms.append(ind)
        if hits:
            weight = p["severity"] + (hits - 1)
            score += weight
            matches.append({
                "pattern_id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "matched_indicators": hit_terms,
                "weight": weight,
                "description": p["description"],
                "sa_example": p["sa_example"],
                "advice": p["advice"],
            })
    matches.sort(key=lambda m: -m["weight"])

    risk = "critical"
    for ceiling, label in _RISK_BANDS:
        if score <= ceiling:
            risk = label
            break

    verdict = {
        "none": "No known scam patterns detected. Stay alert anyway — new scams appear daily.",
        "low": "Weak signals only. Verify independently before acting.",
        "medium": "Caution: this matches known scam patterns. Do not pay or share details until independently verified.",
        "high": "WARNING: strong match to known scam patterns. Do not send money or personal information.",
        "critical": "SCAM ALERT: this matches multiple severe fraud patterns. Stop all contact, send nothing, and report it.",
    }[risk]

    return {
        "risk_level": risk,
        "risk_score": score,
        "verdict": verdict,
        "matched_patterns": matches,
        "golden_rules": [
            "Guaranteed returns do not exist.",
            "Never share OTPs, PINs, or passwords.",
            "Never pay to receive money.",
            "Urgency is a weapon — pause 48 hours.",
            "Verify independently (FSCA for investments, NCR for loans).",
        ],
        "report_line": REPORT_LINE if score > 0 else None,
        "disclaimer": DISCLAIMER,
    }
