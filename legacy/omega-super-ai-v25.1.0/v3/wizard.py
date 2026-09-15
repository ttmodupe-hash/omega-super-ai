"""Omega AI v3.2 — Guided Workflow Wizards
Interactive multi-step wizards for complex tasks.

Example:
    >>> engine = WizardEngine()
    >>> engine.list_wizards()
    ['mining_setup', 'tax_filing', 'budget_setup', 'investment_plan', 'startup_checklist']
    >>> result = engine.run("mining_setup")
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

# ── ANSI Colors ──
R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
C = "\033[36m"
G = "\033[32m"
Y = "\033[33m"
RD = "\033[31m"


def _c(t: str, color: str) -> str:
    return f"{color}{t}{R}"


def _prompt(text: str, default: str = "") -> str:
    hint = f" {D}[{default}]{R}" if default else ""
    ans = input(f"\n{C}?{R} {text}{hint}\n{B}>{R} ").strip()
    return ans if ans else default


def _prompt_num(text: str, default: float = 0.0) -> float:
    while True:
        a = _prompt(text, str(default))
        if a.lower() in ("quit", "cancel"):
            raise KeyboardInterrupt
        try:
            return float(a)
        except ValueError:
            print(_c("  Enter a valid number.", Y))


def _prompt_choice(text: str, options: list[str], default: str = "") -> str:
    opts = "/".join(f"{B}{o}{R}" if o == default else o for o in options)
    while True:
        a = _prompt(f"{text} ({opts})", default)
        if a.lower() in ("quit", "cancel"):
            raise KeyboardInterrupt
        if a.lower() in [o.lower() for o in options]:
            return next(o for o in options if o.lower() == a.lower())
        if not a and default:
            return default


def _prompt_yn(text: str, default: bool = True) -> bool:
    d = "yes" if default else "no"
    return _prompt_choice(text, ["yes", "no"], d).lower() in ("yes", "y")


def _banner(title: str, subtitle: str = "") -> str:
    lines = ["", f"{C}{'═'*64}{R}", f"  {B}{title}{R}"]
    if subtitle:
        lines.append(f"  {D}{subtitle}{R}")
    lines.append(f"{C}{'═'*64}{R}")
    return "\n".join(lines)


def _box(title: str, lines: list[str], width: int = 60) -> str:
    w = max(width, max((len(l) for l in lines), default=0) + 4)
    res = [f"{C}┌{'─'*w}┐{R}"]
    res.append(f"{C}│{R} {B}{C}{title:^{w}}{R} {C}│{R}")
    res.append(f"{C}├{'─'*w}┤{R}")
    for line in lines:
        res.append(f"{C}│{R} {line:<{w-1}}{C}│{R}")
    res.append(f"{C}└{'─'*w}┘{R}")
    return "\n".join(res)


def _step(cur: int, total: int) -> str:
    p = cur / total
    f = int(p * 20)
    bar = "=" * f + ">" + " " * (19 - f) if f < 20 else "=" * 20
    color = G if p >= 0.8 else C if p >= 0.5 else Y
    return f"{D}Step {B}{cur}{R}{D}/{B}{total}  [{color}{bar}{R}{D}]{R}"


# ── Wizard Session ──
class WizardSession:
    def __init__(self, name: str) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.step = 0
        self.answers: dict[str, Any] = {}
        self.started = datetime.now(timezone.utc).isoformat()

    def answer(self, key: str, value: Any) -> None:
        self.answers[key] = value
        self.step += 1


# ── Wizard Engine ──
class WizardEngine:
    def __init__(self) -> None:
        self._wizards: dict[str, Callable[..., str]] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        for name, fn in [
            ("mining_setup", wizard_mining_setup),
            ("tax_filing", wizard_tax_filing),
            ("budget_setup", wizard_budget_setup),
            ("investment_plan", wizard_investment_plan),
            ("startup_checklist", wizard_startup_checklist),
        ]:
            self.register(name, fn)

    def register(self, name: str, fn: Callable[..., str]) -> None:
        if name in self._wizards:
            raise ValueError(f"Wizard '{name}' already registered.")
        self._wizards[name] = fn

    def list_wizards(self) -> list[str]:
        return sorted(self._wizards.keys())

    def run(self, name: str) -> str:
        if name not in self._wizards:
            return f"Wizard '{name}' not found. Available: {', '.join(self.list_wizards())}"
        try:
            return self._wizards[name]()
        except KeyboardInterrupt:
            return _c("\nWizard cancelled.", Y)


# ═══════════════════════════════════════
#  WIZARD: Mining Setup
# ═══════════════════════════════════════
def wizard_mining_setup() -> str:
    """5-step Bitcoin mining setup wizard."""
    s = WizardSession("Bitcoin Mining Setup")
    print(_banner("Bitcoin Mining Setup", "Configure your mining operation"))

    print(f"\n{_step(1,5)}")
    cost = _prompt_num("Electricity cost per kWh (USD)?", 0.08)
    s.answer("cost", cost)

    print(f"\n{_step(2,5)}")
    budget = _prompt_num("Hardware budget (USD)?", 5000)
    s.answer("budget", budget)

    print(f"\n{_step(3,5)}")
    country = _prompt("Operating country?", "South Africa")
    s.answer("country", country)

    print(f"\n{_step(4,5)}")
    risk = _prompt_choice("Risk tolerance?", ["conservative", "balanced", "aggressive"], "balanced")
    s.answer("risk", risk)

    print(f"\n{_step(5,5)}")
    tax = _prompt_yn("Include tax estimate?", True)
    s.answer("tax", tax)

    # ASIC lookup
    asics = [
        {"name": "Antminer S19 XP", "price": 4500, "hash": 140, "power": 3010},
        {"name": "Antminer S19j Pro", "price": 2800, "hash": 104, "power": 3068},
        {"name": "Whatsminer M30S++", "price": 3200, "hash": 112, "power": 3472},
        {"name": "Antminer T19", "price": 1800, "hash": 84, "power": 3150},
    ]
    asic = next((a for a in asics if budget >= a["price"]), asics[-1])

    btc = 105_000
    daily_btc = (asic["hash"] * 1e12) / (72e12 * 2**32) * 86400 * 3.125
    daily_rev = daily_btc * btc
    daily_pwr = (asic["power"] / 1000) * 24 * cost
    daily_profit = daily_rev - daily_pwr
    roi = asic["price"] / daily_profit if daily_profit > 0 else float("inf")

    lines = [
        f"{B}Configuration:{R}  ${cost:.4f}/kWh | Budget: ${budget:,.0f} | {country}",
        "",
        f"{B}Recommended:{R}  {asic['name']} ({asic['hash']} TH/s, {asic['power']}W)",
        "",
        f"{B}Daily:{R}     Revenue: ${daily_rev:.2f} | Power: ${daily_pwr:.2f} | Profit: {_c(f'${daily_profit:.2f}', G if daily_profit > 0 else RD)}",
        f"{B}Monthly:{R}   Profit: {_c(f'${daily_profit*30:.2f}', G if daily_profit > 0 else RD)}",
        f"{B}Yearly:{R}    Profit: {_c(f'${daily_profit*365:.2f}', G if daily_profit > 0 else RD)}",
        f"{B}ROI:{R}       {roi:.0f} days" if roi != float("inf") else f"{B}ROI:{R} Unprofitable",
        "",
        f"{Y}⚠ Risk ({risk}):{R}",
        f"  • Monitor difficulty adjustments monthly",
        f"  • BTC price below $40k may make this unprofitable",
        f"  • Keep 3 months operating costs as reserve",
    ]
    if tax:
        lines.extend(["", f"{B}Tax note:{R} Mining rewards taxed as income. Deduct hardware, electricity, rent."])
    return "\n" + _box("⛏ MINING SETUP REPORT", lines)


# ═══════════════════════════════════════
#  WIZARD: Tax Filing
# ═══════════════════════════════════════
def wizard_tax_filing() -> str:
    """5-step tax filing preparation wizard."""
    s = WizardSession("Tax Filing")
    print(_banner("Tax Filing Wizard", "Get your filing checklist"))

    print(f"\n{_step(1,5)}")
    country = _prompt("Filing country?", "South Africa")
    s.answer("country", country)

    print(f"\n{_step(2,5)}")
    itype = _prompt_choice("Income type?", ["salary", "business", "freelance", "mixed"], "salary")
    s.answer("type", itype)

    print(f"\n{_step(3,5)}")
    income = _prompt_num("Annual income?", 50000)
    s.answer("income", income)

    print(f"\n{_step(4,5)}")
    print(f"{D}Enter deductions (name amount). Type 'done'.{R}")
    ded = []
    while True:
        e = input(f"  {C}ded>{R} ").strip()
        if e.lower() == "done":
            break
        if e:
            ded.append(e)
    s.answer("deductions", ded)

    print(f"\n{_step(5,5)}")
    aware = _prompt_yn("Know your filing deadline?", False)
    s.answer("aware", aware)

    rates = {"south africa": 0.26, "nigeria": 0.21, "kenya": 0.30, "ghana": 0.25}
    rate = rates.get(country.lower(), 0.25)
    tax = income * rate

    items = ["Gather income documents", "Collect bank interest certs", "Medical receipts"]
    if itype in ("business", "freelance", "mixed"):
        items.extend(["Profit & loss statement", "Business expense receipts"])
    items.extend(["Submit before deadline", "Keep copies 5 years"])

    lines = [
        f"{B}Profile:{R}  {country} | {itype.title()} | Income: ${income:,.0f}",
        f"{B}Est. Tax:{R} {rate*100:.0f}% = ${_c(f'{tax:,.0f}', RD)}",
        "",
        f"{B}Checklist:{R}",
    ] + [f"  ☐ {i}" for i in items]

    if not aware:
        lines.append(f"\n{RD}⚠ CONFIRM YOUR FILING DEADLINE IMMEDIATELY{R}")
    return "\n" + _box("📋 TAX FILING CHECKLIST", lines)


# ═══════════════════════════════════════
#  WIZARD: Budget Setup
# ═══════════════════════════════════════
def wizard_budget_setup() -> str:
    """5-step personal budget creation wizard."""
    s = WizardSession("Budget Setup")
    print(_banner("Budget Wizard", "Build your budget (50/30/20 rule)"))

    print(f"\n{_step(1,5)}")
    income = _prompt_num("Monthly income (after tax)?", 5000)
    s.answer("income", income)

    print(f"\n{_step(2,5)}")
    print(f"{D}Fixed expenses (name amount). Type 'done'.{R}")
    fixed: dict[str, float] = {}
    while True:
        e = input(f"  {C}fixed>{R} ").strip()
        if e.lower() == "done":
            break
        parts = e.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                fixed[parts[0]] = float(parts[1])
            except ValueError:
                pass
    s.answer("fixed", fixed)

    print(f"\n{_step(3,5)}")
    print(f"{D}Variable expenses (name amount). Type 'done'.{R}")
    var: dict[str, float] = {}
    while True:
        e = input(f"  {C}var>{R} ").strip()
        if e.lower() == "done":
            break
        parts = e.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                var[parts[0]] = float(parts[1])
            except ValueError:
                pass
    s.answer("var", var)

    print(f"\n{_step(4,5)}")
    savings = _prompt_num("Monthly savings goal?", income * 0.20)
    s.answer("savings", savings)

    print(f"\n{_step(5,5)}")
    s.answer("review", True)

    total_f = sum(fixed.values())
    total_v = sum(var.values())
    total = total_f + total_v + savings
    remain = income - total

    def bar(label: str, actual: float, target: float) -> str:
        p = min(actual / target * 100, 100) if target > 0 else 0
        b = "█" * int(p / 5) + "░" * (20 - int(p / 5))
        col = G if actual <= target else RD
        return f"  {label:8} {b} {col}{actual:,.0f}{R}/{target:,.0f}"

    lines = [
        f"{B}Overview:{R}  Income: ${income:,.0f}",
        f"  Fixed: ${total_f:,.0f} | Variable: ${total_v:,.0f} | Savings: ${savings:,.0f}",
        f"  Total: ${total:,.0f} | Remaining: {_c(f'${remain:,.0f}', G if remain >= 0 else RD)}",
        "",
        f"{B}50/30/20 Analysis:{R}",
        bar("Needs", total_f, income * 0.50),
        bar("Wants", total_v, income * 0.30),
        bar("Save", savings, income * 0.20),
        "",
        f"{'✓ Within budget!' if remain >= 0 else '⚠ Over by $' + f'{abs(remain):,.0f}'}",
    ]
    return "\n" + _box("💰 BUDGET PLAN", lines)


# ═══════════════════════════════════════
#  WIZARD: Investment Plan
# ═══════════════════════════════════════
def wizard_investment_plan() -> str:
    """5-step investment plan wizard."""
    s = WizardSession("Investment Plan")
    print(_banner("Investment Plan Wizard", "Create your strategy"))

    print(f"\n{_step(1,5)}")
    amt = _prompt_num("Investment amount (USD)?", 10000)
    s.answer("amount", amt)

    print(f"\n{_step(2,5)}")
    yrs = int(_prompt_num("Time horizon (years)?", 5))
    s.answer("years", yrs)

    print(f"\n{_step(3,5)}")
    risk = _prompt_choice("Risk tolerance?", ["low", "medium", "high"], "medium")
    s.answer("risk", risk)

    print(f"\n{_step(4,5)}")
    assets = _prompt_choice("Preferred assets?", ["crypto", "stocks", "both"], "both")
    s.answer("assets", assets)

    print(f"\n{_step(5,5)}")
    country = _prompt("Country (for tax)?", "South Africa")
    s.answer("country", country)

    # Allocation
    alloc = {
        "low": {"BTC": 10, "ETH": 10, "SOL": 5, "stocks": 55, "cash": 20},
        "medium": {"BTC": 20, "ETH": 15, "SOL": 10, "stocks": 45, "cash": 10},
        "high": {"BTC": 35, "ETH": 20, "SOL": 15, "stocks": 25, "cash": 5},
    }.get(risk, alloc["medium"])

    if assets == "crypto":
        alloc = {k: v * 2 if k in ("BTC", "ETH", "SOL") else 0 for k, v in alloc.items()}
        total = sum(alloc.values())
        alloc = {k: round(v / total * 100) for k, v in alloc.items() if v > 0}
    elif assets == "stocks":
        alloc = {"stocks": 80, "cash": 20}

    lines = [f"{B}Strategy:{R}  ${amt:,.0f} over {yrs} years | {risk.title()} risk | {assets}", ""]
    for asset, pct in alloc.items():
        if pct > 0:
            val = amt * pct / 100
            lines.append(f"  {asset.upper():8} {pct:3}%  =  ${_c(f'${val:,.0f}', C)}")
    lines.extend(["", f"{Y}⚠ DYOR: Past performance ≠ future results. Consider dollar-cost averaging.{R}"])
    return "\n" + _box("📈 INVESTMENT PLAN", lines)


# ═══════════════════════════════════════
#  WIZARD: Startup Checklist
# ═══════════════════════════════════════
def wizard_startup_checklist() -> str:
    """5-step African startup launch wizard."""
    s = WizardSession("Startup Launch")
    print(_banner("Startup Launch Wizard", "African market entry guide"))

    print(f"\n{_step(1,5)}")
    idea = _prompt("Describe your business idea briefly:", "")
    s.answer("idea", idea)

    print(f"\n{_step(2,5)}")
    mkt = _prompt("Target country/market?", "Nigeria")
    s.answer("market", mkt)

    print(f"\n{_step(3,5)}")
    sector = _prompt_choice("Sector?", ["tech", "agriculture", "fintech", "health", "education", "energy", "other"], "tech")
    s.answer("sector", sector)

    print(f"\n{_step(4,5)}")
    budget = _prompt_num("Startup budget (USD)?", 5000)
    s.answer("budget", budget)

    print(f"\n{_step(5,5)}")
    legal = _prompt_choice("Legal structure?", ["sole proprietorship", "partnership", "limited company", "ngo"], "limited company")
    s.answer("legal", legal)

    checklist = [
        f"Register {legal} in {mkt}",
        "Open business bank account",
        "Obtain tax identification number",
        "Register with local business authority",
        "Draft partnership/shareholder agreements" if legal != "sole proprietorship" else "",
        "Secure initial funding ($" + f"{budget:,.0f}" + " allocated)",
        "Develop MVP/prototype",
        "Conduct market validation in " + mkt,
        "Build local team/partnerships",
        "Set up accounting system",
        "Understand sector regulations for " + sector,
        "Register trademarks/intellectual property",
        "Set up digital presence (website, social)",
        "Launch pilot program",
        "Monitor compliance requirements",
    ]

    lines = [f"{B}Business:{R}  {idea}", f"{B}Market:{R}    {mkt} | {sector.title()} | ${budget:,.0f} | {legal}", "", f"{B}Launch Checklist:{R}"]
    lines.extend(f"  ☐ {c}" for c in checklist if c)
    return "\n" + _box("🚀 STARTUP CHECKLIST", lines)


# ── Main for testing ──
if __name__ == "__main__":
    engine = WizardEngine()
    print("Available wizards:", engine.list_wizards())
