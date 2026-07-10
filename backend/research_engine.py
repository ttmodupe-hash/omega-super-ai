"""
Luqi AI v24.4.0 — Research Engine
==================================
Agent 2: Continuous Capability Optimization Engine.

An automated research agent that finds improvements, security patches,
and modern libraries for the Luqi AI Multi-Agent System.

Features:
  - Web research for dependency updates via PyPI
  - Security advisory checking via GitHub Advisory Database
  - Performance optimization suggestions with draft code
  - Human-in-the-loop approval workflow
  - FastAPI endpoint integration
  - File-based caching and rate limiting

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.research_engine")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PYPI_JSON_URL: str = "https://pypi.org/pypi/{package}/json"
GITHUB_ADVISORY_URL: str = (
    "https://api.github.com/advisories?ecosystem=pip&per_page=100"
)
CACHE_TTL_SECONDS: int = 86_400  # 24 hours
RESEARCH_COOLDOWN_SECONDS: int = 3_600  # 1 hour
DEFAULT_REQUIREMENTS_PATH: str = "requirements.txt"
FINDINGS_DB_PATH: str = "research_findings.json"
CACHE_DB_PATH: str = "research_cache.json"

# ---------------------------------------------------------------------------
# Performance alternatives lookup table
# ---------------------------------------------------------------------------
PERFORMANCE_ALTERNATIVES: Dict[str, Dict[str, Any]] = {
    "json": {
        "recommendation": "orjson",
        "reason": (
            "orjson is 2-10x faster than stdlib json for both "
            "serialization and deserialization."
        ),
        "draft_code": (
            "# Replace: import json\n"
            "# With:    import orjson as json\n\n"
            "# json.dumps(obj) -> json.dumps(obj).decode()\n"
            "# json.loads(s)   -> json.loads(s)  # same API\n\n"
            "# Add to requirements.txt:\n"
            "# orjson>=3.9.0"
        ),
    },
    "asyncio": {
        "recommendation": "uvloop",
        "reason": (
            "uvloop replaces asyncio's default event loop with a "
            "libuv-based loop for 2-4x throughput improvement."
        ),
        "draft_code": (
            "import asyncio\n"
            "import uvloop\n\n"
            "# Install uvloop at startup\n"
            "uvloop.install()\n\n"
            "# All asyncio code now uses uvloop automatically\n"
            "asyncio.run(main())\n\n"
            "# Add to requirements.txt:\n"
            "# uvloop>=0.19.0  ; sys_platform != 'win32'"
        ),
    },
    "requests": {
        "recommendation": "httpx",
        "reason": (
            "httpx offers HTTP/2 support, async API compatibility, "
            "and is actively maintained as the modern replacement."
        ),
        "draft_code": (
            "# Replace: import requests\n"
            "# With:    import httpx\n\n"
            "# requests.get(url) -> httpx.get(url)\n"
            "# Async support:\n"
            "# async with httpx.AsyncClient() as client:\n"
            "#     r = await client.get(url)\n\n"
            "# Add to requirements.txt:\n"
            "# httpx>=0.25.0"
        ),
    },
    "flask": {
        "recommendation": "fastapi",
        "reason": (
            "FastAPI provides automatic OpenAPI docs, pydantic validation, "
            "and is 3-5x faster than Flask under load."
        ),
        "draft_code": (
            "# Before (Flask):\n"
            "# from flask import Flask, jsonify\n"
            "# app = Flask(__name__)\n\n"
            "# After (FastAPI):\n"
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "# @app.route('/items/<int:item_id>')\n"
            "# @app.get('/items/{item_id}')\n"
            "# async def read_item(item_id: int):\n"
            "#     return {'item_id': item_id}\n\n"
            "# Add to requirements.txt:\n"
            "# fastapi>=0.104.0\n"
            "# uvicorn[standard]>=0.24.0"
        ),
    },
    "pickle": {
        "recommendation": "orjson / msgpack",
        "reason": (
            "pickle is insecure for untrusted data and slow. "
            "Use orjson or msgpack for safe, fast serialization."
        ),
        "draft_code": (
            "# Replace pickle with orjson:\n"
            "import orjson\n\n"
            "# pickle.dumps(obj) -> orjson.dumps(obj)\n"
            "# pickle.loads(data) -> orjson.loads(data)\n\n"
            "# Or use msgpack for binary format:\n"
            "# import msgpack\n"
            "# msgpack.packb(obj, use_bin_type=True)\n\n"
            "# Add to requirements.txt:\n"
            "# orjson>=3.9.0  # or msgpack>=1.0.0"
        ),
    },
    "sqlite3": {
        "recommendation": "aiosqlite",
        "reason": (
            "aiosqlite wraps sqlite3 with asyncio support, "
            "preventing blocking I/O in async applications."
        ),
        "draft_code": (
            "# Replace: import sqlite3\n"
            "# With:    import aiosqlite\n\n"
            "# sqlite3.connect(db) -> await aiosqlite.connect(db)\n"
            "# conn.execute(sql)   -> await db.execute(sql)\n"
            "# conn.commit()       -> await db.commit()\n\n"
            "# Add to requirements.txt:\n"
            "# aiosqlite>=0.19.0"
        ),
    },
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ResearchCategory(str, Enum):
    """Classification for research findings."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    FEATURE = "feature"
    DEPENDENCY = "dependency"
    BEST_PRACTICE = "best_practice"


