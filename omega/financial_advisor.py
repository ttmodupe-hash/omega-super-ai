"""
Financial Advisor Module — Omega Super AI v10

Financial literacy and investment guidance with STRONG safety guardrails.
Every response includes an educational disclaimer reminding users that
this is NOT professional financial advice.

This module provides:
- General financial education and concept explanations
- Investment legitimacy analysis with scam-pattern detection
- Budget planning using the 50/30/20 framework
- Side-by-side financial option comparisons
- Financial scam detection with red-flag analysis

Classes:
    FinancialAdvisor: Educational financial guidance with safety guardrails.

Example:
    advisor = FinancialAdvisor(openai_client=client)
    result = advisor.advise("How does diversification work?")
    plan = advisor.budget_planner(income=5000, expenses={"rent": 1500, "food": 600})
    scam_check = advisor.detect_financial_scam(
        "Guaranteed 500% returns in 1 week with no risk!"
    )
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class FinancialAdvisor:
    """Educational financial guidance with comprehensive safety guardrails.

    Provides financial literacy, investment analysis, budget planning,
    and scam detection. **Every response includes a disclaimer** stating
    that the information is educational only and not professional advice.

    Attributes:
        DISCLAIMER (str): Standard disclaimer appended to all responses.
    """

    DISCLAIMER: str = (
        "This is educational information only, not professional financial advice. "
        "Consult a licensed financial advisor for personalized guidance. "
        "Investment involves risk, including possible loss of principal. "
        "Past performance does not guarantee future results."
    )

    KNOWN_CONCEPTS: dict[str, str] = {
        "compound_interest": (
            "Interest calculated on the initial principal and also on the accumulated "
            "interest of previous periods. Often called 'interest on interest.'"
        ),
        "inflation": (
            "The rate at which the general level of prices for goods and services rises, "
            "eroding purchasing power over time."
        ),
        "diversification": (
            "Spreading investments across various assets to reduce risk. "
            "'Don't put all your eggs in one basket.'"
        ),
        "credit_score": (
            "A numerical expression (300-850) representing creditworthiness based on "
            "credit history. Higher scores mean better loan terms."
        ),
        "mortgage": (
            "A loan used to purchase real estate, where the property serves as collateral. "
            "Typically repaid over 15-30 years."
        ),
        "retirement_planning": (
            "The process of determining retirement income goals and the actions "
            "needed to achieve them, including savings and investment strategies."
        ),
        "tax_basics": (
            "Understanding how income tax works: taxable income, deductions, credits, "
            "brackets, and filing requirements."
        ),
        "budgeting": (
            "Creating a plan for spending and saving based on income and expenses. "
            "Common frameworks include 50/30/20."
        ),
        "emergency_fund": (
            "Savings set aside for unexpected expenses or financial emergencies. "
            "Typically 3-6 months of living expenses."
        ),
        "debt_management": (
            "Strategies for managing and paying off debt, including prioritization "
            "methods like avalanche (highest interest first) and snowball (smallest first)."
        ),
    }

    SCAM_PATTERNS: dict[str, dict[str, Any]] = {
        "guaranteed_returns": {
            "patterns": [
                r"guaranteed\s+\d+%",
                r"guaranteed\s+return",
                r"no\s+risk.*\d+%",
                r"\d+%\s+guaranteed",
                r"risk[-\s]?free.*return",
                r"promised\s+return",
            ],
            "severity": "CRITICAL",
            "description": "Guarantees returns — all legitimate investments carry risk",
        },
        "too_good_to_be_true": {
            "patterns": [
                r"\b\d{3,}%\s+return",
                r"double\s+your\s+money\s+(?:in|within)",
                r"(?:get|earn)\s+rich\s+quick",
                r"(?:no|zero)\s+risk.*(?:high|huge)\s+return",
                r"passive\s+income.*\d{3,}%",
            ],
            "severity": "HIGH",
            "description": "Returns that are unrealistically high",
        },
        "pyramid_scheme": {
            "patterns": [
                r"recruit.*(?:downline|others|people)",
                r"(?:mlm|multi[-\s]?level)\s+marketing",
                r"referral.*(?:bonus|commission|payment)",
                r"build\s+your\s+team",
                r"network\s+marketing",
                r"passive\s+income.*recruit",
            ],
            "severity": "CRITICAL",
            "description": "Requires recruiting others to earn money",
        },
        "upfront_fee": {
            "patterns": [
                r"(?:pay|send)\s+(?:fee|payment).*first",
                r"(?:admin|processing|release)\s+fee",
                r"advance\s+fee",
                r"send\s+money.*(?:receive|get|unlock)",
                r"(?:deposit|payment)\s+required",
            ],
            "severity": "HIGH",
            "description": "Requires payment before receiving promised benefit",
        },
        "urgency_pressure": {
            "patterns": [
                r"limited\s+(?:time|spots)",
                r"act\s+(?:now|fast|quickly)",
                r"(?:today|now)\s+only",
                r"(?:urgent|hurry|deadline)",
                r"exclusive\s+opportunity",
                r"spots\s+filling\s+fast",
            ],
            "severity": "MEDIUM",
            "description": "Creates false urgency to pressure a decision",
        },
        "unregistered_securities": {
            "patterns": [
                r"unregistered\s+(?:security|investment)",
                r"private\s+placement",
                r"not\s+registered\s+(?:with|by)\s+(?:SEC|securities)",
                r"exempt\s+from\s+registration",
            ],
            "severity": "HIGH",
            "description": "Investment not registered with regulatory authorities",
        },
        "fake_credentials": {
            "patterns": [
                r"secret\s+(?:method|strategy|system)",
                r"(?:insider|exclusive)\s+information",
                r"guaranteed\s+by\s+(?:government|bank|FDIC)",
                r"(?:certified|licensed)\s+(?:without|no)\s+verification",
            ],
            "severity": "HIGH",
            "description": "Uses unverifiable or false credentials",
        },
        "offshore_unregulated": {
            "patterns": [
                r"offshore\s+(?:account|investment)",
                r"unregulated\s+(?:broker|exchange|fund)",
                r"tax[-\s]?haven",
                r"no\s+reporting\s+required",
            ],
            "severity": "HIGH",
            "description": "Operates outside regulated jurisdictions",
        },
    }

    def __init__(self, openai_client: Any) -> None:
        """Initialize FinancialAdvisor with an AI client.

        Args:
            openai_client: An initialized OpenAI-compatible API client.
        """
        self.openai_client = openai_client
        logger.info("FinancialAdvisor initialized")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _chat(self, system: str, user: str, temperature: float = 0.5) -> str:
        """Call the OpenAI-compatible chat endpoint safely.

        Args:
            system: System-level instructions.
            user: User message.
            temperature: Sampling temperature.

        Returns:
            Model response text or an error string.
        """
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            return f"[Error contacting AI service: {exc}]"

    def _safe_json(self, text: str) -> Any:
        """Parse JSON from model output, stripping markdown fences."""
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                logger.error("JSON parse error: %s", exc)
                return {"error": "Failed to parse JSON", "raw": text}

    def _add_disclaimer(self, response: dict[str, Any]) -> dict[str, Any]:
        """Ensure every response dictionary includes the disclaimer."""
        response["disclaimer"] = self.DISCLAIMER
        response["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return response

    def _analyze_scam_patterns(self, text: str) -> dict[str, Any]:
        """Scan text against known financial scam patterns.

        Returns:
            Analysis with flags, severity, and pattern matches.
        """
        text_lower = text.lower()
        red_flags: list[str] = []
        yellow_flags: list[str] = []
        pattern_matches: list[dict[str, Any]] = []
        highest_severity = "LOW"
        severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

        for pattern_name, pattern_info in self.SCAM_PATTERNS.items():
            matched = False
            for regex in pattern_info["patterns"]:
                if re.search(regex, text_lower, re.IGNORECASE):
                    matched = True
                    break

            if matched:
                pattern_matches.append({
                    "pattern": pattern_name,
                    "description": pattern_info["description"],
                    "severity": pattern_info["severity"],
                })
                if severity_order.get(pattern_info["severity"], 0) > severity_order.get(highest_severity, 0):
                    highest_severity = pattern_info["severity"]

                if pattern_info["severity"] in ("HIGH", "CRITICAL"):
                    red_flags.append(pattern_info["description"])
                else:
                    yellow_flags.append(pattern_info["description"])

        return {
            "pattern_matches": pattern_matches,
            "red_flags": red_flags,
            "yellow_flags": yellow_flags,
            "highest_severity": highest_severity,
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def advise(self, query: str, risk_profile: str = "moderate") -> dict[str, Any]:
        """Answer financial questions with educational intent.

        Provides balanced, educational information with risk context
        and always includes the financial disclaimer.

        Args:
            query: The financial question.
            risk_profile: ``"conservative"``, ``"moderate"``, or ``"aggressive"``.

        Returns:
            An educational response with risk assessment and warnings.
        """
        system = (
            "You are a financial literacy educator. Your goal is to help people "
            "understand financial concepts. You NEVER give personalized investment advice, "
            "stock picks, or specific buy/sell recommendations. "
            "You ALWAYS explain risks and alternatives. "
            f"Include this disclaimer: {self.DISCLAIMER}"
        )
        user_prompt = (
            f"Question: {query}\n"
            f"Risk profile context: {risk_profile}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "answer": "string (educational answer only)",\n'
            '  "risk_assessment": "string (explain risks)",\n'
            '  "alternatives_considered": ["string"],\n'
            '  "warnings": ["string"],\n'
            '  "educational_resources": ["string"],\n'
            '  "complexity_level": "Basic|Intermediate|Advanced",\n'
            '  "related_concepts": ["string"]\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.5)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return self._add_disclaimer(data)

        return self._add_disclaimer({
            "answer": (
                f"I can provide general information about '{query}'. "
                "Please consult a licensed financial advisor for personalized advice."
            ),
            "risk_assessment": "All financial decisions involve risk.",
            "alternatives_considered": ["Consult a financial advisor"],
            "warnings": ["This is educational information only"],
            "educational_resources": [
                "Investopedia.com",
                "SEC.gov investor education",
                "CFPB.gov consumer resources",
            ],
            "complexity_level": "Intermediate",
            "related_concepts": ["Risk management", "Financial planning"],
        })

    def analyze_investment(self, description: str) -> dict[str, Any]:
        """Analyze an investment opportunity for legitimacy.

        Scans the description against known scam patterns and provides
        a legitimacy score with red/green flags.

        Args:
            description: The investment description or pitch.

        Returns:
            A comprehensive legitimacy analysis.
        """
        # Pattern-based analysis
        scam_analysis = self._analyze_scam_patterns(description)
        red_flags = list(scam_analysis["red_flags"])
        yellow_flags = list(scam_analysis["yellow_flags"])

        # Base legitimacy score
        score = 50
        score -= len(red_flags) * 20
        score -= len(yellow_flags) * 10
        score = max(0, min(100, score))

        # Determine risk level
        if score >= 70:
            risk_level = "LOW"
        elif score >= 40:
            risk_level = "MEDIUM"
        elif score >= 20:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # Green flags (positive indicators)
        green_flags: list[str] = []
        if "registered" in description.lower() or "SEC" in description:
            green_flags.append("Mentions regulatory registration")
        if "disclosure" in description.lower() or "prospectus" in description.lower():
            green_flags.append("Mentions disclosure documents")
        if "risk" in description.lower() and "fees" in description.lower():
            green_flags.append("Acknowledges risks and fees")
        if "diversified" in description.lower():
            green_flags.append("Mentions diversification")
        if "fiduciary" in description.lower():
            green_flags.append("Claims fiduciary duty")
        if "track record" in description.lower() or "audited" in description.lower():
            green_flags.append("References track record or auditing")

        # Build recommendation
        if score < 20:
            recommendation = (
                "This investment shows multiple critical warning signs of a scam. "
                "DO NOT invest. Report to authorities if contacted."
            )
        elif score < 40:
            recommendation = (
                "This investment has significant red flags. Exercise extreme caution. "
                "Consult a licensed advisor and verify all claims independently."
            )
        elif score < 70:
            recommendation = (
                "This investment has some concerns. Thoroughly research all claims, "
                "verify registration, and consult a fiduciary advisor before proceeding."
            )
        else:
            recommendation = (
                "This investment appears to have fewer red flags, but always verify "
                "registration, read all disclosures, and consult a fiduciary advisor."
            )

        questions_to_ask = [
            "Is the investment registered with the SEC or state regulators?",
            "What are ALL the fees and how are they structured?",
            "What is the historical track record (independently verified)?",
            "Who are the principals and what is their background?",
            "What is the exit strategy and liquidity terms?",
            "Are there any complaints or enforcement actions (check FINRA, SEC)?",
            "Is the advisor a fiduciary?",
            "Can you get a second opinion from an independent advisor?",
        ]

        verification_steps = [
            "Check SEC.gov EDGAR database for registration",
            "Verify advisor credentials at BrokerCheck.FINRA.org",
            "Search for complaints with state securities regulators",
            "Review the full prospectus or offering circular",
            "Consult an independent fee-only financial advisor",
            "Never invest money you cannot afford to lose",
        ]

        return self._add_disclaimer({
            "legitimacy_score": score,
            "red_flags": red_flags,
            "green_flags": green_flags,
            "yellow_flags": yellow_flags,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "questions_to_ask": questions_to_ask,
            "verification_steps": verification_steps,
            "scam_pattern_analysis": scam_analysis["pattern_matches"],
        })

    def budget_planner(self, income: float, expenses: dict[str, float]) -> dict[str, Any]:
        """Create a budget plan using the 50/30/20 rule.

        The 50/30/20 framework allocates:
        - 50% to needs (housing, food, utilities, transport)
        - 30% to wants (entertainment, dining out, hobbies)
        - 20% to savings and debt repayment

        Args:
            income: Monthly after-tax income.
            expenses: Dictionary mapping expense categories to amounts.

        Returns:
            A comprehensive budget analysis with savings plan and recommendations.
        """
        try:
            income = float(income)
            expenses = {k: float(v) for k, v in expenses.items()}
        except (ValueError, TypeError) as exc:
            return self._add_disclaimer({
                "error": f"Invalid numeric input: {exc}",
                "budget": {},
                "savings_plan": {},
                "debt_strategy": {},
                "recommendations": ["Please provide valid numbers for income and expenses."],
            })

        total_expenses = sum(expenses.values())
        remaining = income - total_expenses

        # Categorize expenses (heuristic)
        needs_categories = {"rent", "mortgage", "utilities", "food", "groceries",
                            "insurance", "health", "medical", "transport", "transportation",
                            "gas", "phone", "internet", "childcare", "minimum_debt"}
        wants_categories = {"entertainment", "dining", "restaurants", "hobbies",
                            "shopping", "travel", "subscriptions", "streaming", "gym"}

        needs_total = sum(v for k, v in expenses.items() if k.lower() in needs_categories)
        wants_total = sum(v for k, v in expenses.items() if k.lower() in wants_categories)
        other_total = total_expenses - needs_total - wants_total

        # 50/30/20 targets
        target_needs = income * 0.50
        target_wants = income * 0.30
        target_savings = income * 0.20

        budget = {
            "monthly_income": round(income, 2),
            "total_expenses": round(total_expenses, 2),
            "remaining": round(remaining, 2),
            "breakdown": {
                "needs": {
                    "actual": round(needs_total, 2),
                    "target": round(target_needs, 2),
                    "percentage_of_income": round((needs_total / income) * 100, 1) if income else 0,
                    "status": "on_track" if needs_total <= target_needs else "over_budget",
                    "categories": {k: v for k, v in expenses.items()
                                   if k.lower() in needs_categories},
                },
                "wants": {
                    "actual": round(wants_total, 2),
                    "target": round(target_wants, 2),
                    "percentage_of_income": round((wants_total / income) * 100, 1) if income else 0,
                    "status": "on_track" if wants_total <= target_wants else "over_budget",
                    "categories": {k: v for k, v in expenses.items()
                                   if k.lower() in wants_categories},
                },
                "other": {
                    "actual": round(other_total, 2),
                    "categories": {k: v for k, v in expenses.items()
                                   if k.lower() not in needs_categories
                                   and k.lower() not in wants_categories},
                },
            },
            "50_30_20_analysis": {
                "needs_target_percent": 50,
                "wants_target_percent": 30,
                "savings_target_percent": 20,
                "actual_needs_percent": round((needs_total / income) * 100, 1) if income else 0,
                "actual_wants_percent": round((wants_total / income) * 100, 1) if income else 0,
                "actual_savings_potential_percent": round((remaining / income) * 100, 1) if income else 0,
            },
        }

        # Savings plan
        savings_plan = {
            "emergency_fund_target": round(income * 6, 2),
            "emergency_fund_months_to_save": 12,
            "monthly_savings_goal": round(target_savings, 2),
            "actual_available_for_savings": round(remaining, 2),
            "recommendations": [],
        }

        if remaining >= target_savings:
            savings_plan["recommendations"].append(
                f"Great! You can save ${target_savings:.2f}/month ({target_savings/income*100:.0f}% of income)"
            )
        else:
            shortfall = target_savings - remaining
            savings_plan["recommendations"].append(
                f"Try to increase savings by ${shortfall:.2f}/month to reach the 20% target"
            )

        savings_plan["recommendations"].extend([
            "Automate transfers to savings on payday",
            "Keep emergency fund in a high-yield savings account",
            "Consider increasing 401(k) contribution if employer matches",
        ])

        # Debt strategy
        debt_strategy = {
            "avalanche_method": "Pay minimums on all debts, put extra toward highest-interest debt first",
            "snowball_method": "Pay minimums on all debts, put extra toward smallest balance first",
            "recommendation": "Avalanche saves more money; snowball provides psychological wins. Choose based on your motivation style.",
            "tips": [
                "Never miss minimum payments — it hurts your credit score",
                "Consider balance transfers for high-interest credit cards",
                "Contact creditors for hardship programs if struggling",
                "Avoid taking on new debt while paying off existing debt",
            ],
        }

        # Overall recommendations
        recommendations: list[str] = []
        if remaining < 0:
            recommendations.append(
                f"CRITICAL: You are spending ${abs(remaining):.2f} more than you earn. "
                "Reduce expenses immediately or increase income."
            )
        elif remaining < target_savings * 0.5:
            recommendations.append(
                "Your savings margin is thin. Review wants category for reduction opportunities."
            )
        else:
            recommendations.append(
                f"You have ${remaining:.2f} left after expenses — allocate to savings, debt, and investments."
            )

        if needs_total > target_needs:
            recommendations.append(
                f"Needs are {(needs_total/target_needs)*100:.0f}% of target. "
                "Consider housing/transport cost reduction if possible."
            )

        recommendations.extend([
            "Track spending weekly to stay on budget",
            "Review subscriptions — cancel unused services",
            "Build emergency fund before investing",
            "Increase income through side work or negotiation if needed",
        ])

        return self._add_disclaimer({
            "budget": budget,
            "savings_plan": savings_plan,
            "debt_strategy": debt_strategy,
            "recommendations": recommendations,
        })

    def explain_concept(self, concept: str) -> dict[str, Any]:
        """Explain a financial concept in simple terms.

        Built-in knowledge for common concepts; falls back to AI for others.

        Args:
            concept: The financial concept to explain.
                Supported: compound_interest, inflation, diversification,
                credit_score, mortgage, retirement_planning, tax_basics,
                budgeting, emergency_fund, debt_management.

        Returns:
            A dictionary with simple explanation, example, formula, and importance.
        """
        concept_key = concept.lower().strip().replace(" ", "_")

        # Built-in explanations for known concepts
        built_in = {
            "compound_interest": {
                "concept": "Compound Interest",
                "simple_explanation": (
                    "Interest earned on both your original money AND the interest "
                    "that money has already earned. It's like a snowball growing "
                    "as it rolls downhill — your money grows faster over time."
                ),
                "example": (
                    "If you invest $1,000 at 7% annual interest, after 1 year you have $1,070. "
                    "In year 2, you earn 7% on $1,070 (not just $1,000), giving you $1,144.90. "
                    "After 30 years: $7,612 — without adding any more money!"
                ),
                "formula": "A = P(1 + r/n)^(nt)\nWhere A=final amount, P=principal, r=rate, n=compounds per year, t=years",
                "importance": (
                    "Compound interest is the most powerful force in wealth building. "
                    "Starting early gives you a massive advantage due to exponential growth."
                ),
            },
            "inflation": {
                "concept": "Inflation",
                "simple_explanation": (
                    "The gradual increase in prices over time, which means your money "
                    "buys less each year. If inflation is 3%, something that costs $100 "
                    "today will cost about $103 next year."
                ),
                "example": (
                    "A gallon of milk cost $2.50 in 2000. With 3% average inflation, "
                    "it costs about $4.80 in 2024. Your $100 in 2000 would need to be "
                    "$181 today to buy the same things."
                ),
                "formula": "Future Value = Present Value / (1 + inflation_rate)^years",
                "importance": (
                    "Inflation erodes purchasing power. Your investments must earn more than "
                    "inflation to grow in real terms. Cash loses value over time."
                ),
            },
            "diversification": {
                "concept": "Diversification",
                "simple_explanation": (
                    "Spreading your money across different types of investments so that "
                    "one bad investment doesn't ruin your whole portfolio. "
                    "'Don't put all your eggs in one basket.'"
                ),
                "example": (
                    "Instead of investing $10,000 all in one company's stock, you might "
                    "put $3,000 in US stocks, $2,000 in international stocks, $2,500 in bonds, "
                    "$1,500 in real estate, and $1,000 in cash. If one area drops, others may rise."
                ),
                "formula": "Portfolio risk < weighted average of individual asset risks (due to correlation < 1)",
                "importance": (
                    "Diversification is the only 'free lunch' in investing — it reduces risk "
                    "without necessarily reducing expected returns. Essential for long-term investing."
                ),
            },
            "credit_score": {
                "concept": "Credit Score",
                "simple_explanation": (
                    "A number (300-850) that represents how trustworthy you are with borrowed money. "
                    "Higher scores mean lenders trust you more and offer better interest rates."
                ),
                "example": (
                    "With a 760 credit score, you might get a mortgage at 6.5%. With a 620 score, "
                    "the same mortgage could be 8.0%. On a $300,000 30-year loan, that's a "
                    "difference of $93,000 in total interest paid!"
                ),
                "formula": "FICO Score = Payment History (35%) + Amounts Owed (30%) + Length (15%) + New Credit (10%) + Mix (10%)",
                "importance": (
                    "Your credit score affects loans, credit cards, insurance rates, apartment rentals, "
                    "and even some jobs. Building good credit saves thousands of dollars over a lifetime."
                ),
            },
            "mortgage": {
                "concept": "Mortgage",
                "simple_explanation": (
                    "A loan from a bank to buy a house. The house serves as collateral — "
                    "if you don't pay, the bank can take it. You typically repay over 15-30 years "
                    "with monthly payments covering principal + interest."
                ),
                "example": (
                    "For a $400,000 home with 20% down ($80,000), you borrow $320,000. "
                    "At 7% for 30 years, your monthly payment is about $2,129. Over 30 years, "
                    "you pay $766,440 total — $320,000 principal + $446,440 interest."
                ),
                "formula": "M = P[r(1+r)^n]/[(1+r)^n-1] where M=monthly payment, P=principal, r=monthly rate, n=payments",
                "importance": (
                    "For most people, a mortgage is the largest debt they'll ever have. Understanding "
                    "the terms, rates, and total cost is essential for long-term financial health."
                ),
            },
            "retirement_planning": {
                "concept": "Retirement Planning",
                "simple_explanation": (
                    "Planning how to have enough money to stop working when you want. "
                    "It involves estimating future expenses, calculating how much to save, "
                    "and choosing the right accounts (401k, IRA) and investments."
                ),
                "example": (
                    "If you want $60,000/year in retirement and Social Security provides $24,000, "
                    "you need to generate $36,000/year from savings. Using the 4% rule, "
                    "you need $900,000 saved ($36,000 / 0.04). Starting at 25, saving $500/month "
                    "at 7% returns gets you there by 65."
                ),
                "formula": "Required Savings = Annual Income Needed / Safe Withdrawal Rate (typically 4%)",
                "importance": (
                    "The earlier you start, the less you need to save monthly thanks to compound interest. "
                    "Delaying by even 5 years can double the required monthly savings amount."
                ),
            },
            "tax_basics": {
                "concept": "Tax Basics",
                "simple_explanation": (
                    "Income tax is money you pay the government based on your earnings. "
                    "The US uses a progressive system — higher income is taxed at higher rates, "
                    "but only the portion in each bracket is taxed at that rate."
                ),
                "example": (
                    "If you earn $60,000 in 2024 (single):\n"
                    "- First $11,600: 0% (standard deduction)\n"
                    "- $11,601 to $23,225: 10% = $1,162\n"
                    "- $23,226 to $48,475: 12% = $3,030\n"
                    "- $48,476 to $60,000: 22% = $2,536\n"
                    "Total federal tax: ~$6,728 (effective rate: ~11.2%, not 22%)"
                ),
                "formula": "Tax = sum of (income in bracket x bracket rate) - deductions - credits",
                "importance": (
                    "Understanding taxes helps you make better financial decisions, maximize deductions, "
                    "and avoid surprises. Tax-advantaged accounts (401k, IRA, HSA) can save thousands."
                ),
            },
            "budgeting": {
                "concept": "Budgeting",
                "simple_explanation": (
                    "Creating a plan for how to spend your money. A budget ensures you cover "
                    "needs, enjoy wants responsibly, and save for the future."
                ),
                "example": (
                    "With $4,000/month income:\n"
                    "- Needs (50% = $2,000): Rent $1,200, groceries $300, utilities $150, transport $200, insurance $150\n"
                    "- Wants (30% = $1,200): Dining $200, entertainment $150, gym $50, shopping $200, travel $200, buffer $400\n"
                    "- Savings (20% = $800): Emergency fund $300, retirement $300, goals $200"
                ),
                "formula": "Income = Needs (50%) + Wants (30%) + Savings/Debt (20%)",
                "importance": (
                    "Budgeting is the foundation of financial health. Without one, money "
                    "slips away unnoticed. With one, you control your financial destiny."
                ),
            },
            "emergency_fund": {
                "concept": "Emergency Fund",
                "simple_explanation": (
                    "Savings set aside specifically for unexpected expenses like medical bills, "
                    "car repairs, or job loss. It prevents you from going into debt when life happens."
                ),
                "example": (
                    "If your monthly expenses are $3,000, aim for $9,000-$18,000 in an emergency fund. "
                    "Start with $1,000 as a mini-fund, then build to 3 months, then 6 months. "
                    "Keep it in a high-yield savings account for easy access."
                ),
                "formula": "Target = Monthly Expenses x 3 to 6 months",
                "importance": (
                    "An emergency fund is your financial shock absorber. Without one, a single "
                    "surprise expense can derail your finances for years through high-interest debt."
                ),
            },
            "debt_management": {
                "concept": "Debt Management",
                "simple_explanation": (
                    "Strategies for paying off debt efficiently. The two main methods are: "
                    "Avalanche (pay highest interest first — saves the most money) and "
                    "Snowball (pay smallest balance first — gives psychological wins)."
                ),
                "example": (
                    "You have:\n"
                    "- Credit card A: $5,000 at 22% APR\n"
                    "- Credit card B: $2,000 at 18% APR\n"
                    "- Student loan: $15,000 at 5% APR\n\n"
                    "Avalanche: Pay minimums on B and student loan, put extra toward A (22%).\n"
                    "Snowball: Pay minimums on A and student loan, put extra toward B ($2,000).\n"
                    "Avalanche saves ~$800 more in interest; snowball may keep you motivated."
                ),
                "formula": "Total Interest = sum of (balance x rate x time) for each debt",
                "importance": (
                    "High-interest debt (especially credit cards at 20%+) is a financial emergency. "
                    "The interest alone can double your debt in 3-4 years. Aggressive payoff is critical."
                ),
            },
        }

        if concept_key in built_in:
            result = dict(built_in[concept_key])
            return self._add_disclaimer(result)

        # Fall back to AI for unknown concepts
        system = (
            "You are a financial literacy educator. Explain financial concepts clearly "
            "with examples and practical formulas. Never give investment advice."
        )
        user_prompt = (
            f"Explain the financial concept: '{concept}'\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "concept": "string",\n'
            '  "simple_explanation": "string",\n'
            '  "example": "string",\n'
            '  "formula": "string",\n'
            '  "importance": "string"\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.6)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return self._add_disclaimer(data)

        return self._add_disclaimer({
            "concept": concept,
            "simple_explanation": f"'{concept}' is an important financial concept. Consult educational resources for details.",
            "example": "See Investopedia or similar educational sites for examples.",
            "formula": "N/A",
            "importance": "Understanding financial concepts is key to financial well-being.",
        })

    def compare_options(self, option_a: str, option_b: str) -> dict[str, Any]:
        """Compare two financial options side-by-side.

        Args:
            option_a: First financial option (e.g. ``"Rent"``).
            option_b: Second financial option (e.g. ``"Buy"``).

        Returns:
            A structured comparison with pros, cons, and verdict.
        """
        system = (
            "You are a balanced financial educator. Present both sides fairly, "
            "highlight key trade-offs, and help people understand the factors "
            "that matter for THEIR situation. Never give one-size-fits-all advice."
        )
        user_prompt = (
            f"Compare these two financial options:\n"
            f"Option A: {option_a}\n"
            f"Option B: {option_b}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "comparison_table": [{"factor": "string", "option_a": "string", "option_b": "string"}],\n'
            '  "pros_a": ["string"],\n'
            '  "cons_a": ["string"],\n'
            '  "pros_b": ["string"],\n'
            '  "cons_b": ["string"],\n'
            '  "when_a_is_better": "string",\n'
            '  "when_b_is_better": "string",\n'
            '  "verdict": "string (balanced summary, no definitive recommendation)"\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.5)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return self._add_disclaimer(data)

        return self._add_disclaimer({
            "comparison_table": [
                {"factor": "Cost", "option_a": f"Varies for {option_a}", "option_b": f"Varies for {option_b}"},
                {"factor": "Flexibility", "option_a": "Depends on situation", "option_b": "Depends on situation"},
                {"factor": "Risk", "option_a": "Varies", "option_b": "Varies"},
            ],
            "pros_a": [f"Benefits specific to {option_a}"],
            "cons_a": [f"Drawbacks specific to {option_a}"],
            "pros_b": [f"Benefits specific to {option_b}"],
            "cons_b": [f"Drawbacks specific to {option_b}"],
            "when_a_is_better": f"When {option_a} aligns with your goals and situation",
            "when_b_is_better": f"When {option_b} aligns with your goals and situation",
            "verdict": f"Both {option_a} and {option_b} have merits. The right choice depends on your personal financial situation, goals, and risk tolerance. Consult a fiduciary advisor for personalized guidance.",
        })

    def detect_financial_scam(self, description: str) -> dict[str, Any]:
        """Specific analysis for financial scams.

        Performs deep pattern matching against known scam indicators
        and provides actionable protection advice.

        Args:
            description: The investment pitch, message, or offer.

        Returns:
            A comprehensive scam analysis with likelihood, type,
            red flags, and protective actions.
        """
        analysis = self._analyze_scam_patterns(description)

        # Calculate scam likelihood (0-100)
        base_score = 0
        base_score += len(analysis["red_flags"]) * 15
        base_score += len(analysis["yellow_flags"]) * 8
        base_score += len(analysis["pattern_matches"]) * 5

        # Boost for critical patterns
        for pm in analysis["pattern_matches"]:
            if pm["severity"] == "CRITICAL":
                base_score += 20

        likelihood = min(100, base_score)

        # Determine scam type
        scam_type = "Unknown"
        type_scores: dict[str, int] = {}
        for pm in analysis["pattern_matches"]:
            type_scores[pm["pattern"]] = type_scores.get(pm["pattern"], 0) + 1

        if type_scores:
            scam_type = max(type_scores, key=type_scores.get)
            scam_type = scam_type.replace("_", " ").title()

        # Risk level
        if likelihood >= 80:
            risk_level = "CRITICAL"
        elif likelihood >= 60:
            risk_level = "HIGH"
        elif likelihood >= 40:
            risk_level = "MEDIUM"
        elif likelihood >= 20:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        # Red flags list
        all_red_flags = list(analysis["red_flags"])
        additional_red_flags = [
            "Requests payment via wire transfer, gift cards, or cryptocurrency",
            "Uses high-pressure sales tactics",
            "Claims 'everyone is doing it' or uses social proof manipulation",
            "Refuses to provide written information",
            "No verifiable physical address or contact info",
            "Promises 'secret' or 'exclusive' methods",
            "Asks you to recruit friends and family",
            "Unregistered with SEC, FINRA, or state regulators",
        ]

        # Add contextual red flags
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["crypto", "bitcoin", "ethereum"]):
            all_red_flags.append("Cryptocurrency investments are highly volatile and often targeted by scammers")
        if "forex" in desc_lower:
            all_red_flags.append("Forex scams are common — verify registration with CFTC/NFA")
        if "binary option" in desc_lower:
            all_red_flags.append("Binary options are banned or heavily restricted in most jurisdictions")

        protections = [
            "NEVER send money to someone you don't know and trust",
            "Verify registration at SEC.gov, FINRA.org, or your state securities regulator",
            "Search the company name + 'scam', 'complaint', or 'review'",
            "Get everything in writing — verbal promises mean nothing",
            "Consult an independent, fee-only financial advisor before investing",
            "If it sounds too good to be true, it almost certainly is",
            "Never share bank account, Social Security, or login information",
            "Report suspected scams to SEC.gov/complaint, FTC.gov, or FBI's IC3.gov",
            "Check if the salesperson has disciplinary history at BrokerCheck.FINRA.org",
            "Take time to research — legitimate investments don't evaporate overnight",
        ]

        return self._add_disclaimer({
            "scam_likelihood": likelihood,
            "identified_scam_type": scam_type,
            "risk_level": risk_level,
            "red_flags": all_red_flags + [rf for rf in additional_red_flags
                                           if rf not in all_red_flags][:10],
            "yellow_flags": analysis["yellow_flags"],
