"""
OMEGA-LUQI Submission Consensus - independent checks must agree.

The honest core of "multi-agent consensus": not personas, but INDEPENDENT
validators voting on a submission, with a tie meaning "human review" -
never a blind pass, never a harsh auto-reject of a student.

Three independent checks (any disagreement -> needs_human_review):
  1. VALIDATOR  - the skill's registered heuristic (core/skill_engine)
  2. STRUCTURAL - content-quality pass: minimum unique-token diversity and
                  not a verbatim copy of the validator's own documentation
                  (catches keyword-stuffing the regex)
  3. SAFETY     - injection/guardrail patterns (shared with hybrid_ai)

Works for EVERY registered skill - no hardcoded trade names.
"""
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .skill_engine import VALIDATORS, verify_submission

router = APIRouter(prefix="/v1/skills", tags=["Submission Consensus"])

SAFETY_PATTERNS = [r"drop table", r"union select", r"';", r"--", r"ignore previous instructions"]


class ConsensusRequest(BaseModel):
    skill: str
    submission: str


def structural_check(submission: str, skill: str) -> Dict[str, Any]:
    """Content-quality pass: diversity + not a copy of the validator docs."""
    text = submission.strip()
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    unique_ratio = len(set(tokens)) / max(1, len(tokens))
    doc_copy = False
    spec = VALIDATORS.get(skill)
    if spec:
        doc_text = " ".join(name + " " + spec["doc"] for name, _ in spec["checks"])
        # if the submission is mostly the validator's own documentation words, suspicious
        overlap = sum(1 for t in set(tokens) if t in doc_text.lower())
        doc_copy = len(set(tokens)) > 0 and overlap / len(set(tokens)) > 0.85 and len(tokens) < 40
    ok = len(tokens) >= 5 and unique_ratio >= 0.55 and not doc_copy
    return {"passed": ok, "unique_ratio": round(unique_ratio, 2), "doc_copy": doc_copy}


def safety_check(submission: str) -> Dict[str, Any]:
    low = submission.lower()
    hits = [p for p in SAFETY_PATTERNS if re.search(p, low)]
    return {"passed": not hits, "hits": hits}


def consensus_verify(skill: str, submission: str) -> Dict[str, Any]:
    """Three independent checks; agreement required, disagreement -> human review."""
    validator = verify_submission(skill, submission)
    structural = structural_check(submission, skill)
    safety = safety_check(submission)

    votes = {
        "validator": bool(validator.get("passed")),
        "structural": structural["passed"],
        "safety": safety["passed"],
    }
    checks = {"validator": validator, "structural": structural, "safety": safety}

    if all(votes.values()):
        return {"consensus": True, "verdict": "approved", "votes": votes, "checks": checks}
    if not votes["safety"]:
        return {"consensus": False, "verdict": "blocked_unsafe",
                "votes": votes, "checks": checks}
    return {"consensus": False, "verdict": "needs_human_review",
            "votes": votes, "checks": checks,
            "note": "Independent checks disagreed - route to an assessor rather than auto-judging a student."}


@router.post("/verify-consensus")
async def verify_with_consensus(req: ConsensusRequest,
                                user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """Consensus verification across independent checks. Auth-gated (JWT, not headers)."""
    return consensus_verify(req.skill, req.submission)
