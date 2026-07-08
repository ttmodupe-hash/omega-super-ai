#!/usr/bin/env python3
"""Luqi AI v21 -- Jobs, WhatsApp Bot, Government Services Endpoints
=================================================================
Endpoints for jobs and skills advisor, WhatsApp conversational bot,
and government services guide covering ID, business, tax, voting,
passport, land, social services, document checklists, and agency lookup.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Jobs & Skills Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/jobs/cv-build")
async def api_jobs_cv_build(request: Request):
    """Build a professional CV/resume from user data."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import build_cv
        result = build_cv(data=data)
        return JSONResponse(result)
    except Exception as e:
        logger.error("CV build error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/interview")
async def api_jobs_interview(request: Request):
    """Get interview questions for a specific field and experience level."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import get_interview_questions
        result = get_interview_questions(
            field=data.get("field", ""),
            level=data.get("level", "mid")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Interview questions error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/assess")
async def api_jobs_assess(request: Request):
    """Assess skills for a given topic from user answers."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import assess_skills
        result = assess_skills(
            topic=data.get("topic", ""),
            answers=data.get("answers", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Skills assessment error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/market")
async def api_jobs_market(
    country: str = Query("nigeria"),
    field: str = Query("")
):
    """Get job market overview for a country and field."""
    try:
        from backend.jobs_skills import get_job_market
        result = get_job_market(country=country, field=field)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Job market error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/career-plan")
async def api_jobs_career_plan(request: Request):
    """Generate a career plan from current role to goal role."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import plan_career
        result = plan_career(
            current_role=data.get("current_role", ""),
            goal_role=data.get("goal_role", ""),
            timeline_years=data.get("timeline_years", 5)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Career plan error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/freelance")
async def api_jobs_freelance(request: Request):
    """Get a freelance guide for a skill on a given platform."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import get_freelance_guide
        result = get_freelance_guide(
            skill=data.get("skill", ""),
            platform=data.get("platform", "upwork")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Freelance guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/coverletter")
async def api_jobs_coverletter(request: Request):
    """Generate a tailored cover letter for a job application."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import generate_coverletter
        result = generate_coverletter(
            job_title=data.get("job_title", ""),
            company=data.get("company", ""),
            applicant_skills=data.get("applicant_skills", [])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cover letter error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/salary-guide")
async def api_jobs_salary_guide(request: Request):
    """Get a salary guide for a role in a given country."""
    try:
        data = json.loads(await request.body())
        from backend.jobs_skills import get_salary_guide
        result = get_salary_guide(
            country=data.get("country", "nigeria"),
            role=data.get("role", ""),
            experience_years=data.get("experience_years", 0)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Salary guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# WhatsApp Bot Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/whatsapp/webhook")
async def api_whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp webhook events."""
    try:
        data = json.loads(await request.body())
        from backend.whatsapp_bot import handle_webhook
        result = handle_webhook(data=data)
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp webhook error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/whatsapp/send")
async def api_whatsapp_send(request: Request):
    """Send a WhatsApp message to a phone number."""
    try:
        data = json.loads(await request.body())
        from backend.whatsapp_bot import send_message
        result = send_message(
            phone=data.get("phone", ""),
            message=data.get("message", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp send error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/whatsapp/sessions")
async def api_whatsapp_sessions():
    """List all active WhatsApp conversation sessions."""
    try:
        from backend.whatsapp_bot import get_all_sessions
        result = get_all_sessions()
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp sessions list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/whatsapp/session/{phone}")
async def api_whatsapp_session_get(phone: str):
    """Get a specific WhatsApp conversation session by phone number."""
    try:
        from backend.whatsapp_bot import get_session
        result = get_session(phone=phone)
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp session get error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/whatsapp/session/{phone}")
async def api_whatsapp_session_delete(phone: str):
    """Reset (delete) a WhatsApp conversation session by phone number."""
    try:
        from backend.whatsapp_bot import reset_session
        result = reset_session(phone=phone)
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp session delete error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/whatsapp/analytics")
async def api_whatsapp_analytics(
    days: int = Query(7)
):
    """Get WhatsApp bot analytics summary for a given period."""
    try:
        from backend.whatsapp_bot import get_analytics_summary
        result = get_analytics_summary(days=days)
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/whatsapp/menu")
async def api_whatsapp_menu(request: Request):
    """Show the main menu for the WhatsApp bot in a given language."""
    try:
        data = json.loads(await request.body())
        from backend.whatsapp_bot import show_main_menu
        result = show_main_menu(lang=data.get("lang", "en"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("WhatsApp menu error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# Government Services Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/government/id-guide")
async def api_government_id_guide(
    country: str = Query("nigeria"),
    id_type: str = Query("national_id")
):
    """Get an ID application guide for a specific country and ID type."""
    try:
        from backend.government_services import get_id_guide
        result = get_id_guide(country=country, id_type=id_type)
        return JSONResponse(result)
    except Exception as e:
        logger.error("ID guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/business-reg")
async def api_government_business_reg(
    country: str = Query("nigeria"),
    business_type: str = Query("sole_proprietorship")
):
    """Get a business registration guide for a country and business type."""
    try:
        from backend.government_services import get_business_registration_guide
        result = get_business_registration_guide(
            country=country,
            business_type=business_type
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Business registration guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/tax-guide")
async def api_government_tax_guide(
    country: str = Query("nigeria"),
    tax_type: str = Query("income")
):
    """Get a tax guide for a specific country and tax type."""
    try:
        from backend.government_services import get_tax_guide
        result = get_tax_guide(country=country, tax_type=tax_type)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Tax guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/voting")
async def api_government_voting(
    country: str = Query("nigeria")
):
    """Get voting and election information for a country."""
    try:
        from backend.government_services import get_voting_info
        result = get_voting_info(country=country)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voting info error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/passport")
async def api_government_passport(
    country: str = Query("nigeria"),
    passport_type: str = Query("standard")
):
    """Get a passport application guide for a country and passport type."""
    try:
        from backend.government_services import get_passport_guide
        result = get_passport_guide(
            country=country,
            passport_type=passport_type
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Passport guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/land")
async def api_government_land(
    country: str = Query("nigeria"),
    transaction_type: str = Query("buy")
):
    """Get a land transaction guide for a country and transaction type."""
    try:
        from backend.government_services import get_land_guide
        result = get_land_guide(
            country=country,
            transaction_type=transaction_type
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Land guide error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/social-services")
async def api_government_social_services(
    country: str = Query("nigeria"),
    service_type: str = Query("healthcare")
):
    """Get social services information for a country and service type."""
    try:
        from backend.government_services import get_social_services
        result = get_social_services(
            country=country,
            service_type=service_type
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Social services error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/government/document-checklist")
async def api_government_document_checklist(request: Request):
    """Generate a document checklist for a given purpose and country."""
    try:
        data = json.loads(await request.body())
        from backend.government_services import generate_document_checklist
        result = generate_document_checklist(
            purpose=data.get("purpose", ""),
            country=data.get("country", "nigeria")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Document checklist error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/government/agencies")
async def api_government_agencies(
    country: str = Query("nigeria"),
    agency_type: str = Query(""),
    city: str = Query("")
):
    """Find government agencies in a country, optionally filtered by type and city."""
    try:
        from backend.government_services import find_agency
        result = find_agency(
            country=country,
            agency_type=agency_type,
            city=city
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Agency lookup error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v21 endpoints loaded: jobs_skills(8), whatsapp_bot(7), government_services(9) = 24 endpoints")
