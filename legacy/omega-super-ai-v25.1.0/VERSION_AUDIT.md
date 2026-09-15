# Luqi AI Version Audit — 2026-07-10

## Current State: v24.4.0 (partial)

### Version Strings Found (INCONSISTENT)

| File | Claims | Should Be |
|------|--------|-----------|
| `backend/router.py` docstring | "v20" | "v24.4.0" |
| `backend/router.py` title | "Luqi AI v24" | "Luqi AI v24.4.0" |
| `backend/router.py` version | "24.3.0" | "24.4.0" |
| `backend/__init__.py` | "24.0.0" | "24.4.0" |
| `README.md` | "24.0.0" | "24.4.0" |
| `web/manifest.json` | "24.3.0" | "24.4.0" |

### Files That ARE on GitHub (confirmed real)

**v24.4.0 Security Hardening (7 files):**
- backend/exception_handler.py (15.3 KB)
- backend/validators.py (17.9 KB)
- backend/db_utils.py (9.4 KB)
- backend/government_services_fix.py (4.7 KB)
- backend/data_portability_fix.py (8.4 KB)
- backend/v24_security_endpoints.py (17.8 KB)
- backend/it_security_training.py — NOT ON GITHUB (287 KB, too large)

**v24.3.0 Infrastructure (7 files):**
- backend/health_system.py (26.6 KB)
- backend/config_validator.py (16.3 KB)
- backend/lifecycle_manager.py (16.0 KB)
- backend/secrets_manager.py (16.2 KB)
- backend/cache_manager.py (9.7 KB)
- backend/background_tasks.py (9.9 KB)
- backend/middleware_enhanced.py (13.4 KB)

**v24.3.0 Digital Wellness & Branding (4 files):**
- backend/branding.py (8.0 KB)
- backend/v24_wellness_endpoints.py (19.1 KB)
- backend/v24_branding_endpoints.py (2.9 KB)
- backend/digital_wellness.py — NOT ON GITHUB (172 KB, too large)

**v24 Core Modules (4 files):**
- backend/v24_endpoints.py (26.9 KB)
- backend/v23_endpoints.py (23.2 KB)
- backend/workspace_agent.py (16.3 KB)
- backend/workspace_collab.py (13.6 KB)

**Fixes for missing imports (2 files):**
- backend/chat.py (4.2 KB)
- backend/financial.py (5.7 KB)

### Files NOT on GitHub (too large for MCP push)

| File | Size | Status |
|------|------|--------|
| backend/digital_wellness.py | 172 KB | EXISTS in sandbox, needs push |
| backend/it_security_training.py | 287 KB | EXISTS in sandbox, needs push |
| web/wellness.html | 80+ KB | EXISTS in sandbox, needs push |

### Router.py Issues

1. Version says "24.3.0" — should be "24.4.0"
2. Docstring says "v20" — should be "v24.4.0"
3. MISSING: import for backend.v24_security_endpoints
4. Has imports for: v14-v24, wellness, branding (all correct)

### How to Fix

1. Pull latest: `git pull origin main`
2. Fix version strings (this file will be updated)
3. Push large files using `py push_training_windows.py YOUR_TOKEN`
