"""Luqi AI v17 — Captainship & Companionship Endpoints

AI project captain and emotional companion endpoints.
"""

import json
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from backend.router import app

logger = logging.getLogger(__name__)

def _get_user_id(request: Request) -> str:
    api_key = request.headers.get("X-API-Key", "anonymous")
    try:
        from backend.subscriptions import get_user_id
        return get_user_id(api_key)
    except Exception:
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════
# CAPTAINSHIP ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/captain/projects")
async def api_captain_projects(request: Request):
    """List all projects."""
    try:
        from backend.captainship import get_all_projects
        return JSONResponse({"projects": get_all_projects()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/project")
async def api_captain_create_project(request: Request):
    """Create a new project."""
    try:
        from backend.captainship import ProjectCaptain
        data = json.loads(await request.body())
        captain = ProjectCaptain()
        result = captain.create_project(
            name=data.get("name", ""),
            description=data.get("description", ""),
            goals=data.get("goals", []),
            team_size=data.get("team_size", 1),
            deadline=data.get("deadline", ""),
            budget=data.get("budget"),
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/captain/project/{project_id}")
async def api_captain_project_detail(project_id: str):
    """Get project details and progress."""
    try:
        from backend.captainship import ProjectCaptain
        captain = ProjectCaptain()
        progress = captain.track_progress(project_id)
        blockers = captain.identify_blockers(project_id)
        actions = captain.suggest_next_actions(project_id)
        return JSONResponse({"progress": progress, "blockers": blockers, "next_actions": actions})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/swot")
async def api_captain_swot(request: Request):
    """SWOT analysis."""
    try:
        from backend.captainship import swot_analysis
        data = json.loads(await request.body())
        result = swot_analysis(data.get("subject", ""), data.get("context", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/decision")
async def api_captain_decision(request: Request):
    """Weighted decision matrix."""
    try:
        from backend.captainship import decision_matrix
        data = json.loads(await request.body())
        result = decision_matrix(data.get("decision", ""), data.get("options", []), data.get("criteria", []))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/risk")
async def api_captain_risk(request: Request):
    """Risk assessment."""
    try:
        from backend.captainship import risk_assessment
        data = json.loads(await request.body())
        result = risk_assessment(data.get("description", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/okr")
async def api_captain_okr(request: Request):
    """Generate OKRs."""
    try:
        from backend.captainship import generate_okrs
        data = json.loads(await request.body())
        result = generate_okrs(data.get("objective", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/meeting/agenda")
async def api_captain_agenda(request: Request):
    """Generate meeting agenda."""
    try:
        from backend.captainship import TeamCoordinator
        data = json.loads(await request.body())
        coord = TeamCoordinator()
        result = coord.generate_meeting_agenda(data.get("project_id", ""), data.get("type", "standup"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/meeting/minutes")
async def api_captain_minutes(request: Request):
    """Generate meeting minutes."""
    try:
        from backend.captainship import TeamCoordinator
        data = json.loads(await request.body())
        coord = TeamCoordinator()
        result = coord.generate_meeting_minutes(data.get("notes", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/status-report")
async def api_captain_status(request: Request):
    """Generate status report."""
    try:
        from backend.captainship import generate_status_report
        data = json.loads(await request.body())
        result = generate_status_report(data.get("project_id", ""), data.get("audience", "internal"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/crisis")
async def api_captain_crisis(request: Request):
    """Crisis management response."""
    try:
        from backend.captainship import CrisisManager
        data = json.loads(await request.body())
        cm = CrisisManager()
        result = cm.crisis_response(data.get("type", ""), data.get("description", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/time-estimate")
async def api_captain_time(request: Request):
    """PERT time estimation."""
    try:
        from backend.captainship import time_estimation
        data = json.loads(await request.body())
        result = time_estimation(data.get("tasks", []), data.get("velocity"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/captain/budget")
async def api_captain_budget(request: Request):
    """Budget forecast."""
    try:
        from backend.captainship import budget_forecast
        data = json.loads(await request.body())
        result = budget_forecast(data.get("current", 0), data.get("planned", 0), data.get("timeline", {}))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# COMPANIONSHIP ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/companion/greeting")
async def api_companion_greeting(request: Request):
    """Personalized companion greeting."""
    try:
        from backend.companionship import CompanionMemory, RelationshipTracker
        user_id = _get_user_id(request)
        memory = CompanionMemory()
        tracker = RelationshipTracker()
        digest = memory.get_memory_digest(user_id)
        level = tracker.get_relationship_level(user_id)
        return JSONResponse({"digest": digest, "relationship": level})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/checkin")
async def api_companion_checkin(request: Request):
    """Daily check-in."""
    try:
        from backend.companionship import CompanionMemory, generate_morning_checkin, generate_evening_reflection
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        memory = CompanionMemory()
        time_of_day = data.get("time", "morning")
        if time_of_day == "morning":
            result = generate_morning_checkin(user_id, memory)
        else:
            from backend.companionship import EmotionalEngine
            result = generate_evening_reflection(user_id, memory, EmotionalEngine())
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/mood")
async def api_companion_mood(request: Request):
    """Record mood and get empathetic response."""
    try:
        from backend.companionship import EmotionalEngine, CompanionMemory, RelationshipTracker
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        text = data.get("text", "")
        engine = EmotionalEngine()
        memory = CompanionMemory()
        tracker = RelationshipTracker()
        mood = engine.detect_mood(text)
        memory.record_emotional_state(user_id, mood.get("primary_mood", "neutral"), mood.get("intensity", 5), text[:100])
        tracker.record_interaction(user_id, "chat", mood.get("intensity", 5))
        level = tracker.get_relationship_level(user_id)
        response = engine.generate_empathetic_response(
            mood.get("primary_mood", "neutral"), mood.get("intensity", 5), text, level.get("level", 0)
        )
        return JSONResponse({"mood": mood, "response": response, "relationship": level})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/story")
async def api_companion_story(request: Request):
    """Generate a personalized story."""
    try:
        from backend.companionship import generate_daily_story, CompanionMemory
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        memory = CompanionMemory()
        result = generate_daily_story(user_id, memory, data.get("theme", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/journal")
async def api_companion_journal(request: Request):
    """Create a journal entry."""
    try:
        from backend.companionship import JournalSystem
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        journal = JournalSystem()
        result = journal.create_entry(user_id, data.get("content", ""), data.get("mood", ""), data.get("tags"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companion/journal/insights")
async def api_companion_journal_insights(request: Request):
    """Get journal insights."""
    try:
        from backend.companionship import JournalSystem
        user_id = _get_user_id(request)
        journal = JournalSystem()
        result = journal.get_insights(user_id)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/goal")
async def api_companion_goal(request: Request):
    """Set a personal growth goal."""
    try:
        from backend.companionship import GrowthCompanion
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        gc = GrowthCompanion()
        result = gc.set_goal(user_id, data.get("goal", ""), data.get("category", "personal"), data.get("deadline"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companion/growth")
async def api_companion_growth(request: Request):
    """Get personal growth report."""
    try:
        from backend.companionship import GrowthCompanion
        user_id = _get_user_id(request)
        gc = GrowthCompanion()
        result = gc.get_growth_report(user_id)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companion/activity")
async def api_companion_activity(mood: str = "neutral", request: Request = None):
    """Get activity suggestion."""
    try:
        from backend.companionship import suggest_activity
        from backend.companionship import CompanionMemory
        user_id = _get_user_id(request)
        memory = CompanionMemory()
        facts = memory.recall_facts(user_id, "interest")
        interests = [f.get("fact", "") for f in facts] if facts else []
        result = suggest_activity(mood, interests)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companion/celebrate")
async def api_companion_celebrate(request: Request):
    """Celebrate a milestone."""
    try:
        from backend.companionship import celebrate_milestone
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        result = celebrate_milestone(user_id, data.get("type", ""), data.get("details", {}))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companion/boundaries")
async def api_companion_boundaries():
    """Get companion boundaries."""
    try:
        from backend.companionship import COMPANION_BOUNDARIES
        return JSONResponse({"boundaries": COMPANION_BOUNDARIES})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

logger.info("v17 endpoints loaded: captain(13), companion(12) = 25 new endpoints")
