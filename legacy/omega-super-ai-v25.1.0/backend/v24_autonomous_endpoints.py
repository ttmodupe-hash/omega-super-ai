"""Luqi AI v24.4.0 — Autonomous System Endpoints
=================================================
Registers all multi-agent system endpoints.

This module imports the shared FastAPI app instance and registers
all autonomous orchestrator endpoints via register_system_endpoints().

Endpoints registered:
  GET  /api/system/status           — Full system status (all agents)
  GET  /api/system/config           — Current configuration
  POST /api/system/config           — Update configuration
  POST /api/system/health-check     — Trigger health check
  POST /api/system/research/run     — Trigger research cycle
  POST /api/system/submit-update    — Submit code for validation
  POST /api/system/approve-deploy/{id} — Human approval + deploy
  POST /api/system/rollback         — Emergency rollback
  GET  /api/system/alerts           — Active alerts
  POST /api/system/alerts/ack       — Acknowledge alert

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from backend.router import app
from backend.autonomous_system import register_system_endpoints

# Register all autonomous system endpoints on the shared app instance
register_system_endpoints(app)
