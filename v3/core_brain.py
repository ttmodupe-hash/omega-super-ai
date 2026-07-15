"""Omega AI v3 — Central Brain / Orchestrator
Routes queries to the correct capability module.
"""
from __future__ import annotations

from typing import Any

from utils import colorize, Colors
from local_llm import LLM


class OmegaBrain:
    """Central orchestrator for Luqi-AI capabilities."""

    # Intent detection keywords — ordered by specificity
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

    def __init__(self) -> None:
        self.llm = LLM()

    def analyze_intent(self, query: str) -> dict[str, Any]:
        """Classify user intent into capability category."""
        q_lower = query.lower().strip()

        scores: dict[str, int] = {cat: 0 for cat in self.INTENT_KEYWORDS}

        for category, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if "*" in kw:
                    # Wildcard pattern
                    parts = kw.split("*")
                    if parts[0] in q_lower and parts[1] in q_lower:
                        scores[category] += 3
                elif kw in q_lower:
                    scores[category] += 2

        # Find best match
        best = max(scores, key=scores.get)
        best_score = scores[best]

        if best_score == 0:
            return {"category": "general", "confidence": 0, "all_scores": scores}

        return {
            "category": best,
            "confidence": min(1.0, best_score / 5),
            "all_scores": scores,
        }

    def route_query(self, query: str, intent: dict[str, Any]) -> str:
        """Return which module should handle the query."""
        return intent.get("category", "general")

    def orchestrate_response(self, query: str, history: list | None = None) -> dict[str, Any]:
        """Full pipeline: intent → route → execute → return."""
        intent = self.analyze_intent(query)
        category = intent["category"]

        response_data: dict[str, Any] = {
            "query": query,
            "category": category,
            "confidence": intent["confidence"],
            "response": "",
            "sources": [],
        }

        # Route to appropriate handler
        handler = self._get_handler(category)
        if handler:
            try:
                result = handler(query)
                if isinstance(result, dict):
                    response_data["response"] = result.get("response", result.get("summary", str(result)))
                    response_data["sources"] = result.get("sources", [])
                else:
                    response_data["response"] = str(result)
            except Exception as e:
                response_data["response"] = f"[Error in {category} module: {e}]\n\nFalling back to general response."
                response_data["category"] = "general"
        else:
            response_data["response"] = self._general_response(query)

        return response_data

    def _get_handler(self, category: str):
        """Get handler function for category."""
        handlers = {
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

    def _handle_research(self, query: str) -> dict[str, Any]:
        from deep_research import deep_research
        return deep_research(query, depth="deep")

    def _handle_investment(self, query: str) -> dict[str, Any]:
        from investment_mining import InvestmentMining
        im = InvestmentMining()
        if "mining" in query.lower() or "profitability" in query.lower():
            return {"response": im.mining_guide("profitability", {}), "sources": []}
        elif "portfolio" in query.lower():
            return {"response": im.portfolio_advice({"BTC": 0.5, "ETH": 0.3}), "sources": []}
        else:
            return {"response": im.investment_analysis("bitcoin")["outlook"] + im.disclaimer(), "sources": []}

    def _handle_tax(self, query: str) -> dict[str, Any]:
        from tax_engine import TaxEngine
        te = TaxEngine()
        country = "south africa"
        for c in ["south africa", "nigeria", "kenya", "ghana", "egypt", "morocco", "united states", "united kingdom"]:
            if c in query.lower():
                country = c
                break
        return {"response": te.tax_query(country, "personal_income"), "sources": [{"title": f"{country.title()} Tax Guide", "source": "Tax Authority"}]}

    def _handle_companion(self, query: str) -> dict[str, Any]:
        return {"response": "Enter training mode with command: /train\n\nYou can:\n• Rate my responses (1-5 stars)\n• Submit corrections\n• View training status\n\nYour feedback helps me improve!"}

    def _handle_self_improve(self, query: str) -> dict[str, Any]:
        from self_improve import SelfImprovementLab
        lab = SelfImprovementLab()
        return {"response": lab.lab_report(), "sources": []}

    def _handle_language(self, query: str) -> dict[str, Any]:
        from african_languages import AfricanLanguages
        al = AfricanLanguages()
        for lang_code in al.LANGUAGES:
            if f"in {lang_code}" in query.lower() or al.LANGUAGES[lang_code]["name"].lower() in query.lower():
                return {"response": al.translate("hello", lang_code), "sources": []}
        return {"response": al.learn_mode("zu"), "sources": []}

    def _handle_financial_lit(self, query: str) -> dict[str, Any]:
        from financial_literacy import FinancialLiteracy
        fl = FinancialLiteracy()
        if "scam" in query.lower():
            result = fl.scam_check(query)
            return {"response": f"Scam Risk Score: {result['risk_score']}/100\n{result['risk_level']}\n\nRed Flags:\n" + "\n".join(result['red_flags']) + f"\n\n{result['advice']}", "sources": []}
        return {"response": fl.lesson("budgeting"), "sources": []}

    def _handle_professional(self, query: str) -> dict[str, Any]:
        from professional_assist import ProfessionalAssist
        pa = ProfessionalAssist()
        return {"response": pa.get_help("software_eng", query), "sources": []}

    def _handle_opportunity(self, query: str) -> dict[str, Any]:
        from opportunity_engine import OpportunityEngine
        oe = OpportunityEngine()
        ops = oe.african_opportunities()
        return {"response": "## African Business Opportunities\n\n" + "\n".join(f"- {op['title']}: {op['description'][:100]}..." for op in ops[:5]), "sources": [{"title": op["title"], "source": op["source"]} for op in ops[:3]]}

    def _handle_email(self, query: str) -> dict[str, Any]:
        from email_assistant import EmailAssistant
        ea = EmailAssistant()
        if "write" in query.lower() or "draft" in query.lower():
            return {"response": ea.compose_email("follow_up", "Recipient", ["Project update"], topic="Project Update"), "sources": []}
        return {"response": ea.improve_email(query), "sources": []}

    def _general_response(self, query: str) -> str:
        """Fallback general response."""
        return self.llm.chat(query, system_prompt="You are Luqi-AI, a helpful, knowledgeable assistant. Always provide well-structured, accurate responses with citations when possible.")

    @staticmethod
    def startup_banner() -> str:
        """Branded startup banner."""
        return """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ██╗     ██╗   ██╗  ██████╗ ██╗      █████╗ ██╗         ║
║   ██║     ██║   ██║ ██╔═══██╗██║     ██╔══██╗██║         ║
║   ██║     ██║   ██║ ██║   ██║██║     ███████║██║         ║
║   ██║     ██║   ██║ ██║▄▄ ██║██║     ██╔══██║██║         ║
║   ███████╗╚██████╔╝ ╚██████╔╝███████╗██║  ██║███████╗    ║
║   ╚══════╝ ╚═════╝   ╚══▀▀═╝ ╚══════╝╚═╝  ╚═╝╚══════╝    ║
║                                                          ║
║              Intelligence Without Limits                 ║
║                    Version 3.0                           ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def show_menu() -> str:
        """Display capability menu."""
        menu = """
┌─────────────────────────────────────────────────────────┐
│  CAPABILITY MENU                                        │
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
│  Commands: /menu  /train  /status  /quit                │
└─────────────────────────────────────────────────────────┘
"""
        return menu


if __name__ == "__main__":
    brain = OmegaBrain()
    print(OmegaBrain.startup_banner())
    print(OmegaBrain.show_menu())
    intent = brain.analyze_intent("How do I invest in Bitcoin mining in South Africa?")
    print(f"Intent: {intent['category']} (confidence: {intent['confidence']:.2f})")