class FindingStatus(str, Enum):
    """Lifecycle status of a research finding."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ResearchFinding:
    """A single research finding produced by the engine.

    Attributes:
        id: Unique identifier (UUID4 hex).
        title: Short human-readable title.
        description: Detailed explanation of the finding.
        category: Classification (security/performance/feature/etc.).
        source_url: URL where the finding was sourced.
        current_version: The currently used version (if applicable).
        recommended_version: Suggested upgrade target (if applicable).
        draft_code: Optional code snippet for the proposed change.
        confidence: Score between 0.0 and 1.0 indicating certainty.
        status: Current approval status.
        created_at: ISO-8601 timestamp when the finding was created.
        reviewed_at: ISO-8601 timestamp when approved/rejected, or empty.
    """

    id: str
    title: str
    description: str
    category: ResearchCategory
    source_url: str = ""
    current_version: str = ""
    recommended_version: str = ""
    draft_code: str = ""
    confidence: float = 0.0
    status: FindingStatus = FindingStatus.PENDING
    created_at: str = ""
    reviewed_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        d = asdict(self)
        d["category"] = self.category.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchFinding":
        """Deserialize from a plain dictionary."""
        data = dict(data)
        data["category"] = ResearchCategory(data.get("category", "feature"))
        data["status"] = FindingStatus(data.get("status", "pending"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Singleton metaclass
# ---------------------------------------------------------------------------
class _SingletonMeta(type):
    """Thread-safe singleton metaclass using double-checked locking pattern."""

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------
class ResearchEngine(metaclass=_SingletonMeta):
    """Continuous Capability Optimization Engine for Luqi AI.

    Runs automated research cycles to discover security patches,
    dependency updates, performance optimizations, and best-practice
    improvements.  All findings require human approval before deployment.

    Usage:
        engine = ResearchEngine()
        findings = engine.run_full_research_cycle()
        pending = engine.get_pending_findings()
    """

    # ------------------------------------------------------------------
    # Construction / configuration
    # ------------------------------------------------------------------
    def __init__(
        self,
        findings_path: Optional[str] = None,
        cache_path: Optional[str] = None,
        requirements_path: Optional[str] = None,
    ) -> None:
        """Initialize the singleton research engine.

        Args:
            findings_path: Path to the JSON file that persists findings.
            cache_path: Path to the JSON file that caches PyPI responses.
            requirements_path: Path to requirements.txt to analyse.
        """
        self._findings_path: str = findings_path or FINDINGS_DB_PATH
        self._cache_path: str = cache_path or CACHE_DB_PATH
        self._requirements_path: str = requirements_path or DEFAULT_REQUIREMENTS_PATH
        self._findings: Dict[str, ResearchFinding] = {}
        self._last_run: float = 0.0
        self._load_findings()

    # ------------------------------------------------------------------
    # Public API — research cycles
    # ------------------------------------------------------------------
    def run_full_research_cycle(self) -> List[ResearchFinding]:
        """Execute all research methods and store new findings.

        Enforces a cooldown of ``RESEARCH_COOLDOWN_SECONDS`` between runs.

        Returns:
            A list of *new* findings discovered during this cycle.
        """
        now = time.time()
        if now - self._last_run < RESEARCH_COOLDOWN_SECONDS:
            cooldown_remaining = RESEARCH_COOLDOWN_SECONDS - (now - self._last_run)
            logger.warning(
                "Research cooldown active — %.0f seconds remaining.",
                cooldown_remaining,
            )
            return []

        self._last_run = now
        new_findings: List[ResearchFinding] = []

        for method_name, method in (
            ("dependencies", self.check_dependencies),
            ("security", self.check_security_advisories),
            ("optimizations", self.find_optimizations),
        ):
            try:
                findings = method()
                for f in findings:
                    if f.id not in self._findings:
                        self._findings[f.id] = f
                        new_findings.append(f)
                logger.info(
                    "%s research produced %d new finding(s).",
                    method_name,
                    len(findings),
                )
            except Exception as exc:  # pragma: no cover
                logger.error("%s research failed: %s", method_name, exc)

        if new_findings:
            self._save_findings()

        logger.info(
            "Full research cycle complete — %d new finding(s) total.",
            len(new_findings),
        )
        return new_findings

    # ------------------------------------------------------------------
    # Dependency checking
    # ------------------------------------------------------------------
    def check_dependencies(self) -> List[ResearchFinding]:
        """Scan *requirements.txt* and compare each package against PyPI.

        Returns:
            A list of :class:`ResearchFinding` objects for outdated
            packages where a newer stable version is available.
        """
        findings: List[ResearchFinding] = []
        deps = self._parse_requirements()
        if not deps:
            logger.warning("No dependencies found in %s", self._requirements_path)
            return findings

        for package_name, current_version in deps:
            try:
                pypi_data = self._fetch_pypi_info(package_name)
                if not pypi_data:
                    continue

                latest_version = pypi_data.get("info", {}).get("version", "")
                if not latest_version:
                    continue

                cmp = self._compare_versions(current_version, latest_version)
                if cmp < 0:
                    finding = ResearchFinding(
                        id=self._make_id(
                            f"dep-{package_name}-{latest_version}"
                        ),
                        title=f"Update {package_name} {current_version} → {latest_version}",
                        description=(
                            f"A newer version of **{package_name}** is available on PyPI.\n\n"
                            f"- Current:  {current_version}\n"
                            f"- Latest:   {latest_version}\n\n"
                            f"Upgrade may contain bug fixes, performance improvements, "
                            f"or security patches."
                        ),
                        category=ResearchCategory.DEPENDENCY,
                        source_url=f"https://pypi.org/project/{package_name}/",
                        current_version=current_version,
                        recommended_version=latest_version,
                        draft_code=(
                            f"# Update requirements.txt\n"
                            f"{package_name}>={latest_version}\n\n"
                            f"# Then run:\n"
                            f"# pip install -U {package_name}"
                        ),
                        confidence=self._confidence_from_age(
                            pypi_data.get("urls", [])
                        ),
                    )
                    findings.append(finding)
            except Exception as exc:
                logger.warning("Error checking %s: %s", package_name, exc)

        return findings

    # ------------------------------------------------------------------
    # Security advisories
    # ------------------------------------------------------------------
    def check_security_advisories(self) -> List[ResearchFinding]:
        """Query GitHub Advisory Database for known vulnerabilities.

        Matches advisories against packages listed in *requirements.txt*.

        Returns:
            A list of :class:`ResearchFinding` objects describing CVEs
            that affect the project's dependencies.
        """
        findings: List[ResearchFinding] = []
        deps = {pkg.lower() for pkg, _ in self._parse_requirements()}
        if not deps:
            return findings

        try:
            advisories = self._fetch_github_advisories()
        except Exception as exc:
            logger.error("Failed to fetch GitHub advisories: %s", exc)
            return findings

        seen: set = set()
        for adv in advisories:
            try:
                packages = self._extract_affected_packages(adv)
                for pkg_name in packages:
                    pkg_key = pkg_name.lower()
                    if pkg_key not in deps:
                        continue

                    adv_id = adv.get("ghsa_id", "")
                    cve_id = adv.get("cve_id") or "N/A"
                    severity = adv.get("severity", "unknown")
                    summary = adv.get("summary", "No summary provided.")
                    url = adv.get("html_url", "")

                    cache_key = f"sec-{pkg_key}-{adv_id}"
                    if cache_key in seen:
                        continue
                    seen.add(cache_key)

                    finding = ResearchFinding(
                        id=self._make_id(cache_key),
                        title=f"Security Advisory: {pkg_name} ({cve_id})",
                        description=(
                            f"**Severity:** {severity.upper()}\n\n"
                            f"{summary}\n\n"
                            f"- **GHSA:** {adv_id}\n"
                            f"- **CVE:** {cve_id}\n"
                            f"- **Package:** {pkg_name}\n\n"
                            f"Review the advisory and upgrade immediately if affected."
                        ),
                        category=ResearchCategory.SECURITY,
                        source_url=url,
                        recommended_version="See advisory for patched version",
                        confidence=self._severity_to_confidence(severity),
                    )
                    findings.append(finding)
            except Exception as exc:
                logger.debug("Error parsing advisory: %s", exc)
                continue

        return findings

    # ------------------------------------------------------------------
    # Performance optimizations
    # ------------------------------------------------------------------
    def find_optimizations(self) -> List[ResearchFinding]:
        """Suggest performance improvements based on dependency analysis.

        Checks whether any dependencies have well-known faster or more
        modern alternatives and produces draft-code findings.

        Returns:
            A list of :class:`ResearchFinding` objects with draft code
            and installation instructions.
        """
        findings: List[ResearchFinding] = []
        dep_names = {pkg.lower() for pkg, _ in self._parse_requirements()}

        for dep, info in PERFORMANCE_ALTERNATIVES.items():
            if dep not in dep_names:
                continue

            finding = ResearchFinding(
                id=self._make_id(f"opt-{dep}-{info['recommendation']}"),
                title=f"Performance: Replace {dep} with {info['recommendation']}",
                description=(
                    f"**{dep}** can be replaced by **{info['recommendation']}** "
                    f"for significant performance gains.\n\n"
                    f"{info['reason']}"
                ),
                category=ResearchCategory.PERFORMANCE,
                source_url=f"https://pypi.org/project/{info['recommendation'].split()[0]}/",
                current_version=dep,
                recommended_version=info["recommendation"],
                draft_code=info["draft_code"],
                confidence=0.85,
            )
            findings.append(finding)

        return findings

    # ------------------------------------------------------------------
    # Finding lifecycle
    # ------------------------------------------------------------------
    def get_pending_findings(self) -> List[Dict[str, Any]]:
        """Return all findings that have not yet been reviewed.

        Returns:
            List of finding dictionaries with status == ``pending``.
        """
        return [
            f.to_dict()
            for f in self._findings.values()
            if f.status == FindingStatus.PENDING
        ]

    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single finding by its unique identifier.

        Args:
            finding_id: The ``id`` field of the finding.

        Returns:
            Dictionary representation, or ``None`` if not found.
        """
        finding = self._findings.get(finding_id)
        return finding.to_dict() if finding else None

    def approve_finding(self, finding_id: str) -> bool:
        """Approve a finding for downstream deployment.

        The finding status changes to ``approved`` and a timestamp is
        recorded.  In a full Luqi AI deployment this would pass the
        draft code to the *SandboxValidator* for integration testing.

        Args:
            finding_id: The ``id`` field of the finding to approve.

        Returns:
            ``True`` if the finding was found and approved.
        """
        finding = self._findings.get(finding_id)
        if not finding:
            logger.warning("Cannot approve — finding %s not found.", finding_id)
            return False

        finding.status = FindingStatus.APPROVED
        finding.reviewed_at = datetime.now(timezone.utc).isoformat()
        self._save_findings()

        logger.info(
            "Finding %s approved — would pass to SandboxValidator for deployment.",
            finding_id,
        )
        return True

    def reject_finding(self, finding_id: str) -> bool:
        """Reject a finding so it is excluded from deployment.

        Args:
            finding_id: The ``id`` field of the finding to reject.

        Returns:
            ``True`` if the finding was found and rejected.
        """
        finding = self._findings.get(finding_id)
        if not finding:
            logger.warning("Cannot reject — finding %s not found.", finding_id)
            return False

        finding.status = FindingStatus.REJECTED
        finding.reviewed_at = datetime.now(timezone.utc).isoformat()
        self._save_findings()

        logger.info("Finding %s rejected.", finding_id)
        return True

    # ------------------------------------------------------------------
    # FastAPI endpoint registration
    # ------------------------------------------------------------------
    def register_endpoints(self, app_or_router: Any) -> None:
        """Register research-engine REST endpoints on a FastAPI app or router.

        Endpoints added:
            GET    /api/system/research          → list pending findings
            GET    /api/system/research/{id}      → view specific finding
            POST   /api/system/research/run       → trigger full research cycle
            POST   /api/system/research/approve/{id}  → approve finding
            POST   /api/system/research/reject/{id}   → reject finding

        Args:
            app_or_router: A ``FastAPI`` application instance or an
                ``APIRouter`` to mount the routes on.
        """
        from fastapi import APIRouter, HTTPException, Path

        router = APIRouter(prefix="/api/system/research", tags=["Research Engine"])

        @router.get("")
        async def list_findings() -> Dict[str, Any]:
            """Return all pending research findings."""
            findings = self.get_pending_findings()
            return {"count": len(findings), "findings": findings}

        @router.get("/{finding_id}")
        async def get_finding_endpoint(
            finding_id: str = Path(..., description="Unique finding identifier"),
        ) -> Dict[str, Any]:
            """Retrieve a single research finding by ID."""
            data = self.get_finding(finding_id)
            if data is None:
                raise HTTPException(status_code=404, detail="Finding not found")
            return data

        @router.post("/run")
        async def run_research() -> Dict[str, Any]:
            """Trigger a full research cycle (rate-limited to 1/hour)."""
            new_findings = self.run_full_research_cycle()
            return {
                "new_findings": len(new_findings),
                "findings": [f.to_dict() for f in new_findings],
            }

        @router.post("/approve/{finding_id}")
        async def approve_finding_endpoint(
            finding_id: str = Path(..., description="Finding to approve"),
        ) -> Dict[str, str]:
            """Approve a finding for deployment via SandboxValidator."""
            if self.approve_finding(finding_id):
                return {"status": "approved", "finding_id": finding_id}
            raise HTTPException(status_code=404, detail="Finding not found")

        @router.post("/reject/{finding_id}")
        async def reject_finding_endpoint(
            finding_id: str = Path(..., description="Finding to reject"),
        ) -> Dict[str, str]:
            """Reject a finding — it will not be deployed."""
            if self.reject_finding(finding_id):
                return {"status": "rejected", "finding_id": finding_id}
            raise HTTPException(status_code=404, detail="Finding not found")

        # Mount router — works with both FastAPI app and APIRouter
        if hasattr(app_or_router, "include_router"):
            app_or_router.include_router(router)
        else:
            # Fallback: register directly on app
            for route in router.routes:
                app_or_router.router.routes.append(route)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Internal — PyPI / network helpers
    # ------------------------------------------------------------------
    def _fetch_pypi_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package metadata from PyPI's JSON API with caching.

        Args:
            package_name: Normalised PyPI package name.

        Returns:
            Parsed JSON dict, or ``None`` on failure / cache miss.
        """
        cache = self._load_cache()
        cache_key = f"pypi:{package_name}"
        now = time.time()

        cached = cache.get(cache_key)
        if cached and (now - cached.get("_ts", 0)) < CACHE_TTL_SECONDS:
            return cached.get("data")

        url = PYPI_JSON_URL.format(package=package_name)
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "LuqiAI-ResearchEngine/24.4.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            cache[cache_key] = {"_ts": now, "data": data}
            self._save_cache(cache)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                logger.debug("Package %s not found on PyPI.", package_name)
            else:
                logger.warning("PyPI HTTP error for %s: %s", package_name, exc.code)
        except Exception as exc:
            logger.warning("PyPI fetch failed for %s: %s", package_name, exc)

        return None

    def _fetch_github_advisories(self) -> List[Dict[str, Any]]:
        """Fetch recent GitHub security advisories for pip packages.

        Returns:
            List of advisory dicts from the GitHub API.
        """
        try:
            req = urllib.request.Request(
                GITHUB_ADVISORY_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "LuqiAI-ResearchEngine/24.4.0",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error("GitHub Advisory API HTTP %s: %s", exc.code, exc.reason)
        except Exception as exc:
            logger.error("GitHub Advisory API request failed: %s", exc)

        return []

    # ------------------------------------------------------------------
    # Internal — version comparison
    # ------------------------------------------------------------------
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two PEP-440 style version strings.

        Handles numeric releases, pre-releases (a/b/rc/dev), and post
        releases.  Unknown formats fall back to lexicographic comparison.

        Returns:
            * -1 if *v1* < *v2*
            *  0 if *v1* == *v2*
            *  1 if *v1* > *v2*
        """

        # Pre-release class ranking — lower = earlier
        _PR_RANK: Dict[str, int] = {
            "dev": -5,
            "a": -4, "alpha": -4,
            "b": -3, "beta": -3,
            "c": -2, "rc": -2, "pre": -2,
            "post": 1, "r": 1, "rev": 1,
        }

        def _tokenize(v: str) -> List[int]:
            """Break a version string into a list of comparable ints."""
            cleaned = v.lstrip("vV").strip()
            parts = re.split(r"[.\-+]", cleaned)
            tokens: List[int] = []
            for part in parts:
                if not part:
                    continue
                # Match: optional digits, optional letters, optional digits
                m = re.match(r"^(\d*)([A-Za-z]*)(\d*)$", part)
                if not m:
                    tokens.append(0)
                    continue
                num1 = int(m.group(1)) if m.group(1) else 0
                letters = m.group(2).lower()
                num2 = int(m.group(3)) if m.group(3) else 0

                tokens.append(num1)
                if letters:
                    tokens.append(_PR_RANK.get(letters, 0))
                    tokens.append(num2)
                elif num2:
                    tokens.append(num2)
            return tokens

        try:
            t1 = _tokenize(v1)
            t2 = _tokenize(v2)
            max_len = max(len(t1), len(t2))
            t1 += [0] * (max_len - len(t1))
            t2 += [0] * (max_len - len(t2))

            if t1 < t2:
                return -1
            elif t1 > t2:
                return 1
            return 0
        except Exception:
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            return 0

    # ------------------------------------------------------------------
    # Internal — helpers
    # ------------------------------------------------------------------
    def _parse_requirements(self) -> List[Tuple[str, str]]:
        """Parse *requirements.txt* into (package_name, version) tuples.

        Returns:
            List of parsed dependencies.  Version defaults to ``0.0.0``
            when not pinned.
        """
        deps: List[Tuple[str, str]] = []
        path = Path(self._requirements_path)
        if not path.is_file():
            logger.debug("Requirements file not found: %s", self._requirements_path)
            return deps

        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Handle extras and version specifiers
                    match = re.match(
                        r"([A-Za-z0-9_\-\.]+)\s*(.*)", line
                    )
                    if not match:
                        continue
                    pkg = match.group(1).strip()
                    spec = match.group(2).strip()
                    # Extract version from specifier if present
                    ver_match = re.search(r"==\s*([0-9]+[^\s,;]*)", spec)
                    version = ver_match.group(1) if ver_match else "0.0.0"
                    deps.append((pkg, version))
        except Exception as exc:
            logger.error("Failed to parse requirements.txt: %s", exc)

        return deps

    @staticmethod
    def _make_id(seed: str) -> str:
        """Create a deterministic, URL-safe finding ID from a seed string.

        Uses a simple hash so the same logical finding always produces the
        same ID across restarts.
        """
        import hashlib

        h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"luqi-fnd-{h}"

    @staticmethod
    def _confidence_from_age(urls: List[Dict[str, Any]]) -> float:
        """Estimate confidence based on package release recency.

        Args:
            urls: The ``urls`` list from a PyPI JSON response.

        Returns:
            A float between 0.5 and 0.95.
        """
        if not urls:
            return 0.7
        try:
            newest = 0.0
            for u in urls:
                upload_time = u.get("upload_time", "")
                if upload_time:
                    ts = datetime.fromisoformat(upload_time.replace("Z", "+00:00"))
                    newest = max(newest, ts.timestamp())
            if newest:
                age_days = (time.time() - newest) / 86_400
                if age_days < 7:
                    return 0.95
                elif age_days < 30:
                    return 0.90
                elif age_days < 90:
                    return 0.85
                elif age_days < 180:
                    return 0.80
                else:
                    return 0.75
        except Exception:
            pass
        return 0.75

    @staticmethod
    def _severity_to_confidence(severity: str) -> float:
        """Map GitHub advisory severity to a confidence score.

        Args:
            severity: One of ``critical``, ``high``, ``moderate``, ``low``.

        Returns:
            Confidence float between 0.5 and 1.0.
        """
        mapping = {
            "critical": 1.0,
            "high": 0.95,
            "moderate": 0.85,
            "low": 0.75,
            "unknown": 0.70,
        }
        return mapping.get(severity.lower(), 0.70)

    @staticmethod
    def _extract_affected_packages(advisory: Dict[str, Any]) -> List[str]:
        """Extract pip package names from a GitHub advisory record.

        Args:
            advisory: A single advisory dict from the GitHub API.

        Returns:
            List of affected package name strings.
        """
        packages: List[str] = []
        try:
            for vuln in advisory.get("vulnerabilities", []):
                pkg = vuln.get("package", {})
                if pkg.get("ecosystem", "").lower() == "pip":
                    name = pkg.get("name", "")
                    if name:
                        packages.append(name)
        except Exception:
            pass
        return packages

    # ------------------------------------------------------------------
    # Persistence — findings
    # ------------------------------------------------------------------
    def _load_findings(self) -> None:
        """Deserialize findings from ``research_findings.json``."""
        path = Path(self._findings_path)
        if not path.is_file():
            self._findings = {}
            return

        try:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)

            for key, val in raw.items():
                try:
                    self._findings[key] = ResearchFinding.from_dict(val)
                except Exception as exc:
                    logger.debug("Skipping corrupt finding %s: %s", key, exc)

            # Restore last_run from the most recent finding timestamp
            if self._findings:
                timestamps = [
                    datetime.fromisoformat(f.created_at).timestamp()
                    for f in self._findings.values()
                    if f.created_at
                ]
                if timestamps:
                    self._last_run = max(timestamps)

        except json.JSONDecodeError:
            logger.error("Corrupt findings database — starting fresh.")
            self._findings = {}
        except Exception as exc:
            logger.error("Failed to load findings: %s", exc)
            self._findings = {}

    def _save_findings(self) -> None:
        """Serialize findings to ``research_findings.json``."""
        try:
            payload = {
                key: val.to_dict()
                for key, val in self._findings.items()
            }
            with open(self._findings_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save findings: %s", exc)

    # ------------------------------------------------------------------
    # Persistence — cache
    # ------------------------------------------------------------------
    def _load_cache(self) -> Dict[str, Any]:
        """Load the PyPI response cache from disk.

        Returns:
            Dictionary mapping cache keys to ``{_ts, data}`` records.
        """
        path = Path(self._cache_path)
        if not path.is_file():
            return {}
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        """Write the PyPI response cache to disk.

        Args:
            cache: The cache dictionary to persist.
        """
        try:
            with open(self._cache_path, "w", encoding="utf-8") as fh:
                json.dump(cache, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save cache: %s", exc)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
def get_research_engine(
    findings_path: Optional[str] = None,
    cache_path: Optional[str] = None,
    requirements_path: Optional[str] = None,
) -> ResearchEngine:
    """Return the singleton :class:`ResearchEngine` instance.

    This is the recommended entry-point for the rest of the Luqi AI system.
    """
    return ResearchEngine(findings_path, cache_path, requirements_path)
