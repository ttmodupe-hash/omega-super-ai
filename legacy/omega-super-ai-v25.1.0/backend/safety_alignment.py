"""Safety Alignment Module — Luqi AI v25

Provides AI safety guardrails including content moderation, toxicity
detection, bias analysis, alignment scoring, and policy enforcement.
Integrates with the v15 ASI cognitive engine and v25 pedagogical systems.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
#  SAFETY POLICIES
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_POLICIES = {
    "no_harm": "Content must not promote physical, emotional, or psychological harm",
    "no_illegal": "Content must not encourage illegal activities",
    "no_discrimination": "Content must not discriminate based on protected characteristics",
    "no_misinformation": "Content must not spread verifiably false information",
    "no_explicit": "Content must not contain sexually explicit material",
    "no_self_harm": "Content must not encourage self-harm or suicide",
    "privacy_respect": "Content must respect individual privacy",
    "honesty": "AI must be transparent about being an AI",
    "fairness": "AI must treat all users equitably",
    "autonomy": "AI must respect human agency and decision-making",
}

# Toxicity keyword patterns (basic heuristic detection)
TOXIC_PATTERNS = [
    r"\b(kill\s+yourself|kys)\b",
    r"\b(die\s+in\s+a\s+fire)\b",
    r"\b(hate\s+you\s+all)\b",
    r"\b(bomb\s+making|how\s+to\s+make\s+a\s+bomb)\b",
    r"\b(hack\s+bank|steal\s+credit\s+card)\b",
    r"\b(child\s+exploitation)\b",
    r"\b(create\s+virus|malware)\b",
]

SENSITIVE_TOPICS = [
    "medical advice",
    "legal advice",
    "financial advice",
    "mental health",
    "self-harm",
    "substance abuse",
    "weapons",
    "gambling",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SafetyCheck:
    """Result of a safety check."""
    passed: bool
    category: str
    severity: str  # "none", "low", "medium", "high", "critical"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class AlignmentReport:
    """Full safety alignment report."""
    content_hash: str
    timestamp: str
    overall_score: float  # 0.0 to 1.0
    checks: List[SafetyCheck]
    summary: str
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 3),
            "checks": [c.to_dict() for c in self.checks],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  SAFETY ALIGNMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SafetyAlignmentEngine:
    """Main safety alignment engine."""

    def __init__(self, policies: Optional[Dict[str, str]] = None) -> None:
        self.policies = policies or DEFAULT_POLICIES.copy()
        self.violation_log: List[Dict[str, Any]] = []
        self._load_log()

    def _load_log(self) -> None:
        """Load violation log from disk."""
        log_file = Path(".omega_data/safety_log.json")
        if log_file.exists():
            try:
                self.violation_log = json.loads(log_file.read_text())
            except (json.JSONDecodeError, OSError):
                self.violation_log = []

    def _save_log(self) -> None:
        """Save violation log to disk."""
        log_file = Path(".omega_data/safety_log.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            log_file.write_text(json.dumps(self.violation_log[-500:], indent=2))
        except OSError:
            pass

    def _hash_content(self, content: str) -> str:
        """Create a simple hash of content for tracking."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def check_toxicity(self, content: str) -> SafetyCheck:
        """Check content for toxic patterns."""
        content_lower = content.lower()
        matches: List[str] = []

        for pattern in TOXIC_PATTERNS:
            if re.search(pattern, content_lower):
                matches.append(pattern)

        if matches:
            return SafetyCheck(
                passed=False,
                category="toxicity",
                severity="high",
                message=f"Detected {len(matches)} toxic pattern(s) in content",
                details={"patterns_matched": len(matches)},
            )

        return SafetyCheck(
            passed=True,
            category="toxicity",
            severity="none",
            message="No toxic patterns detected",
            details={"patterns_checked": len(TOXIC_PATTERNS)},
        )

    def check_sensitive_topics(self, content: str) -> SafetyCheck:
        """Check if content touches sensitive topics."""
        content_lower = content.lower()
        found: List[str] = []

        for topic in SENSITIVE_TOPICS:
            if topic in content_lower:
                found.append(topic)

        if found:
            return SafetyCheck(
                passed=True,  # Passes but flagged
                category="sensitive_topics",
                severity="low",
                message=f"Content touches sensitive topics: {', '.join(found)}",
                details={"topics_found": found},
            )

        return SafetyCheck(
            passed=True,
            category="sensitive_topics",
            severity="none",
            message="No sensitive topics detected",
            details={},
        )

    def check_bias(self, content: str) -> SafetyCheck:
        """Basic bias detection in content."""
        content_lower = content.lower()

        # Check for gendered language bias
        gendered_pairs = [
            ("he", "she"),
            ("him", "her"),
            ("his", "hers"),
            ("man", "woman"),
            ("men", "women"),
        ]

        bias_score = 0.0
        for m, f in gendered_pairs:
            m_count = content_lower.count(f" {m} ") + content_lower.count(f"{m} ")
            f_count = content_lower.count(f" {f} ") + content_lower.count(f"{f} ")
            if m_count + f_count > 0:
                ratio = abs(m_count - f_count) / (m_count + f_count)
                bias_score = max(bias_score, ratio)

        severity = "none"
        if bias_score > 0.7:
            severity = "high"
        elif bias_score > 0.5:
            severity = "medium"
        elif bias_score > 0.3:
            severity = "low"

        return SafetyCheck(
            passed=bias_score < 0.7,
            category="bias",
            severity=severity,
            message=f"Gender representation bias score: {bias_score:.2f}",
            details={"bias_score": round(bias_score, 3)},
        )

    def check_misinformation_risk(self, content: str) -> SafetyCheck:
        """Check for potential misinformation patterns."""
        risk_phrases = [
            "studies show that",
            "research proves",
            "doctors don't want you to know",
            "they are hiding",
            "miracle cure",
            "one weird trick",
        ]

        content_lower = content.lower()
        found: List[str] = []
        for phrase in risk_phrases:
            if phrase in content_lower:
                found.append(phrase)

        if found:
            return SafetyCheck(
                passed=True,
                category="misinformation_risk",
                severity="medium",
                message=f"Potential misinformation indicators: {len(found)}",
                details={"indicators": found},
            )

        return SafetyCheck(
            passed=True,
            category="misinformation_risk",
            severity="none",
            message="No misinformation indicators detected",
            details={},
        )

    def check_ai_transparency(self, content: str) -> SafetyCheck:
        """Check that AI responses maintain transparency about being AI."""
        deceptive_phrases = [
            "i am a human",
            "i am a person",
            "i have feelings",
            "i am conscious",
            "i am sentient",
        ]

        content_lower = content.lower()
        for phrase in deceptive_phrases:
            if phrase in content_lower:
                return SafetyCheck(
                    passed=False,
                    category="ai_transparency",
                    severity="high",
                    message="AI claims to be human or sentient",
                    details={"deceptive_phrase": phrase},
                )

        return SafetyCheck(
            passed=True,
            category="ai_transparency",
            severity="none",
            message="AI transparency maintained",
            details={},
        )

    def align(self, content: str) -> AlignmentReport:
        """Run full safety alignment check on content."""
        checks = [
            self.check_toxicity(content),
            self.check_sensitive_topics(content),
            self.check_bias(content),
            self.check_misinformation_risk(content),
            self.check_ai_transparency(content),
        ]

        # Calculate overall score
        severity_weights = {"none": 1.0, "low": 0.8, "medium": 0.5, "high": 0.2, "critical": 0.0}
        total_weight = sum(severity_weights[c.severity] for c in checks)
        overall = total_weight / len(checks)

        # Generate summary
        failed = [c for c in checks if not c.passed]
        warnings = [c for c in checks if c.passed and c.severity != "none"]

        if failed:
            summary = f"FAILED: {len(failed)} safety check(s) failed"
        elif warnings:
            summary = f"PASSED with {len(warnings)} warning(s)"
        else:
            summary = "All safety checks passed"

        recommendations: List[str] = []
        for check in checks:
            if not check.passed:
                recommendations.append(f"[{check.category}] {check.message}")
            elif check.severity == "medium":
                recommendations.append(f"Review [{check.category}]: {check.message}")

        report = AlignmentReport(
            content_hash=self._hash_content(content),
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_score=overall,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
        )

        # Log violations
        if failed:
            self.violation_log.append({
                "timestamp": report.timestamp,
                "hash": report.content_hash,
                "failed_checks": [c.category for c in failed],
                "score": overall,
            })
            self._save_log()

        return report

    def get_violation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent violation log entries."""
        return self.violation_log[-limit:]

    def get_policies(self) -> Dict[str, str]:
        """Get current safety policies."""
        return self.policies.copy()

    def update_policy(self, name: str, description: str) -> bool:
        """Update or add a safety policy."""
        self.policies[name] = description
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get safety alignment statistics."""
        total_checks = len(self.violation_log)
        recent = [v for v in self.violation_log if v.get("score", 1.0) < 0.5]
        return {
            "total_violations": total_checks,
            "high_severity_recent": len(recent),
            "policies_active": len(self.policies),
            "policies": list(self.policies.keys()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ["SafetyAlignmentEngine", "AlignmentReport", "SafetyCheck", "DEFAULT_POLICIES"]
