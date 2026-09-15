#!/usr/bin/env python3
"""Luqi AI v24 — Global Knowledge Academy, PM Training, Digital Workspace Endpoints"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  KNOWLEDGE ACADEMY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/academy/disciplines")
async def api_academy_disciplines():
    """Get all 11 disciplines with schools of thought."""
    try:
        from backend.knowledge_academy import get_all_disciplines
        result = get_all_disciplines()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching disciplines: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/discipline/{discipline_id}")
async def api_academy_discipline(discipline_id: str):
    """Get a specific discipline with all its schools."""
    try:
        from backend.knowledge_academy import get_discipline
        result = get_discipline(discipline_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching discipline %s: %s", discipline_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/school/{school_id}")
async def api_academy_school(school_id: str):
    """Get detailed information about a school of thought."""
    try:
        from backend.knowledge_academy import get_school
        result = get_school(school_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching school %s: %s", school_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/assess")
async def api_academy_assess(request: Request):
    """Assess student knowledge level."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import assess_level
        result = assess_level(data.get("student_id", ""), data.get("answers", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error assessing level: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/path")
async def api_academy_path(request: Request):
    """Generate personalized learning path."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import generate_learning_path
        result = generate_learning_path(
            data.get("student_id", ""),
            data.get("interests", []),
            data.get("pace", "medium")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating path: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/lesson/{school_id}/{lesson_number}")
async def api_academy_lesson(school_id: str, lesson_number: int, level: str = Query("intermediate")):
    """Get a lesson adapted to student level."""
    try:
        from backend.knowledge_academy import get_lesson
        result = get_lesson(school_id, lesson_number, level)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching lesson: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/explain")
async def api_academy_explain(request: Request):
    """Explain a concept at appropriate level."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import explain_concept
        result = explain_concept(data.get("concept_id", ""), data.get("level", "intermediate"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error explaining concept: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/explain/simple")
async def api_academy_explain_simple(request: Request):
    """Explain Like I'm 5 — simplest possible explanation."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import explain_like_im_five
        result = explain_like_im_five(data.get("concept_id", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error in ELI5: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/debate")
async def api_academy_debate(request: Request):
    """Simulate a debate between two schools of thought."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import simulate_debate
        result = simulate_debate(
            data.get("school_a", ""),
            data.get("school_b", ""),
            data.get("topic", ""),
            data.get("format", "structured")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error simulating debate: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/debate/topics")
async def api_academy_debate_topics():
    """Get curated debate topics."""
    try:
        from backend.knowledge_academy import get_debate_topics
        result = get_debate_topics()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching debate topics: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/compare")
async def api_academy_compare(request: Request):
    """Compare two schools of thought side by side."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import compare_schools
        result = compare_schools(data.get("school_a", ""), data.get("school_b", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error comparing schools: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/connections")
async def api_academy_connections(request: Request):
    """Find connections between two disciplines."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import find_connections
        result = find_connections(data.get("discipline_a", ""), data.get("discipline_b", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error finding connections: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/interdisciplinary")
async def api_academy_interdisciplinary():
    """Get interdisciplinary fields."""
    try:
        from backend.knowledge_academy import get_interdisciplinary_fields
        result = get_interdisciplinary_fields()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching interdisciplinary fields: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/progress/{student_id}")
async def api_academy_progress(student_id: str):
    """Get student learning progress."""
    try:
        from backend.knowledge_academy import track_progress
        result = track_progress(student_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching progress: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/quiz")
async def api_academy_quiz(request: Request):
    """Generate a quiz for a concept."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import quiz_concept
        result = quiz_concept(data.get("concept_id", ""), data.get("question_count", 5))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/quiz/grade")
async def api_academy_quiz_grade(request: Request):
    """Grade a quiz submission."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import grade_quiz
        result = grade_quiz(data.get("student_id", ""), data.get("quiz_id", ""), data.get("answers", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error grading quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/academy/starter-pack")
async def api_academy_starter_pack():
    """Get beginner starter pack."""
    try:
        from backend.knowledge_academy import get_starter_pack
        result = get_starter_pack()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching starter pack: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/academy/study-plan")
async def api_academy_study_plan(request: Request):
    """Generate a study plan."""
    try:
        data = json.loads(await request.body())
        from backend.knowledge_academy import generate_study_plan
        result = generate_study_plan(data.get("hours_per_week", 5), data.get("goals", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating study plan: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PROJECT MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/pm/methodologies")
async def api_pm_methodologies():
    """Get all project management methodologies."""
    try:
        from backend.project_management import get_all_methodologies
        result = get_all_methodologies()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching methodologies: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/methodology/{methodology_id}")
async def api_pm_methodology(methodology_id: str):
    """Get a specific methodology."""
    try:
        from backend.project_management import get_methodology
        result = get_methodology(methodology_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching methodology: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/templates")
async def api_pm_templates():
    """List all project templates."""
    try:
        from backend.project_management import list_templates
        result = list_templates()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching templates: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/template/{template_id}")
async def api_pm_template(template_id: str):
    """Get a specific project template."""
    try:
        from backend.project_management import get_template
        result = get_template(template_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching template: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/gantt")
async def api_pm_gantt(request: Request):
    """Generate a Gantt chart."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import generate_gantt_chart
        result = generate_gantt_chart(data.get("project_data", {}))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating Gantt: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/sprint/simulate")
async def api_pm_sprint_simulate(request: Request):
    """Simulate a sprint."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import simulate_sprint
        result = simulate_sprint(
            data.get("team_size", 5),
            data.get("sprint_duration", 14),
            data.get("backlog", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error simulating sprint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/velocity")
async def api_pm_velocity(request: Request):
    """Calculate team velocity."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import calculate_velocity
        result = calculate_velocity(data.get("previous_sprints", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error calculating velocity: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/risks/assess")
async def api_pm_risks_assess(request: Request):
    """Assess project risks."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import assess_risks
        result = assess_risks(data.get("risks", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error assessing risks: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/risks/register/{project_type}")
async def api_pm_risk_register(project_type: str):
    """Get default risk register for project type."""
    try:
        from backend.project_management import generate_risk_register
        result = generate_risk_register(project_type)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching risk register: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/resources/allocate")
async def api_pm_resources_allocate(request: Request):
    """Allocate project resources."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import allocate_resources
        result = allocate_resources(data.get("project", {}), data.get("team", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error allocating resources: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/raci")
async def api_pm_raci(request: Request):
    """Create RACI matrix."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import create_raci_matrix
        result = create_raci_matrix(data.get("tasks", []), data.get("roles", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error creating RACI: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/communication-plan")
async def api_pm_communication_plan(request: Request):
    """Generate communication plan."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import generate_communication_plan
        result = generate_communication_plan(data.get("stakeholders", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating comm plan: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/quiz")
async def api_pm_quiz(request: Request):
    """Get PM quiz questions."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import get_pm_quiz
        result = get_pm_quiz(data.get("level", "beginner"), data.get("topic", "general"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching PM quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/quiz/grade")
async def api_pm_quiz_grade(request: Request):
    """Grade PM quiz."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import grade_pm_quiz
        result = grade_pm_quiz(data.get("answers", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error grading PM quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/pmp-simulator")
async def api_pm_pmp_simulator():
    """Get PMP exam simulator."""
    try:
        from backend.project_management import get_pmp_exam_simulator
        result = get_pmp_exam_simulator()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching PMP simulator: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/tools/recommend")
async def api_pm_tools_recommend(request: Request):
    """Recommend PM tools."""
    try:
        data = json.loads(await request.body())
        from backend.project_management import recommend_tools
        result = recommend_tools(
            data.get("budget", "free"),
            data.get("team_size", 5),
            data.get("project_type", "software")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error recommending tools: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  DIGITAL WORKSPACE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/workspace/tools")
async def api_workspace_tools():
    """List all digital workspace tools."""
    try:
        from backend.digital_workspace import list_tools
        result = list_tools()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error listing tools: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/tool/{tool_id}")
async def api_workspace_tool(tool_id: str):
    """Get guide for a specific tool."""
    try:
        from backend.digital_workspace import get_tool_guide
        result = get_tool_guide(tool_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching tool guide: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/tools/compare")
async def api_workspace_tools_compare(request: Request):
    """Compare tools in a category."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import compare_tools
        result = compare_tools(data.get("category", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error comparing tools: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/docs/guide/{topic}")
async def api_workspace_docs_guide(topic: str):
    """Get document management guide."""
    try:
        from backend.digital_workspace import get_document_guide
        result = get_document_guide(topic)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching doc guide: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/docs/structure")
async def api_workspace_docs_structure(request: Request):
    """Generate folder structure."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import generate_folder_structure
        result = generate_folder_structure(data.get("project_type", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating structure: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/security/modules")
async def api_workspace_security_modules():
    """List security awareness modules."""
    try:
        from backend.digital_workspace import list_security_modules
        result = list_security_modules()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error listing security modules: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/security/{module_id}")
async def api_workspace_security_module(module_id: str):
    """Get a security awareness module."""
    try:
        from backend.digital_workspace import get_security_module
        result = get_security_module(module_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching security module: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/security/phishing")
async def api_workspace_phishing(request: Request):
    """Simulate a phishing test."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import simulate_phishing_test
        result = simulate_phishing_test(data.get("difficulty", "medium"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error simulating phishing: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/productivity/methods")
async def api_workspace_productivity_methods():
    """List productivity methods."""
    try:
        from backend.digital_workspace import list_productivity_methods
        result = list_productivity_methods()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error listing methods: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/productivity/{method_id}")
async def api_workspace_productivity_method(method_id: str):
    """Get a productivity method guide."""
    try:
        from backend.digital_workspace import get_productivity_method
        result = get_productivity_method(method_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching method: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/schedule")
async def api_workspace_schedule(request: Request):
    """Create daily schedule."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import create_daily_schedule
        result = create_daily_schedule(data.get("preferences", {}))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error creating schedule: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/remote/topics")
async def api_workspace_remote_topics():
    """List remote work topics."""
    try:
        from backend.digital_workspace import list_remote_work_topics
        result = list_remote_work_topics()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error listing remote topics: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/remote/{topic}")
async def api_workspace_remote_guide(topic: str):
    """Get remote work guide."""
    try:
        from backend.digital_workspace import get_remote_work_guide
        result = get_remote_work_guide(topic)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching remote guide: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/remote/assess")
async def api_workspace_remote_assess(request: Request):
    """Assess remote work readiness."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import assess_remote_readiness
        result = assess_remote_readiness(data.get("team", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error assessing readiness: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/communication/{channel}")
async def api_workspace_communication(channel: str):
    """Get communication guide for a channel."""
    try:
        from backend.digital_workspace import get_communication_guide
        result = get_communication_guide(channel)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching comm guide: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/email-template")
async def api_workspace_email_template(request: Request):
    """Generate email template."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import generate_email_template
        result = generate_email_template(data.get("purpose", ""), data.get("tone", "professional"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error generating template: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/setup/recommend")
async def api_workspace_setup_recommend(request: Request):
    """Recommend workspace setup."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import recommend_workspace_setup
        result = recommend_workspace_setup(
            data.get("budget", "standard"),
            data.get("work_type", "office"),
            data.get("space", "dedicated")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error recommending setup: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/quiz")
async def api_workspace_quiz(request: Request):
    """Get workspace quiz."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import get_workspace_quiz
        result = get_workspace_quiz(data.get("topic", "general"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error fetching quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/quiz/grade")
async def api_workspace_quiz_grade(request: Request):
    """Grade workspace quiz."""
    try:
        data = json.loads(await request.body())
        from backend.digital_workspace import grade_workspace_quiz
        result = grade_workspace_quiz(data.get("answers", []))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Error grading quiz: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v24 endpoints registered: 53 endpoints (18 Knowledge + 16 PM + 19 Digital Workspace)")
