# Luqi-AI Sovereign Entrepreneurial Manual

Africa's sovereign operating machine for economic action, business fortification, and technical creation.

## 1. Sovereign Corporate Tax Estimation & Preparation Assistant

**How it works:**
1. **Data Intake** — provide your figures via `POST /v1/agent/tax-compute` (`gross_revenue`, `allowable_expenses`, `tax_exemptions`).
2. **Autonomous Accounting** — the engine computes taxable income and estimated liability instantly (27% SARS headline baseline).
3. **The 30% Safety Halt** — the filing is NEVER auto-submitted. The engine registers a task in `pending_human_approval` state and returns a `gate_task_id`.
4. **Action Required** — review the calculation, then release it: `POST /v1/human/override/{gate_task_id}?approve=true` with your `X-Luqi-Admin-Auth` header. Unauthorized release attempts are rejected with 403.

> Output is an ESTIMATE, not a filed return. A qualified practitioner must review before any real submission.

## 2. Consumer Shield Mediation Brief Generator

**How it works:**
1. **Incident Intake** — `POST /v1/agent/consumer-shield` with `incident_details`, `company_name`, `target_jurisdiction`.
2. **Statutory Routing** — the engine selects the correct statute automatically (Consumer Protection Act 68 of 2008 for ZAF; generic frameworks elsewhere).
3. **Brief Generation** — you receive a case file with ID, violation summary, restitution demands, and the escalation pathway (National Consumer Commission / industry ombudsman).
4. **Zero dependencies** — this module runs fully offline, no AI keys required.

## 3. Sovereign Tender Scan

See `POST /v1/agent/scan-opportunities` — describe your intent and region; the engine aggregates procurement registers and historical winning frameworks into an execution blueprint with compliance checklist (BBBEE / local content).

## 4. Ground-Up Software Builds

See `POST /v1/agent/dev-build` — describe requirements and target stack; the engine returns a JSON codebase manifest. Compilation inside the isolated Docker lab is Phase 2.
