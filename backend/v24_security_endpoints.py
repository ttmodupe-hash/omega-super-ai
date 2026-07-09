#!/usr/bin/env python3
"""
Luqi AI v24.4 - IT Security Training Academy Endpoints
=======================================================
24 REST API endpoints for the security training platform.

Part of Luqi AI v24.4.0 — Built by Limitless Telecoms
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Import the security training module
try:
    from backend.it_security_training import (
        get_all_courses, get_course, enroll_user, get_user_progress,
        update_lesson_progress, submit_lab, submit_quiz, generate_certificate,
        get_skill_tree, get_leaderboard, search_courses, get_recommended_courses,
        create_ctf_challenge, verify_ctf_flag, get_all_modules_for_course,
        get_lessons_for_module, get_labs_for_module, get_quiz_for_module,
        take_skill_assessment, get_platform_stats,
    )
    SECURITY_TRAINING_AVAILABLE = True
except ImportError as e:
    SECURITY_TRAINING_AVAILABLE = False
    logger.warning("IT Security Training module not available: %s", e)

# Import shared app
from backend.router import app


def _check_available():
    if not SECURITY_TRAINING_AVAILABLE:
        raise HTTPException(status_code=503, detail="IT Security Training module not available")


def _security_response(data: Any, meta: dict = None) -> JSONResponse:
    body = {"data": data, "module": "it_security_training", "timestamp": datetime.utcnow().isoformat()}
    if meta:
        body["meta"] = meta
    return JSONResponse(body)


SECURITY_ENDPOINT_REGISTRY = []


def _register(method: str, path: str, handler: str):
    SECURITY_ENDPOINT_REGISTRY.append({"method": method, "path": path, "handler": handler})


# ═══════════════════════════════════════════════════════════════════
# COURSE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/courses")
async def api_security_courses_list():
    """List all IT security training courses."""
    _check_available()
    try:
        courses = get_all_courses()
        _register("GET", "/api/security/courses", "api_security_courses_list")
        return _security_response(courses, {"count": len(courses)})
    except Exception as e:
        logger.error("Error listing security courses: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/courses/{course_id}")
async def api_security_course_get(course_id: str):
    """Get a specific course with full details."""
    _check_available()
    try:
        course = get_course(course_id)
        if not course:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")
        return _security_response(course)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting course %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/courses/{course_id}/enroll")
async def api_security_course_enroll(course_id: str, request: Request):
    """Enroll a user in a course."""
    _check_available()
    try:
        data = json.loads(await request.body())
        user_id = data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        result = enroll_user(user_id, course_id)
        return _security_response(result)
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error enrolling in course %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/courses/search")
async def api_security_courses_search(q: str = "", category: str = None, difficulty: str = None):
    """Search and filter courses."""
    _check_available()
    try:
        results = search_courses(q, category=category, difficulty=difficulty)
        return _security_response(results, {"query": q, "category": category, "difficulty": difficulty})
    except Exception as e:
        logger.error("Error searching courses: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# CONTENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/modules/{course_id}")
async def api_security_modules_get(course_id: str):
    """Get all modules for a course."""
    _check_available()
    try:
        modules = get_all_modules_for_course(course_id)
        return _security_response(modules)
    except Exception as e:
        logger.error("Error getting modules for %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/lessons/{module_id}")
async def api_security_lessons_get(module_id: str):
    """Get all lessons for a module."""
    _check_available()
    try:
        lessons = get_lessons_for_module(module_id)
        return _security_response(lessons)
    except Exception as e:
        logger.error("Error getting lessons for %s: %s", module_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/labs/{module_id}")
async def api_security_labs_get(module_id: str):
    """Get all labs for a module."""
    _check_available()
    try:
        labs = get_labs_for_module(module_id)
        return _security_response(labs)
    except Exception as e:
        logger.error("Error getting labs for %s: %s", module_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/quiz/{module_id}")
async def api_security_quiz_get(module_id: str):
    """Get quiz for a module."""
    _check_available()
    try:
        quiz = get_quiz_for_module(module_id)
        return _security_response(quiz)
    except Exception as e:
        logger.error("Error getting quiz for %s: %s", module_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# PROGRESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/progress/{user_id}")
async def api_security_progress_get(user_id: str, course_id: str = None):
    """Get user progress for a course or all courses."""
    _check_available()
    try:
        if course_id:
            progress = get_user_progress(user_id, course_id)
        else:
            from backend.it_security_training import _user_progress_db
            progress = {}
            for cid in _user_progress_db:
                if user_id in _user_progress_db.get(cid, {}):
                    progress[cid] = get_user_progress(user_id, cid)
        return _security_response(progress)
    except Exception as e:
        logger.error("Error getting progress for %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/progress/lesson")
async def api_security_progress_lesson(request: Request):
    """Mark a lesson as complete."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = update_lesson_progress(
            data.get("user_id"), data.get("course_id"),
            data.get("module_id"), data.get("lesson_id"),
        )
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error updating lesson progress: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# ASSESSMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/security/labs/submit")
async def api_security_lab_submit(request: Request):
    """Submit a lab for grading."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = submit_lab(data.get("user_id"), data.get("lab_id"), data.get("submission", {}))
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error submitting lab: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/quiz/submit")
async def api_security_quiz_submit(request: Request):
    """Submit a quiz for grading."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = submit_quiz(data.get("user_id"), data.get("quiz_id"), data.get("answers", {}))
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error submitting quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/assessment")
async def api_security_assessment(request: Request):
    """Take a skill assessment."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = take_skill_assessment(data.get("user_id"), data.get("answers", {}))
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error processing assessment: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# CERTIFICATE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/certificates/{user_id}")
async def api_security_certificates_get(user_id: str):
    """Get all certificates for a user."""
    _check_available()
    try:
        from backend.it_security_training import _user_certificates
        certs = _user_certificates.get(user_id, [])
        return _security_response(certs)
    except Exception as e:
        logger.error("Error getting certificates for %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/certificates/generate")
async def api_security_certificate_generate(request: Request):
    """Generate a certificate for course completion."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = generate_certificate(data.get("user_id"), data.get("course_id"))
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error generating certificate: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# SKILL TREE & LEADERBOARD
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/skill-tree/{user_id}")
async def api_security_skill_tree_get(user_id: str):
    """Get user's skill tree with badges and levels."""
    _check_available()
    try:
        tree = get_skill_tree(user_id)
        return _security_response(tree)
    except Exception as e:
        logger.error("Error getting skill tree for %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/badges/{user_id}")
