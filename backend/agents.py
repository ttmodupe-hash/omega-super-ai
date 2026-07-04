"""Multi-Agent Orchestration System

Coordinates multiple specialized AI agents to handle complex queries
through planning, research, analysis, and synthesis phases.

Classes:
    AgentOrchestrator: Main coordinator for multi-agent execution.

Typical usage:
    from backend.agents import AgentOrchestrator
    orch = AgentOrchestrator()
    result = orch.execute("Analyze Tesla stock and recent news")
    # Or with streaming:
    for update in orch.execute_stream("Research quantum computing"):
        print(update)
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

# ── Data Structures ────────────────────────────────────────────────────


@dataclass
class AgentStep:
    """A single step in an execution plan.

    Attributes:
        name: Human-readable step name.
        agent: Agent responsible (plan, research, analyze, synthesize).
        description: What this step does.
        status: Current status (pending, running, completed, error).
        result: Output from this step.
    """

    name: str
    agent: str
    description: str
    status: str = "pending"
    result: str = ""


@dataclass
class ExecutionPlan:
    """A plan for executing a complex query.

    Attributes:
        query: Original user query.
        mode: Detected operational mode.
        steps: Ordered list of execution steps.
        context: Shared context across steps.
    """

    query: str
    mode: str
    steps: List[AgentStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


# ── Individual Agents ──────────────────────────────────────────────────


class PlanAgent:
    """Breaks complex queries into actionable steps.

    Analyzes the user query, determines the best operational mode,
    and creates a structured execution plan.
    """

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(self, query: str) -> ExecutionPlan:
        """Create an execution plan for the given query.

        Args:
            query: User's natural language query.

        Returns:
            ExecutionPlan with detected mode and ordered steps.
        """
        logger.info("PlanAgent analyzing query")

        mode = self._detect_mode(query)

        plan = ExecutionPlan(query=query, mode=mode)

        # Always start with planning (already done)
        plan.steps.append(
            AgentStep(
                name="Analyze Query",
                agent="plan",
                description=f"Detected mode: {mode}",
                status="completed",
                result=f"Mode: {mode}",
            )
        )

        # Add steps based on mode
        if mode in ("research", "finance", "scam", "opps"):
            plan.steps.append(
                AgentStep(
                    name="Web Research",
                    agent="research",
                    description="Search for current information",
                )
            )

        plan.steps.append(
            AgentStep(
                name="Deep Analysis",
                agent="analyze",
                description="Analyze findings and think critically",
            )
        )

        plan.steps.append(
            AgentStep(
                name="Synthesize Response",
                agent="synthesize",
                description="Combine into coherent answer",
            )
        )

        return plan

    def _detect_mode(self, query: str) -> str:
        """Detect the best operational mode from query content.

        Uses a lightweight classification to avoid unnecessary API calls.
        Falls back to AI classification for ambiguous queries.

        Args:
            query: User query text.

        Returns:
            Mode string (research, think, mentor, expert, finance,
            scam, learn, opps, default).
        """
        q = query.lower()

        # Keyword-based detection
        if any(w in q for w in ["stock", "price", "market", "invest", "crypto"]):
            return "finance"
        if any(w in q for w in ["scam", "fraud", "fake", "phishing", "legit"]):
            return "scam"
        if any(w in q for w in ["learn", "tutorial", "how to", "course", "teach me"]):
            return "learn"
        if any(w in q for w in ["opportunity", "trend", "future", "prediction", "forecast"]):
            return "opps"
        if any(w in q for w in ["research", "news", "latest", "recent", "current"]):
            return "research"
        if any(w in q for w in ["think", "analyze", "why", "how does", "explain"]):
            return "think"
        if any(w in q for w in ["mentor", "help me understand", "guide"]):
            return "mentor"
        if any(w in q for w in ["expert", "technical", "advanced", "professional"]):
            return "expert"

        return "default"


class ResearchAgent:
    """Multi-step web research with synthesis.

    Performs targeted searches and compiles findings into
    a structured research report.
    """

    def __init__(self, ai_engine: AIEngine, search_engine: SearchEngine) -> None:
        self.ai = ai_engine
        self.search = search_engine

    def run(self, query: str, step: AgentStep) -> str:
        """Execute web research and compile findings.

        Args:
            query: Research query.
            step: Current execution step (updated in place).

        Returns:
            Markdown-formatted research findings.
        """
        step.status = "running"
        logger.info("ResearchAgent: %s", query[:60])

        try:
            # Generate search queries
            search_queries = self._generate_queries(query)

            all_results: List[Dict[str, str]] = []
            for sq in search_queries[:3]:  # Max 3 queries
                results = self.search.search(sq, max_results=5)
                all_results.extend(results)

            if not all_results:
                step.status = "completed"
                step.result = "*No web results found.*"
                return step.result

            # Deduplicate by link
            seen = set()
            unique = []
            for r in all_results:
                link = r.get("link", "")
                if link and link not in seen:
                    seen.add(link)
                    unique.append(r)

            # Compile into markdown
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
        """Generate targeted search queries from user query.

        Uses AI to break down complex queries into specific
        search queries for better coverage.

        Args:
            query: Original user query.

        Returns:
            List of search query strings.
        """
        prompt = (
            f"Break down this query into 2-3 specific web search queries "
            f"that will find the most relevant information. "
            f"Return ONLY a JSON array of strings, no other text.\n\n"
            f'Query: "{query}"'
        )
        try:
            raw = self.ai.chat_sync(
                [{"role": "user", "content": prompt}], mode="default"
            )
            # Extract JSON array
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            queries = json.loads(raw)
            if isinstance(queries, list) and queries:
                return [str(q) for q in queries]
        except Exception as exc:
            logger.debug("Query generation fallback: %s", exc)

        # Fallback: use original query
        return [query]


class AnalyzeAgent:
    """Deep analysis and critical thinking agent.

    Takes research findings (or raw query) and produces
    thorough analysis with reasoning.
    """

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(self, query: str, context: str, step: AgentStep) -> str:
        """Execute deep analysis on the given context.

        Args:
            query: Original user query.
            context: Research findings or prior context.
            step: Current execution step (updated in place).

        Returns:
            Analysis text with reasoning.
        """
        step.status = "running"
        logger.info("AnalyzeAgent running")

        try:
            prompt = (
                f"Analyze the following information in response to this query:\n\n"
                f"Query: {query}\n\n"
                f"Context:\n{context[:8000]}\n\n"
                f"Provide a thorough analysis that:\n"
                f"1. Identifies key points and patterns\n"
                f"2. Evaluates strengths and weaknesses\n"
                f"3. Considers multiple perspectives\n"
                f"4. Highlights any uncertainties or gaps\n"
                f"5. Draws well-reasoned conclusions\n\n"
                f"Be objective, thorough, and show your reasoning."
            )

            analysis = self.ai.chat_sync(
                [{"role": "user", "content": prompt}],
                mode="think",
            )

            step.status = "completed"
            step.result = analysis
            return analysis

        except Exception as exc:
            step.status = "error"
            step.result = f"Analysis error: {exc}"
            logger.error("Analysis error: %s", exc)
            return step.result


class SynthesizeAgent:
    """Combines all findings into a coherent final response.

    Takes the analysis and produces a polished, well-structured
    answer appropriate for the operational mode.
    """

    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai = ai_engine

    def run(
        self, query: str, analysis: str, mode: str, step: AgentStep
    ) -> str:
        """Synthesize final response from analysis.

        Args:
            query: Original user query.
            analysis: Analysis text from prior steps.
            mode: Operational mode for response style.
            step: Current execution step (updated in place).

        Returns:
            Polished final response.
        """
        step.status = "running"
        logger.info("SynthesizeAgent running")

        try:
            prompt = (
                f"Based on the following analysis, provide a clear, "
                f"well-structured response to the user's query.\n\n"
                f"Query: {query}\n\n"
                f"Analysis:\n{analysis[:6000]}\n\n"
                f"Guidelines:\n"
                f"- Use markdown formatting\n"
                f"- Include sections with headers\n"
                f"- Be direct and actionable\n"
                f"- Cite sources where applicable\n"
                f"- Add a brief summary at the end\n\n"
                f"Respond in the style of a {mode} specialist."
            )

            response = self.ai.chat_sync(
                [{"role": "user", "content": prompt}],
                mode=mode,
            )

            step.status = "completed"
            step.result = response
            return response

        except Exception as exc:
            step.status = "error"
            step.result = f"Synthesis error: {exc}"
            logger.error("Synthesis error: %s", exc)
            return step.result


# ── Orchestrator ───────────────────────────────────────────────────────


class AgentOrchestrator:
    """Coordinates multi-agent execution for complex queries.

    Manages the full pipeline: planning → research → analysis → synthesis.
    Supports both synchronous and streaming execution modes.

    Attributes:
        config: Backend configuration dictionary.
        ai_engine: Shared AIEngine instance.
        search_engine: Shared SearchEngine instance.
        plan_agent: PlanAgent instance.
        research_agent: ResearchAgent instance.
        analyze_agent: AnalyzeAgent instance.
        synthesize_agent: SynthesizeAgent instance.

    Example:
        >>> orch = AgentOrchestrator()
        >>> result = orch.execute("Research AI safety developments")
        >>> print(result["response"])
    """

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        """Initialize the orchestrator with all agents.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.ai_engine = AIEngine(self.config)
        self.search_engine = SearchEngine(self.config)

        self.plan_agent = PlanAgent(self.ai_engine)
        self.research_agent = ResearchAgent(self.ai_engine, self.search_engine)
        self.analyze_agent = AnalyzeAgent(self.ai_engine)
        self.synthesize_agent = SynthesizeAgent(self.ai_engine)

        logger.info("AgentOrchestrator initialized with 4 agents")

    # ── Public API ──────────────────────────────────────────────────────

    def execute(
        self, query: str, mode: str = "auto"
    ) -> Dict[str, object]:
        """Execute the full multi-agent pipeline.

        Args:
            query: User's natural language query.
            mode: Operational mode or "auto" for automatic detection.

        Returns:
            Dictionary with keys:
            - response: Final synthesized response text
            - plan: ExecutionPlan with all step results
            - mode: Detected/used operational mode
            - steps_completed: Number of completed steps
            - steps_total: Total number of steps
        """
        logger.info("Executing query: %s (mode=%s)", query[:60], mode)

        # Step 1: Plan
        plan = self.plan_agent.run(query)
        if mode != "auto":
            plan.mode = mode

        # Execute steps
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
                result = self.synthesize_agent.run(
                    query, analysis, plan.mode, step
                )
                plan.context["response"] = result

        completed = sum(1 for s in plan.steps if s.status == "completed")

        return {
            "response": plan.context.get("response", ""),
            "plan": plan,
            "mode": plan.mode,
            "steps_completed": completed,
            "steps_total": len(plan.steps),
        }

    def execute_stream(
        self, query: str, mode: str = "auto"
    ) -> Generator[str, None, None]:
        """Execute with streaming updates for each step.

        Yields JSON-serializable status updates showing progress
        through the agent pipeline.

        Args:
            query: User's natural language query.
            mode: Operational mode or "auto" for automatic detection.

        Yields:
            JSON strings with step updates:
            {"step": "name", "status": "running|completed", "output": "..."}
        """
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
                result = self.synthesize_agent.run(
                    query, analysis, plan.mode, step
                )
                plan.context["response"] = result
                yield self._status("synthesize", "completed", result)

        # Final response
        yield self._status(
            "final",
            "completed",
            plan.context.get("response", ""),
        )

    async def execute_stream_async(
        self, query: str, mode: str = "auto"
    ) -> AsyncGenerator[str, None]:
        """Async streaming execution of the agent pipeline.

        Args:
            query: User's natural language query.
            mode: Operational mode or "auto".

        Yields:
            JSON status update strings.
        """
        # Use sync agents but yield async
        for update in self.execute_stream(query, mode):
            yield update

    # ── Private ─────────────────────────────────────────────────────────

    @staticmethod
    def _status(step: str, status: str, output: str) -> str:
        """Create a JSON status string."""
        return json.dumps(
            {"step": step, "status": status, "output": output},
            ensure_ascii=False,
        )
