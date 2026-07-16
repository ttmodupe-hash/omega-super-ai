"""Omega AI v3 — Calculation Engine
Quick calculators for currency, mining ROI, tax estimates, compound interest,
and loan amortization.  All methods are stateless and self-contained.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


# Fixed exchange rates (2026 mid-year estimates, USD base)
_RATES: dict[str, float] = {
    "usd": 1.0, "zar": 0.055, "ngn": 0.00062, "kes": 0.0077,
    "ghs": 0.065, "egp": 0.020, "gbp": 1.27, "eur": 1.08,
}

_SYMBOLS: dict[str, str] = {
    "usd": "$", "zar": "R", "ngn": "₦", "kes": "KSh",
    "ghs": "GH₵", "egp": "E£", "gbp": "£", "eur": "€",
}


class CalcEngine:
    """ Stateless calculator hub.  Every method returns a formatted string. """

    # ── Currency ──
    def currency_convert(self, amount: float, from_currency: str, to_currency: str) -> str:
        """Convert *amount* from one currency to another."""
        from_code = from_currency.lower().strip()
        to_code = to_currency.lower().strip()

        if from_code not in _RATES or to_code not in _RATES:
            supported = ", ".join(sorted(_RATES.keys()))
            return f"[Calc] Unsupported currency. Supported: {supported}"

        usd = amount * _RATES[from_code]
        result = usd / _RATES[to_code]
        sym = _SYMBOLS.get(to_code, "")
        from_sym = _SYMBOLS.get(from_code, "")

        lines = [
            f"💱 Currency Conversion",
            f"   {from_sym}{amount:,.2f} {from_code.upper()} = {sym}{result:,.2f} {to_code.upper()}",
            "",
            "   African equivalents:",
        ]
        for code, rate in sorted(_RATES.items()):
            if code in (from_code, to_code, "usd"):
                continue
            val = usd / rate
            s = _SYMBOLS.get(code, "")
            lines.append(f"     {s}{val:,.2f} {code.upper()}")
        lines.append(f"     ${usd:,.2f} USD")
        return "\n".join(lines)

    # ── Mining ROI ──
    def mining_roi(self, hashrate_ths: float, power_cost: float, power_watts: float,
                   hardware_cost: float = 3000, months: int = 12) -> str:
        """Quick BTC mining ROI projection."""
        btc_price = 105_000.0
        network_hashrate_eh = 850.0
        block_reward = 3.125
        blocks_per_day = 144
        hash_ratio = (hashrate_ths * 1e12) / (network_hashrate_eh * 1e18)
        daily_btc = hash_ratio * blocks_per_day * block_reward
        daily_rev = daily_btc * btc_price
        daily_power_cost = (power_watts / 1000) * 24 * power_cost
        daily_profit = daily_rev - daily_power_cost

        lines = [
            f"⛏️  Mining ROI Projection ({months} months)",
            f"   Hardware: ${hardware_cost:,.0f}  |  Hashrate: {hashrate_ths} TH/s  |  Power: {power_watts}W @ ${power_cost}/kWh",
            "",
            "   Daily:",
            f"     Revenue:    ${daily_rev:,.2f}  ({daily_btc:.6f} BTC)",
            f"     Power cost: ${daily_power_cost:,.2f}",
            f"     Profit:     ${daily_profit:,.2f}",
            "",
            "   Monthly:",
            f"     Profit:     ${daily_profit * 30:,.2f}",
            "",
            "   Yearly:",
            f"     Profit:     ${daily_profit * 365:,.2f}",
        ]

        if daily_profit > 0:
            breakeven_days = hardware_cost / daily_profit
            lines.extend([
                "",
                f"   ⚡ Breakeven: {breakeven_days:.0f} days ({breakevenven_days / 30:.1f} months)",
                f"   Annual ROI:  {(daily_profit * 365 / hardware_cost) * 100:.1f}%",
            ])
        else:
            lines.extend(["", "   ⚠️  Unprofitable at current rates."])

        return "\n".join(lines)

    # ── Tax estimate ──
    def tax_estimate(self, country: str, income: float) -> str:
        """Quick tax estimate wrapper around TaxEngine."""
        try:
            from tax_engine import TaxEngine
            te = TaxEngine()
            result = te.calculate_estimate(country, income)
            tax = result.get("estimated_tax", result.get("tax", 0))
            effective = (tax / income * 100) if income > 0 else 0
            lines = [
                f"🧾 Tax Estimate: {country.title()}",
                f"   Income:       {self._fmt_money(income)}",
                f"   Est. tax:     {self._fmt_money(tax)}",
                f"   Effective rate: {effective:.1f}%",
            ]
            return "\n".join(lines)
        except Exception as exc:
            return f"[Calc] Tax error: {exc}"

    # ── Compound Interest ──
    def compound_interest(self, principal: float, rate: float, years: int,
                          monthly_contribution: float = 0) -> str:
        """Year-by-year compound interest table."""
        lines = [
            f"📈 Compound Interest ({rate*100:.1f}% over {years} years)",
            f"   Principal: ${principal:,.2f}" +
            (f"  + ${monthly_contribution:,.2f}/month" if monthly_contribution else ""),
            "",
            f"   {'Year':>4} {'Balance':>14} {'Interest':>12}",
            f"   {'-'*4} {'-'*14} {'-'*12}",
        ]
        balance = principal
        for y in range(1, years + 1):
            for _ in range(12):
                balance += monthly_contribution
                balance *= (1 + rate / 12)
            interest = balance - principal - (monthly_contribution * y * 12)
            lines.append(f"   {y:>4} ${balance:>12,.2f} ${interest:>10,.2f}")
        total_contrib = principal + monthly_contribution * years * 12
        lines.append(f"\n   Final: ${balance:,.2f}  (Total contributed: ${total_contrib:,.2f})")
        return "\n".join(lines)

    # ── Loan Calculator ──
    def loan_calculator(self, principal: float, annual_rate: float, years: int) -> str:
        """Monthly payment and amortization summary."""
        r = annual_rate / 12
        n = years * 12
        if r == 0:
            payment = principal / n
        else:
            payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        total = payment * n
        lines = [
            f"🏦 Loan Calculator",
            f"   Principal: ${principal:,.2f}  |  Rate: {annual_rate*100:.2f}%  |  Term: {years} years",
            "",
            f"   Monthly payment: ${payment:,.2f}",
            f"   Total payments:  ${total:,.2f}",
            f"   Total interest:  ${total - principal:,.2f}",
        ]
        # Year 1 breakdown
        balance = principal
        yr_interest = 0
        yr_principal = 0
        for _ in range(12):
            interest = balance * r
            princ = payment - interest
            balance -= princ
            yr_interest += interest
            yr_principal += princ
        lines.extend([
            "",
            f"   Year 1 breakdown:",
            f"     Principal paid: ${yr_principal:,.2f}",
            f"     Interest paid:  ${yr_interest:,.2f}",
            f"     Remaining:      ${balance:,.2f}",
        ])
        return "\n".join(lines)

    # ── Command Router ──
    def handle_command(self, args: list[str]) -> str:
        """Parse CLI-style args and dispatch."""
        if not args:
            return self._help_text()
        cmd = args[0].lower()

        # Currency: 50000 ZAR to USD
        if len(args) >= 4 and args[2].lower() == "to":
            try:
                return self.currency_convert(float(args[0]), args[1], args[3])
            except ValueError:
                return "[Calc] Invalid amount for currency conversion."

        if cmd == "mining" and len(args) >= 4:
            try:
                return self.mining_roi(float(args[1]), float(args[2]), float(args[3]),
                                       float(args[4]) if len(args) > 4 else 3000,
                                       int(args[5]) if len(args) > 5 else 12)
            except (ValueError, IndexError):
                return "[Calc] Usage: calc mining <hashrate_TH/s> <power_cost> <power_W> [hardware_cost] [months]"

        if cmd == "tax" and len(args) >= 3:
            return self.tax_estimate(args[1], float(args[2]))

        if cmd == "compound" and len(args) >= 4:
            try:
                return self.compound_interest(float(args[1]), float(args[2]), int(args[3]),
                                              float(args[4]) if len(args) > 4 else 0)
            except ValueError:
                return "[Calc] Usage: calc compound <principal> <rate> <years> [monthly_contrib]"

        if cmd == "loan" and len(args) >= 4:
            try:
                return self.loan_calculator(float(args[1]), float(args[2]), int(args[3]))
            except ValueError:
                return "[Calc] Usage: calc loan <principal> <rate> <years>"

        return self._help_text()

    def _fmt_money(self, val: float) -> str:
        return f"${val:,.2f}" if val >= 1 else f"${val:.4f}"

    def _help_text(self) -> str:
        return (
            "🧮 Calculator Commands:\n"
            "   calc <amount> <from> to <to>     — Currency conversion\n"
            "   calc mining <TH/s> <$/kWh> <W> [cost] [mo] — Mining ROI\n"
            "   calc tax <country> <income>      — Tax estimate\n"
            "   calc compound <P> <rate> <yrs> [monthly] — Compound interest\n"
            "   calc loan <P> <rate> <years>     — Loan amortization"
        )