"""
OMEGA-LUQI Code Integrity & Plagiarism Engine

Local lexical analysis (AST node-shape fingerprint - immune to variable
renaming) plus a Kimi K3 heuristic similarity review. Auth-gated (token cost),
fail-closed without KIMI_API_KEY.

Honesty labels: the similarity score is an LLM HEURISTIC, not proof. Local
fingerprint equality is the deterministic signal; the AI output is advisory
feedback for educators, not an automated verdict.
"""
import ast
import asyncio
import hashlib
import json
from typing import Any, Dict
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .kimi_parse import extract_assistant_content
from .pii_scrub import scrub_pii

integrity_router = APIRouter(prefix="/v1/integrity", tags=["Code Integrity & Plagiarism Engine"])

_RUN_STATS = {"checks": 0, "failures": 0}


class SubmissionSchema(BaseModel):
    lab_id: UUID
    student_id: UUID
    submitted_source_code: str


def structural_fingerprint(source_code: str) -> str:
    """AST node-shape fingerprint.

    FIXED: the pasted code used Python's built-in hash(), which is randomized
    per process (PYTHONHASHSEED) - the same submission would fingerprint
    differently on every server restart. SHA-256 is deterministic across
    processes and machines - comparable across the whole fleet and over time.
    """
    try:
        tree = ast.parse(source_code)
        shapes = [type(node).__name__ for node in ast.walk(tree)]
        joined = ",".join(shapes).encode()
        return hashlib.sha256(joined).hexdigest()
    except SyntaxError:
        return "SYNTAX_ERROR_MALFORMED_CODE"


DIRECTIVE = (
    "You are the senior Luqi-AI Code Integrity Examiner. Assess the submission for "
    "architectural plagiarism (copy-paste templates, near-verbatim public sources). "
    "Output strictly valid JSON with keys: 'similarity_percentage_score' (0-100 heuristic), "
    "'plagiarism_flags_detected' (boolean), 'jarvis_remedial_feedback' (constructive guidance)."
)


def _call_integrity_engine(schema: SubmissionSchema) -> Dict[str, Any]:
    """Unified client: structural fingerprint + advisory similarity review."""
    from .kimi_client import chat_completion
    fingerprint = structural_fingerprint(schema.submitted_source_code)
    content = chat_completion(
        DIRECTIVE,
        scrub_pii(f"Structural fingerprint (SHA-256 of AST shapes): {fingerprint}\n\n"
                  f"Raw submission:\n{schema.submitted_source_code[:8000]}"),
        timeout=30,
    )
    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        analysis = {"raw_review": content}
    from .contracts import check_contract
    check_contract("integrity", analysis if isinstance(analysis, dict) else {})
    return {
        "status": "success",
        "lab_id": str(schema.lab_id),
        "local_structural_fingerprint": fingerprint,
        "analysis_kind": "llm_heuristic_advisory",
        "analysis": analysis,
    }


@integrity_router.post("/verify-submission")
async def verify_lab_submission_integrity(
    submission: SubmissionSchema,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Structural + heuristic integrity check. Advisory - educators decide."""
    try:
        result = await asyncio.to_thread(_call_integrity_engine, submission)
        _RUN_STATS["checks"] += 1
        return result
    except requests.exceptions.RequestException as e:
        _RUN_STATS["failures"] += 1
        raise HTTPException(status_code=503, detail=f"Plagiarism Pipeline Bridge Failure: {e}")


@integrity_router.get("/stats")
async def integrity_stats():
    return dict(_RUN_STATS)
