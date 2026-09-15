"""
OMEGA-LUQI Skill Engine - trade gap analysis + structured-submission verification.

Two honest capabilities:
  1. GAP ANALYSIS: user skills vs a trade's required-skill registry
     (African TVET trades), producing readiness % and an experience-project
     roadmap. "Market telemetry" is a VERSIONED REGISTRY with an admin refresh
     path - live job-board feeds are documented future work, not faked.
  2. STRUCTURED-SUBMISSION CHECKS: heuristic validators for document-style
     evidence (wiring plans, quotes, campaign structures) that regex-check
     required structural elements.

IMPORTANT HONESTY NOTE: these validators raise the bar - they do NOT prove
competence and do not "defeat resume inflation". A determined user can paste
keywords. Real competency sign-off remains with the institution; practical
trades should additionally use the dev-verify sandbox (code) or human assessors.
"""
import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import LuqiAuthManager, UserSessionProfile
from .admin_auth import verify_admin
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/skills", tags=["Skill Engine"])

# ---------------- trade registry (versioned; admin-refreshable) ----------------
TRADE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "electrician": {
        "required_skills": ["AC Theory", "Three-Phase Systems", "SANS 10142 Wiring",
                            "Earth Leakage Protection", "Motor Control"],
        "experience_projects": {
            "SANS 10142 Wiring": "Wire a complete distribution board with earth-leakage protection; test and document per SANS 10142.",
            "Three-Phase Systems": "Build a star-delta motor starter panel and produce a commissioning report.",
        },
        "demand": "HIGH",
    },
    "fitter_and_turner": {
        "required_skills": ["Lathe Operations", "Milling", "Engineering Drawing",
                            "Metrology", "Hydraulics"],
        "experience_projects": {
            "Lathe Operations": "Turn a shaft to ±0.02mm tolerance; record measurements with a micrometer log.",
        },
        "demand": "STEADY",
    },
    "plumber": {
        "required_skills": ["Drainage Design", "Geyser Installation", "SANS 10252",
                            "Brazing", "Rainwater Harvesting"],
        "experience_projects": {
            "Geyser Installation": "Produce a full geyser installation plan including vacuum breakers and safety valve sizing.",
        },
        "demand": "HIGH",
    },
    "bricklayer": {
        "required_skills": ["Mortar Mixes", "Setting Out", "SANS 10400",
                            "Plastering", "Arches and Lintels"],
        "experience_projects": {
            "Setting Out": "Set out a single-storey building footprint from a plan using a builder's square and profiles.",
        },
        "demand": "STEADY",
    },
    "solar_technician": {
        "required_skills": ["PV Array Design", "Inverters", "Battery Storage",
                            "Net Metering", "SANS 10142"],
        "experience_projects": {
            "PV Array Design": "Size a 5kW residential array for Johannesburg; produce panel layout, string sizing and inverter selection sheet.",
        },
        "demand": "CRITICAL",
    },
    "software_dev": {
        "required_skills": ["Python", "SQL", "Git", "APIs", "Docker"],
        "experience_projects": {
            "Docker": "Containerize a small API and document the build.",
            "SQL": "Design and query a normalized schema for a school records system.",
        },
        "demand": "HIGH",
    },
    "data_analyst": {
        "required_skills": ["SQL", "Spreadsheets", "Statistics", "Visualization", "Python"],
        "experience_projects": {},
        "demand": "HIGH",
    },
}


# ---------------- heuristic validators (structured-submission checks) ----------------
def _rx(pattern: str, flags=re.IGNORECASE):
    return re.compile(pattern, flags)


VALIDATORS: Dict[str, Dict[str, Any]] = {
    "Electrical Installation Plan": {
        "checks": [
            ("distribution board", _rx(r"\b(db|distribution\s+board)\b")),
            ("earth leakage", _rx(r"earth\s+leakage")),
            ("SANS 10142 reference", _rx(r"sans\s*10142")),
        ],
        "doc": "Wiring plan must reference the DB, earth-leakage protection and SANS 10142.",
    },
    "Plumbing Quote": {
        "checks": [
            ("materials list", _rx(r"\b(material|pipe|fitting)s?\b")),
            ("labour line", _rx(r"labo[u]?r")),
            ("VAT", _rx(r"\bvat\b")),
        ],
        "doc": "Quote must include materials, labour and VAT.",
    },
    "Solar Array Design": {
        "checks": [
            ("panels", _rx(r"\b(pv|panel)s?\b")),
            ("inverter", _rx(r"inverter")),
            ("capacity", _rx(r"\b\d+\.?\d*\s*(kw|kwh)\b")),
        ],
        "doc": "Design must state panels, inverter and capacity in kW/kWh.",
    },
    "Marketing Campaign Structure": {
        "checks": [
            ("performance metric", _rx(r"\b(roas|roi)\b[:\s]*[1-9]\d*(\.\d+)?\s*[%x]?")),
            ("funnel element", _rx(r"\b(tof|mof|bof|lookalike|retargeting)\b")),
            ("budget figure", _rx(r"\b(budget|spend)\b[:\s]*\$?\d+")),
        ],
        "doc": "Campaign structure must state a ROAS/ROI target, funnel element and budget.",
    },
    "Balance Sheet": {
        "checks": [
            ("assets", _rx(r"\b(total\s+)?assets\b")),
            ("liabilities", _rx(r"\b(total\s+)?liabilit(?:y|ies)\b")),
            ("equity", _rx(r"\b(shareholder[s']?\s+)?equity\b")),
            ("formula", None),  # special-cased below
        ],
        "doc": "Sheet must declare assets, liabilities, equity and contain a formula.",
    },
}


