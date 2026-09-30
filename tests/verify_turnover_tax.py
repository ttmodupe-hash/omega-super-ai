"""TAX-TURNOVER-1 battery: SARS turnover-tax estimate on the VERIFIED 2026/27
table (https://www.sars.gov.za/types-of-tax/turnover-tax/, checked 2026-09-30).

Every assertion is derived from the official SARS table, not from the external
draft that proposed this feature - the draft's figures were confirmed against
SARS before integration. Bracket continuity is asserted at every boundary so
a future edit cannot silently move a band edge.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.tax_matrix import (  # noqa: E402
    MAX_QUALIFYING_TURNOVER,
    TURNOVER_TAX_SOURCE,
    TURNOVER_TAX_YEAR,
    compute_turnover_tax,
    router,
)

CHECKS = 0


def ok(cond, label):
    global CHECKS
    CHECKS += 1
    assert cond, f"TAX-TURNOVER-1 check failed: {label}"
    print(f"[PASS] {label}")


def tax_at(amount):
    return compute_turnover_tax(amount)["estimated_turnover_tax"]


# --- SARS 2026/27 table values (in-bracket examples) ------------------------
ok(tax_at(500_000) == 0.0, "R500k -> R0 (inside the 0% band)")
ok(tax_at(800_000) == 2_000.0, "R800k -> 1% x R200k = R2,000")
ok(tax_at(1_200_000) == 8_500.0, "R1.2m -> R3,500 + 2% x R250k = R8,500")
ok(tax_at(2_000_000) == 30_500.0, "R2.0m -> R12,500 + 3% x R600k = R30,500")

# --- Boundary continuity (no silent band-edge drift) ------------------------
ok(tax_at(600_000) == 0.0, "boundary R600,000 -> R0")
ok(abs(tax_at(600_001) - 0.01) < 1e-9, "boundary R600,001 -> R0.01")
ok(tax_at(950_000) == 3_500.0, "boundary R950,000 -> R3,500 (continuous)")
ok(abs(tax_at(950_001) - 3_500.02) < 1e-9, "boundary R950,001 -> R3,500.02")
ok(tax_at(1_400_000) == 12_500.0, "boundary R1,400,000 -> R12,500 (continuous)")
ok(abs(tax_at(1_400_001) - 12_500.03) < 1e-9, "boundary R1,400,001 -> R12,500.03")

# --- Qualifying threshold (Budget 2026: R1m -> R2.3m) ------------------------
top = compute_turnover_tax(2_300_000)
ok(top["qualifies_for_turnover_tax"] is True, "R2.3m still qualifies")
ok(top["estimated_turnover_tax"] == 39_500.0, "R2.3m -> R12,500 + 3% x R900k = R39,500")
over = compute_turnover_tax(2_300_001)
ok(over["qualifies_for_turnover_tax"] is False, "R2,300,001 does NOT qualify")
ok(over["estimated_turnover_tax"] is None, "non-qualifying turnover -> no turnover-tax figure")
ok("R2.3 million" in over["bracket"], "non-qualifying bracket message names the threshold")
ok(MAX_QUALIFYING_TURNOVER == 2_300_000.0, "qualifying threshold constant is R2.3m")
zero = compute_turnover_tax(0)
ok(zero["estimated_turnover_tax"] == 0.0 and zero["effective_rate_pct"] == 0.0,
   "R0 turnover -> R0 tax, 0% effective rate (no division error)")

# --- Honesty invariants ------------------------------------------------------
ok(TURNOVER_TAX_YEAR == "2026/27", "table labelled with its year of assessment")
ok(TURNOVER_TAX_SOURCE.startswith("https://www.sars.gov.za/"),
   "source is the official sars.gov.za domain")
ok("ESTIMATE ONLY" in top["disclaimer"], "output is always labelled ESTIMATE ONLY")
ok("not tax advice" in top["disclaimer"], "disclaimer states it is not tax advice")
ok("registered tax practitioner" in top["disclaimer"], "disclaimer points to a practitioner")
ok(top["source"] == TURNOVER_TAX_SOURCE, "every response carries the SARS source URL")
ok(abs(top["effective_rate_pct"] - round(100 * 39_500 / 2_300_000, 4)) < 1e-9,
   "effective rate reported honestly (R39,500 / R2.3m ~ 1.7174%)")

# --- Input validation + route exposure ---------------------------------------
try:
    compute_turnover_tax(-1)
    raise SystemExit("negative turnover must raise ValueError")
except ValueError:
    ok(True, "negative turnover raises ValueError")

paths = {getattr(r, "path", None) for r in router.routes}
ok("/v1/agent/turnover-tax-estimate" in paths,
   "router exposes POST /v1/agent/turnover-tax-estimate")
ok("/v1/agent/tax-compute" in paths, "existing corporate tax-compute route untouched")

print(f"\nTAX-TURNOVER-1 verification: all {CHECKS} checks passed.")
sys.exit(0)
