"""Omega AI v3 — Financial Literacy & Scam Protection
Education and protection against financial scams.
"""
from __future__ import annotations

import re
from typing import Any

from utils import colorize, Colors


class FinancialLiteracy:
    """Financial education and scam protection engine."""

    LESSONS: dict[str, dict[str, str]] = {
        "budgeting": {
            "beginner": "## Budgeting Basics\n\nThe 50/30/20 Rule:\n- 50% Needs (rent, food, transport)\n- 30% Wants (entertainment, dining)\n- 20% Savings & Debt\n\n**Action:** Track every expense for 30 days. Use a simple spreadsheet or app.",
            "intermediate": "## Advanced Budgeting\n\n- Zero-based budgeting: Assign every dollar a job\n- Envelope system: Cash in envelopes per category\n- 60% Solution: 60% committed expenses, 10% irregular, 10% fun, 20% savings\n\n**Tools:** YNAB, Mint, or a custom spreadsheet.",
            "advanced": "## Master Budgeting\n\n- Rolling forecasts: Adjust monthly\n- Sinking funds: Save for predictable expenses\n- Expense ratios: Track needs/wants ratio over time\n- Automate: Auto-transfer savings on payday\n\n**Goal:** Savings rate >30% of income.",
        },
        "saving": {
            "beginner": "## Saving Fundamentals\n\n1. Emergency fund: 3-6 months expenses\n2. Pay yourself first: Save before spending\n3. High-yield savings account\n4. Automate transfers\n\n**Start:** Even R100/month builds the habit.",
            "intermediate": "## Saving Strategies\n\n- Ladder CDs for better rates\n- Sinking funds for annual expenses\n- 52-week challenge\n- Round-up apps\n\n**Target:** 20% savings rate minimum.",
            "advanced": "## Advanced Saving\n\n- Tax-advantaged accounts (TFSA, RA)\n- Treasury bonds\n- Money market funds\n- Currency diversification\n\n**Optimize:** Maximize tax-free savings first.",
        },
        "debt": {
            "beginner": "## Debt Basics\n\nGood debt: Education, home (appreciating assets)\nBad debt: Credit cards, consumer loans\n\n**Priority:** Pay highest interest first (avalanche method).",
            "intermediate": "## Debt Management\n\n- Debt snowball: Pay smallest first (psychological wins)\n- Debt avalanche: Pay highest interest first (mathematical optimal)\n- Consolidation: Combine into lower rate\n- Negotiate with creditors\n\n**Rule:** Never miss minimum payments.",
            "advanced": "## Debt Mastery\n\n- Balance transfer arbitrage\n- Refinancing strategies\n- Debt-to-income ratio management (<36%)\n- Strategic leverage for investments\n\n**Goal:** Debt-free except mortgage.",
        },
        "crypto_lit": {
            "beginner": "## Crypto Basics\n\n- Blockchain: Digital ledger\n- Bitcoin: Digital gold (limited supply)\n- Ethereum: Smart contract platform\n- Wallet: Stores your keys (not coins)\n- Exchange: Where you buy/sell\n\n⚠️ Only invest what you can lose. Volatility is extreme.",
            "intermediate": "## Intermediate Crypto\n\n- Private keys = ownership\n- Cold wallet > hot wallet for large amounts\n- DCA (Dollar Cost Averaging) reduces risk\n- Staking earns passive income\n- Gas fees vary by network\n\n🔒 Never share seed phrases.",
            "advanced": "## Advanced Crypto\n\n- DeFi: Lending, borrowing, yield farming\n- Layer 2: Faster, cheaper transactions\n- On-chain analysis\n- Tax implications (tracked per transaction)\n- Multi-sig wallets for security\n\n**Risk:** Smart contract bugs, rug pulls, regulatory changes.",
        },
        "investing": {
            "beginner": "## Investing 101\n\n- Start early (compound interest)\n- Diversify (don't put all eggs in one basket)\n- Index funds for beginners\n- Understand fees (ER, transaction costs)\n- Time in market beats timing the market",
            "intermediate": "## Building Portfolio\n\n- Asset allocation: Stocks/Bonds/Cash/Alternative\n- Rebalancing: Quarterly or threshold-based\n- Tax-efficient placement\n- Dollar-cost averaging\n- Core-satellite strategy",
            "advanced": "## Advanced Investing\n\n- Factor investing (value, momentum, quality)\n- Options strategies (covered calls, protective puts)\n- Alternatives: REITs, commodities, private equity\n- Geographic diversification\n- ESG/SRI investing",
        },
        "mobile_money": {
            "beginner": "## Mobile Money Basics\n\n- M-Pesa (Kenya/Tanzania): Send, receive, pay\n- MTN MoMo: Across 15+ African countries\n- No bank account needed\n- Agent networks for cash-in/cash-out\n\n**Safety:** Use PIN, verify recipient, keep receipts.",
            "intermediate": "## Mobile Money Advanced\n\n- Interest-bearing wallets\n- International transfers\n- Merchant payments\n- Savings groups via mobile\n- Integration with banking\n\n**Tip:** Compare fees across providers.",
            "advanced": "## Mobile Money Mastery\n\n- API integration for business\n- Bulk payments\n- Micro-insurance products\n- Credit scoring via transaction history\n- Cross-border interoperability",
        },
        "stokvels": {
            "beginner": "## Stokvels (Rotating Savings)\n\n- Group saves together, members rotate payouts\n- Common in South Africa\n- Types: Savings, burial, investment, grocery\n- Trust-based system\n\n**Benefit:** Financial discipline + community support.",
            "intermediate": "## Stokvel Management\n\n- Formalize with constitution\n- Bank account in all members' names\n- Transparent record-keeping\n- Insurance for group\n- Digital stokvel apps available\n\n**Risk:** Default, fraud, disputes — formalize early.",
            "advanced": "## Advanced Stokvels\n\n- Investment stokvels (property, stocks)\n- Registered as co-operative\n- Professional management\n- Due diligence on investments\n- Estate planning for members\n\n**Growth:** Some stokvels manage millions in assets.",
        },
        "scam_protection": {
            "beginner": "## Scam Protection Basics\n\nRed Flags:\n- Guaranteed high returns\n- Pressure to act NOW\n- Requests for upfront payment\n- Unsolicited contact\n- Too good to be true\n\n**Rule:** If it sounds too good to be true, it is.",
            "intermediate": "## Identifying Scams\n\n- Verify registration with regulators (FSCA, SEC)\n- Search '[company] + scam/review/complaint'\n- Check domain age (new = suspicious)\n- Reverse image search profiles\n- Never share passwords or PINs\n\n**Verify:** Always independently verify claims.",
            "advanced": "## Advanced Protection\n\n- OSINT techniques for due diligence\n- Blockchain analysis for crypto scams\n- Report to authorities (FBI IC3, Action Fraud)\n- Document everything\n- Legal recourse options\n\n**Community:** Share warnings to protect others.",
        },
    }

    EXTRA_TOPICS: dict[str, str] = {
        "credit": "Credit scores measure your creditworthiness. Pay on time, keep utilization <30%, check reports annually.",
        "retirement": "Start retirement savings early. Use tax-advantaged accounts. Aim for 15x annual income by retirement age.",
        "insurance": "Protect against catastrophic loss: health, life, disability, property. Compare quotes. Understand exclusions.",
        "forex": "Currency trading is high-risk. 90% of retail traders lose money. Learn technical & fundamental analysis first.",
        "property": "Real estate: location matters, leverage carefully, factor in all costs (bond, rates, maintenance, vacancy).",
        "side_hustle": "Extra income ideas: freelancing, tutoring, delivery, online selling, consulting. Declare all income for tax.",
        "passive_income": "Dividend stocks, rental property, royalties, online courses. Requires upfront effort, then earns with minimal work.",
        "emergency_fund": "Save 3-6 months of expenses in accessible account. This is your financial shock absorber. Priority #1.",
        "banking": "Compare fees, interest rates, digital features. Protect your cards, enable notifications, review statements.",
        "tax_basics": "Understand your tax bracket, deductions available, filing deadlines. Use tax-free savings vehicles first.",
        "wealth_building": "Wealth = Assets - Liabilities. Build assets (investments, property, business). Minimize liabilities.",
        "financial_independence": "FIRE: Save aggressively (50-70%), invest in index funds, live below means. Goal: passive income > expenses.",
    }

    SCAM_PATTERNS: list[dict[str, str]] = [
        {"type": "Ponzi Scheme", "description": "Pays returns from new investors' money, not profits. Collapses when recruitment slows.", "red_flags": "Guaranteed returns, no real product, recruitment emphasis, complex structure"},
        {"type": "Pyramid Scheme", "description": "Money flows up the chain. You recruit others who pay fees. Illegal in most countries.", "red_flags": "Recruitment over product, multiple levels, upfront fee, income from recruiting"},
        {"type": "Phishing", "description": "Fake emails/websites steal your credentials. Looks identical to real sites.", "red_flags": "Urgent requests, suspicious links, asks for passwords, poor grammar"},
        {"type": "Advance Fee Fraud (419)", "description": "Promise large sum in exchange for small upfront payment. Classic Nigerian prince scam.", "red_flags": "Unexpected windfall, upfront fee required, overseas sender, secrecy requested"},
        {"type": "Romance Scam", "description": "Fake online relationship to extract money. Often claims emergency or travel need.", "red_flags": "Never met in person, asks for money, claims to be overseas, love declared quickly"},
        {"type": "Investment Scam", "description": "Fake investments with guaranteed high returns. Often uses crypto or forex as cover.", "red_flags": "Guaranteed returns, no risk mentioned, pressure to invest, unregistered"},
        {"type": "Crypto Scam", "description": "Fake ICOs, rug pulls, pump & dump schemes. Stolen funds are rarely recovered.", "red_flags": "Anonymous team, unaudited contracts, guaranteed yields, celebrity endorsements"},
        {"type": "Forex Scam", "description": "Unregulated brokers, signal sellers, managed account fraud. High leverage traps.", "red_flags": "Unregulated broker, guaranteed profits, bonus traps, can't withdraw"},
        {"type": "Fake Job Offer", "description": "Job that requires payment for training, equipment, or background check.", "red_flags": "Pay to work, no interview, too-good salary, vague description"},
        {"type": "SIM Swap Fraud", "description": "Criminals port your number to steal 2FA codes and access accounts.", "red_flags": "Sudden loss of service, unexpected bank messages, can't access accounts"},
        {"type": "Cloud Mining Scam", "description": "Sells mining contracts that don't exist or never ROI. Fake hashrate.", "red_flags": "Guaranteed mining returns, no hardware proof, Ponzi-like payouts, no transparency"},
        {"type": "Pump & Dump", "description": "Group artificially inflates price, sells at peak, retail buyers lose.", "red_flags": "Hyped on social media, coordinated buying, celebrity promotion, sudden spikes"},
    ]

    def lesson(self, topic: str, level: str = "beginner") -> str:
        """Get educational content for a topic."""
        topic = topic.lower().strip()
        level = level.lower().strip()

        if topic in self.LESSONS and level in self.LESSONS[topic]:
            return self.LESSONS[topic][level]
        if topic in self.EXTRA_TOPICS:
            return f"## {topic.title().replace('_', ' ')}\n\n{self.EXTRA_TOPICS[topic]}"

        return f"Topic '{topic}' not found. Available topics: {', '.join(sorted(set(list(self.LESSONS.keys()) + list(self.EXTRA_TOPICS.keys()))))}"

    def scam_check(self, offer_description: str) -> dict[str, Any]:
        """Analyze potential scam. Returns risk assessment."""
        text = offer_description.lower()
        score = 0
        red_flags: list[str] = []

        flags = {
            "guaranteed": (20, "Guaranteed returns are impossible"),
            "guarantee": (15, "Guarantees in investing are red flags"),
            "100%": (15, "100% returns/rates don't exist legally"),
            "risk-free": (20, "No investment is risk-free"),
            "act now": (15, "Urgency pressure is a sales tactic"),
            "limited time": (10, "Artificial scarcity tactic"),
            "secret": (10, "Secret methods don't exist"),
            "exclusive": (5, "Exclusivity often hides problems"),
            "no experience needed": (10, "If it were easy, everyone would do it"),
            "double your": (15, "Doubling money quickly = Ponzi"),
            "send money": (15, "Upfront payment for opportunity = scam"),
            "wire transfer": (10, "Irreversible payment method preferred by scammers"),
            "bitcoin": (5, "Crypto often used to hide traces"),
            "crypto": (3, "Crypto is high-risk, not automatically scam"),
            "mining contract": (10, "Many cloud mining contracts are fraudulent"),
            "pump": (15, "Pump and dump is market manipulation"),
            "roi": (5, "Check if ROI is realistic"),
            "daily profit": (15, "Daily guaranteed profits = Ponzi"),
            "referral": (5, "Referral emphasis may indicate pyramid"),
            "mlm": (10, "Multi-level marketing often = pyramid"),
            "cloud mining": (10, "Cloud mining has high scam rate"),
            "registration fee": (10, "Paying to work is suspicious"),
            "nigerian prince": (50, "Classic advance fee fraud"),
            "won lottery": (20, "You can't win a lottery you didn't enter"),
            "inheritance": (15, "Unexpected inheritance from strangers = 419"),
            "urgent": (10, "Artificial urgency is manipulation"),
            "confidential": (5, "Secrecy requests are suspicious"),
        }

        for keyword, (points, reason) in flags.items():
            if keyword in text:
                score += points
                red_flags.append(f"🚩 {reason} (detected: '{keyword}')")

        red_flags = list(dict.fromkeys(red_flags))
        score = min(100, score)

        if score >= 70:
            verdict = "🔴 HIGH RISK — Very likely a scam. Avoid entirely."
        elif score >= 50:
            verdict = "🟠 ELEVATED RISK — Multiple warning signs. Proceed with extreme caution."
        elif score >= 30:
            verdict = "🟡 MODERATE RISK — Some concerns. Do thorough due diligence."
        elif score >= 15:
            verdict = "🟢 LOW-MODERATE RISK — A few minor flags. Verify independently."
        else:
            verdict = "🟢 LOW RISK — No major scam indicators detected, but always verify."

        return {
            "is_scam": score >= 50,
            "risk_score": score,
            "risk_level": verdict,
            "red_flags": red_flags,
            "advice": "Always verify: (1) Is the company registered? (2) Search '[name] + scam' (3) Check regulator warnings (4) Never send money to strangers (5) If too good to be true, it is." if score >= 30 else "Standard precautions apply.",
        }

    def scam_patterns(self) -> list[dict[str, str]]:
        """Return all known scam patterns."""
        return self.SCAM_PATTERNS

    def scam_types(self) -> list[str]:
        """List all covered scam types."""
        return [s["type"] for s in self.SCAM_PATTERNS]

    def budget_planner(self, income: float, expenses: dict[str, float]) -> str:
        """Create budget breakdown."""
        total_expenses = sum(expenses.values())
        balance = income - total_expenses

        needs = sum(v for k, v in expenses.items() if k.lower() in ["rent", "bond", "groceries", "transport", "utilities", "medical", "insurance", "school fees"])
        wants = sum(v for k, v in expenses.items() if k.lower() in ["entertainment", "dining", "shopping", "streaming", "hobbies", "vacation"])
        savings_debt = total_expenses - needs - wants

        lines = ["## Budget Analysis\n"]
        lines.append(f"Income:  R{income:>10,.2f}")
        lines.append(f"Expenses: R{total_expenses:>10,.2f}")
        lines.append(f"Balance:  R{balance:>10,.2f} {'✓ Surplus' if balance >= 0 else '✗ Deficit'}")
        lines.append(f"\nBy Category:")
        lines.append(f"  Needs (50% target):    R{needs:>10,.2f} ({needs/income*100:.0f}%)")
        lines.append(f"  Wants (30% target):    R{wants:>10,.2f} ({wants/income*100:.0f}%)")
        lines.append(f"  Save/Debt (20% tgt):   R{savings_debt:>10,.2f} ({savings_debt/income*100:.0f}%)")

        if balance < 0:
            lines.append(f"\n⚠️ You're spending R{abs(balance):,.2f} more than you earn.")
            lines.append("Recommend: Cut wants first, then reduce needs if possible.")
        elif balance / income < 0.1:
            lines.append(f"\n⚠️ Savings rate is low. Aim for at least 20%.")
        else:
            lines.append(f"\n✓ Healthy budget! Consider investing the surplus.")

        return "\n".join(lines)

    def savings_plan(self, goal: str, target_amount: float, months: int) -> str:
        """Create savings roadmap."""
        monthly = target_amount / months if months > 0 else 0
        lines = [f"## Savings Plan: {goal}"]
        lines.append(f"Target:  R{target_amount:,.2f}")
        lines.append(f"Timeline: {months} months")
        lines.append(f"Monthly:  R{monthly:,.2f}")
        lines.append(f"\nMilestones:")
        for pct in [25, 50, 75, 100]:
            milestone = target_amount * pct / 100
            milestone_month = int(months * pct / 100)
            lines.append(f"  {pct}%: R{milestone:>10,.2f} (Month {milestone_month})")
        lines.append(f"\nTips:\n- Automate the monthly transfer\n- Put in separate savings account\n- Cut one non-essential expense to fund this")
        return "\n".join(lines)

    def protective_tips(self) -> str:
        return """## Financial Protection Tips

### General Safety:
1. Never share passwords, PINs, or OTPs
2. Enable 2FA on all financial accounts
3. Check statements regularly
4. Use strong, unique passwords
5. Be skeptical of unsolicited offers

### Investment Safety:
1. Verify registration with regulators (FSCA, SEC, FCA)
2. If guaranteed returns are promised, it's a scam
3. Diversify — never all-in on one investment
4. Understand what you're investing in
5. If you don't understand it, don't invest

### Emergency Contacts:
- South Africa: FSCA (012 428 8000)
- Nigeria: EFCC (+234 9 460 3790)
- Kenya: DCI (020 334 1000)
- Ghana: EOCO (0302 766 292)
- USA: FTC (1-877-FTC-HELP)
- UK: Action Fraud (0300 123 2040)"""


if __name__ == "__main__":
    fl = FinancialLiteracy()
    print(fl.lesson("budgeting"))
    print("\n--- Scam Check ---")
    result = fl.scam_check("Guaranteed 100% returns daily with our Bitcoin mining contract! Act now! Send $500 to start.")
    print(f"Score: {result['risk_score']}/100 — {result['risk_level']}")
    for flag in result['red_flags']:
        print(f"  {flag}")
