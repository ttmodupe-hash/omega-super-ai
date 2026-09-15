# OMEGA-LUQI Unit-Cost & Subsidy Model (Investor Verification Layer)

How premium subscribers fund free African student accounts under heavy usage.

## Cost Metrics (verify all rates at contract time - provider pricing shifts)

**Premium heavy session** (100K input / 10K reasoning-output tokens, kimi-k3):
- Input: 100,000 / 1M x $3.00  = $0.30
- Output: 10,000 / 1M x $15.00 = $0.15
- **Total per heavy session: $0.45**

**Free-tier student session** (capped 5K input / 1K output, routed to kimi-k2.7-code):
- Input: 5,000 / 1M x ~$1.00  = $0.005
- Output: 1,000 / 1M x ~$5.00  = $0.005
- **Total per student session: $0.01 (1 US cent)**

> Why routing matters: free-tier queries go through the cheaper code model AND
> smaller context caps. K3's always-on thinking at $15/M output would cost
> ~10x more per student session - the KIMI_MODEL env override is the control.

## Subsidy Equation

One Global Premium subscriber at $30.00/month flat:

| Allocation | Amount |
|---|---|
| Platform overhead (compute + vault storage) | $10.00 |
| Premium token usage (capped 20 heavy sessions) | $9.00 |
| **Margin into African education pool (30% target)** | **$11.00** |

    Student sessions covered = $11.00 / $0.01 = 1,100 student sessions / month

**Conclusion:** each premium international account funds ~1,100 free technical
practical sessions. The flywheel is economically real if (a) premium churn stays
low, (b) free-tier caps hold, and (c) token rates are re-verified quarterly.

## Open risks to model
- K3 output pricing changes (always-on thinking makes output tokens the cost driver)
- Free-tier abuse without per-student session caps (enforce in orchestrator before launch)
- FX: M-Pesa/PayFast settlement in ZAR/KES vs USD-denominated token costs
