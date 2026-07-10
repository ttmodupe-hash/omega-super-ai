"""Luqi AI v24.5.0 — Metrics Dashboard

Time-series metrics tracking for the autonomous system.

Features:
  - Tracks CPU, memory, disk usage over time
  - Records API response times and error rates
  - Stores historical data in JSON file (data/metrics.jsonl)
  - Provides trend analysis (is system getting worse?)
  - FastAPI endpoints for dashboard data
  - Configurable retention (default: keep 7 days)

Part of Luqi AI v24.5.0 by Limitless Telecoms
"""