def verify_submission(skill: str, submission: str) -> Dict[str, Any]:
    """Run the structured-submission check. Returns matched/missing criteria.
    Honest label: NOT a competence verdict."""
    spec = VALIDATORS.get(skill)
    if not spec:
        return {"skill": skill, "checkable": False,
                "note": "no heuristic validator for this skill - use sandbox or human assessment"}
    text = scrub_pii(submission)
    matched, missing = [], []
    for name, pattern in spec["checks"]:
        if pattern is None:  # formula special case
            ok = "=" in text or "SUM" in text or "NPV" in text
        else:
            ok = bool(pattern.search(text))
        (matched if ok else missing).append(name)
    passed = not missing
    return {"skill": skill, "checkable": True, "passed": passed,
            "matched": matched, "missing": missing, "doc": spec["doc"],
            "honesty_note": "structured-submission check only - not proof of competence"}


# ---------------- profile store (thread-safe; optional JSON persistence) ----------------
_lock = threading.Lock()
_profiles: Dict[str, Dict[str, Any]] = {}
_DB_PATH = os.getenv("SKILL_DB_PATH", "")  # set to persist profiles across restarts


def _load():
    global _profiles
    if _DB_PATH and os.path.exists(_DB_PATH):
        try:
            _profiles = json.load(open(_DB_PATH))
        except (OSError, json.JSONDecodeError):
            _profiles = {}


def _save():
    if _DB_PATH:
        try:
            json.dump(_profiles, open(_DB_PATH, "w"))
        except OSError:
            pass


_load()


def get_profile(user_id: str) -> Dict[str, Any]:
    with _lock:
        return dict(_profiles.get(user_id, {"verified_skills": [], "projects": [],
                                            "hours": 0, "registered_trades": []}))


def gap_analysis(skills: List[str], trade: str) -> Dict[str, Any]:
    t = trade.lower().strip().replace(" ", "_").replace("-", "_")
    spec = TRADE_REGISTRY.get(t)
    if not spec:
        raise HTTPException(status_code=404,
                            detail=f"trade '{trade}' not in registry. Available: {sorted(TRADE_REGISTRY)}")
    required = spec["required_skills"]
    have = {s.lower() for s in skills}
    missing = [s for s in required if s.lower() not in have]
    readiness = (len(required) - len(missing)) / len(required)
    projects = spec["experience_projects"]
    roadmap = [{"skill": s, "project": projects.get(s, "Structured practice project with assessor sign-off.")}
               for s in missing]
    return {"trade": t, "readiness_pct": round(readiness * 100, 1),
            "demand": spec["demand"], "missing_skills": missing,
            "roadmap": roadmap,
            "telemetry_note": "registry is versioned data; live job-board feeds are future work"}


