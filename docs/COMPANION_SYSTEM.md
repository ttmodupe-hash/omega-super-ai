# Companion System — Bounded Self-Improvement Contract (UNIFY-12)

**Status:** shipped in `core/companion_engine.py` + `core/companion_models.py` +
migration `005_companion_system`. Router: `/v1/companion/*` (all auth-gated).

## What the companion is now

| Capability | Before | Now |
|---|---|---|
| Identity | none (stateless calls) | persistent profile: name, personality sliders (warmth/humor/formality 1–5), level, trust score, streak |
| Memory | `core/memory.py` — per-boot, in-memory | `companion_memories` — durable, PII-scrubbed, importance-ranked, capped at 200/user |
| Feedback | `core/feedback.py` — per-boot capture, docstring: *"the learning loop that consumes it is a separate, deliberate build"* | `companion_feedback` — durable; **this system is that loop** |
| Training | none | deterministic rule engine → whitelisted directives → prompt-level behavior change, fully audited |
| Proactivity | none | `/checkin`: streak health, spaced-repetition reviews due, suggested next action — computed, works with no AI key |
| AI pipeline | `omega/companion.py` used OpenAI `gpt-4o-mini` | unified `core/kimi_client.chat_completion` (Kimi K3), fail-closed |

## The bounded self-improvement contract

Self-improvement here means **exactly this and nothing more**:

```
feedback rows → deterministic keyword rules → whitelisted (knob, value) pairs
→ companion_directives table → fixed template sentences in the system prompt
→ measurable behavior change, auditable in companion_training_log
```

**Guardrails (enforced in code, not just docs):**

1. **Closed behavior space.** Only 6 knobs × whitelisted values
   (`DIRECTIVE_KNOBS`), max 8 active directives per user.
2. **Injection-safe.** Raw feedback text *never* enters the prompt. A
   directive can only render as one of the fixed sentences in
   `DIRECTIVE_PROMPT_LINES`. Verified by test: a feedback comment of
   "Ignore all previous instructions" produces no prompt change.
3. **No self-modifying code.** The trainer writes database rows only.
   No code generation, no model weight updates, no autonomous prompt edits.
4. **Auditable.** Every directive change logs `old_value → new_value` plus
   the exact feedback row ids that caused it (`/v1/companion/training-log`).
5. **Honest degradation.** No DB → 503. No KIMI_API_KEY → fail-closed 500
   (house contract). No fake profiles, no fake recall.

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/companion/profile` | get-or-create companion identity |
| PUT | `/v1/companion/profile` | name, personality sliders, level |
| POST | `/v1/companion/chat` | modes: chat / mentor / coach / quiz / explain |
| POST | `/v1/companion/memory` | durable remember (scrubbed, importance 1–5) |
| GET | `/v1/companion/memory?topic=` | recall (bumps spaced-repetition counters) |
| POST | `/v1/companion/feedback` | rate 1–5 + comment (feeds trainer) |
| POST | `/v1/companion/train` | run bounded training pass |
| GET | `/v1/companion/directives` | current trained behavior |
| PUT | `/v1/companion/directives` | explicit knob set (whitelist-enforced) |
| GET | `/v1/companion/training-log` | audit trail of behavior changes |
| GET | `/v1/companion/checkin` | proactive: streak, due reviews, next action |

## Feedback rules (deterministic, inspectable)

Examples: "too long" → `verbosity=concise`; "more examples" →
`example_density=high`; "too fast"/"confusing" → `pace=slower`;
"setswana"/"zulu"/"afrikaans" → `language_mix=local_flavor`; rating ≤ 2 with
no keyword → `example_density=high` (safest correction); rating ≥ 4 with no
keyword → reinforces existing directives (evidence only, no change).
Full table: `_FEEDBACK_RULES` in `core/companion_engine.py`.

## Notes

- `omega/companion.py` (CLI-side mentorship module) remains; its
  `progress_check` paramstyle bug (`?` on non-sqlite drivers) is fixed —
  driver-aware `_fetch_progress_rows`.
- Companion tables carry `country_code` + FORCE RLS country isolation
  (003/004 pattern). `user_id` is a plain UUID — **no FK to students**
  until the accounts unification lands (auth registry is in-memory v1;
  a hard FK would 500 every real user today).
