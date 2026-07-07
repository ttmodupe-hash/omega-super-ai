"""Luqi AI v19 — Law Studies Endpoints"""
import json
import logging
from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse
from backend.router import app

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# LEGAL RESEARCH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/research")
async def api_law_research(request: Request):
    """Legal research query — returns statutes, cases, principles."""
    try:
        from backend.law_studies import legal_research
        data = json.loads(await request.body())
        result = legal_research(
            query=data.get("query", ""),
            jurisdiction=data.get("jurisdiction", "us"),
            area=data.get("area", "general")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Law research error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/case/search")
async def api_law_case_search(request: Request):
    """Search landmark cases by keywords, jurisdiction, and area."""
    try:
        from backend.law_studies import search_cases
        data = json.loads(await request.body())
        result = search_cases(
            keywords=data.get("keywords", ""),
            jurisdiction=data.get("jurisdiction", "us"),
            area=data.get("area", "general")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Case search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/case/brief")
async def api_law_case_brief(request: Request):
    """Brief a case using IRAC/CREAC/CRAC methodology."""
    try:
        from backend.law_studies import brief_case
        data = json.loads(await request.body())
        result = brief_case(
            case_text=data.get("case_text", ""),
            case_name=data.get("case_name", ""),
            method=data.get("method", "IRAC")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Case brief error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/case/analyze")
async def api_law_case_analyze(request: Request):
    """Analyze a case text — extract issues, holdings, reasoning, dissents."""
    try:
        from backend.law_studies import analyze_case
        data = json.loads(await request.body())
        result = analyze_case(case_text=data.get("case_text", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Case analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/law/cases/landmark")
async def api_law_cases_landmark(
    jurisdiction: str = Query(None),
    area: str = Query(None),
    limit: int = Query(50)
):
    """List all landmark cases with optional filtering."""
    try:
        from backend.law_studies import list_landmark_cases
        result = list_landmark_cases(jurisdiction=jurisdiction, area=area, limit=limit)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Landmark cases error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# CONTRACT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/contract/draft")
async def api_law_contract_draft(request: Request):
    """Draft a contract from type, parties, terms, and jurisdiction."""
    try:
        from backend.law_studies import draft_contract
        data = json.loads(await request.body())
        result = draft_contract(
            contract_type=data.get("contract_type", "nda"),
            parties=data.get("parties", {}),
            terms=data.get("terms", {}),
            jurisdiction=data.get("jurisdiction", "us")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Contract draft error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/contract/analyze")
async def api_law_contract_analyze(request: Request):
    """Analyze a contract for risks, missing clauses, and recommendations."""
    try:
        from backend.law_studies import analyze_contract
        data = json.loads(await request.body())
        result = analyze_contract(contract_text=data.get("contract_text", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Contract analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# DOCUMENT DRAFTING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/document/draft")
async def api_law_document_draft(request: Request):
    """Draft a legal document from a template with variables."""
    try:
        from backend.law_studies import draft_document
        data = json.loads(await request.body())
        result = draft_document(
            template=data.get("template", "demand_letter"),
            variables=data.get("variables", {}),
            jurisdiction=data.get("jurisdiction", "us")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Document draft error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# BAR EXAM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/barexam/question")
async def api_law_barexam_question(request: Request):
    """Get an MBE-style bar exam question by subject and difficulty."""
    try:
        from backend.law_studies import get_bar_question
        data = json.loads(await request.body())
        result = get_bar_question(
            subject=data.get("subject", "constitutional"),
            difficulty=data.get("difficulty", 1)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Bar exam question error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/barexam/check")
async def api_law_barexam_check(request: Request):
    """Check a bar exam answer — returns correct/incorrect with explanation."""
    try:
        from backend.law_studies import check_bar_answer
        data = json.loads(await request.body())
        result = check_bar_answer(
            question_id=data.get("question_id", ""),
            answer=data.get("answer", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Bar exam check error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/law/barexam/subjects")
async def api_law_barexam_subjects():
    """List all bar exam subjects with user performance stats."""
    try:
        from backend.law_studies import list_bar_subjects
        result = list_bar_subjects()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Bar exam subjects error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# CITATION & COMPARISON ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/cite")
async def api_law_cite(request: Request):
    """Generate a legal citation in the requested style (Bluebook, APA, etc.)."""
    try:
        from backend.law_studies import generate_citation
        data = json.loads(await request.body())
        result = generate_citation(
            source=data.get("source", {}),
            style=data.get("style", "bluebook")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Citation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/compare")
async def api_law_compare(request: Request):
    """Cross-jurisdictional comparison of a legal topic."""
    try:
        from backend.law_studies import compare_jurisdictions
        data = json.loads(await request.body())
        result = compare_jurisdictions(
            topic=data.get("topic", ""),
            jurisdictions=data.get("jurisdictions", ["us"])
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Jurisdiction comparison error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# RULES & PROCEDURE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/evidence")
async def api_law_evidence(request: Request):
    """Look up an evidence rule by number or topic."""
    try:
        from backend.law_studies import lookup_evidence_rule
        data = json.loads(await request.body())
        result = lookup_evidence_rule(
            rule_number=data.get("rule_number"),
            topic=data.get("topic", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Evidence rule error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/procedure")
async def api_law_procedure(request: Request):
    """Get step-by-step court procedure for a given court type."""
    try:
        from backend.law_studies import get_procedure
        data = json.loads(await request.body())
        result = get_procedure(
            court_type=data.get("court_type", "federal_district"),
            jurisdiction=data.get("jurisdiction", "us")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Procedure error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/statute/interpret")
async def api_law_statute_interpret(request: Request):
    """Interpret a statute text using canons of construction."""
    try:
        from backend.law_studies import interpret_statute
        data = json.loads(await request.body())
        result = interpret_statute(
            statute_text=data.get("statute_text", ""),
            question=data.get("question", "")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Statute interpretation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# LEGAL CLINIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/clinic/intake")
async def api_law_clinic_intake(request: Request):
    """Legal clinic client intake — returns issue analysis and advice (with disclaimer)."""
    try:
        from backend.law_studies import clinic_intake
        data = json.loads(await request.body())
        result = clinic_intake(
            client_info=data.get("client_info", {}),
            facts=data.get("facts", ""),
            area=data.get("area", "general")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Clinic intake error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# MOOT COURT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/law/moot/problem")
async def api_law_moot_problem(request: Request):
    """Generate a moot court problem statement by area and complexity."""
    try:
        from backend.law_studies import generate_moot_problem
        data = json.loads(await request.body())
        result = generate_moot_problem(
            area=data.get("area", "constitutional"),
            complexity=data.get("complexity", 3)
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Moot problem error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/law/moot/prep")
async def api_law_moot_prep(request: Request):
    """Moot court argument prep — returns suggested arguments for a side."""
    try:
        from backend.law_studies import moot_prep
        data = json.loads(await request.body())
        result = moot_prep(
            side=data.get("side", "appellant"),
            facts=data.get("facts", ""),
            area=data.get("area", "constitutional")
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Moot prep error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# PRACTICE AREA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/law/areas")
async def api_law_areas():
    """List all practice areas with descriptions."""
    try:
        from backend.law_studies import list_practice_areas
        result = list_practice_areas()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Practice areas error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

logger.info("v19 endpoints loaded: law_studies(20) = 20 new endpoints")
