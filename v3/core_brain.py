"""Omega AI v3.1 — Central Brain / Orchestrator
Routes queries to the correct capability module.
Includes: conversation memory, unified response schema, structured logging.
"""
from __future__ import annotations

import time
from typing import Any

from response_schema import ResponseDict, ok, err, from_dict
from logger import info, warning, error
from utils import colorize, Colors
from local_llm import LLM


class OmegaBrain:
    """Central orchestrator for Luqi-AI capabilities."""

    # Intent detection keywords — ordered by specificity (most specific first)
    INTENT_KEYWORDS: dict[str, list[str]] = {
        "language": ["translate", "in zulu", "in xhosa", "in swahili", "say in", "how do you say",
                     "greetings in", "language lesson", "speak", "meaning of", "what does * mean in"],
        "tax": ["tax", "sars", "firs", "kra", "gra", "vat", "income tax", "corporate tax",
                "tax return", "filing", "deduction", "rebate", "capital gains tax", "crypto tax"],
        "investment": ["bitcoin", "btc", "ethereum", "crypto", "mining", "asic", "hashrate",
                       "portfolio", "invest", "trading", "forex", "stock market", "dividend",
                       "blockchain", "altcoin", "defi", "nft", "staking", "wallet"],
        "companion": ["train you", "teach you", "rate your answer", "feedback", "that was wrong",
                      "improve your", "learn from", "training mode", "companion mode"],
        "self_improve": ["self improve", "lab report", "health check", "benchmark", "system status",
                         "performance report", "analyze yourself", "how are you doing"],
        "opportunity": ["business opportunity", "market gap", "trend analysis", "entrepreneur",
                        "startup idea", "african market", "investment opportunity", "side hustle"],
        "email": ["write an email", "draft email", "email to", "professional email", "grammar check",
                  "improve this email", "email template", "tone analysis", "subject line"],
        "financial_lit": ["scam", "ponzi", "budget", "save money", "financial literacy",
                          "debt", "credit score", "emergency fund", "stokvel", "mobile money",
                          "protect from", "is this a scam", "red flag", "too good to be true"],
        "professional": ["write code", "python function", "javascript", "engineering calc",
                         "how to build", "architecture question", "plumbing help", "electrical",
                         "medical info", "legal question", "hr policy", "marketing strategy"],
        "deep_research": ["research", "analyze", "compare", "difference between", "explain",
                          "what is", "how does", "why is", "history of", "pros and cons",
                          "deep dive", "comprehensive", "overview of", "tell me about"],
    }

    def __init__(self, max_history: int = 6) -> None:
        self.llm = LLM()
        self.max_history = max_history
        self.history: list[dict[str, str]] = []
        info("OmegaBrain initialized (history_window=%d)", max_history)

    def analyze_intent(self, query: str) -> dict[str, Any]:
        """Classify user intent into capability category."""
        q_lower = query.lower().strip()
        scores: dict[str, int] = {cat: 0 for cat in self.INTENT_KEYWORDS}

        for category, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if "*" in kw:
                    parts = kw.split("*")
                    if parts[0] in q_lower and parts[1] in q_lower:
                        scores[category] += 3
                elif kw in q_lower:
                    scores[category] += 2

        best = max(scores, key=scores.get)
        best_score = scores[best]

        if best_score == 0:
            return {"category": "general", "confidence": 0, "all_scores": scores}

        return {
            "category": best,
            "confidence": min(1.0, best_score / 5),
            "all_scores": scores,
        }

    def _build_context(self) -> str:
        """Build conversation context from history for LLM prompts."""
        if not self.history:
            return ""
        lines = ["Previous conversation:"]
        for h in self.history[-self.max_history:]:
            lines.append(f"  User: {h['query']}")
            resp_preview = h['response'][:180]
            if len(h['response']) > 180:
                resp_preview += "..."
            lines.append(f"  Assistant: {resp_preview}")
        return "\n".join(lines)

    def orchestrate_response(self, query: str) -> ResponseDict:
        """Full pipeline: intent -> route -> execute -> store -> return."""
        start = time.perf_counter()
        intent = self.analyze_intent(query)
        category = intent["category"]
        info("Intent: %s (confidence=%.2f) for query: %s", category, intent["confidence"], query[:60])

        handler = self._get_handler(category)
        if handler:
            try:
                raw_result = handler(query)
                if isinstance(raw_result, dict) and "success" in raw_result:
                    result = from_dict(raw_result, module=category)
                elif isinstance(raw_result, dict):
                    result = from_dict(raw_result, module=category)
                else:
                    result = ok(str(raw_result), module=category)
            except Exception as exc:
                error("Handler %s failed: %s", category, exc, exc_info=True)
                result = err(str(exc), module=category,
                             fallback_response=self._general_response(query))
                category = "general"
        else:
            result = ok(self._general_response(query), module="general")

        # Attach timing
        elapsed_ms = (time.perf_counter() - start) * 1000
        result["response_time_ms"] = round(elapsed_ms, 1)
        result["module"] = category

        # Store in conversation history
        self.history.append({"query": query, "response": result["response"]})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history:]

        return result

    def _get_handler(self, category: str):
        """Get handler method for a category."""
        handlers: dict[str, Any] = {
            "deep_research": self._handle_research,
            "investment": self._handle_investment,
            "tax": self._handle_tax,
            "companion": self._handle_companion,
            "self_improve": self._handle_self_improve,
            "language": self._handle_language,
            "financial_lit": self._handle_financial_lit,
            "professional": self._handle_professional,
            "opportunity": self._handle_opportunity,
            "email": self._handle_email,
        }
        return handlers.get(category)

    # -- Individual handlers

    def _handle_research(self, query: str) -> ResponseDict:
        """DEEP RESEARCH — multi-source research with citations."""
        from deep_research import DeepResearch
        dr = DeepResearch()
        result = dr.research(query, depth="deep")
        return from_dict(result, module="deep_research")

    def _handle_investment(self, query: str) -> ResponseDict:
        """INVESTMENT — crypto, mining, portfolio guidance."""
        from investment_mining import InvestmentMining
        im = InvestmentMining()
        q = query.lower()
        if "mining" in q or "profitability" in q or "asic" in q:
            return ok(im.mining_guide("profitability", {}), module="investment")
        elif "portfolio" in q:
            return ok(im.portfolio_advice({"BTC": 0.5, "ETH": 0.3}), module="investment")
        else:
            analysis = im.investment_analysis("bitcoin")
            return ok(analysis.get("outlook", "") + im.disclaimer(),
                      module="investment",
                      sources=analysis.get("sources", []))

    def _handle_tax(self, query: str) -> ResponseDict:
        """TAX ENGINE — country-specific tax guidance."""
        from tax_engine import TaxEngine
        te = TaxEngine()
        country = "south africa"
        for c in ["south africa", "nigeria", "kenya", "ghana", "egypt", "morocco",
                  "united states", "united kingdom", "australia"]:
            if c in query.lower():
                country = c
                break
        return ok(te.tax_query(country, "personal_income"),
                  module="tax",
                  sources=[{"title": f"{country.title()} Tax Guide", "source": "Tax Authority"}])

    def _handle_companion(self, query: str) -> ResponseDict:
        return ok(
            "Enter training mode with command: /train\n\nYou can:\n"
            "• Rate my responses (1-5 stars)\n"
            "• Submit corrections\n"
            "• View training status\n\n"
            "Your feedback helps me improve!",
            module="companion"
        )

    def _handle_self_improve(self, query: str) -> ResponseDict:
        from self_improve import SelfImprovementLab
        lab = SelfImprovementLab()
        return ok(lab.lab_report(), module="self_improve")

    def _handle_language(self, query: str) -> ResponseDict:
        from african_languages import AfricanLanguages
        al = AfricanLanguages()
        q = query.lower()
        for lang_code, info_data in al.LANGUAGES.items():
            lang_name = info_data["name"].lower()
            if f" in {lang_code}" in q or lang_name in q:
                text = "hello"
                if '"' in query:
                    parts = query.split('"')
                    if len(parts) >= 2:
                        text = parts[1]
                elif "translate" in q:
                    text = q.replace("translate", "").replace(f"in {lang_code}", "").replace(lang_name, "").strip(" '").split(" to ")[0]
                    if not text:
                        text = "hello"
                return ok(al.translate(text, lang_code), module="language")
        return ok(al.learn_mode("zu"), module="language")

    def _handle_financial_lit(self, query: str) -> ResponseDict:
        from financial_literacy import FinancialLiteracy
        fl = FinancialLiteracy()
        if "scam" in query.lower():
            result = fl.scam_check(query)
            lines = [
                f"Scam Risk Score: {result['risk_score']}/100",
                result['risk_level'],
                "",
                "Red Flags:",
            ]
            for flag in result['red_flags']:
                lines.append(f"  • {flag}")
            lines.extend(["", result['advice']])
            return ok("\n".join(lines), module="financial_lit")
        return ok(fl.lesson("budgeting"), module="financial_lit")

    def _handle_professional(self, query: str) -> ResponseDict:
        from professional_assist import ProfessionalAssist
        pa = ProfessionalAssist()
        return ok(pa.get_help("software_eng", query), module="professional")

    def _handle_opportunity(self, query: str) -> ResponseDict:
        from opportunity_engine import OpportunityEngine
        oe = OpportunityEngine()
        country = ""
        for c in ["nigeria", "kenya", "ghana", "south africa", "egypt", "morocco", "ethiopia"]:
            if c in query.lower():
                country = c
                break
        ops = oe.african_opportunities(country)
        lines = [f"## African Business Opportunities{f' in {country.title()}' if country else ''}\n"]
        sources: list[dict[str, str]] = []
        for op in ops[:5]:
            lines.append(f"• {op['title']}")
            lines.append(f"  {op['description'][:120]}...")
            if op.get("source"):
                sources.append({"title": op["title"], "source": op["source"]})
        return ok("\n".join(lines), module="opportunity", sources=sources)

    def _handle_email(self, query: str) -> ResponseDict:
        from email_assistant import EmailAssistant
        ea = EmailAssistant()
        if "write" in query.lower() or "draft" in query.lower():
            return ok(ea.compose_email("follow_up", "Recipient", ["Project update"], topic="Project Update"),
                      module="email")
        return ok(ea.improve_email(query), module="email")

    def _general_response(self, query: str) -> str:
        context = self._build_context()
        if context:
            full_prompt = f"{context}\n\nCurrent query: {query}\n\nPlease respond helpfully."
        else:
            full_prompt = query
        return self.llm.chat(
            full_prompt,
            system_prompt=(
                "You are Luqi-AI, a helpful, knowledgeable assistant specialized in "
                "African markets, finance, technology, and languages. Always provide "
                "well-structured, accurate responses with citations when possible."
            ),
        )

    @staticmethod
    def startup_banner() -> str:
        return "\n".join([
            "╔══════════════════════════════════════════════════════════╗",
            "║                                                          ║",
            "║   Luqi-AI                                                ║",
            "║              Intelligence Without Limits                 ║",
            "║                    Version 3.1                           ║",
            "║                                                          ║",
            "╚══════════════════════════════════════════════════════════╝",
        ])

    @staticmethod
    def show_menu() -> str:
        return """
┌─────────────────────────────────────────────────────────┐
│  CAPABILITY MENU (v3.1)                                  │
├─────────────────────────────────────────────────────────┤
│  [1]  Deep Research   — Multi-source research           │
│  [2]  Investment      — Crypto & mining guidance        │
│  [3]  Tax Engine      — Global tax support              │
│  [4]  Financial Lit   — Education & scam protection     │
│  [5]  Languages       — African language support        │
│  [6]  Professional    — Multi-domain assistance         │
│  [7]  Opportunities   — Business & market seeking       │
│  [8]  Email Assistant — Grammar & composition           │
│  [9]  Companion       — Train & improve Luqi-AI         │
│  [10] Lab Report      — System health & analytics       │
├─────────────────────────────────────────────────────────┤
│  Commands: /menu  /train  /status  /save  /quit         │
└─────────────────────────────────────────────────────────┘
"""