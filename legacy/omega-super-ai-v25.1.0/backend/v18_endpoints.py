"""Luqi AI v18 — Automotive Diagnostic & Writing Assistant Endpoints
"""
import json
import logging
from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse
from backend.router import app

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# AUTOMOTIVE DIAGNOSTIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/automotive/diagnose")
async def api_automotive_diagnose(request: Request):
    """Full automotive diagnostic from symptom description."""
    try:
        from backend.automotive import diagnose, parse_symptoms
        data = json.loads(await request.body())
        description = data.get("description", "")
        vehicle = data.get("vehicle", {})
        symptoms = parse_symptoms(description)
        result = diagnose(symptoms, vehicle)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Auto diagnose error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/automotive/obd2/{code}")
async def api_automotive_obd2(code: str):
    """Look up OBD-II diagnostic trouble code."""
    try:
        from backend.automotive import lookup_obd2
        result = lookup_obd2(code.upper())
        return JSONResponse(result)
    except Exception as e:
        logger.error("OBD2 lookup error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/automotive/symptoms")
async def api_automotive_symptoms(category: str = None):
    """List all symptoms by category."""
    try:
        from backend.automotive import SYMPTOM_DATABASE
        if category and category in SYMPTOM_DATABASE:
            return JSONResponse({"category": category, "symptoms": list(SYMPTOM_DATABASE[category].keys())})
        return JSONResponse({"categories": list(SYMPTOM_DATABASE.keys()), "total": sum(len(v) for v in SYMPTOM_DATABASE.values())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/automotive/inspections")
async def api_automotive_inspections(request: Request):
    """Get zero-cost inspections for suspected causes."""
    try:
        from backend.automotive import generate_inspections
        data = json.loads(await request.body())
        result = generate_inspections(data.get("causes", []))
        return JSONResponse({"inspections": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/automotive/cost-estimate")
async def api_automotive_cost(request: Request):
    """Estimate repair costs."""
    try:
        from backend.automotive import estimate_repair_cost
        data = json.loads(await request.body())
        result = estimate_repair_cost(data.get("diagnosis", {}), data.get("year"), data.get("luxury", False))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/automotive/systems")
async def api_automotive_systems():
    """List vehicle systems reference."""
    try:
        from backend.automotive import VEHICLE_SYSTEMS
        return JSONResponse({"systems": {k: {"components": v["components"][:5], "common_failures": v["common_failures"][:3]} for k, v in VEHICLE_SYSTEMS.items()}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/automotive/maintenance-schedule")
async def api_automotive_maintenance(request: Request):
    """Get maintenance schedule for a vehicle."""
    try:
        from backend.automotive import get_maintenance_schedule
        data = json.loads(await request.body())
        result = get_maintenance_schedule(data.get("make", ""), data.get("model", ""), data.get("year"), data.get("mileage", 0))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# WRITING ASSISTANT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/writing/grammar")
async def api_writing_grammar(request: Request):
    """Check grammar and return issues with suggestions."""
    try:
        from backend.writing_assistant import check_grammar
        data = json.loads(await request.body())
        result = check_grammar(data.get("text", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Grammar check error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/grammar/fix")
async def api_writing_grammar_fix(request: Request):
    """Auto-fix all grammar issues."""
    try:
        from backend.writing_assistant import fix_grammar
        data = json.loads(await request.body())
        result = fix_grammar(data.get("text", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/improve")
async def api_writing_improve(request: Request):
    """Improve wording and phrasing."""
    try:
        from backend.writing_assistant import improve_wording
        data = json.loads(await request.body())
        result = improve_wording(data.get("text", ""), data.get("style", "general"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/readability")
async def api_writing_readability(request: Request):
    """Analyze text readability."""
    try:
        from backend.writing_assistant import analyze_readability
        data = json.loads(await request.body())
        result = analyze_readability(data.get("text", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/tone")
async def api_writing_tone(request: Request):
    """Adjust writing tone."""
    try:
        from backend.writing_assistant import adjust_tone
        data = json.loads(await request.body())
        result = adjust_tone(data.get("text", ""), data.get("tone", "professional"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/originality")
async def api_writing_originality(request: Request):
    """Check originality (clichés, generic phrases)."""
    try:
        from backend.writing_assistant import check_originality
        data = json.loads(await request.body())
        result = check_originality(data.get("text", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/style-guide")
async def api_writing_style_guide(request: Request):
    """Check style guide compliance."""
    try:
        from backend.writing_assistant import check_style_guide
        data = json.loads(await request.body())
        result = check_style_guide(data.get("text", ""), data.get("guide", "apa"))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/writing/stats")
async def api_writing_stats(request: Request):
    """Get comprehensive text statistics."""
    try:
        from backend.writing_assistant import get_text_stats
        data = json.loads(await request.body())
        result = get_text_stats(data.get("text", ""))
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/writing/rules")
async def api_writing_rules():
    """List all grammar rules and writing resources."""
    try:
        from backend.writing_assistant import GRAMMAR_RULES, WORD_UPGRADES, TONE_PROFILES
        return JSONResponse({
            "grammar_rules": list(GRAMMAR_RULES.keys()),
            "improvement_styles": list(WORD_UPGRADES.keys()),
            "tone_profiles": list(TONE_PROFILES.keys()),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

logger.info("v18 endpoints loaded: automotive(7), writing(10) = 17 new endpoints")