def record_verified(user_id: str, skill: str, submission_excerpt: str) -> Dict[str, Any]:
    credential = hashlib.sha256(f"{user_id}|{skill}|{time.time()}".encode()).hexdigest()[:16]
    with _lock:
        p = _profiles.setdefault(user_id, {"verified_skills": [], "projects": [],
                                           "hours": 0, "registered_trades": []})
        if skill not in p["verified_skills"]:
            p["verified_skills"].append(skill)
            p["hours"] += 40
        p["projects"].append({"skill": skill, "credential": credential,
                              "excerpt": submission_excerpt[:60],
                              "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        _save()
    # Real-time student notification (fire-and-forget; never blocks the unlock)
    try:
        import asyncio
        from .progress_alerts import notify_module_unlock
        from .auth import UserSessionProfile as _USP
        import uuid as _uuid
        profile = _USP(user_id=_uuid.UUID(user_id) if len(user_id) == 36 else _uuid.UUID(int=0),
                       email="student@luqi.ai", country_code="ZAF", tier="tvet")
        asyncio.get_running_loop().create_task(
            notify_module_unlock(profile, skill, len(p["verified_skills"]), p["hours"]))
    except Exception:
        pass
    return {"credential": credential, "verified_skills": p["verified_skills"], "hours": p["hours"]}


# ---------------- certificate authority (shareable proof) ----------------
# Signing salt comes from env ONLY - a hardcoded salt in source is worthless.
_cert_ledger: Dict[str, Dict[str, Any]] = {}
_cert_lock = threading.Lock()


def _signing_salt() -> str:
    salt = os.getenv("CERT_SIGNING_SALT", "")
    if not salt:
        raise HTTPException(status_code=503,
                            detail="CERT_SIGNING_SALT not set - credential signing disabled")
    return salt


def issue_certificate(user_id: str, trade: str) -> Dict[str, Any]:
    """Issue a shareable credential ONLY at 100% live readiness (recomputed now,
    not read from a stored index that could drift)."""
    salt = _signing_salt()
    profile = get_profile(user_id)
    analysis = gap_analysis(profile["verified_skills"], trade)  # raises 404 on unknown trade
    if analysis["readiness_pct"] < 100.0:
        return {"eligible": False,
                "reason": f"readiness {analysis['readiness_pct']}% - 100% required",
                "missing_skills": analysis["missing_skills"]}
    t = trade.lower().strip().replace(" ", "_").replace("-", "_")
    issued = int(time.time())
    digest = hashlib.sha256(f"{user_id}|{t}|{issued}|{salt}".encode()).hexdigest()
    cert_id = f"CERT-{user_id.upper()}-{issued % 100000}"
    base = os.getenv("PUBLIC_BASE_URL", "https://api.luqi-ai.org")
    payload = {"certificate_id": cert_id, "user_ref": user_id[:8], "user_id": user_id,
               "trade": t.upper().replace("_", " "),
               "verification_hash": digest,
               "verification_url": f"{base}/v1/skills/certificate/{cert_id}",
               "issued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(issued)),
               "scope_note": "structured-submission track - practical assessment by institution"}
    with _cert_lock:
        _cert_ledger[cert_id] = payload
        _save_ledger()
    return {"eligible": True, **payload}


def _ledger_path() -> str:
    return os.getenv("SKILL_DB_PATH", "") and os.path.join(
        os.path.dirname(_DB_PATH) if _DB_PATH else "", "cert_ledger.json") or ""


def _save_ledger():
    path = _ledger_path()
    if path:
        try:
            json.dump(_cert_ledger, open(path, "w"))
        except OSError:
            pass


def _load_ledger():
    global _cert_ledger
    path = _ledger_path()
    if path and os.path.exists(path):
        try:
            _cert_ledger = json.load(open(path))
        except (OSError, json.JSONDecodeError):
            _cert_ledger = {}


_load_ledger()


def verify_certificate(cert_id: str) -> Dict[str, Any]:
    with _cert_lock:
        return dict(_cert_ledger.get(cert_id, {}))


# ---------------- endpoints ----------------
class RegisterTrade(BaseModel):
    trade: str


class VerifyRequest(BaseModel):
    skill: str
    submission: str = Field(min_length=10)


@router.post("/register")
async def register_trade(req: RegisterTrade,
                         user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    t = req.trade.lower().strip().replace(" ", "_").replace("-", "_")
    if t not in TRADE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"unknown trade: {sorted(TRADE_REGISTRY)}")
    with _lock:
        p = _profiles.setdefault(str(user.user_id), {"verified_skills": [], "projects": [],
                                                     "hours": 0, "registered_trades": []})
        if t not in p["registered_trades"]:
            p["registered_trades"].append(t)
        _save()
    return {"registered": t}


@router.get("/gap-analysis")
async def analyse(trade: str,
                  user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    profile = get_profile(str(user.user_id))
    return gap_analysis(profile["verified_skills"], trade)


@router.post("/verify")
async def verify(req: VerifyRequest,
                 user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    result = verify_submission(req.skill, req.submission)
    if result.get("passed"):
        cred = record_verified(str(user.user_id), req.skill, req.submission)
        result.update(cred)
    return result


@router.get("/profile")
async def profile(user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    return get_profile(str(user.user_id))


@router.post("/certificate/issue")
async def issue_cert(req: RegisterTrade,
                     user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """Issue a shareable credential at 100% readiness. Fail-closed without salt."""
    return issue_certificate(str(user.user_id), req.trade)


@router.get("/certificate/{cert_id}")
async def verify_cert(cert_id: str):
    """PUBLIC verification endpoint - the whole point is employers check without auth."""
    payload = verify_certificate(cert_id)
    if not payload:
        raise HTTPException(status_code=404, detail="certificate not found")
    return payload


@router.get("/certificates")
async def my_certificates(user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """The caller's issued certificates, for the dashboard."""
    uid = str(user.user_id)
    with _cert_lock:
        mine = [dict(v) for v in _cert_ledger.values() if v.get("user_id") == uid]
    mine.sort(key=lambda c: c.get("issued_at", ""), reverse=True)
    return {"certificates": mine}


@router.get("/registry")
async def registry(is_authenticated: bool = Depends(verify_admin)):
    return {"trades": sorted(TRADE_REGISTRY),
            "validators": sorted(VALIDATORS),
            "telemetry_note": "versioned registry; live feeds documented as future work"}


@router.post("/registry/reload")
async def reload_registry(is_authenticated: bool = Depends(verify_admin)):
    """Future: pull trade registry from a curated feed. Currently documents the path."""
    return {"reloaded": False,
            "note": "registry is bundled data; wire a curated market feed here when one is vetted"}
