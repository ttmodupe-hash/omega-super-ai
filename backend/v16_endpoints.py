"""Luqi AI v16 — Production Endpoints

GitHub integration, push notifications, data portability endpoints.
"""

import json
import logging
from typing import Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse

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
# GITHUB INTEGRATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/dev/github/auth")
async def api_github_auth(pat: str = Query(...)):
    """Verify GitHub PAT and return user info."""
    try:
        from backend.github_integration import auth_with_pat
        return JSONResponse(auth_with_pat(pat))
    except Exception as e:
        logger.error("GitHub auth error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dev/github/repos")
async def api_github_repos(pat: str = Query(...), page: int = 1):
    """List user's GitHub repositories."""
    try:
        from backend.github_integration import list_repos
        return JSONResponse({"repos": list_repos(pat, page)})
    except Exception as e:
        logger.error("GitHub repos error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/github/repo")
async def api_github_create_repo(request: Request):
    """Create a new GitHub repository."""
    try:
        from backend.github_integration import create_repo
        data = json.loads(await request.body())
        result = create_repo(data["pat"], data["name"], data.get("description", ""),
                           data.get("private", False))
        return JSONResponse(result)
    except Exception as e:
        logger.error("GitHub create repo error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/github/push")
async def api_github_push(request: Request):
    """Push files to a GitHub repository."""
    try:
        from backend.github_integration import push_files
        data = json.loads(await request.body())
        result = push_files(data["pat"], data["owner"], data["repo"],
                          data["files"], data.get("message", "Update from Luqi AI"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("GitHub push error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/github/project")
async def api_github_project(request: Request):
    """One-click: create repo + push project files."""
    try:
        from backend.github_integration import push_project
        data = json.loads(await request.body())
        result = push_project(data["pat"], data["owner"], data["repo_name"],
                            data["files"], data.get("description", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("GitHub project error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dev/github/review")
async def api_github_review(pat: str = Query(...), owner: str = Query(...), repo: str = Query(...)):
    """Review a GitHub repository."""
    try:
        from backend.github_integration import review_repo
        return JSONResponse(review_repo(pat, owner, repo))
    except Exception as e:
        logger.error("GitHub review error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/github/branch")
async def api_github_branch(request: Request):
    """Create a new branch."""
    try:
        from backend.github_integration import create_branch
        data = json.loads(await request.body())
        result = create_branch(data["pat"], data["owner"], data["repo"],
                             data["branch"], data.get("from_branch", "main"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("GitHub branch error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dev/github/pr")
async def api_github_pr(request: Request):
    """Create a pull request."""
    try:
        from backend.github_integration import create_pull_request
        data = json.loads(await request.body())
        result = create_pull_request(data["pat"], data["owner"], data["repo"],
                                    data["title"], data["head"], data.get("base", "main"),
                                    data.get("body", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("GitHub PR error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# PUSH NOTIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/notifications/vapid-key")
async def api_vapid_key():
    """Get VAPID public key for push subscription."""
    try:
        from backend.notifications import get_vapid_public_key
        return JSONResponse({"publicKey": get_vapid_public_key()})
    except Exception as e:
        logger.error("Vapid key error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/subscribe")
async def api_notifications_subscribe(request: Request):
    """Subscribe to push notifications."""
    try:
        from backend.notifications import PushSubscriptionManager
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        mgr = PushSubscriptionManager()
        result = mgr.subscribe(user_id, data)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Subscribe error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/unsubscribe")
async def api_notifications_unsubscribe(request: Request):
    """Unsubscribe from push notifications."""
    try:
        from backend.notifications import PushSubscriptionManager
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        mgr = PushSubscriptionManager()
        result = mgr.unsubscribe(user_id, data.get("endpoint", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Unsubscribe error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/send")
async def api_notifications_send(request: Request):
    """Send a push notification."""
    try:
        from backend.notifications import send_push, render_notification
        data = json.loads(await request.body())
        if data.get("template"):
            payload = render_notification(data["template"], **data.get("vars", {}))
        else:
            payload = data.get("payload", {})
        result = send_push(data["subscription"], payload)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Send notification error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/broadcast")
async def api_notifications_broadcast(request: Request):
    """Broadcast notification to users."""
    try:
        from backend.notifications import broadcast_push, render_notification
        data = json.loads(await request.body())
        if data.get("template"):
            payload = render_notification(data["template"], **data.get("vars", {}))
        else:
            payload = data.get("payload", {})
        result = broadcast_push(data.get("user_ids", []), payload)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Broadcast error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/schedule")
async def api_notifications_schedule(request: Request):
    """Schedule a recurring notification."""
    try:
        from backend.notifications import NotificationScheduler
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        sched = NotificationScheduler()
        result = sched.schedule(
            user_id, data["type"], data.get("frequency", "daily"),
            data.get("time", "09:00"), data.get("payload", {})
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Schedule error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/templates")
async def api_notifications_templates():
    """List available notification templates."""
    try:
        from backend.notifications import NOTIFICATION_TEMPLATES
        return JSONResponse({"templates": list(NOTIFICATION_TEMPLATES.keys())})
    except Exception as e:
        logger.error("Templates error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# DATA PORTABILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/export/all")
async def api_export_all(request: Request, format: str = "json"):
    """Export all user data (GDPR data portability)."""
    try:
        from backend.data_portability import export_user_data
        user_id = _get_user_id(request)
        result = export_user_data(user_id, format)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Export all error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/conversations")
async def api_export_conversations(request: Request, format: str = "json"):
    """Export chat conversations."""
    try:
        from backend.data_portability import export_conversations
        user_id = _get_user_id(request)
        result = export_conversations(user_id, format)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Export conversations error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/zip")
async def api_export_zip(request: Request):
    """Export all user data as ZIP archive."""
    try:
        from backend.data_portability import create_zip_export
        user_id = _get_user_id(request)
        result = create_zip_export(user_id)
        if result.get("file_path"):
            return FileResponse(result["file_path"], filename=result["file_name"])
        return JSONResponse(result)
    except Exception as e:
        logger.error("Export zip error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import")
async def api_import_data(request: Request):
    """Import previously exported data."""
    try:
        from backend.data_portability import import_user_data, validate_import_data
        data = json.loads(await request.body())
        validation = validate_import_data(data)
        if not validation.get("valid"):
            return JSONResponse({"error": "Invalid data", "details": validation})
        user_id = _get_user_id(request)
        result = import_user_data(user_id, data)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Import error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/user/data")
async def api_delete_user_data(request: Request):
    """Delete all user data (GDPR right to erasure)."""
    try:
        from backend.data_portability import delete_all_user_data
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        result = delete_all_user_data(user_id, data.get("confirmation", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Delete data error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/anonymize")
async def api_anonymize_user_data(request: Request):
    """Anonymize user data."""
    try:
        from backend.data_portability import anonymize_user_data
        user_id = _get_user_id(request)
        result = anonymize_user_data(user_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Anonymize error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v16 endpoints loaded: github(8), notifications(7), data_portability(6) = 21 new endpoints")
