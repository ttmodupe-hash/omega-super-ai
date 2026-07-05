"""Multi-Agent Orchestration System

Coordinates multiple specialized AI agents to handle complex queries
through planning, research, analysis, and synthesis phases.
"""

import json
import logging
from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.ai_engine import AIEngine
from backend.config import load_backend_config
from backend.search import SearchEngine

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """A single step in an execution plan."""
    name: str
    agent: str
    description: str
    status: str = "pending"
    result: str = ""


@dataclass
class ExecutionPlan:
    """A plan for executing a complex query."""
    query: str
    mode: str
    steps: List[AgentStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class PlanAgent:
    """Breaks complex queries into actionable steps."""

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(self, query: str) -> ExecutionPlan:
        """Create an execution plan for the given query."""
        logger.info("PlanAgent analyzing query")
        mode = self._detect_mode(query)
        plan = ExecutionPlan(query=query, mode=mode)
        plan.steps.append(AgentStep(name="Analyze Query", agent="plan", description=f"Detected mode: {mode}", status="completed", result=f"Mode: {mode}"))

        if mode in ("research", "finance", "scam", "opps"):
            plan.steps.append(AgentStep(name="Web Research", agent="research", description="Search for current information"))
        plan.steps.append(AgentStep(name="Deep Analysis", agent="analyze", description="Analyze findings and think critically"))
        plan.steps.append(AgentStep(name="Synthesize Response", agent="synthesize", description="Combine into coherent answer"))
        return plan

    def _detect_mode(self, query: str) -> str:
        """Detect the best operational mode from query content."""
        q = query.lower()
        if any(w in q for w in ["stock", "price", "market", "invest", "crypto"]): return "finance"
        if any(w in q for w in ["scam", "fraud", "fake", "phishing", "legit"]): return "scam"
        if any(w in q for w in ["learn", "tutorial", "how to", "course", "teach me"]): return "learn"
        if any(w in q for w in ["opportunity", "trend", "future", "prediction", "forecast"]): return "opps"
        if any(w in q for w in ["research", "news", "latest", "recent", "current"]): return "research"
        if any(w in q for w in ["think", "analyze", "why", "how does", "explain"]): return "think"
        if any(w in q for w in ["mentor", "help me understand", "guide"]): return "mentor"
        if any(w in q for w in ["expert", "technical", "advanced", "professional"]): return "expert"
        return "default"


class ResearchAgent:
    """Multi-step web research with synthesis."""

    def __init__(self, ai_engine: AIEngine, search_engine: SearchEngine) -> None:
        self.ai = ai_engine
        self.search = search_engine

    def run(self, query: str, step: AgentStep) -> str:
        """Execute web research and compile findings."""
        step.status = "running"
        logger.info("ResearchAgent: %s", query[:60])
        try:
            search_queries = self._generate_queries(query)
            all_results: List[Dict[str, str]] = []
            for sq in search_queries[:3]:
                results = self.search.search(sq, max_results=5)
                all_results.extend(results)
            if not all_results:
                step.status = "completed"
                step.result = "*No web results found.*"
                return step.result
            seen = set()
            unique = []
            for r in all_results:
                link = r.get("link", "")
                if link and link not in seen:
                    seen.add(link)
                    unique.append(r)
            md = self.search.to_markdown(unique[:10])
            step.status = "completed"
            step.result = md
            return md
        except Exception as exc:
            step.status = "error"
            step.result = f"Research error: {exc}"
            logger.error("Research error: %s", exc)
            return step.result

    def _generate_queries(self, query: str) -> List[str]:
        """Generate targeted search queries from user query."""
        prompt = f"Break down this query into 2-3 specific web search queries. Return ONLY a JSON array of strings.\n\nQuery: \"{query}\""
        try:
            raw = self.ai.chat_sync([{"role": "user", "content": prompt}], mode="default")
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            queries = json.loads(raw)
            if isinstance(queries, list) and queries:
                return [str(q) for q in queries]
        except Exception as exc:
            logger.debug("Query generation fallback: %s", exc)
        return [query]


class AnalyzeAgent:
    """Deep analysis and critical thinking agent."""

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(self, query: str, context: str, step: AgentStep) -> str:
        """Execute deep analysis on the given context."""
        step.status = "running"
        logger.info("AnalyzeAgent running")
        try:
            prompt = f"Analyze the following in response to this query:\n\nQuery: {query}\n\nContext:\n{context[:8000]}\n\nProvide a thorough analysis identifying key points, patterns, strengths, weaknesses, multiple perspectives, and well-reasoned conclusions."
            analysis = self.ai.chat_sync([{"role": "user", "content": prompt}], mode="think")
            step.status = "completed"
            step.result = analysis
            return analysis
        except Exception as exc:
            step.status = "error"
            step.result = f"Analysis error: {exc}"
            logger.error("Analysis error: %s", exc)
            return step.result


class SynthesizeAgent:
    """Combines all findings into a coherent final response."""

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(self, query: str, analysis: str, mode: str, step: AgentStep) -> str:
        """Synthesize final response from analysis."""
        step.status = "running"
        logger.info("SynthesizeAgent running")
        try:
            prompt = f"Based on the following analysis, provide a clear, well-structured response.\n\nQuery: {query}\n\nAnalysis:\n{analysis[:6000]}\n\nUse markdown formatting, sections with headers, be direct and actionable, cite sources where applicable, and add a brief summary. Respond as a {mode} specialist."
            response = self.ai.chat_sync([{"role": "user", "content": prompt}], mode=mode)
            step.status = "completed"
            step.result = response
            return response
        except Exception as exc:
            step.status = "error"
            step.result = f"Synthesis error: {exc}"
            logger.error("Synthesis error: %s", exc)
            return step.result


class AgentOrchestrator:
    """Coordinates multi-agent execution for complex queries."""

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        self.config = config or load_backend_config()
        self.ai_engine = AIEngine(self.config)
        self.search_engine = SearchEngine(self.config)
        self.plan_agent = PlanAgent(self.ai_engine)
        self.research_agent = ResearchAgent(self.ai_engine, self.search_engine)
        self.analyze_agent = AnalyzeAgent(self.ai_engine)
        self.synthesize_agent = SynthesizeAgent(self.ai_engine)
        logger.info("AgentOrchestrator initialized with 4 agents")

    def execute(self, query: str, mode: str = "auto") -> Dict[str, object]:
        """Execute the full multi-agent pipeline."""
        logger.info("Executing query: %s (mode=%s)", query[:60], mode)
        plan = self.plan_agent.run(query)
        if mode != "auto":
            plan.mode = mode
        context_parts: List[str] = []
        for step in plan.steps:
            if step.agent == "research":
                result = self.research_agent.run(query, step)
                context_parts.append(f"Research findings:\n{result}")
                plan.context["research"] = result
            elif step.agent == "analyze":
                context = "\n\n".join(context_parts)
                result = self.analyze_agent.run(query, context, step)
                context_parts.append(f"Analysis:\n{result}")
                plan.context["analysis"] = result
            elif step.agent == "synthesize":
                analysis = plan.context.get("analysis", "")
                result = self.synthesize_agent.run(query, analysis, plan.mode, step)
                plan.context["response"] = result
        completed = sum(1 for s in plan.steps if s.status == "completed")
        return {"response": plan.context.get("response", ""), "plan": plan, "mode": plan.mode, "steps_completed": completed, "steps_total": len(plan.steps)}

    def execute_stream(self, query: str, mode: str = "auto") -> Generator[str, None, None]:
        """Execute with streaming updates for each step."""
        plan = self.plan_agent.run(query)
        if mode != "auto":
            plan.mode = mode
        yield self._status("plan", "completed", f"Mode: {plan.mode}")
        context_parts: List[str] = []
        for step in plan.steps:
            if step.agent == "research":
                yield self._status("research", "running", "Searching...")
                result = self.research_agent.run(query, step)
                context_parts.append(f"Research findings:\n{result}")
                plan.context["research"] = result
                yield self._status("research", "completed", result)
            elif step.agent == "analyze":
                yield self._status("analyze", "running", "Analyzing...")
                context = "\n\n".join(context_parts)
                result = self.analyze_agent.run(query, context, step)
                context_parts.append(f"Analysis:\n{result}")
                plan.context["analysis"] = result
                yield self._status("analyze", "completed", result)
            elif step.agent == "synthesize":
                yield self._status("synthesize", "running", "Synthesizing...")
                analysis = plan.context.get("analysis", "")
                result = self.synthesize_agent.run(query, analysis, plan.mode, step)
                plan.context["response"] = result
                yield self._status("synthesize", "completed", result)
        yield self._status("final", "completed", plan.context.get("response", ""))

    @staticmethod
    def _status(step: str, status: str, output: str) -> str:
        return json.dumps({"step": step, "status": status, "output": output}, ensure_ascii=False)
