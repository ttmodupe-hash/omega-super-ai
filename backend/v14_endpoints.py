"""Luqi AI v14 -- SaaS Endpoints Extension

Adds subscription, developer workspace, website builder, dashboard,
and auto-upgrader endpoints to the existing FastAPI app.

Import this in router.py to activate all v14 endpoints.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

# Import the shared app from router
from backend.router import app

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE INIT
# =============================================================================

def _init_v14():
    """Initialize all v14 databases."""
    try:
        from backend.subscriptions import init_db as init_subs
        init_subs()
    except Exception as e:
        logger.warning("Subscriptions init failed: %s", e)

    try:
        from backend.dashboard import init_db as init_dash
        init_dash()
    except Exception as e:
        logger.warning("Dashboard init failed: %s", e)

# Initialize on module load
_init_v14()


# =============================================================================
# AUTH HELPER
# =============================================================================

def _get_user_id(request: Request) -> str:
    """Extract user_id from API key in header."""
    api_key = request.headers.get("X-API-Key", "anonymous")
    try:
        from backend.subscriptions import get_user_id
        return get_user_id(api_key)
    except Exception:
        # Fallback: hash the key
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]


# =============================================================================
# v14: SUBSCRIPTION ENDPOINTS
# =============================================================================

@app.get("/api/subscription/plans")
async def api_subscription_plans():
    """Get all available subscription plans."""
    try:
        from backend.subscriptions import get_plans
        return JSONResponse({"plans": get_plans()})
    except Exception as e:
        logger.error("Plans error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription")
async def api_subscription_get(request: Request):
    """Get current user's subscription."""
    try:
        from backend.subscriptions import get_or_create_subscription
        user_id = _get_user_id(request)
        return JSONResponse(get_or_create_subscription(user_id))
    except Exception as e:
        logger.error("Subscription get error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subscription/checkout")
