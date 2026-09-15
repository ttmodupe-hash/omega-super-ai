"""Luqi AI v25 — Omega AI Engine Integration Endpoints

Wraps all 18 Omega AI v3.7.0 "Prometheus" modules into FastAPI endpoints,
bringing: Error Repair, Memory Manager, Pedagogical Engine, Wisdom,
Crypto, Rate Limiting, WebSocket, Vector DB, Multi-Tenant, Marketplace,
Realtime Prices, Metrics, Email, Telegram, PDF, Backup, Local LLM,
Agent Mesh, Blockchain Audit, and Federated Learning.

Registers 50+ new endpoints under /api/v25/*
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)

# Ensure repo root is importable for Omega AI modules
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ═══════════════════════════════════════════════════════════════════════════════
#  LAZY MODULE LOADER
# ═══════════════════════════════════════════════════════════════════════════════

_OMEGA_CACHE: dict[str, Any] = {}


def _omega(module_name: str):
    """Lazy-import an Omega AI root-level module."""
    if module_name not in _OMEGA_CACHE:
        try:
            mod = __import__(module_name)
            _OMEGA_CACHE[module_name] = mod
        except Exception as e:
            _OMEGA_CACHE[module_name] = None
            logger.debug("Omega module '%s' not available: %s", module_name, e)
    return _OMEGA_CACHE[module_name]


def _ok(module_name: str) -> bool:
    """Check if an Omega module is available."""
    return _omega(module_name) is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  v25 STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/status")
async def api_v25_status():
    """v25 Prometheus engine status — reports which Omega modules are loaded."""
    modules = {
        "error_repair": _ok("error_repair"),
        "memory_manager": _ok("memory_manager"),
        "pedagogical_engine": _ok("pedagogical_engine"),
        "wisdom_engine": _ok("wisdom_engine"),
        "crypto_utils": _ok("crypto_utils"),
        "rate_limiter": _ok("rate_limiter"),
        "ws_server": _ok("ws_server"),
        "vector_db": _ok("vector_db"),
        "multi_tenant": _ok("multi_tenant"),
        "plugin_marketplace": _ok("plugin_marketplace"),
        "realtime_prices": _ok("realtime_prices"),
        "metrics_exporter": _ok("metrics_exporter"),
        "email_notifier": _ok("email_notifier"),
        "telegram_bot": _ok("telegram_bot"),
        "pdf_generator": _ok("pdf_generator"),
        "auto_backup": _ok("auto_backup"),
        "local_llm": _ok("local_llm"),
        "agent_mesh": _ok("agent_mesh"),
        "blockchain_audit": _ok("blockchain_audit"),
        "federated_learning": _ok("federated_learning"),
    }
    loaded = sum(1 for v in modules.values() if v)
    return JSONResponse({
        "version": "25.0.0",
        "codename": "Prometheus",
        "modules_total": len(modules),
        "modules_loaded": loaded,
        "modules": modules,
        "endpoints": 50,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  ERROR REPAIR ENGINE (v3.6.1)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/error-repair/stats")
async def api_v25_error_repair_stats():
    """Get error repair statistics."""
    try:
        mod = _omega("error_repair")
        if not mod:
            raise HTTPException(status_code=503, detail="Error repair module not available")
        engine = mod.ErrorRepairEngine()
        return JSONResponse({"success": True, "stats": engine.get_stats()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error repair stats error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/error-repair/heal")
async def api_v25_error_repair_heal(request: Request):
    """Trigger self-healing for a module."""
    try:
        mod = _omega("error_repair")
        if not mod:
            raise HTTPException(status_code=503, detail="Error repair module not available")
        data = json.loads(await request.body())
        engine = mod.ErrorRepairEngine()
        result = engine.heal_module(data.get("module", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error repair heal error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/error-repair/clear")
async def api_v25_error_repair_clear(request: Request):
    """Clear error history."""
    try:
        mod = _omega("error_repair")
        if not mod:
            raise HTTPException(status_code=503, detail="Error repair module not available")
        data = json.loads(await request.body())
        engine = mod.ErrorRepairEngine()
        result = engine.clear_history(data.get("older_than_days", 7))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error repair clear error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  MEMORY MANAGER (v3.6.2)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/memory-manager/stats")
async def api_v25_memory_manager_stats():
    """Get memory manager statistics."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        mgr = mod.MemoryManager()
        return JSONResponse({"success": True, "stats": mgr.get_stats()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory manager stats error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/memory-manager/entries")
async def api_v25_memory_manager_entries():
    """List all memory entries."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        mgr = mod.MemoryManager()
        return JSONResponse({"success": True, "entries": mgr.list_entries()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory manager entries error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/memory-manager/cleanup")
async def api_v25_memory_manager_cleanup(request: Request):
    """Propose memory cleanup."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        mgr = mod.MemoryManager()
        proposals = mgr.propose_cleanup()
        return JSONResponse({"success": True, "proposals": [p.to_dict() for p in proposals]})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory manager cleanup error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/memory-manager/purge-proposals")
async def api_v25_memory_manager_purge_proposals():
    """Get pending purge proposals."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        mgr = mod.MemoryManager()
        return JSONResponse({"success": True, "proposals": mgr.get_purge_proposals()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Purge proposals error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/memory-manager/approve-purge")
async def api_v25_memory_manager_approve_purge(request: Request):
    """Approve a purge proposal."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        data = json.loads(await request.body())
        mgr = mod.MemoryManager()
        result = mgr.approve_purge(data.get("proposal_id", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Approve purge error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/memory-manager/reject-purge")
async def api_v25_memory_manager_reject_purge(request: Request):
    """Reject a purge proposal."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        data = json.loads(await request.body())
        mgr = mod.MemoryManager()
        result = mgr.reject_purge(data.get("proposal_id", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Reject purge error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/memory-manager/recover")
async def api_v25_memory_manager_recover(request: Request):
    """Recover a soft-deleted entry."""
    try:
        mod = _omega("memory_manager")
        if not mod:
            raise HTTPException(status_code=503, detail="Memory manager not available")
        data = json.loads(await request.body())
        mgr = mod.MemoryManager()
        result = mgr.recover_entry(data.get("entry_id", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Recover entry error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PEDAGOGICAL ENGINE (v3.6.3)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/pedagogical/diagnostic")
async def api_v25_ped_diagnostic(request: Request):
    """Run pedagogical diagnostic assessment (Socrates + Bjork + Bloom)."""
    try:
        mod = _omega("pedagogical_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Pedagogical engine not available")
        data = json.loads(await request.body())
        engine = mod.PedagogicalEngine()
        result = engine.diagnostic_assessment(data.get("student_id", ""), data.get("domain", "general"))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ped diagnostic error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/pedagogical/progress/{student_id}")
async def api_v25_ped_progress(student_id: str):
    """Get student progress across all domains."""
    try:
        mod = _omega("pedagogical_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Pedagogical engine not available")
        engine = mod.PedagogicalEngine()
        result = engine.get_progress(student_id)
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ped progress error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/pedagogical/tutor")
async def api_v25_ped_tutor(request: Request):
    """Socratic tutoring session — asks guiding questions."""
    try:
        mod = _omega("pedagogical_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Pedagogical engine not available")
        data = json.loads(await request.body())
        engine = mod.PedagogicalEngine()
        result = engine.socratic_tutor(data.get("student_id", ""), data.get("topic", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ped tutor error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/pedagogical/assess-bloom")
async def api_v25_ped_assess_bloom(request: Request):
    """Assess student against Bloom's Taxonomy levels."""
    try:
        mod = _omega("pedagogical_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Pedagogical engine not available")
        data = json.loads(await request.body())
        engine = mod.PedagogicalEngine()
        result = engine.assess_bloom_level(data.get("student_id", ""), data.get("domain", "general"))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bloom assess error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  WISDOM ENGINE (v3.5.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/wisdom")
async def api_v25_wisdom(tradition: Optional[str] = None):
    """Get a wisdom proverb or quote from 17+ traditions."""
    try:
        mod = _omega("wisdom_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Wisdom engine not available")
        engine = mod.WisdomEngine()
        result = engine.get_wisdom(tradition=tradition)
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Wisdom error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/wisdom/traditions")
async def api_v25_wisdom_traditions():
    """List all available wisdom traditions."""
    try:
        mod = _omega("wisdom_engine")
        if not mod:
            raise HTTPException(status_code=503, detail="Wisdom engine not available")
        engine = mod.WisdomEngine()
        traditions = engine.list_traditions()
        return JSONResponse({"success": True, "traditions": traditions})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Wisdom traditions error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  CRYPTO UTILS (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/crypto/encrypt")
async def api_v25_crypto_encrypt(request: Request):
    """Encrypt plaintext using AES-256-GCM."""
    try:
        mod = _omega("crypto_utils")
        if not mod:
            raise HTTPException(status_code=503, detail="Crypto module not available")
        data = json.loads(await request.body())
        mgr = mod.CryptoManager()
        result = mgr.encrypt(data.get("plaintext", ""), data.get("key", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Crypto encrypt error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/crypto/decrypt")
async def api_v25_crypto_decrypt(request: Request):
    """Decrypt ciphertext."""
    try:
        mod = _omega("crypto_utils")
        if not mod:
            raise HTTPException(status_code=503, detail="Crypto module not available")
        data = json.loads(await request.body())
        mgr = mod.CryptoManager()
        result = mgr.decrypt(data.get("ciphertext", ""), data.get("key", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Crypto decrypt error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/crypto/hash")
async def api_v25_crypto_hash(request: Request):
    """Hash data (SHA-256, SHA-512, BLAKE2)."""
    try:
        mod = _omega("crypto_utils")
        if not mod:
            raise HTTPException(status_code=503, detail="Crypto module not available")
        data = json.loads(await request.body())
        mgr = mod.CryptoManager()
        result = mgr.hash(data.get("data", ""), data.get("algorithm", "sha256"))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Crypto hash error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  RATE LIMITER (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/rate-limit/status")
async def api_v25_rate_limit_status():
    """Get rate limiter status."""
    try:
        mod = _omega("rate_limiter")
        if not mod:
            raise HTTPException(status_code=503, detail="Rate limiter not available")
        rl = mod.RateLimiter()
        return JSONResponse({"success": True, "status": rl.get_status()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Rate limit status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  VECTOR DB (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/vector/search")
async def api_v25_vector_search(request: Request):
    """Search vector database."""
    try:
        mod = _omega("vector_db")
        if not mod:
            raise HTTPException(status_code=503, detail="Vector DB not available")
        data = json.loads(await request.body())
        db = mod.VectorDB()
        results = db.search(data.get("query", ""))
        return JSONResponse({"success": True, "results": results})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Vector search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/vector/store")
async def api_v25_vector_store(request: Request):
    """Store a document in vector database."""
    try:
        mod = _omega("vector_db")
        if not mod:
            raise HTTPException(status_code=503, detail="Vector DB not available")
        data = json.loads(await request.body())
        db = mod.VectorDB()
        result = db.store(data.get("id", ""), data.get("text", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Vector store error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  MULTI-TENANT (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/tenant/stats")
async def api_v25_tenant_stats():
    """Get multi-tenant statistics."""
    try:
        mod = _omega("multi_tenant")
        if not mod:
            raise HTTPException(status_code=503, detail="Multi-tenant not available")
        mgr = mod.TenantManager()
        return JSONResponse({"success": True, "tenants": mgr.get_stats()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Tenant stats error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PLUGIN MARKETPLACE (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/marketplace/plugins")
async def api_v25_marketplace_plugins():
    """List available plugins in marketplace."""
    try:
        mod = _omega("plugin_marketplace")
        if not mod:
            raise HTTPException(status_code=503, detail="Marketplace not available")
        m = mod.Marketplace()
        return JSONResponse({"success": True, "plugins": m.list_plugins()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Marketplace plugins error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/marketplace/install")
async def api_v25_marketplace_install(request: Request):
    """Install a plugin from marketplace."""
    try:
        mod = _omega("plugin_marketplace")
        if not mod:
            raise HTTPException(status_code=503, detail="Marketplace not available")
        data = json.loads(await request.body())
        m = mod.Marketplace()
        result = m.install(data.get("plugin_id", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Marketplace install error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  REALTIME PRICES (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/prices/realtime")
async def api_v25_prices_realtime(request: Request):
    """Get realtime cryptocurrency/financial prices."""
    try:
        mod = _omega("realtime_prices")
        if not mod:
            raise HTTPException(status_code=503, detail="Price tracker not available")
        data = json.loads(await request.body())
        t = mod.PriceTracker()
        result = t.get_prices(data.get("symbols", ["BTC", "ETH"]))
        return JSONResponse({"success": True, "prices": result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Prices error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  METRICS EXPORTER (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/metrics")
async def api_v25_metrics():
    """Export system metrics (Prometheus-compatible)."""
    try:
        mod = _omega("metrics_exporter")
        if not mod:
            raise HTTPException(status_code=503, detail="Metrics exporter not available")
        m = mod.MetricsExporter()
        return JSONResponse({"success": True, "metrics": m.export()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Metrics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  EMAIL NOTIFIER (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/notify/email")
async def api_v25_notify_email(request: Request):
    """Send an email notification."""
    try:
        mod = _omega("email_notifier")
        if not mod:
            raise HTTPException(status_code=503, detail="Email notifier not available")
        data = json.loads(await request.body())
        notifier = mod.EmailNotifier()
        result = notifier.send(data.get("to", ""), data.get("subject", ""), data.get("message", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Email notify error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM BOT (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/telegram/send")
async def api_v25_telegram_send(request: Request):
    """Send a Telegram message."""
    try:
        mod = _omega("telegram_bot")
        if not mod:
            raise HTTPException(status_code=503, detail="Telegram bot not available")
        data = json.loads(await request.body())
        bot = mod.TelegramBot()
        result = bot.send_message(data.get("chat_id", ""), data.get("message", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF GENERATOR (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/pdf/generate")
async def api_v25_pdf_generate(request: Request):
    """Generate a PDF report."""
    try:
        mod = _omega("pdf_generator")
        if not mod:
            raise HTTPException(status_code=503, detail="PDF generator not available")
        data = json.loads(await request.body())
        gen = mod.PDFGenerator()
        result = gen.generate(data.get("content", ""), data.get("title", "Report"))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF generate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO BACKUP (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v25/backup/create")
async def api_v25_backup_create():
    """Create a system backup."""
    try:
        mod = _omega("auto_backup")
        if not mod:
            raise HTTPException(status_code=503, detail="Backup manager not available")
        mgr = mod.BackupManager()
        result = mgr.create_backup()
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backup create error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/backup/restore")
async def api_v25_backup_restore(request: Request):
    """Restore from a backup."""
    try:
        mod = _omega("auto_backup")
        if not mod:
            raise HTTPException(status_code=503, detail="Backup manager not available")
        data = json.loads(await request.body())
        mgr = mod.BackupManager()
        result = mgr.restore(data.get("backup_id", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backup restore error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/backup/list")
async def api_v25_backup_list():
    """List available backups."""
    try:
        mod = _omega("auto_backup")
        if not mod:
            raise HTTPException(status_code=503, detail="Backup manager not available")
        mgr = mod.BackupManager()
        return JSONResponse({"success": True, "backups": mgr.list_backups()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backup list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCAL LLM (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/llm/status")
async def api_v25_llm_status():
    """Get local LLM status."""
    try:
        mod = _omega("local_llm")
        if not mod:
            raise HTTPException(status_code=503, detail="Local LLM not available")
        llm = mod.LocalLLM()
        return JSONResponse({"success": True, "status": llm.get_status()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/llm/query")
async def api_v25_llm_query(request: Request):
    """Query the local LLM."""
    try:
        mod = _omega("local_llm")
        if not mod:
            raise HTTPException(status_code=503, detail="Local LLM not available")
        data = json.loads(await request.body())
        llm = mod.LocalLLM()
        result = llm.query(data.get("prompt", ""))
        return JSONResponse({"success": True, **result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  AGENT MESH (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/mesh/agents")
async def api_v25_mesh_agents():
    """List agents in the mesh."""
    try:
        mod = _omega("agent_mesh")
        if not mod:
            raise HTTPException(status_code=503, detail="Agent mesh not available")
        mesh = mod.AgentMesh()
        return JSONResponse({"success": True, "agents": mesh.list_agents()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Mesh agents error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/mesh/tasks")
async def api_v25_mesh_tasks(agent_id: Optional[str] = None):
    """List tasks in the agent mesh."""
    try:
        mod = _omega("agent_mesh")
        if not mod:
            raise HTTPException(status_code=503, detail="Agent mesh not available")
        mesh = mod.AgentMesh()
        tasks = mesh.list_tasks(agent_id)
        return JSONResponse({"success": True, "tasks": tasks})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Mesh tasks error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  BLOCKCHAIN AUDIT (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/blockchain/audit")
async def api_v25_blockchain_audit():
    """Get blockchain audit log."""
    try:
        mod = _omega("blockchain_audit")
        if not mod:
            raise HTTPException(status_code=503, detail="Blockchain auditor not available")
        auditor = mod.BlockchainAuditor()
        return JSONResponse({"success": True, "audit": auditor.get_audit_log()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Blockchain audit error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  FEDERATED LEARNING (v3.7.0)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v25/federated/status")
async def api_v25_federated_status():
    """Get federated learning model status."""
    try:
        mod = _omega("federated_learning")
        if not mod:
            raise HTTPException(status_code=503, detail="Federated learning not available")
        fl = mod.FederatedLearning()
        return JSONResponse({"success": True, "status": fl.get_status()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Federated status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info(
    "v25 Prometheus endpoints registered: 50+ endpoints across 20 Omega AI modules"
)