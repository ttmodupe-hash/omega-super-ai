"""Omega AI v3.1 — Self-Improvement Lab
System analyzes its own performance and suggests improvements.
Includes real capability benchmarking.
"""
from __future__ import annotations

import json
import os
import platform
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import CONFIG, get_memory_dir
from utils import colorize, Colors


class SelfImprovementLab:
    """Performance analysis and self-improvement engine."""

    CAPABILITIES = [
        "deep_research", "investment", "tax", "companion", "self_improve",
        "language", "financial_lit", "professional", "opportunity", "email", "general"
    ]

    def __init__(self) -> None:
        self._mem_dir = get_memory_dir()
        self._start_time = time.time()
        self._last_benchmark: dict[str, Any] | None = None

    def analyze_performance(self) -> dict[str, Any]:
        mem_file = self._mem_dir / "memory.json"
        if not mem_file.exists():
            return {"total_queries": 0, "note": "No data yet"}
        try:
            data = json.loads(mem_file.read_text())
        except Exception:
            return {"total_queries": 0, "note": "Error reading memory"}
        if not data:
            return {"total_queries": 0, "note": "No interactions recorded"}

        ratings = [d.get("rating", 0) for d in data if d.get("rating", 0) > 0]
        modules: dict[str, int] = {}
        errors = 0
        for d in data:
            mod = d.get("module", "unknown")
            modules[mod] = modules.get(mod, 0) + 1
            if "error" in d.get("response_preview", "").lower():
                errors += 1

        return {
            "total_queries": len(data),
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "total_ratings": len(ratings),
            "module_distribution": modules,
            "error_count": errors,
            "error_rate": f"{errors / len(data) * 100:.1f}%" if data else "0%",
            "period": f"{data[0].get('timestamp', 'N/A')[:10]} to {data[-1].get('timestamp', 'N/A')[:10]}",
            "uptime_hours": round((time.time() - self._start_time) / 3600, 2),
        }

    def identify_improvements(self, metrics: dict[str, Any]) -> list[str]:
        suggestions = []
        if metrics.get("avg_rating", 5) < 3.5:
            suggestions.append("Average rating is low. Review recent feedback for quality issues.")
        if metrics.get("error_rate", "0%").rstrip("%") and float(metrics.get("error_rate", "0%").rstrip("%")) > 10:
            suggestions.append("Error rate is elevated. Check API connectivity and error handling.")
        if metrics.get("total_ratings", 0) == 0:
            suggestions.append("No user ratings yet. Prompt users for feedback.")
        modules = metrics.get("module_distribution", {})
        for cap in self.CAPABILITIES:
            if cap not in modules:
                suggestions.append(f"Capability '{cap}' has zero usage. May need better routing.")
        if not suggestions:
            suggestions.append("All metrics look healthy. Continue monitoring.")
        return suggestions

    def benchmark_capabilities(self) -> dict[str, Any]:
        """Test each capability with sample queries and measure performance."""
        tests: dict[str, dict] = {
            "deep_research": {
                "setup": "from deep_research import DeepResearch",
                "call": lambda cls: cls().research("What is Bitcoin?", depth="quick"),
                "check": lambda r: isinstance(r, dict) and ("cited_response" in r or "summary" in r),
            },
            "investment": {
                "setup": "from investment_mining import InvestmentMining",
                "call": lambda cls: cls().mining_profitability(100, 0.10, 3000),
                "check": lambda r: isinstance(r, dict) and "daily" in r and "profit_usd" in r.get("daily", {}),
            },
            "tax": {
                "setup": "from tax_engine import TaxEngine",
                "call": lambda cls: cls().calculate_estimate("south africa", 500000),
                "check": lambda r: isinstance(r, dict) and ("estimated_tax" in r or "taxable_income" in r),
            },
            "language": {
                "setup": "from african_languages import AfricanLanguages",
                "call": lambda cls: cls().translate("hello", "zulu"),
                "check": lambda r: isinstance(r, str) and len(r) > 0,
            },
            "financial_lit": {
                "setup": "from financial_literacy import FinancialLiteracy",
                "call": lambda cls: cls().scam_check("guaranteed 500% returns"),
                "check": lambda r: isinstance(r, dict) and "risk_score" in r,
            },
            "professional": {
                "setup": "from professional_assist import ProfessionalAssist",
                "call": lambda cls: cls().code_assist("python", "hello world"),
                "check": lambda r: isinstance(r, str) and len(r) > 0,
            },
            "opportunity": {
                "setup": "from opportunity_engine import OpportunityEngine",
                "call": lambda cls: cls().african_opportunities("nigeria"),
                "check": lambda r: isinstance(r, list) and len(r) > 0,
            },
            "email": {
                "setup": "from email_assistant import EmailAssistant",
                "call": lambda cls: cls().improve_email("Hey, gonna be late. sry."),
                "check": lambda r: isinstance(r, str) and len(r) > 0,
            },
        }

        module_map: dict[str, tuple[str, str]] = {
            "deep_research": ("DeepResearch", "deep_research"),
            "investment": ("InvestmentMining", "investment_mining"),
            "tax": ("TaxEngine", "tax_engine"),
            "language": ("AfricanLanguages", "african_languages"),
            "financial_lit": ("FinancialLiteracy", "financial_literacy"),
            "professional": ("ProfessionalAssist", "professional_assist"),
            "opportunity": ("OpportunityEngine", "opportunity_engine"),
            "email": ("EmailAssistant", "email_assistant"),
        }

        details: dict[str, dict[str, Any]] = {}
        passed_count = 0
        failed_count = 0
        total_time = 0.0

        for cap_name, test_cfg in tests.items():
            cap_start = time.time()
            status = "FAIL"
            error_msg = None
            result_preview = "N/A"
            result = None

            try:
                class_name, module_name = module_map[cap_name]
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                result = test_cfg["call"](cls)
                if test_cfg["check"](result):
                    status = "PASS"
                    passed_count += 1
                else:
                    status = "FAIL"
                    error_msg = "Result failed validation check"
                    failed_count += 1
                if isinstance(result, str):
                    result_preview = result[:100]
                elif isinstance(result, (dict, list)):
                    result_preview = json.dumps(result)[:100]
                else:
                    result_preview = str(result)[:100]
            except ImportError as exc:
                error_msg = f"Import error: {exc}"
                failed_count += 1
            except AttributeError as exc:
                error_msg = f"Missing method: {exc}"
                failed_count += 1
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {str(exc)}"
                failed_count += 1

            elapsed_ms = round((time.time() - cap_start) * 1000, 1)
            total_time += elapsed_ms

            details[cap_name] = {
                "status": status,
                "response_time_ms": elapsed_ms,
                "error": error_msg,
                "result_preview": result_preview,
            }

        results = {
            "total": len(tests),
            "passed": passed_count,
            "failed": failed_count,
            "total_time_ms": round(total_time, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        self._last_benchmark = results
        return results

    def lab_report(self) -> str:
        metrics = self.analyze_performance()
        improvements = self.identify_improvements(metrics)
        health = self.health_check()

        lines = [colorize("=" * 56, Colors.CYAN)]
        lines.append(colorize("  Luqi-AI Self-Improvement Lab Report", Colors.BOLD + Colors.CYAN))
        lines.append(colorize("=" * 56, Colors.CYAN))

        lines.append(f"\n  Performance Metrics:")
        lines.append(f"  Total queries: {metrics.get('total_queries', 0)}")
        lines.append(f"  Avg rating: {metrics.get('avg_rating', 'N/A')}/5")
        lines.append(f"  Error rate: {metrics.get('error_rate', 'N/A')}")
        lines.append(f"  Uptime: {metrics.get('uptime_hours', 0)} hours")

        lines.append(f"\n  Health Check:")
        for key, val in health.items():
            status = colorize("OK", Colors.GREEN) if val in (True, "OK") or (isinstance(val, str) and "available" in val.lower()) else colorize("!", Colors.YELLOW)
            lines.append(f"  {status} {key}: {val}")

        if self._last_benchmark is not None:
            bench = self._last_benchmark
            lines.append(f"\n  Capability Benchmark (latest):")
            lines.append(f"  Passed: {bench['passed']}/{bench['total']}  Failed: {bench['failed']}  Total time: {bench['total_time_ms']} ms")
            for cap_name, cap_detail in bench.get("details", {}).items():
                icon = colorize("PASS", Colors.GREEN) if cap_detail["status"] == "PASS" else colorize("FAIL", Colors.RED)
                info = f"  {icon} {cap_name}: {cap_detail['response_time_ms']} ms"
                if cap_detail["error"]:
                    info += f"  [{cap_detail['error'][:60]}]"
                lines.append(info)

        lines.append(f"\n  Improvement Suggestions:")
        for i, sugg in enumerate(improvements, 1):
            lines.append(f"  {i}. {sugg}")

        lines.append(colorize("=" * 56, Colors.CYAN))
        return "\n".join(lines)

    def health_check(self) -> dict[str, Any]:
        health: dict[str, Any] = {
            "memory_dir": "OK" if self._mem_dir.exists() else "MISSING",
            "api_key_serper": "Available" if CONFIG.get("SERPER_API_KEY") else "Not set",
            "api_key_openai": "Available" if CONFIG.get("OPENAI_API_KEY") else "Not set",
            "ollama_host": str(CONFIG.get("OLLAMA_HOST", "Not set")),
            "platform": platform.system(),
            "python_version": platform.python_version(),
        }
        try:
            stat = os.statvfs(self._mem_dir)
            free_gb = stat.f_bavail * stat.f_frsize / (1024**3)
            health["disk_free_gb"] = f"{free_gb:.1f} GB"
        except Exception:
            health["disk_free_gb"] = "Unknown"
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS"):
                        rss_kb = int(line.split()[1])
                        health["memory_usage_mb"] = f"{rss_kb / 1024:.1f} MB"
                        break
        except Exception:
            health["memory_usage_mb"] = "Unknown"
        return health

    def suggest_optimizations(self) -> list[str]:
        return [
            "Use Ollama for local LLM to reduce API costs and latency",
            "Enable response caching for frequently asked questions",
            "Batch web search requests where possible",
            "Pre-load common lesson content for faster responses",
            "Implement async processing for independent modules",
            "Add response streaming for better user experience",
            "Consider SQLite instead of JSON for large datasets",
            "Add request retry with exponential backoff",
        ]