async def api_subscription_checkout(request: Request):
    """Create Stripe checkout session."""
    try:
        from backend.subscriptions import create_checkout_session
        import json
        body = await request.body()
        data = json.loads(body) if body else {}
        user_id = _get_user_id(request)
        result = create_checkout_session(user_id, data.get("plan_id", "pro"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Checkout error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subscription/cancel")
async def api_subscription_cancel(request: Request):
    """Cancel subscription."""
    try:
        from backend.subscriptions import cancel_subscription
        user_id = _get_user_id(request)
        return JSONResponse(cancel_subscription(user_id))
    except Exception as e:
        logger.error("Cancel error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription/portal")
async def api_subscription_portal(request: Request):
    """Get Stripe customer portal URL."""
    try:
        from backend.subscriptions import create_customer_portal
        user_id = _get_user_id(request)
        return JSONResponse(create_customer_portal(user_id))
    except Exception as e:
        logger.error("Portal error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription/usage")
async def api_subscription_usage(request: Request):
    """Get usage statistics."""
    try:
        from backend.subscriptions import get_usage
        user_id = _get_user_id(request)
        return JSONResponse(get_usage(user_id))
    except Exception as e:
        logger.error("Usage error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v14: DEVELOPER WORKSPACE ENDPOINTS
# =============================================================================

@app.get("/api/dev/languages")
async def api_dev_languages():
    """Get all supported programming languages."""
    try:
        from backend.developer import get_languages
        return JSONResponse({"languages": get_languages()})
    except Exception as e:
        logger.error("Dev languages error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dev/frameworks")
async def api_dev_frameworks(language: Optional[str] = None):
    """Get supported frameworks, optionally filtered by language."""
    try:
        from backend.developer import get_frameworks
        return JSONResponse({"frameworks": get_frameworks(language)})
    except Exception as e:
        logger.error("Dev frameworks error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dev/methodologies")
async def api_dev_methodologies():
    """Get supported development methodologies."""
    try:
        from backend.developer import get_methodologies
        return JSONResponse({"methodologies": get_methodologies()})
    except Exception as e:
        logger.error("Dev methodologies error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/generate")
async def api_dev_generate(request: Request):
    """Generate code from description."""
    try:
        from backend.developer import generate_code
        import json
        data = json.loads(await request.body())
        result = generate_code(
            prompt=data.get("prompt", ""),
            language=data.get("language", "python"),
            framework=data.get("framework", ""),
            context=data.get("context", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev generate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/review")
async def api_dev_review(request: Request):
    """Review code for issues and improvements."""
    try:
        from backend.developer import review_code
        import json
        data = json.loads(await request.body())
        result = review_code(
            code=data.get("code", ""),
            language=data.get("language", "python"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev review error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/debug")
async def api_dev_debug(request: Request):
    """Debug code with error analysis."""
    try:
        from backend.developer import debug_code
        import json
        data = json.loads(await request.body())
        result = debug_code(
            code=data.get("code", ""),
            error=data.get("error", ""),
            language=data.get("language", "python"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev debug error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/architecture")
async def api_dev_architecture(request: Request):
    """Design system architecture."""
    try:
        from backend.developer import design_architecture
        import json
        data = json.loads(await request.body())
        result = design_architecture(
            description=data.get("description", ""),
            scale=data.get("scale", "medium"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev architecture error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/scaffold")
async def api_dev_scaffold(request: Request):
    """Scaffold a complete project."""
    try:
        from backend.developer import scaffold_project
        import json
        data = json.loads(await request.body())
        result = scaffold_project(
            name=data.get("name", "my-project"),
            project_type=data.get("type", "webapp"),
            language=data.get("language", "python"),
            framework=data.get("framework", ""),
            features=data.get("features", []),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev scaffold error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/explain")
async def api_dev_explain(request: Request):
    """Explain code in natural language."""
    try:
        from backend.developer import explain_code
        import json
        data = json.loads(await request.body())
        result = explain_code(
            code=data.get("code", ""),
            language=data.get("language", "python"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev explain error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/convert")
async def api_dev_convert(request: Request):
    """Convert code between languages."""
    try:
        from backend.developer import convert_code
        import json
        data = json.loads(await request.body())
        result = convert_code(
            code=data.get("code", ""),
            from_lang=data.get("from_language", "python"),
            to_lang=data.get("to_language", "javascript"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev convert error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/tests")
async def api_dev_tests(request: Request):
    """Generate unit tests for code."""
    try:
        from backend.developer import generate_tests
        import json
        data = json.loads(await request.body())
        result = generate_tests(
            code=data.get("code", ""),
            language=data.get("language", "python"),
            test_type=data.get("test_type", "unit"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Dev tests error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v14: WEBSITE BUILDER ENDPOINTS
# =============================================================================

@app.get("/api/website/templates")
async def api_website_templates():
    """List all website templates."""
    try:
        from backend.website_builder import list_templates
        return JSONResponse({"templates": list_templates()})
    except Exception as e:
        logger.error("Website templates error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/website/generate")
async def api_website_generate(request: Request):
    """Generate a website from description."""
    try:
        from backend.website_builder import generate_site
        import json
        data = json.loads(await request.body())
        result = generate_site(
            description=data.get("description", ""),
            template_id=data.get("template_id", ""),
            colors=data.get("colors"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Website generate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/website/components")
async def api_website_components():
    """List all UI components."""
    try:
        from backend.website_builder import list_components
        return JSONResponse({"components": list_components()})
    except Exception as e:
        logger.error("Website components error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/website/build")
async def api_website_build(request: Request):
    """Build a custom page from components."""
    try:
        from backend.website_builder import build_page
        import json
        data = json.loads(await request.body())
        result = build_page(
            components=data.get("components", []),
            settings=data.get("settings", {}),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Website build error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v14: DASHBOARD ENDPOINTS
# =============================================================================

@app.get("/api/dashboard/widgets")
async def api_dashboard_widgets(request: Request):
    """Get user's widgets."""
    try:
        from backend.dashboard import get_widgets
        user_id = _get_user_id(request)
        return JSONResponse({"widgets": get_widgets(user_id)})
    except Exception as e:
        logger.error("Dashboard widgets error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/widgets")
async def api_dashboard_widgets_save(request: Request):
    """Save a widget."""
    try:
        from backend.dashboard import save_widget
        import json
        user_id = _get_user_id(request)
        data = json.loads(await request.body())
        return JSONResponse(save_widget(user_id, data))
    except Exception as e:
        logger.error("Dashboard widgets save error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dashboard/widgets/{widget_id}")
async def api_dashboard_widgets_remove(widget_id: int, request: Request):
    """Remove a widget."""
    try:
        from backend.dashboard import remove_widget
        user_id = _get_user_id(request)
        remove_widget(user_id, widget_id)
        return JSONResponse({"status": "removed", "widget_id": widget_id})
    except Exception as e:
        logger.error("Dashboard widgets remove error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/kb")
async def api_dashboard_kb(request: Request):
    """Get knowledge base pages."""
    try:
        from backend.dashboard import get_kb_pages
        user_id = _get_user_id(request)
        return JSONResponse({"pages": get_kb_pages(user_id)})
    except Exception as e:
        logger.error("Dashboard KB error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/kb")
async def api_dashboard_kb_save(request: Request):
    """Save a knowledge base page."""
    try:
        from backend.dashboard import save_kb_page
        import json
        user_id = _get_user_id(request)
        data = json.loads(await request.body())
        return JSONResponse(save_kb_page(user_id, data))
    except Exception as e:
        logger.error("Dashboard KB save error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/kb/search")
async def api_dashboard_kb_search(q: str, request: Request):
    """Search knowledge base."""
    try:
        from backend.dashboard import search_kb
        user_id = _get_user_id(request)
        return JSONResponse({"results": search_kb(user_id, q)})
    except Exception as e:
        logger.error("Dashboard KB search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/habits")
async def api_dashboard_habits(request: Request):
    """Get habits."""
    try:
        from backend.dashboard import get_habits
        user_id = _get_user_id(request)
        return JSONResponse({"habits": get_habits(user_id)})
    except Exception as e:
        logger.error("Dashboard habits error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/habits")
async def api_dashboard_habits_save(request: Request):
    """Save a habit."""
    try:
        from backend.dashboard import save_habit
        import json
        user_id = _get_user_id(request)
        data = json.loads(await request.body())
        return JSONResponse(save_habit(user_id, data))
    except Exception as e:
        logger.error("Dashboard habits save error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/habits/{habit_id}/track")
async def api_dashboard_habits_track(habit_id: int, request: Request):
    """Track a habit."""
    try:
        from backend.dashboard import track_habit
        user_id = _get_user_id(request)
        return JSONResponse(track_habit(user_id, habit_id))
    except Exception as e:
        logger.error("Dashboard habits track error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/daily")
async def api_dashboard_daily(request: Request):
    """Get daily summary."""
    try:
        from backend.dashboard import get_daily_summary
        user_id = _get_user_id(request)
        return JSONResponse(get_daily_summary(user_id))
    except Exception as e:
        logger.error("Dashboard daily error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v14: AUTO-UPGRADER ENDPOINTS
# =============================================================================

@app.get("/api/system/status")
async def api_system_status():
    """Get full system status."""
    try:
        from backend.auto_upgrader import get_system_status
        return JSONResponse(get_system_status())
    except Exception as e:
        logger.error("System status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/updates")
async def api_system_updates():
    """Check for available updates/improvements."""
    try:
        from backend.auto_upgrader import check_for_updates
        return JSONResponse(check_for_updates())
    except Exception as e:
        logger.error("System updates error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/analyze")
async def api_system_analyze(request: Request):
    """Run capability analysis."""
    try:
        from backend.auto_upgrader import run_capability_analysis
        result = run_capability_analysis()
        return JSONResponse(result)
    except Exception as e:
        logger.error("System analyze error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/improve")
async def api_system_improve(request: Request):
    """Apply an improvement."""
    try:
        from backend.auto_upgrader import apply_improvement
        import json
        data = json.loads(await request.body())
        result = apply_improvement(data.get("task_id", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("System improve error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/changelog")
async def api_system_changelog():
    """Get version changelog."""
    try:
        from backend.auto_upgrader import get_changelog
        return JSONResponse({"changelog": get_changelog()})
    except Exception as e:
        logger.error("System changelog error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/analytics")
async def api_admin_analytics(request: Request, days: int = 7):
    """Get API analytics."""
    try:
        from backend.subscriptions import get_analytics
        return JSONResponse(get_analytics(days=days))
    except Exception as e:
        logger.error("Admin analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/health/detailed")
async def api_admin_health_detailed():
    """Get detailed health check."""
    try:
        from backend.subscriptions import get_health_detailed
        return JSONResponse(get_health_detailed())
    except Exception as e:
        logger.error("Admin health error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v14 endpoints loaded: subscriptions(6), developer(11), website(4), dashboard(13), system(5), admin(2) = 41 new endpoints")
