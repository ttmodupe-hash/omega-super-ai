# OMEGA-Super-AI Monolith - Capability Gap Analysis
Audit date: 2026-09-15. Source: ttmodupe-hash/omega-super-ai @ main (v25.1.0 lineage,
351 files, 6.62 MB), archived byte-for-byte at legacy/omega-super-ai-v25.1.0/.

This document maps every monolith capability against the rebuilt engine, so the
consolidation is a deliberate port - not a bulk copy that would regress 30 versions
of hardening (the monolith's api_server.py carries its own unhardened auth and DB).

## Verdict categories
- SUPERSEDED: engine has an equal-or-better equivalent (do not port)
- PARTIAL: engine has a fragment; monolith version worth a port review
- MISSING: no engine equivalent - ranked port candidates

## Ranked port candidates (MISSING)
1. dead_mans_switch.py - digital legacy / inactivity trustee. Unique; no engine equivalent.
2. data_portability.py (+_fix) - POPIA/GDPR-style user data export. Legally valuable, small surface.
3. accessibility_deaf.py - deaf-accessibility services. Unique; on-mission for inclusion.
4. companionship.py - full companionship module; engine has fragments (avatar.js, universal_learning).
5. agricultural_advisor.py (335KB) / automotive.py (230KB) - large domain advisors; evaluate overlap
   with sovereign_core/universal_learning before porting (likely consolidation candidates, not new engines).
6. knowledge_academy.py / education_system.py - compare against pedagogy_engine; port the delta.

## PARTIAL (port review)
- lang/ package (african_languages, language_detector, multilingual_router, tts_stt)
  -> engine has languages.html + speechSynthesis; detector/router logic worth porting.
- jobs_skills.py -> skill_engine.py exists; monolith's job-market data worth a look.
- financial.py / business_advisor.py -> action_engine + tax_matrix exist; port any unique matrices.
- healthcare_assistant.py / health_system.py -> health_sources exists; port unique flows.
- law_studies.py -> consumer_shield exists; port any unique statute packs.
- offline_engine.py -> PWA sw.js + roadmap TinyML core; port any genuinely offline logic.
- physics_simulator.py / netai_simulator.py -> dev sandbox + verify harness; port sim definitions if richer.
- education_system.py -> pedagogy_engine; port assessment-bank data if present.
- jarvis_agent.py / luqi_agent.py -> persona layer; the engine's avatar is visual-only - port dialogue persona data.
- prometheus/ + metrics_dashboard.py -> ops_metrics + telemetry boards; port any unique metric definitions.

## SUPERSEDED (do not port)
api_server.py (monolith), middleware*.py, db_utils.py, exception_handler.py,
cache_manager.py, background_tasks.py, lifecycle_manager.py, auto_upgrader.py,
github_integration.py, alert_system.py, email_alerts/email_system.py,
notifications.py, memory.py, cognitive_engine.py, ai_engine.py, agents.py,
chat.py, dashboard.py, images.py, files.py, branding.py, config*.py,
captainship.py, government_services_fix.py, netai_training.py, health_monitor.py,
middleware_enhanced.py, developer.py.

## Archive inventory (preserved as-is, no port planned)
- training_parts/ (79 files) - training data/prompt fragments; archive only.
- v3/ (61 files) - versioned legacy snapshots; archive only.
- web/ (10 files) - legacy web assets; the PWA supersedes.
- omega/ (19 files) - omega-era core; superseded.
- Root: launch plans, version audits, push/fix utility scripts - retained for archaeology.

## Method note
Mapping done from the monolith's file inventory (all 351 paths + sizes). Content-level
review of each port candidate happens at port time, at the house standard (tested,
fail-closed, import-safe) - never by copying files wholesale.
