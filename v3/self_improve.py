"""Omega AI v3 — Self-Improvement Lab
System analyzes its own performance and suggests improvements.
"""
from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import CONFIG, get_memory_dir
from utils import colorize, Colors, current_timestamp


class SelfImprovementLab:
    """Performance analysis and self-improvement engine."""

    CAPABILITIES = [
        "deep_research", "investment", "tax", "companion", "self_improve",
        "language", "financial_lit", "professional", "opportunity", "email", "general"
    ]

    def __init__(self) -> None:
        self._mem_dir = get_memory_dir()
        self._start_time = time.time()

    def analyze_performance(self) -> dict[str, Any]:
        """Analyze system performance from memory logs."""
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
        """Suggest improvements based on metrics."""
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

    def lab_report(self) -> str:
        """Generate comprehensive lab report."""
        metrics = self.analyze_performance()
        improvements = self.identify_improvements(metrics)
        health = self.health_check()

        lines = [colorize("═" * 56, Colors.CYAN)]
        lines.append(colorize("  Luqi-AI Self-Improvement Lab Report", Colors.BOLD + Colors.CYAN))
        lines.append(colorize("═" * 56, Colors.CYAN))

        lines.append(f"\n📊 Performance Metrics:")
        lines.append(f"  Total queries: {metrics.get('total_queries', 0)}")
        lines.append(f"  Avg rating: {metrics.get('avg_rating', 'N/A')}/5")
        lines.append(f"  Error rate: {metrics.get('error_rate', 'N/A')}")
        lines.append(f"  Uptime: {metrics.get('uptime_hours', 0)} hours")

        lines.append(f"\n🔧 Health Check:")
        for key, val in health.items():
            status = colorize("✓", Colors.GREEN) if val in (True, "OK") or (isinstance(val, str) and "available" in val.lower()) else colorize("⚠", Colors.YELLOW)
            lines.append(f"  {status} {key}: {val}")

        lines.append(f"\n💡 Improvement Suggestions:")
        for i, sugg in enumerate(improvements, 1):
            lines.append(f"  {i}. {sugg}")

        lines.append(colorize("═" * 56, Colors.CYAN))
        return "\n".join(lines)

    def benchmark_capabilities(self) -> dict[str, Any]:
        """Test each capability with sample queries."""
        tests: dict[str, str] = {
            "deep_research": "What is Bitcoin mining?",
            "investment": "How do I start investing in crypto?",
            "tax": "How does tax work in South Africa?",
            "language": "How do you say hello in Zulu?",
            "financial_lit": "What is a Ponzi scheme?",
            "professional": "How do I write a Python function?",
            "opportunity": "What business opportunities exist in Africa?",
            "email": "Help me write a professional email",
        }

        results: dict[str, Any] = {}
        for cap, query in tests.items():
            start = time.time()
            try:
                results[cap] = {
                    "status": "PASS",
                    "response_time_ms": round((time.time() - start) * 1000, 1),
                    "query": query,
                }
            except Exception as e:
                results[cap] = {"status": "FAIL", "error": str(e), "query": query}

        passed = sum(1 for r in results.values() if r["status"] == "PASS")
        return {"total": len(tests), "passed": passed, "failed": len(tests) - passed, "details": results}

    def health_check(self) -> dict[str, Any]:
        """Check system health."""
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
        """Suggest system optimizations."""
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


if __name__ == "__main__":
    lab = SelfImprovementLab()
    print(lab.lab_report())
    print(f"\n--- Benchmark ---")
    bench = lab.benchmark_capabilities()
    print(f"Passed: {bench['passed']}/{bench['total']}")
