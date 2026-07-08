#!/usr/bin/env python3
"""Luqi AI v23 -- Network & AI Engineering Training Endpoints
=============================================================
Endpoints for the Network & AI Engineering Training Platform covering
curriculum & content, hands-on labs, topology generation & simulation,
scenario injection & grading, device simulation, packet tracing,
telemetry collection, quizzes, AI mentoring, progress tracking,
leaderboards, and certificate generation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Curriculum & Content Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/netai/curriculum")
async def api_netai_curriculum():
    """Retrieve the full Network & AI Engineering training curriculum."""
    try:
        from backend.netai_training import get_curriculum
        result = get_curriculum()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Curriculum retrieval error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/curriculum/{phase_id}")
async def api_netai_curriculum_phase(phase_id: str):
    """Retrieve details for a specific training phase by its ID."""
    try:
        from backend.netai_training import get_phase
        result = get_phase(phase_id=phase_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Phase retrieval error for phase_id=%s: %s", phase_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/curriculum/{phase_id}/modules/{module_id}")
async def api_netai_curriculum_module(phase_id: str, module_id: str):
    """Retrieve a specific module within a training phase."""
    try:
        from backend.netai_training import get_module
        result = get_module(module_id=module_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Module retrieval error for module_id=%s: %s", module_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/explain/{concept}")
async def api_netai_explain_concept(
    concept: str,
    level: str = Query("intermediate")
):
    """Get an AI-generated explanation of a network or AI concept at a given level."""
    try:
        from backend.netai_training import explain_concept
        result = explain_concept(concept=concept, level=level)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Concept explanation error for concept=%s: %s", concept, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Labs Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/netai/labs")
async def api_netai_labs_list(
    filters: str = Query(""),
    difficulty: str = Query(""),
    topic: str = Query("")
):
    """List all available hands-on labs, optionally filtered."""
    try:
        from backend.netai_training import list_labs
        result = list_labs(filters=filters, difficulty=difficulty, topic=topic)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Labs list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/labs/{lab_id}/start")
async def api_netai_lab_start(lab_id: str, request: Request):
    """Start a new lab session for a student."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import start_lab
        result = start_lab(
            student_id=data.get("student_id", ""),
            lab_id=lab_id
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lab start error for lab_id=%s: %s", lab_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/labs/{session_id}")
async def api_netai_lab_status(session_id: str):
    """Get the current status of an active lab session."""
    try:
        from backend.netai_training import get_lab_status
        result = get_lab_status(session_id=session_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lab status error for session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/labs/{session_id}/submit")
async def api_netai_lab_submit(session_id: str, request: Request):
    """Submit a completed lab for grading and feedback."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import submit_lab
        result = submit_lab(
            session_id=session_id,
            submission=data.get("submission", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lab submission error for session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/labs/{session_id}/hint")
async def api_netai_lab_hint(session_id: str, request: Request):
    """Request a hint for the current lab session at a specified level."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import get_hint
        result = get_hint(
            session_id=session_id,
            hint_level=data.get("hint_level", 1)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lab hint error for session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/labs/{session_id}/reset")
async def api_netai_lab_reset(session_id: str):
    """Reset a lab session to its initial state."""
    try:
        from backend.netai_training import reset_lab
        result = reset_lab(session_id=session_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lab reset error for session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Topology & Simulation Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/netai/topology/generate")
async def api_netai_topology_generate(request: Request):
    """Generate a network topology from a natural language prompt."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import generate_topology
        result = generate_topology(
            prompt=data.get("prompt", ""),
            platform=data.get("platform", "cisco")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Topology generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/topology/build")
async def api_netai_topology_build(request: Request):
    """Build a network topology in the simulator from a type and parameters."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import build_topology
        result = build_topology(
            topology_type=data.get("topology_type", ""),
            params=data.get("params", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Topology build error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/topology/{topology_id}")
async def api_netai_topology_get(topology_id: str):
    """Retrieve the current state of a simulated topology by ID."""
    try:
        from backend.netai_simulator import get_topology
        result = get_topology(topology_id=topology_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Topology get error for topology_id=%s: %s", topology_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/topology/validate")
async def api_netai_topology_validate(request: Request):
    """Validate a network topology for correctness and best practices."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import validate_topology
        result = validate_topology(topology=data.get("topology", {}))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Topology validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Scenarios & Grading Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/netai/scenario/inject")
async def api_netai_scenario_inject(request: Request):
    """Inject a fault or attack scenario into an existing topology."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import inject_scenario
        result = inject_scenario(
            topology_id=data.get("topology_id", ""),
            type=data.get("type", ""),
            difficulty=data.get("difficulty", "medium")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Scenario injection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/scenario/verify")
async def api_netai_scenario_verify(request: Request):
    """Verify a student's fix for an injected scenario."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import verify_fix
        result = verify_fix(
            scenario_id=data.get("scenario_id", ""),
            student_config=data.get("student_config", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Scenario verification error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/grade")
async def api_netai_grade(request: Request):
    """Grade a student submission with detailed AI feedback."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import grade_submission
        result = grade_submission(submission=data)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Grading error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Device Simulation Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/netai/devices")
async def api_netai_device_create(request: Request):
    """Create a new simulated network device."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import create_device
        result = create_device(
            hostname=data.get("hostname", ""),
            platform=data.get("platform", "cisco_ios"),
            role=data.get("role", "router")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Device creation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/devices/{device_id}")
async def api_netai_device_get(device_id: str):
    """Get the current state of a simulated network device."""
    try:
        from backend.netai_simulator import get_device_state
        result = get_device_state(device_id=device_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Device state error for device_id=%s: %s", device_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/devices/{device_id}/command")
async def api_netai_device_command(device_id: str, request: Request):
    """Send a CLI command to a simulated network device."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import send_command
        result = send_command(
            device_id=device_id,
            command=data.get("command", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Device command error for device_id=%s: %s", device_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/devices/validate-config")
async def api_netai_device_validate_config(request: Request):
    """Validate a device configuration for a given platform and level."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import validate_config
        result = validate_config(
            config=data.get("config", ""),
            platform=data.get("platform", "cisco_ios"),
            level=data.get("level", "beginner")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Config validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Packet Tracing Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/netai/trace/packet")
async def api_netai_trace_packet(request: Request):
    """Trace a packet through the simulated network from source to destination."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import trace_packet
        result = trace_packet(
            src=data.get("src", ""),
            dst=data.get("dst", ""),
            packet=data.get("packet", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Packet trace error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/trace/flow")
async def api_netai_trace_flow(request: Request):
    """Generate a packet flow diagram from a network trace."""
    try:
        data = json.loads(await request.body())
        from backend.netai_simulator import generate_packet_flow_diagram
        result = generate_packet_flow_diagram(trace=data.get("trace", {}))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Flow diagram generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Telemetry Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/netai/telemetry/{device_id}")
async def api_netai_telemetry_get(
    device_id: str,
    metric_type: str = Query("all"),
    duration: int = Query(3600)
):
    """Retrieve telemetry data for a device over a specified duration."""
    try:
        from backend.netai_training import get_telemetry
        result = get_telemetry(
            device_id=device_id,
            metric_type=metric_type,
            duration=duration
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Telemetry retrieval error for device_id=%s: %s", device_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/telemetry/inject")
async def api_netai_telemetry_inject(request: Request):
    """Inject an anomaly into telemetry data for training purposes."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import inject_anomaly
        result = inject_anomaly(
            telemetry=data.get("telemetry", {}),
            anomaly_type=data.get("anomaly_type", "spike")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Telemetry anomaly injection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Quiz Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/netai/quiz/{module_id}")
async def api_netai_quiz_get(
    module_id: str,
    difficulty: str = Query("mixed")
):
    """Retrieve a quiz for a given module at the specified difficulty."""
    try:
        from backend.netai_training import get_quiz
        result = get_quiz(module_id=module_id, difficulty=difficulty)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Quiz retrieval error for module_id=%s: %s", module_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/quiz/{quiz_id}/submit")
async def api_netai_quiz_submit(quiz_id: str, request: Request):
    """Submit quiz answers for grading and receive results."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import grade_quiz
        result = grade_quiz(
            quiz_id=quiz_id,
            answers=data.get("answers", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Quiz grading error for quiz_id=%s: %s", quiz_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Mentor (AI Tutor) Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/netai/mentor")
async def api_netai_mentor_chat(request: Request):
    """Send a message to the AI mentor and receive guidance."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import mentor_chat
        result = mentor_chat(
            student_id=data.get("student_id", ""),
            message=data.get("message", ""),
            context=data.get("context", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Mentor chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/mentor/history/{student_id}")
async def api_netai_mentor_history(student_id: str):
    """Retrieve the AI mentor conversation history for a student."""
    try:
        from backend.netai_training import get_mentor_history
        result = get_mentor_history(student_id=student_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Mentor history error for student_id=%s: %s", student_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Progress & Certificates Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/netai/progress/{student_id}")
async def api_netai_progress_get(student_id: str):
    """Get the training progress overview for a student."""
    try:
        from backend.netai_training import get_progress
        result = get_progress(student_id=student_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Progress retrieval error for student_id=%s: %s", student_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/leaderboard")
async def api_netai_leaderboard(
    limit: int = Query(50),
    track: str = Query("all")
):
    """Retrieve the training leaderboard with optional track filter."""
    try:
        from backend.netai_training import get_leaderboard
        result = get_leaderboard(limit=limit, track=track)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Leaderboard retrieval error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/netai/certificate")
async def api_netai_certificate_generate(request: Request):
    """Generate a completion certificate for a student in a given track."""
    try:
        data = json.loads(await request.body())
        from backend.netai_training import generate_certificate
        result = generate_certificate(
            student_id=data.get("student_id", ""),
            track=data.get("track", "network_engineering")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Certificate generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netai/certificate/{cert_id}")
async def api_netai_certificate_get(cert_id: str):
    """Retrieve a previously generated certificate by its ID."""
    try:
        from backend.netai_training import get_certificate
        result = get_certificate(cert_id=cert_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Certificate retrieval error for cert_id=%s: %s", cert_id, e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info(
    "v23 NetAI training endpoints registered: "
    "curriculum(4), labs(6), topology(4), scenarios(3), "
    "devices(4), packet_trace(2), telemetry(2), "
    "quizzes(2), mentor(2), progress_certs(4) = 33 endpoints"
)
