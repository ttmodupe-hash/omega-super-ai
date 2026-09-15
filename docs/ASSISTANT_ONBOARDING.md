# Assistant Onboarding - Repository as Source of Truth

Paste the block below as the FIRST message of any new assistant session
(Kimi, Claude, GPT, or this engine's companion). It replaces chat-history
isolation with the repo as the single, immutable record.

---

Please scan the repository https://github.com/ttmodupe-hash/omega-super-ai.
Read these files in order before any other work:
1. docs/OMEGA_STREAM_COVERAGE.md - the ledger: everything merged, rejected, open
2. docs/OMEGA_SUPERAI_GAP_ANALYSIS.md - monolith capability map + port priorities
3. CHANGELOG.md - version history and what each release enables
4. CONTRIBUTING.md - the house standard (fail-closed, no simulated data,
   import-safety, 30% gate is sacred, PII scrub, one-line-idea protocol)
5. DEPLOYMENT_RUNBOOK.md - if the task touches infrastructure

House rules you must follow without being reminded:
- No simulated or fabricated behavior anywhere; fail closed loudly.
- Secrets come from .env only; never commit, print, or accept them in chat.
- Every freeze at the 30% Human Gate stays sacred; new critical actions join CRITICAL_ACTIONS.
- New modules must import with only fastapi+pydantic; heavy deps load lazily.
- Every change ships with tests; the suites are the definition of done.
- Update CHANGELOG.md and the coverage ledger with every PR.

---

Why this works: chat histories are invisible across sessions, but the repo is
not. The ledger makes the repo complete by construction (one-line ideas are
built here, then recorded), so any assistant that reads it starts exactly where
the last session ended.
