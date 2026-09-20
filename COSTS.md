# COSTS.md — Running OMEGA-LUQI self-funded, pre-revenue

Every rand must either cut cost or create revenue. This is the lean operating
manual until the first wallet top-up lands.

## 1. Your minimum monthly burn (today)

| Item | Cost | Notes |
|---|---|---|
| Railway hobby plan | ~$5/mo | app service + Postgres included in usage |
| Kimi API (K3) | usage, ~$3/$15 per M tokens | **NOW HARD-CAPPED** — see §3 |
| Domain (optional) | ~$10/yr | skip until revenue; use the free `.up.railway.app` domain |
| Everything else | $0 | Stripe/Paystack charge per transaction, never monthly |

**Do NOT buy yet** (each adds fixed monthly cost with zero return at current scale):
- ❌ Railway Redis plugin — only needed at replicas > 1; you are correctly at 1
- ❌ Extra replicas — in-memory ledger is correct for single-replica
- ❌ Docker-capable VPS for lab sandboxes — labs stay honestly "degraded" until revenue justifies it (see §4 for the $0 path)
- ❌ ElevenLabs / Hume / Africa's Talking keys — features work without them; add per-feature when users ask

## 2. Revenue activation order — $0 fixed cost each step

1. **Stripe live keys** (or Paystack for ZAR-local): pay-per-transaction only.
   Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_TABLE`
   (wallet top-ups, e.g. R50/R100/R200). Run the R10 gate test.
2. **First paid tier**: wallet top-ups already flow webhook → 30% gate →
   admin release → ledger. You approve each release manually at first —
   that IS the business model working, not a limitation.
3. **Marketing surface**: finlit + scam-shield content is the free funnel —
   it costs only capped Kimi tokens per visitor.

## 3. LLM spend circuit-breaker (shipped in v5.35.9)

`MONTHLY_TOKEN_BUDGET_USD` now has teeth:

- **80%** → SMS alarm (once/day, best-effort)
- **100%** (`COST_HARD_STOP_PCT`) → `chat_completion()` refuses new upstream
  calls with HTTP 429 **before any money moves** — every engine routes
  through this single choke point, so one guard covers all of them

**Set it today to a number you can actually afford:**

```
MONTHLY_TOKEN_BUDGET_USD=10      # example: cap LLM spend at $10/mo
# COST_HARD_STOP_PCT=100         # default; lower it for an earlier stop
```

The estimate is input-chars/4 — reconcile against the Moonshot invoice
monthly; the breaker errs on the side of stopping early, never late.

Model choice matters: `KIMI_MODEL=kimi-k2.7-code` is ~3x cheaper than K3 for
high-volume codegen; `KIMI_REASONING_EFFORT=low` cuts thinking-token spend
for simple queries.

## 4. The $0 path for lab sandboxes (when you need them)

Oracle Cloud **Always Free** tier: 4 ARM cores / 24 GB RAM VM, free forever,
runs Docker. That is the future home of the lab sandbox engine — no VPS bill.
Until then, labs report "engine offline" honestly rather than faking capacity.

## 5. Standing rules

- New fixed cost requires: revenue covering it 2x, or a user paying for the
  feature it enables.
- Free-tier users are already capped (`resource_caps.py`) — subsidized usage
  cannot eat your budget.
- Check `GET /v1/cost/telemetry` (admin) weekly: estimated spend, pct of
  budget, per-provider breakdown.
