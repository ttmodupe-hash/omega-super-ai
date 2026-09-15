#!/usr/bin/env python3
"""Luqi AI v20 — Africa-First Capabilities Endpoints
=====================================================
Endpoints for agricultural advisor, healthcare assistant, teacher assistant,
business advisor, and offline engine.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Agricultural Advisor Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/agriculture/advice")
async def api_agriculture_advice(request: Request):
    """Get farming advice for a specific crop and region."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import farming_advice
        result = farming_advice(
            query=data.get("query", ""),
            region=data.get("region", "west_africa"),
            crop=data.get("crop")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Agriculture advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agriculture/pest-diagnosis")
async def api_pest_diagnosis(request: Request):
    """Diagnose pests or diseases from crop symptoms."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import pest_diagnosis
        result = pest_diagnosis(
            crop=data.get("crop", ""),
            symptoms=data.get("symptoms", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Pest diagnosis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agriculture/market")
async def api_agriculture_market(request: Request):
    """Get market advice for agricultural commodities."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import market_advice
        result = market_advice(
            commodity=data.get("commodity", ""),
            region=data.get("region", "west_africa")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Market advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agriculture/farm-plan")
async def api_farm_plan(request: Request):
    """Create a comprehensive farm plan."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import farm_plan
        result = farm_plan(
            land_size=data.get("land_size", 1),
            region=data.get("region", "west_africa"),
            budget=data.get("budget", "low"),
            goals=data.get("goals", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Farm plan error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agriculture/livestock")
async def api_livestock_advice(request: Request):
    """Get livestock care advice."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import livestock_advice
        result = livestock_advice(
            animal=data.get("animal", ""),
            topic=data.get("topic", "general"),
            symptoms=data.get("symptoms"),
            budget=data.get("budget", "low")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Livestock advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agriculture/irrigation")
async def api_irrigation_advice(request: Request):
    """Get irrigation and water management advice."""
    try:
        data = json.loads(await request.body())
        from backend.agricultural_advisor import get_irrigation_advice
        result = get_irrigation_advice(
            crop=data.get("crop"),
            land_size=data.get("land_size", 1),
            budget=data.get("budget", "low"),
            water_source=data.get("water_source")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Irrigation advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agriculture/crops")
async def api_agriculture_crops():
    """List all supported crops."""
    try:
        from backend.agricultural_advisor import CropAdvisor
        advisor = CropAdvisor()
        return JSONResponse({"crops": list(advisor.CROPS.keys())})
    except Exception as e:
        logger.error("Crops list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agriculture/regions")
async def api_agriculture_regions():
    """List all supported African regions."""
    try:
        from backend.agricultural_advisor import REGIONS
        return JSONResponse({"regions": list(REGIONS.keys())})
    except Exception as e:
        logger.error("Regions list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Healthcare Assistant Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/health/info")
async def api_health_info(request: Request):
    """Get general health information."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import health_info
        result = health_info(
            query=data.get("query", ""),
            age=data.get("age"),
            country=data.get("country")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Health info error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/health/first-aid")
async def api_first_aid(request: Request):
    """Get first aid guidance for emergencies."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import first_aid
        result = first_aid(emergency_type=data.get("emergency_type", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("First aid error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/health/symptoms")
async def api_check_symptoms(request: Request):
    """Get information about symptoms (NOT a diagnosis)."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import check_symptoms
        result = check_symptoms(
            symptoms=data.get("symptoms", ""),
            age=data.get("age"),
            country=data.get("country")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Symptoms check error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/health/maternal")
async def api_maternal_health(request: Request):
    """Get maternal health information."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import maternal_health
        result = maternal_health(
            topic=data.get("topic", "general"),
            week=data.get("week")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Maternal health error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/health/child")
async def api_child_health(request: Request):
    """Get child health information."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import child_health
        result = child_health(
            topic=data.get("topic", "general"),
            age=data.get("age")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Child health error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/health/nutrition")
async def api_nutrition_advice(request: Request):
    """Get nutrition advice."""
    try:
        data = json.loads(await request.body())
        from backend.healthcare_assistant import nutrition_advice
        result = nutrition_advice(
            age=data.get("age"),
            condition=data.get("condition")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Nutrition advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health/emergency-numbers")
async def api_emergency_numbers(country: str = Query("nigeria")):
    """Get emergency numbers for a country."""
    try:
        from backend.healthcare_assistant import FirstAidGuide
        guide = FirstAidGuide()
        result = guide.get_emergency_numbers(country)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Emergency numbers error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health/diseases")
async def api_health_diseases():
    """List common African diseases in the database."""
    try:
        from backend.healthcare_assistant import DiseaseInformation
        info = DiseaseInformation()
        return JSONResponse({"diseases": list(info.COMMON_AFRICAN_DISEASES.keys())})
    except Exception as e:
        logger.error("Diseases list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Teacher Assistant Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/education/lesson")
async def api_create_lesson(request: Request):
    """Generate a lesson plan."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import create_lesson
        result = create_lesson(
            subject=data.get("subject", "mathematics"),
            topic=data.get("topic", ""),
            grade=data.get("grade", "primary_5"),
            duration=data.get("duration", 40)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Lesson creation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/worksheet")
async def api_create_worksheet(request: Request):
    """Generate a worksheet."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import create_worksheet
        result = create_worksheet(
            subject=data.get("subject", "mathematics"),
            topic=data.get("topic", ""),
            grade=data.get("grade", "primary_5")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Worksheet creation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/teaching-tip")
async def api_teaching_tip(request: Request):
    """Get teaching tips for specific challenges."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import teaching_tip
        result = teaching_tip(challenge=data.get("challenge", "large_class"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Teaching tip error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/stem-experiment")
async def api_stem_experiment(request: Request):
    """Get STEM experiments using household materials."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import stem_experiment
        result = stem_experiment(
            subject=data.get("subject", "science"),
            topic=data.get("topic", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("STEM experiment error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/assessment")
async def api_assessment_tracker(request: Request):
    """Track student assessments."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import assessment_tracker
        result = assessment_tracker(
            subject=data.get("subject", ""),
            students=data.get("students", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Assessment tracker error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/education/subjects")
async def api_education_subjects():
    """List available subjects."""
    try:
        from backend.teacher_assistant import SUBJECTS
        return JSONResponse({"subjects": list(SUBJECTS.keys())})
    except Exception as e:
        logger.error("Subjects list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/education/grades")
async def api_education_grades():
    """List available grade levels."""
    try:
        from backend.teacher_assistant import GRADES
        return JSONResponse({"grades": GRADES})
    except Exception as e:
        logger.error("Grades list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/reading")
async def api_reading_material(request: Request):
    """Generate reading comprehension material."""
    try:
        data = json.loads(await request.body())
        from backend.teacher_assistant import ReadingMaterial
        reader = ReadingMaterial()
        passage = reader.get_reading_passage(
            grade=data.get("grade", "primary_5"),
            topic=data.get("topic")
        )
        questions = reader.get_comprehension_questions(passage.get("passage", ""))
        return JSONResponse({"passage": passage, "questions": questions})
    except Exception as e:
        logger.error("Reading material error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Business Advisor Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/business/advice")
async def api_business_advice(request: Request):
    """Get general business advice."""
    try:
        data = json.loads(await request.body())
        from backend.business_advisor import business_advice
        result = business_advice(
            query=data.get("query", ""),
            location=data.get("location", "nigeria"),
            business_type=data.get("business_type")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Business advice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/business/plan")
async def api_business_plan(request: Request):
    """Create a business plan."""
    try:
        data = json.loads(await request.body())
        from backend.business_advisor import business_plan
        result = business_plan(
            business_type=data.get("business_type", "retail"),
            capital=data.get("capital", 1000),
            location=data.get("location", "nigeria")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Business plan error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/business/financial-plan")
async def api_financial_plan(request: Request):
    """Create a financial plan."""
    try:
        data = json.loads(await request.body())
        from backend.business_advisor import financial_plan
        result = financial_plan(
            income=data.get("income", 0),
            expenses=data.get("expenses", []),
            goals=data.get("goals", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Financial plan error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/business/market-research")
async def api_market_research(request: Request):
    """Conduct market research."""
    try:
        data = json.loads(await request.body())
        from backend.business_advisor import market_research
        result = market_research(
            product=data.get("product", ""),
            location=data.get("location", "nigeria")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Market research error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/business/register")
async def api_register_business(request: Request):
    """Get business registration guidance."""
    try:
        data = json.loads(await request.body())
        from backend.business_advisor import register_business
        result = register_business(
            country=data.get("country", "nigeria"),
            business_type=data.get("business_type", "sole_proprietorship")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Business registration error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/business/types")
async def api_business_types():
    """List supported business types."""
    try:
        from backend.business_advisor import BusinessPlanner
        planner = BusinessPlanner()
        return JSONResponse({"business_types": list(planner.BUSINESS_TEMPLATES.keys())})
    except Exception as e:
        logger.error("Business types error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/business/countries")
async def api_business_countries():
    """List supported countries."""
    try:
        from backend.business_advisor import SUPPORTED_COUNTRIES
        return JSONResponse({"countries": list(SUPPORTED_COUNTRIES.keys())})
    except Exception as e:
        logger.error("Business countries error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Offline Engine Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/offline/query")
async def api_offline_query(request: Request):
    """Handle offline query with fallback."""
    try:
        data = json.loads(await request.body())
        from backend.offline_engine import offline_query
        result = offline_query(
            query=data.get("query", ""),
            user_id=data.get("user_id", "anonymous"),
            module=data.get("module", "general")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Offline query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/offline/sms")
async def api_sms_response(request: Request):
    """Process SMS query."""
    try:
        data = json.loads(await request.body())
        from backend.offline_engine import sms_response
        result = sms_response(
            message=data.get("message", ""),
            user_id=data.get("user_id", "anonymous")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("SMS response error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/offline/cache")
async def api_cache_response(request: Request):
    """Cache a response for offline use."""
    try:
        data = json.loads(await request.body())
        from backend.offline_engine import cache_response
        result = cache_response(
            query=data.get("query", ""),
            response=data.get("response", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cache error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/offline/sync")
async def api_sync_data(request: Request):
    """Trigger data sync."""
    try:
        data = json.loads(await request.body())
        from backend.offline_engine import sync_data
        result = sync_data(user_id=data.get("user_id"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Sync error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/offline/status")
async def api_offline_status():
    """Get offline engine status."""
    try:
        from backend.offline_engine import get_offline_status
        result = get_offline_status()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Offline status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/offline/faq")
async def api_offline_faq(query: str = Query(""), category: str = Query("")):
    """Search offline FAQ."""
    try:
        from backend.offline_engine import OfflineFAQ
        faq = OfflineFAQ()
        if category:
            result = faq.get_by_category(category)
        elif query:
            result = faq.get_answer(query)
        else:
            result = {"categories": list(faq.FAQ_CATEGORIES.keys())}
        return JSONResponse(result)
    except Exception as e:
        logger.error("FAQ error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/offline/sms-commands")
async def api_sms_commands():
    """List supported SMS commands."""
    try:
        from backend.offline_engine import SMSInterface
        sms = SMSInterface()
        return JSONResponse({"commands": sms.get_sms_commands()})
    except Exception as e:
        logger.error("SMS commands error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v20 Africa-First endpoints loaded: agriculture(8), health(8), education(8), business(7), offline(7) = 38 endpoints")
