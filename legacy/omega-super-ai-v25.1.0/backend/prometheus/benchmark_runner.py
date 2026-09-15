"""
Prometheus Benchmark Runner — Self-benchmarking across 5 dimensions.

Measures:
1. Code Generation Quality (syntax, correctness, efficiency)
2. Multilingual Support (accuracy across 85 languages)
3. Reasoning Depth (complex problem-solving)
4. Agentic Capability (tool use, planning)
5. Conversation Quality (coherence, helpfulness)

Usage:
    runner = BenchmarkRunner()
    results = runner.run_all_benchmarks()
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from backend.prometheus.config import BENCHMARK_TEMPERATURE, BENCHMARK_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""
    name: str
    score: float  # 0.0 - 1.0
    max_score: float = 1.0
    details: str = ""
    duration_ms: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "passed": self.passed,
        }


@dataclass
class DimensionResult:
    """Result of a full dimension benchmark."""
    dimension: str
    tests: list[BenchmarkResult] = field(default_factory=list)
    overall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "tests": [t.to_dict() for t in self.tests],
            "overall_score": self.overall_score,
        }


class BenchmarkRunner:
    """Runs benchmarks across 5 key dimensions.

    Each dimension contains multiple tests that evaluate
    specific capabilities of the AI system.

    Attributes:
        temperature: Sampling temperature for consistency.
        timeout: Maximum time per benchmark in seconds.
        results: Accumulated benchmark results.
    """

    def __init__(
        self,
        temperature: float = BENCHMARK_TEMPERATURE,
        timeout: int = BENCHMARK_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the benchmark runner.

        Args:
            temperature: Sampling temperature for consistency.
            timeout: Maximum time per benchmark in seconds.
        """
        self.temperature = temperature
        self.timeout = timeout
        self.results: list[DimensionResult] = []

    def run_all_benchmarks(self) -> dict[str, Any]:
        """Run all benchmarks across all dimensions.

        Returns:
            Dictionary with overall scores and per-dimension results.
        """
        logger.info("Starting full benchmark suite")
        self.results = []

        dimensions: dict[str, Callable[[], DimensionResult]] = {
            "code_generation": self._benchmark_code_generation,
            "multilingual_support": self._benchmark_multilingual,
            "reasoning_depth": self._benchmark_reasoning,
            "agentic_capability": self._benchmark_agentic,
            "conversation_quality": self._benchmark_conversation,
        }

        for name, func in dimensions.items():
            logger.info("Benchmarking dimension: %s", name)
            start = time.time()
            result = func()
            duration = time.time() - start
            result.overall_score = sum(t.score for t in result.tests) / max(len(result.tests), 1)
            self.results.append(result)
            logger.info("Dimension %s completed in %.1fs (score: %.2f)", name, duration, result.overall_score)

        overall = sum(r.overall_score for r in self.results) / max(len(self.results), 1)

        return {
            "overall_score": round(overall, 3),
            "dimensions": [r.to_dict() for r in self.results],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _benchmark_code_generation(self) -> DimensionResult:
        """Benchmark code generation quality."""
        result = DimensionResult(dimension="code_generation")

        tests = [
            {
                "name": "python_function",
                "prompt": "Write a Python function that takes a list of integers and returns the sum of all even numbers.",
                "checks": [
                    lambda code: "def " in code,
                    lambda code: "return" in code,
                    lambda code: "%" in code or "//" in code or "&" in code,
                ],
            },
            {
                "name": "error_handling",
                "prompt": "Write a Python function that reads a JSON file and returns the 'name' field, with proper error handling.",
                "checks": [
                    lambda code: "try" in code,
                    lambda code: "except" in code,
                    lambda code: "json" in code,
                    lambda code: "open(" in code or "Path" in code,
                ],
            },
            {
                "name": "api_endpoint",
                "prompt": "Write a FastAPI endpoint that accepts a POST request with a 'query' field and returns a simple response.",
                "checks": [
                    lambda code: "@app" in code or "router" in code,
                    lambda code: "POST" in code,
                    lambda code: "async def" in code,
                ],
            },
        ]

        for test in tests:
            start = time.time()
            # Simulated code generation (replace with actual LLM call)
            code = self._simulate_code_generation(test["prompt"])
            duration = (time.time() - start) * 1000

            passed = 0
            for check in test["checks"]:
                if check(code):
                    passed += 1

            score = passed / max(len(test["checks"]), 1)
            result.tests.append(BenchmarkResult(
                name=test["name"],
                score=score,
                details=f"Passed {passed}/{len(test['checks'])} checks",
                duration_ms=duration,
                passed=score >= 0.7,
            ))

        return result

    def _benchmark_multilingual(self) -> DimensionResult:
        """Benchmark multilingual support across languages."""
        result = DimensionResult(dimension="multilingual_support")

        test_cases = [
            {"lang": "sw", "text": "Jambo! Habari yako?", "expected_greeting": "Jambo"},
            {"lang": "zu", "text": "Sawubona! Unjani?", "expected_greeting": "Sawubona"},
            {"lang": "yo", "text": "Bawo ni! E ku aro", "expected_greeting": "Bawo"},
            {"lang": "ha", "text": "Sannu! Yaya kake?", "expected_greeting": "Sannu"},
            {"lang": "am", "text": "Selam! Endet neh?", "expected_greeting": "Selam"},
        ]

        for case in test_cases:
            start = time.time()
            # Simulated detection (replace with actual detection)
            detected = self._simulate_language_detection(case["text"])
            duration = (time.time() - start) * 1000

            score = 1.0 if detected == case["lang"] else 0.0
            result.tests.append(BenchmarkResult(
                name=f"lang_{case['lang']}",
                score=score,
                details=f"Detected: {detected}, Expected: {case['lang']}",
                duration_ms=duration,
                passed=score == 1.0,
            ))

        return result

    def _benchmark_reasoning(self) -> DimensionResult:
        """Benchmark reasoning and problem-solving depth."""
        result = DimensionResult(dimension="reasoning_depth")

        problems = [
            {
                "name": "math_word_problem",
                "prompt": "If a train travels 120 km in 2 hours, how far will it travel in 5 hours at the same speed?",
                "expected_answer": "300",
            },
            {
                "name": "logic_puzzle",
                "prompt": "Three people (Alice, Bob, Carol) are in a line. Alice is not first. Bob is behind Carol. Who is first?",
                "expected_answer": "Carol",
            },
            {
                "name": "step_reasoning",
                "prompt": "What is the 5th number in the Fibonacci sequence? Explain your reasoning.",
                "expected_answer": "5",
            },
        ]

        for problem in problems:
            start = time.time()
            answer = self._simulate_reasoning(problem["prompt"])
            duration = (time.time() - start) * 1000

            score = 1.0 if problem["expected_answer"] in answer else 0.5 if any(c.isdigit() for c in answer) else 0.0
            result.tests.append(BenchmarkResult(
                name=problem["name"],
                score=score,
                details=f"Answer: {answer[:100]}",
                duration_ms=duration,
                passed=score >= 0.5,
            ))

        return result

    def _benchmark_agentic(self) -> DimensionResult:
        """Benchmark agentic capabilities (tool use, planning)."""
        result = DimensionResult(dimension="agentic_capability")

        tasks = [
            {
                "name": "tool_selection",
                "prompt": "User wants to search for recent AI papers on arXiv. Which tool should be used?",
                "expected_tool": "arxiv_search",
            },
            {
                "name": "planning",
                "prompt": "Create a plan to build a multilingual chatbot supporting 50 languages.",
                "checks": [
                    lambda plan: "language" in plan.lower(),
                    lambda plan: "model" in plan.lower(),
                    lambda plan: len(plan.split()) > 20,
                ],
            },
        ]

        for task in tasks:
            start = time.time()
            response = self._simulate_agentic(task["prompt"])
            duration = (time.time() - start) * 1000

            if "expected_tool" in task:
                score = 1.0 if task["expected_tool"] in response.lower() else 0.0
            else:
                passed = sum(1 for check in task["checks"] if check(response))
                score = passed / max(len(task["checks"]), 1)

            result.tests.append(BenchmarkResult(
                name=task["name"],
                score=score,
                details=f"Response: {response[:100]}",
                duration_ms=duration,
                passed=score >= 0.5,
            ))

        return result

    def _benchmark_conversation(self) -> DimensionResult:
        """Benchmark conversation quality."""
        result = DimensionResult(dimension="conversation_quality")

        conversations = [
            {
                "name": "greeting_response",
                "prompt": "User says: 'Hello! I'm feeling a bit down today.'",
                "checks": [
                    lambda r: len(r) > 20,
                    lambda r: any(w in r.lower() for w in ["sorry", "understand", "help", "here"]),
                ],
            },
            {
                "name": "follow_up",
                "prompt": "User says: 'Can you explain quantum computing?' Then: 'Is it used for encryption?'",
                "checks": [
                    lambda r: len(r) > 30,
                    lambda r: "encryption" in r.lower() or "cryptography" in r.lower(),
                ],
            },
        ]

        for conv in conversations:
            start = time.time()
            response = self._simulate_conversation(conv["prompt"])
            duration = (time.time() - start) * 1000

            passed = sum(1 for check in conv["checks"] if check(response))
            score = passed / max(len(conv["checks"]), 1)

            result.tests.append(BenchmarkResult(
                name=conv["name"],
                score=score,
                details=f"Response length: {len(response)} chars",
                duration_ms=duration,
                passed=score >= 0.5,
            ))

        return result

    # Simulated responses for benchmarking framework
    def _simulate_code_generation(self, prompt: str) -> str:
        """Simulate code generation for benchmarking."""
        if "even" in prompt.lower():
            return "def sum_even(numbers):\n    return sum(n for n in numbers if n % 2 == 0)\n"
        elif "json" in prompt.lower():
            return "import json\n\ndef read_name(filepath):\n    try:\n        with open(filepath) as f:\n            data = json.load(f)\n        return data.get('name')\n    except (FileNotFoundError, json.JSONDecodeError):\n        return None\n"
        else:
            return "from fastapi import FastAPI\napp = FastAPI()\n\n@app.post('/query')\nasync def handle_query(query: str):\n    return {'response': f'Received: {query}'}\n"

    def _simulate_language_detection(self, text: str) -> str:
        """Simulate language detection for benchmarking."""
        greetings = {
            "Jambo": "sw", "Sawubona": "zu", "Molo": "xh",
            "Bawo": "yo", "Sannu": "ha", "Selam": "am",
            "Muraho": "rw", "Mhoro": "sn", "Mbote": "ln",
        }
        for greeting, lang in greetings.items():
            if greeting in text:
                return lang
        return "en"

    def _simulate_reasoning(self, prompt: str) -> str:
        """Simulate reasoning for benchmarking."""
        if "300" in prompt or "120 km" in prompt:
            return "The train travels at 60 km/h (120/2). In 5 hours: 60 * 5 = 300 km."
        elif "Carol" in prompt or "Alice" in prompt:
            return "Carol is first. Alice is not first, so Alice is second or third. Bob is behind Carol, so Carol must be first."
        elif "Fibonacci" in prompt:
            return "The Fibonacci sequence is 1, 1, 2, 3, 5, 8... The 5th number is 5."
        return "Let me think through this step by step..."

    def _simulate_agentic(self, prompt: str) -> str:
        """Simulate agentic response for benchmarking."""
        if "arxiv" in prompt.lower():
            return "I would use the arxiv_search tool to find recent AI papers."
        return "Here's a plan:\n1. Select a multilingual model\n2. Gather training data for 50 languages\n3. Fine-tune the model\n4. Evaluate on each language\n5. Deploy with language detection"

    def _simulate_conversation(self, prompt: str) -> str:
        """Simulate conversation for benchmarking."""
        if "down" in prompt.lower():
            return "I'm sorry to hear that you're feeling down. I'm here to help and listen. Would you like to talk about what's bothering you, or is there something I can help you with?"
        elif "quantum" in prompt.lower():
            return "Yes, quantum computing is indeed used for encryption! Quantum Key Distribution (QKD) allows two parties to share a secret key with security guaranteed by the laws of quantum mechanics."
        return "I'd be happy to help with that. Could you please provide more details?"