async def api_security_badges_get(user_id: str):
    """Get user badges."""
    _check_available()
    try:
        tree = get_skill_tree(user_id)
        return _security_response(tree.get("badges", []))
    except Exception as e:
        logger.error("Error getting badges for %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/leaderboard")
async def api_security_leaderboard(limit: int = 50):
    """Get global leaderboard."""
    _check_available()
    try:
        board = get_leaderboard(limit=limit)
        return _security_response(board)
    except Exception as e:
        logger.error("Error getting leaderboard: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/leaderboard/{course_id}")
async def api_security_leaderboard_course(course_id: str, limit: int = 50):
    """Get course-specific leaderboard."""
    _check_available()
    try:
        board = get_leaderboard(course_id=course_id, limit=limit)
        return _security_response(board)
    except Exception as e:
        logger.error("Error getting leaderboard for %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/recommendations/{user_id}")
async def api_security_recommendations_get(user_id: str):
    """Get recommended courses for a user."""
    _check_available()
    try:
        recs = get_recommended_courses(user_id)
        return _security_response(recs)
    except Exception as e:
        logger.error("Error getting recommendations for %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# CTF ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/security/ctf/challenge")
async def api_security_ctf_challenge(request: Request):
    """Create a CTF challenge."""
    _check_available()
    try:
        data = json.loads(await request.body())
        challenge = create_ctf_challenge(data.get("difficulty", "medium"), data.get("category"))
        return _security_response(challenge)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error creating CTF challenge: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/ctf/verify")
async def api_security_ctf_verify(request: Request):
    """Verify a CTF flag."""
    _check_available()
    try:
        data = json.loads(await request.body())
        result = verify_ctf_flag(data.get("challenge_id"), data.get("flag"))
        return _security_response(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error("Error verifying CTF flag: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/security/ctf/leaderboard")
async def api_security_ctf_leaderboard(limit: int = 50):
    """Get CTF leaderboard."""
    _check_available()
    try:
        from backend.it_security_training import _ctf_submissions
        scores = {}
        for sub in _ctf_submissions:
            uid = sub.get("user_id")
            if uid and sub.get("correct"):
                scores.setdefault(uid, {"points": 0, "solved": 0})
                scores[uid]["points"] += sub.get("points", 100)
                scores[uid]["solved"] += 1
        board = sorted(
            [{"user_id": k, **v} for k, v in scores.items()],
            key=lambda x: x["points"], reverse=True
        )[:limit]
        return _security_response(board)
    except Exception as e:
        logger.error("Error getting CTF leaderboard: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/security/stats")
async def api_security_stats():
    """Get platform statistics."""
    _check_available()
    try:
        stats = get_platform_stats()
        return _security_response(stats)
    except Exception as e:
        logger.error("Error getting security stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("IT Security Training endpoints registered: %d endpoints", len(SECURITY_ENDPOINT_REGISTRY))
