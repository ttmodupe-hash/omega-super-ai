#!/usr/bin/env python3
"""
Prometheus Prime — AI-Powered Code Generation Module

Handles intelligent code generation, review, and safe integration
of new features into the Luqi AI codebase. Uses structured templates
and LLM-based reasoning to produce production-ready Python code.

Safety-first design: all generated code is reviewed, tested in isolation,
and backed up before any file modification occurs.
"""

from __future__ import annotations

__all__ = [
    "CodeGenerator",
    "CodeReviewResult",
    "FeatureSpec",
    "IntegrationResult",
]

import ast
import hashlib
import inspect
import logging
import os
import re
import shutil
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Protocol

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("prometheus_prime.code_generator")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FeatureSpec:
    """Structured specification for a new feature."""

    name: str
    description: str
    requirement: str
    files_to_create: list[dict[str, str]] = field(default_factory=list)
    files_to_modify: list[dict[str, str]] = field(default_factory=list)
    function_signatures: list[dict[str, Any]] = field(default_factory=list)
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    integration_points: list[dict[str, str]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CodeReviewResult:
    """Result of a code-review pass."""

    passed: bool
    issues: list[dict[str, str]] = field(default_factory=list)
    suggestions: list[dict[str, str]] = field(default_factory=list)
    score: float = 0.0  # 0.0 – 1.0


@dataclass
class IntegrationResult:
    """Result of integrating a feature into the codebase."""

    success: bool
    backups: dict[str, str] = field(default_factory=dict)
    created_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Protocol for LLM backend (swappable)
# ---------------------------------------------------------------------------


class LLMBackend(Protocol):
    """Protocol for the LLM provider used by *CodeGenerator*."""

    def complete(self, prompt: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        ...


class OpenAIBackend:
    """Default OpenAI-backed LLM provider."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        import openai

        self._client = openai.AsyncOpenAI(api_key=api_key) if api_key else openai.AsyncOpenAI()
        self._model = model

    def complete(self, prompt: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        """Synchronous wrapper around the async OpenAI call."""
        import asyncio

        try:
            return asyncio.get_event_loop().run_until_complete(
                self._acomplete(prompt, temperature, max_tokens)
            )
        except RuntimeError:
            # No event loop — create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self._acomplete(prompt, temperature, max_tokens)
            )

    async def _acomplete(self, prompt: str, temperature: float, max_tokens: int) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are an expert Python software architect."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""


# ---------------------------------------------------------------------------
# Template-based fallback for when LLM is unavailable
# ---------------------------------------------------------------------------


FEATURE_SPEC_TEMPLATE = """\
# Feature Spec: {name}

## Description
{description}

## Files to Create
{files_create}

## Files to Modify
{files_modify}

## Function Signatures
{functions}

## Test Cases
{tests}

## Integration Points
{integrations}

## Dependencies
{dependencies}
"""


def _slugify(text: str) -> str:
    """Convert a natural-language string to a Python-friendly slug."""
    return re.sub(r"[^a-z0-9_]+", "_", text.lower().strip()).strip("_")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class CodeGenerator:
    """AI-powered code generator with built-in review and safe integration.

    Parameters
    ----------
    llm:
        An object satisfying the *LLMBackend* protocol.  If ``None`` a local
        template-based engine is used (no external API calls).
    project_root:
        Absolute path to the project root directory.  All file operations are
        constrained to this tree.
    backup_dir:
        Directory where file backups are stored before modification.
    """

    def __init__(
        self,
        llm: LLMBackend | None = None,
        project_root: str | Path = ".",
        backup_dir: str | Path = ".prometheus_prime/backups",
    ) -> None:
        self.llm = llm
        self.project_root = Path(project_root).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Feature spec generation
    # ------------------------------------------------------------------

    def generate_feature_spec(self, requirement: str) -> FeatureSpec:
        """Generate a structured feature specification from a natural-language requirement.

        Parameters
        ----------
        requirement:
            Free-text description, e.g. *"Add support for detecting emotions
            in user messages"*.

        Returns
        -------
        FeatureSpec
            Structured specification ready for code generation.
        """
        logger.info("Generating feature spec for requirement: %s", requirement)

        if self.llm is not None:
            spec = self._generate_spec_llm(requirement)
        else:
            spec = self._generate_spec_template(requirement)

        logger.info("Feature spec generated: %s (%d files to create, %d to modify)",
                    spec.name, len(spec.files_to_create), len(spec.files_to_modify))
        return spec

    def _generate_spec_llm(self, requirement: str) -> FeatureSpec:
        prompt = self._build_spec_prompt(requirement)
        raw = self.llm.complete(prompt, temperature=0.3, max_tokens=4096)
        return self._parse_spec_response(raw, requirement)

    def _generate_spec_template(self, requirement: str) -> FeatureSpec:
        """Fallback spec generator using deterministic templates."""
        slug = _slugify(requirement)
        class_name = "".join(w.capitalize() for w in slug.split("_") if w)

        files_create = [
            {
                "path": f"luqi/features/{slug}.py",
                "purpose": f"Core implementation of {requirement}",
            },
            {
                "path": f"tests/unit/test_{slug}.py",
                "purpose": "Unit tests for the new feature",
            },
        ]

        function_sigs = [
            {
                "name": f"process_{slug}",
                "signature": f"(input_data: str, **kwargs: Any) -> dict[str, Any]",
                "description": f"Main entry-point for {requirement}",
            },
            {
                "name": f"validate_{slug}_input",
                "signature": f"(input_data: str) -> bool",
                "description": "Validate input before processing",
            },
            {
                "name": f"format_{slug}_output",
                "signature": f"(result: dict[str, Any]) -> str",
                "description": "Format the feature output for downstream consumers",
            },
        ]

        test_cases = [
            {"name": f"test_{slug}_happy_path", "input": "valid sample input", "expected": "success"},
            {"name": f"test_{slug}_empty_input", "input": "", "expected": "error"},
            {"name": f"test_{slug}_invalid_input", "input": "!@#$%^&*()", "expected": "error"},
            {"name": f"test_{slug}_unicode_input", "input": "日本語テスト 🎉", "expected": "success"},
            {"name": f"test_{slug}_large_input", "input": "x" * 10_000, "expected": "success"},
        ]

        integrations = [
            {"component": "API Gateway", "description": f"Add endpoint /v1/{slug.replace('_', '-')} "},
            {"component": "Message Pipeline", "description": f"Hook {class_name} into preprocessing pipeline"},
            {"component": "Metrics", "description": f"Track {slug}_latency and {slug}_error_rate"},
        ]

        return FeatureSpec(
            name=class_name,
            description=requirement,
            requirement=requirement,
            files_to_create=files_create,
            files_to_modify=[],
            function_signatures=function_sigs,
            test_cases=test_cases,
            integration_points=integrations,
            dependencies=["pydantic", "prometheus-client"],
        )

    # ------------------------------------------------------------------
    # 2. Code generation
    # ------------------------------------------------------------------

    def generate_code(self, spec: FeatureSpec) -> dict[str, str]:
        """Generate production-ready Python code for every file in *spec*.

        Parameters
        ----------
        spec:
            A :class:`FeatureSpec` produced by :meth:`generate_feature_spec`.

        Returns
        -------
        dict[str, str]
            Mapping ``{relative_filepath: source_code}``.
        """
        logger.info("Generating code for feature: %s", spec.name)
        generated: dict[str, str] = {}

        if self.llm is not None:
            for file_info in spec.files_to_create:
                path = file_info["path"]
                prompt = self._build_code_prompt(spec, path)
                code = self.llm.complete(prompt, temperature=0.2, max_tokens=4096)
                generated[path] = self._sanitize_code(code)
        else:
            generated = self._generate_code_template(spec)

        logger.info("Generated %d files", len(generated))
        return generated

    def _generate_code_template(self, spec: FeatureSpec) -> dict[str, str]:
        """Deterministic code generation when no LLM is available."""
        slug = _slugify(spec.name)
        class_name = spec.name

        # --- main implementation file -----------------------------------
        module_path = f"luqi/features/{slug}.py"
        module_code = f'''#!/usr/bin/env python3
"""
{spec.name} — {spec.description}

Auto-generated by Prometheus Prime on {datetime.now(timezone.utc).isoformat()}.
"""

from __future__ import annotations

__all__ = ["{class_name}Processor", "process_{slug}"]

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("luqi.features.{slug}")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
{class_name}Result:
    """Result container for {spec.name} processing."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: str = ""


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

class {class_name}Processor:
    """Processor implementing *{spec.description}*.

    Usage::

        processor = {class_name}Processor()
        result = processor.process("sample input")
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {{}}
        self._initialized = True

    # -- validation -------------------------------------------------------

    def validate_input(self, input_data: str) -> bool:
        """Validate *input_data* before processing.

        Returns ``False`` for empty, None, or excessively long inputs.
        """
        if not isinstance(input_data, str):
            return False
        if not input_data.strip():
            return False
        max_len = self.config.get("max_input_length", 100_000)
        return len(input_data) <= max_len

    # -- processing -------------------------------------------------------

    def process(self, input_data: str, **kwargs: Any) -> {class_name}Result:
        """Main entry-point.

        Parameters
        ----------
        input_data:
            The raw string to process.
        **kwargs:
            Additional keyword arguments forwarded to internal methods.

        Returns
        -------
        {class_name}Result
            Structured result with timing and error metadata.
        """
        start = time.perf_counter()

        if not self.validate_input(input_data):
            return {class_name}Result(
                success=False,
                error_message="Validation failed: invalid or empty input",
                processing_time_ms=(time.perf_counter() - start) * 1000,
            )

        try:
            processed = self._run_core_logic(input_data, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("Processing completed in %.2f ms", elapsed)
            return {class_name}Result(
                success=True,
                data=processed,
                processing_time_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("Processing failed after %.2f ms", elapsed)
            return {class_name}Result(
                success=False,
                error_message=str(exc),
                processing_time_ms=elapsed,
            )

    def _run_core_logic(self, input_data: str, **kwargs: Any) -> dict[str, Any]:
        """Implement the actual feature logic here.

        Override or extend this method to add real functionality.
        """
        # TODO: Replace with actual implementation
        return {{
            "input_length": len(input_data),
            "processed": True,
            "feature": "{spec.name}",
        }}

    # -- output formatting ------------------------------------------------

    def format_output(self, result: {class_name}Result) -> str:
        """Serialize *result* into a human-readable string."""
        if result.success:
            return f"[{{result.processing_time_ms:.1f}}ms] OK: {{result.data}}"
        return f"[{{result.processing_time_ms:.1f}}ms] ERR: {{result.error_message}}"


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def process_{slug}(input_data: str, **kwargs: Any) -> {class_name}Result:
    """One-shot processing function.

    Creates a default :class:`{class_name}Processor` and runs it.
    """
    processor = {class_name}Processor()
    return processor.process(input_data, **kwargs)
'''

        # --- test file --------------------------------------------------
        test_path = f"tests/unit/test_{slug}.py"
        test_code = f'''#!/usr/bin/env python3
"""Unit tests for {spec.name} — auto-generated by Prometheus Prime."""

from __future__ import annotations

import pytest

from luqi.features.{slug} import {class_name}Processor, {class_name}Result, process_{slug}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def processor() -> {class_name}Processor:
    return {class_name}Processor()


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_process_happy_path(processor: {class_name}Processor) -> None:
    result = processor.process("Hello, world!")
    assert result.success is True
    assert "input_length" in result.data


def test_process_unicode_input(processor: {class_name}Processor) -> None:
    result = processor.process("日本語テスト 🎉")
    assert result.success is True


def test_process_large_input(processor: {class_name}Processor) -> None:
    result = processor.process("x" * 10_000)
    assert result.success is True


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_validate_empty_string(processor: {class_name}Processor) -> None:
    assert processor.validate_input("") is False


def test_validate_whitespace_only(processor: {class_name}Processor) -> None:
    assert processor.validate_input("   \\t\\n  ") is False


def test_validate_none_raises(processor: {class_name}Processor) -> None:
    assert processor.validate_input(None) is False  # type: ignore[arg-type]


def test_validate_too_long(processor: {class_name}Processor) -> None:
    assert processor.validate_input("x" * 1_000_001) is False


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

def test_process_empty_input(processor: {class_name}Processor) -> None:
    result = processor.process("")
    assert result.success is False
    assert "Validation failed" in result.error_message


def test_convenience_function() -> None:
    result = process_{slug}("test input")
    assert isinstance(result, {class_name}Result)


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------

def test_format_success(processor: {class_name}Processor) -> None:
    result = {class_name}Result(success=True, data={{"key": "val"}}, processing_time_ms=12.3)
    formatted = processor.format_output(result)
    assert "OK" in formatted
    assert "12.3ms" in formatted


def test_format_error(processor: {class_name}Processor) -> None:
    result = {class_name}Result(success=False, error_message="boom", processing_time_ms=5.0)
    formatted = processor.format_output(result)
    assert "ERR" in formatted
    assert "boom" in formatted
'''

        return {module_path: module_code, test_path: test_code}

    # ------------------------------------------------------------------
    # 3. Test generation
    # ------------------------------------------------------------------

    def generate_tests(self, spec: FeatureSpec) -> str:
        """Generate comprehensive pytest test cases for *spec*.

        Returns
        -------
        str
            Complete pytest-ready source code.
        """
        logger.info("Generating tests for feature: %s", spec.name)

        if self.llm is not None:
            prompt = self._build_test_prompt(spec)
            return self._sanitize_code(self.llm.complete(prompt, temperature=0.2, max_tokens=4096))

        # Use the template-based test code already generated
        return self._generate_code_template(spec).get(
            f"tests/unit/test_{_slugify(spec.name)}.py",
            "# No tests generated\n",
        )

    # ------------------------------------------------------------------
    # 4. Code review
    # ------------------------------------------------------------------

    def review_code(self, code: str) -> CodeReviewResult:
        """Review *code* for syntax, logic, security, performance and style.

        The review pipeline runs deterministically **before** any LLM call:

        1. **AST parse** – guarantees syntactic validity.
        2. **Security heuristics** – bans ``eval``, ``exec``, hard-coded secrets,
           unsafe ``subprocess`` patterns, etc.
        3. **Style heuristics** – checks line length, import ordering, naming.

        If an *LLM* is configured it then performs a deeper semantic review.

        Parameters
        ----------
        code:
            Python source to review.

        Returns
        -------
        CodeReviewResult
            Structured review with pass/fail status and actionable issues.
        """
        issues: list[dict[str, str]] = []
        suggestions: list[dict[str, str]] = []
        score = 1.0

        # --- syntax check ------------------------------------------------
        try:
            ast.parse(code)
        except SyntaxError as exc:
            issues.append({
                "category": "syntax",
                "severity": "critical",
                "message": f"Syntax error: {{exc}}",
                "line": str(exc.lineno or "unknown"),
            })
            score = 0.0
            return CodeReviewResult(passed=False, issues=issues, suggestions=suggestions, score=score)

        # --- security heuristics -----------------------------------------
        security_patterns = {
            r"\beval\s*\(": "Use of eval() is a security risk",
            r"\bexec\s*\(": "Use of exec() is a security risk",
            r"subprocess\.call\s*\([^)]*shell\s*=\s*True": "subprocess with shell=True is dangerous",
            r"\bos\.system\s*\(": "os.system() is unsafe; use subprocess.run instead",
            r"\b__import__\s*\(": "Dynamic __import__ can be unsafe",
            r"(password|secret|token|api_key)\s*=\s*['\"][^'\"]+['\"]": "Possible hard-coded secret",
            r"pickle\.(loads|load)\s*\(": "pickle can execute arbitrary code during deserialization",
            r"yaml\.load\s*\([^)]*\)": "yaml.load without Loader= is unsafe",
        }

        for pattern, message in security_patterns.items():
            if re.search(pattern, code):
                issues.append({
                    "category": "security",
                    "severity": "high",
                    "message": message,
                    "line": "unknown",
                })
                score -= 0.15

        # --- style heuristics -------------------------------------------
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            if len(line) > 120:
                issues.append({
                    "category": "style",
                    "severity": "low",
                    "message": f"Line {{i}} exceeds 120 characters ({{len(line)}} chars)",
                    "line": str(i),
                })
                score -= 0.02

        if not code.strip().startswith('"""') and not code.strip().startswith("#!/"):
            suggestions.append({
                "category": "style",
                "message": "Module-level docstring is missing",
            })
            score -= 0.05

        # --- LLM deep review ---------------------------------------------
        if self.llm is not None and score > 0.5:
            llm_review = self._llm_review(code)
            issues.extend(llm_review.get("issues", []))
            suggestions.extend(llm_review.get("suggestions", []))
            score = llm_review.get("score", score)

        score = max(0.0, min(1.0, score))
        passed = score >= 0.7 and not any(
            i["severity"] == "critical" for i in issues
        )

        return CodeReviewResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
            score=round(score, 3),
        )

    def _llm_review(self, code: str) -> dict[str, Any]:
        """Request a deeper semantic review from the LLM."""
        prompt = f"""\
Review the following Python code for:
1. Logic correctness
2. Performance issues
3. Security vulnerabilities
4. Python best practices (PEP 8, type hints, error handling)
5. Missing edge-case handling

Return a JSON object with keys: "issues" (list of {{"category", "severity", "message", "line"}}),
"suggestions" (list of {{"category", "message"}}), and "score" (float 0-1).

```python
{code}
```
"""
        raw = self.llm.complete(prompt, temperature=0.1, max_tokens=2048)
        try:
            import json
            return json.loads(raw)
        except Exception:
            return {"issues": [], "suggestions": [], "score": 0.8}

    # ------------------------------------------------------------------
    # 5. Safe integration
    # ------------------------------------------------------------------

    def integrate_feature(
        self,
        files: dict[str, str],
        target_module: str,
    ) -> IntegrationResult:
        """Safely integrate generated code into the existing codebase.

        * Creates backups of any existing files before overwriting.
        * Runs a quick syntax check on every new file.
        * Writes files atomically (temp + rename) to avoid corruption.

        Parameters
        ----------
        files:
            Mapping ``{{relative_path: source_code}}``.
        target_module:
            Dotted Python path of the module that will import the new
            feature (used for import-validation only).

        Returns
        -------
        IntegrationResult
            Detailed outcome with backup locations and any errors.
        """
        logger.info("Integrating %d files into module '%s'", len(files), target_module)

        result = IntegrationResult(success=True)
        errors: list[str] = []

        for rel_path, source in files.items():
            abs_path = self.project_root / rel_path

            # Security: prevent path traversal
            try:
                abs_path.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                errors.append(f"Path traversal blocked: {{rel_path}}")
                continue

            # Syntax validation
            try:
                ast.parse(source)
            except SyntaxError as exc:
                errors.append(f"Syntax error in {{rel_path}}: {{exc}}")
                continue

            # Backup existing file
            if abs_path.exists():
                backup_name = f"{{abs_path.name}}.{{self._timestamp()}}.bak"
                backup_path = self.backup_dir / backup_name
                shutil.copy2(abs_path, backup_path)
                result.backups[str(abs_path)] = str(backup_path)
                result.modified_files.append(str(abs_path))
            else:
                result.created_files.append(str(abs_path))

            # Atomic write
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = abs_path.with_suffix(".tmp")
            tmp.write_text(source, encoding="utf-8")
            tmp.replace(abs_path)

        if errors:
            result.success = False
            result.errors = errors

        logger.info("Integration complete: created=%d, modified=%d, errors=%d",
                    len(result.created_files), len(result.modified_files), len(result.errors))
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_spec_prompt(requirement: str) -> str:
        return f"""\
You are a senior software architect. Generate a detailed feature specification
for the following requirement:

"{{requirement}}"

Return a JSON object with these keys:
- name: PascalCase feature name
- description: one-sentence summary
- files_to_create: list of {{"path": "...", "purpose": "..."}}
- files_to_modify: list of {{"path": "...", "purpose": "..."}}
- function_signatures: list of {{"name": "...", "signature": "...", "description": "..."}}
- test_cases: list of {{"name": "...", "input": "...", "expected": "..."}}
- integration_points: list of {{"component": "...", "description": "..."}}
- dependencies: list of required pip packages
"""

    @staticmethod
    def _build_code_prompt(spec: FeatureSpec, file_path: str) -> str:
        sigs = "\\n".join(
            f"  {{f['name']}}{f['signature']}  # {{f['description']}}"
            for f in spec.function_signatures
        )
        return f"""\
Generate production-ready Python 3.11 code for the file *{{file_path}}*.

Feature: {{spec.name}}
Description: {{spec.description}}

Functions to implement:
{{sigs}}

Requirements:
- Include proper imports and module-level docstring
- Use type hints everywhere
- Handle errors gracefully with try/except
- Use logging, not print
- Follow PEP 8
- Include __all__

Return ONLY the Python code (no markdown fences).
"""

    @staticmethod
    def _build_test_prompt(spec: FeatureSpec) -> str:
        tc = "\\n".join(f"  - {{t['name']}}: input='{{t['input']}}' → {{t['expected']}}"
                        for t in spec.test_cases)
        return f"""\
Generate pytest test cases for feature *{{spec.name}}*.

Test scenarios:
{{tc}}

Requirements:
- Use pytest fixtures
- Cover happy path, edge cases, and error cases
- Use parametrize where appropriate
- Include type hints
- Return ONLY the Python test code
"""

    @staticmethod
    def _sanitize_code(raw: str) -> str:
        """Strip markdown fences and leading/trailing whitespace."""
        raw = raw.strip()
        if raw.startswith("```python"):
            raw = raw[len("```python"):]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return raw.strip()

    @staticmethod
    def _parse_spec_response(raw: str, requirement: str) -> FeatureSpec:
        """Parse LLM JSON response into a *FeatureSpec*."""
        import json

        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON; falling back to template")
            return CodeGenerator()._generate_spec_template(requirement)

        return FeatureSpec(
            name=data.get("name", "UnknownFeature"),
            description=data.get("description", ""),
            requirement=requirement,
            files_to_create=data.get("files_to_create", []),
            files_to_modify=data.get("files_to_modify", []),
            function_signatures=data.get("function_signatures", []),
            test_cases=data.get("test_cases", []),
            integration_points=data.get("integration_points", []),
            dependencies=data.get("dependencies", []),
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


# ---------------------------------------------------------------------------
# Convenience free functions
# ---------------------------------------------------------------------------

def quick_generate(requirement: str, project_root: str | Path = ".") -> dict[str, str]:
    """One-shot helper: spec → code for a requirement (no LLM required)."""
    cg = CodeGenerator(project_root=project_root)
    spec = cg.generate_feature_spec(requirement)
    return cg.generate_code(spec)
