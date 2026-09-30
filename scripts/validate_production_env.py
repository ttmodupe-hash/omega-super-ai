#!/usr/bin/env python3
"""
Luqi AI Production Readiness Validator
Validates runtime configuration, state backend multi-worker safety, and secret entropy.

HARVEST-SEC (MERGE-1): rescued from an accidental paste inside .env.example
(engine commit 8e73ff1) and re-homed here — an env file must never contain code.
"""

import os
import sys
import json
import re

def validate_production_env():
    errors = []
    warnings = []

    # 1. Admin Secret Entropy Check
    admin_secret = os.getenv("LUQI_ADMIN_SECRET", "")
    if "CHANGEME" in admin_secret or len(admin_secret) < 64:
        errors.append("LUQI_ADMIN_SECRET must be set using a 32-byte hex string (openssl rand -hex 32).")

    # 2. XI API Key Verification
    xi_key = os.getenv("XI_API_KEY", "")
    if not xi_key or "CHANGEME" in xi_key:
        errors.append("XI_API_KEY is missing or contains placeholder values.")

    # 3. Model Engine Verification
    model = os.getenv("KIMI_MODEL", "kimi-k3")
    if model == "moonshot-v1-auto":
        errors.append("KIMI_MODEL moonshot-v1-auto sunset on 2026-08-31. Use 'kimi-k3' or 'kimi-k2.7-code'.")

    # 4. Multi-Worker State Backend Check
    state_backend = os.getenv("STATE_BACKEND", "in-memory")
    redis_url = os.getenv("REDIS_URL", "")
    if state_backend == "redis" and not redis_url:
        errors.append("STATE_BACKEND is set to 'redis' but REDIS_URL is not configured.")

    # 5. CORS Origins Validation
    cors_origins = os.getenv("LUQI_CORS_ORIGINS", "")
    if "*" in cors_origins:
        errors.append("LUQI_CORS_ORIGINS contains wildcard '*'. Browsers reject wildcard CORS with credentials.")

    # 6. JSON Price Table Parsing
    price_table = os.getenv("STRIPE_PRICE_TABLE", "")
    if price_table:
        try:
            json.loads(price_table)
        except json.JSONDecodeError as e:
            errors.append(f"STRIPE_PRICE_TABLE is invalid JSON: {e}")

    # Output Results
    if errors:
        print("\033[91m❌ PRODUCTION BOOT BLOCKED - Configuration Errors Detected:\033[0m")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\033[92m✅ Luqi AI Engine Production Pre-Flight Check Passed Successfully.\033[0m")

if __name__ == "__main__":
    validate_production_env()
