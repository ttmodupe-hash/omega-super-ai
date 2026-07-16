"""Omega AI v3 — Capability Pipeline Runner
Chain multiple capabilities together with shared context.
"""
from __future__ import annotations

from typing import Any, Dict


class PipelineRunner:
    """Run capability pipelines with shared context."""

    _PRESETS: Dict[str, list[str]] = {
        "mining_setup": ["research:mining_hardware", "invest:mining_profitability", "tax:mining"],
        "startup_guide": ["opportunity:country", "research:market", "email:pitch"],
        "investment_due_diligence": ["research:asset", "scam:check", "invest:analyze"],
        "daily_digest": ["price:portfolio", "opportunity:trends", "learn:next"],
        "tax_report": ["tax:estimate", "calc:currency", "export:json"],
    }

    def __init__(self) -> None:
        self.context: Dict[str, Any] = {}

    def list_presets(self) -> list[str]:
        return list(self._PRESETS.keys())

    def parse_pipeline(self, command: str) -> list[dict]:
        """Parse pipe syntax like '/research X | /email Y | /lang Z'."""
        steps = []
        for segment in command.split("|"):
            segment = segment.strip()
            if segment.startswith("/"):
                parts = segment[1:].split(None, 1)
                steps.append({"command": parts[0], "args": parts[1] if len(parts) > 1 else ""})
        return steps

    def run_preset(self, preset_name: str, **kwargs: Any) -> list[dict]:
        """Run a predefined pipeline."""
        if preset_name not in self._PRESETS:
            return [{"error": f"Unknown preset: {preset_name}. Available: {', '.join(self._PRESETS.keys())}"}]
        results = []
        for step_def in self._PRESETS[preset_name]:
            module, action = step_def.split(":", 1)
            try:
                result = self._run_step(module, action, kwargs)
                self.context[module] = result
                results.append({"step": step_def, "status": "ok", "result": result})
            except Exception as e:
                results.append({"step": step_def, "status": "error", "error": str(e)})
        return results

    def _run_step(self, module: str, action: str, params: dict) -> str:
        """Execute a single pipeline step."""
        if module == "research":
            from deep_research import DeepResearch
            dr = DeepResearch()
            return dr.research(action, depth="quick").get("summary", "Research complete.")
        elif module == "invest":
            from investment_mining import InvestmentMining
            im = InvestmentMining()
            return im.investment_analysis(action).get("outlook", "Analysis complete.")
        elif module == "tax":
            from tax_engine import TaxEngine
            te = TaxEngine()
            return te.tax_query("south africa", action)
        elif module == "opportunity":
            from opportunity_engine import OpportunityEngine
            oe = OpportunityEngine()
            ops = oe.african_opportunities(params.get("country", action))
            return f"Found {len(ops)} opportunities."
        elif module == "scam":
            from financial_literacy import FinancialLiteracy
            fl = FinancialLiteracy()
            r = fl.scam_check(params.get("description", action))
            return f"Scam risk: {r['risk_score']}/100 — {r['risk_level']}"
        elif module == "email":
            from email_assistant import EmailAssistant
            ea = EmailAssistant()
            return ea.improve_email(params.get("draft", action))
        elif module == "learn":
            from learning_tracker import LearningTracker
            lt = LearningTracker()
            nl = lt.get_next_lesson()
            return f"Next: {nl['topic']} ({nl['level']})" if nl else "All lessons complete!"
        elif module == "price":
            from price_ticker import PriceTicker
            pt = PriceTicker()
            p = pt.get_price("btc")
            return f"BTC: ${p.get('price_usd', 0):,.2f}"
        elif module == "calc":
            from calc_engine import CalcEngine
            ce = CalcEngine()
            return ce.handle_command(["50000", "ZAR", "to", "USD"])
        elif module == "export":
            return "Export functionality available via /save command."
        else:
            return f"[Pipeline] Module '{module}' not yet implemented in pipelines."

    def format_results(self, results: list[dict]) -> str:
        """Pretty-print pipeline results."""
        lines = ["Pipeline Results:", "═" * 50]
        for i, r in enumerate(results, 1):
            status_icon = "✅" if r.get("status") == "ok" else "❌" if r.get("status") == "error" else "⏳"
            lines.append(f"\n  Step {i}: {r.get('step', 'unknown')} {status_icon}")
            if "result" in r:
                result_str = str(r["result"])[:200]
                lines.append(f"    → {result_str}")
            if "error" in r:
                lines.append(f"    ⚠ {r['error']}")
        return "\n".join(lines)