# Luqi-AI Institutional Technical Readiness (2-page summary)

For TVET College Councils, DHET reviewers, POPIA auditors, and AfDB diligence.
Full details live in the referenced documents.

## 1. Sovereignty & Compliance
- POPIA (Act 4 of 2013) alignment: PII scrubbed before ANY external egress
  (core/pii_scrub.py, tested); data pinned to AWS af-south-1 (Cape Town).
- Postgres FORCE Row-Level Security bound to user country (core/security_rls.sql).
- Voice/biometric exclusions per EULA Section 2 (static/terms.html).
- Emergency invariant: crisis guardrail (SADAG 0800 567 567) is UNFLAGGABLE
  (core/feature_flags.py) and evaluated before any ML (core/hybrid_ai.py).

## 2. Safety Architecture (the 30% gate)
- Every payment, filing, and infrastructure action halts at a human gate
  (PENDING_HUMAN_APPROVAL); admin auth required to release; immutable audit
  trail with hashed operator identity (core/enterprise_models.py).
- 100-thread stress tests prove zero unauthorized completions
  (test_security_gates.py).
- Fail-closed everywhere: no key -> 500, provider outage -> chain fallback,
  contract drift -> 502. No simulated-success path exists.

## 3. Reliability & Operations
- 99.5% SLO with error budgets and automated freeze gate (docs/SRE.md,
  core/ops_metrics.py).
- 6 test suites (100+ tests) including a 65-route backend smoke matrix and a
  20-query golden evaluation set for the student-facing classifier.
- Deployment runbook with human sign-off gates (DEPLOYMENT_RUNBOOK.md);
  IaC for af-south-1 (deploy/terraform); encrypted AES-256-GCM backups with
  restore-drill checklist.

## 4. Economics (measured, then modeled)
- Cost telemetry counts real calls, estimates spend vs MONTHLY_TOKEN_BUDGET_USD,
  SMS-alerts at 80% (core/cost_telemetry.py).
- Subsidy model: premium accounts fund ~1,100 free student sessions/month
  (docs/OMEGA-LUQI_Subsidy_Model.md).
- Pilot target: $0.01 per student session; tier-2 offline resolution free.

## 5. The Moat
- Versioned African TVET intent corpus + golden set (core/golden_set.py) -
  empirical query distributions competitors cannot replicate.
- Admin-gated live calibration with CI-enforced regression floor.

Contact: repository maintainers (see SECURITY.md for disclosure).
