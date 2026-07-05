"""Prometheus engine configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# Core Scheduling
# =============================================================================

SRE_CHECK_INTERVAL_HOURS: int = 24  # How often to run self-review
SRE_MAX_RETRIES: int = 3  # Max retries for failed operations
SRE_RETRY_DELAY_SECONDS: int = 5  # Delay between retries

# =============================================================================
# Competitors to Monitor
# =============================================================================

DEFAULT_COMPETITORS: list[str] = [
    "openai/gpt-4",
    "anthropic/claude-3-5-sonnet",
    "google/gemini-1.5-pro",
    "meta/llama-3.1",
    "deepseek/deepseek-v3",
]

# =============================================================================
# Benchmarking
# =============================================================================

BENCHMARK_TIMEOUT_SECONDS: int = 300  # 5 minutes per benchmark
BENCHMARK_TEMPERATURE: float = 0.3  # Low temperature for consistency

# =============================================================================
# Improvement Thresholds
# =============================================================================

IMPROVEMENT_SCORE_THRESHOLD: float = 0.10  # 10% improvement required
MAX_CANDIDATE_FEATURES: int = 5  # Max features to generate per cycle
FEATURE_COMPLEXITY_LIMIT: str = "medium"  # small|medium|large

# =============================================================================
# API Keys (fallback to env vars)
# =============================================================================

@dataclass
class PrometheusConfig:
    """Configuration for the Prometheus engine."""

    # Scheduling
    check_interval_hours: int = SRE_CHECK_INTERVAL_HOURS
    max_retries: int = SRE_MAX_RETRIES
    retry_delay_seconds: int = SRE_RETRY_DELAY_SECONDS

    # Competitors
    competitors: list[str] = field(default_factory=lambda: DEFAULT_COMPETITORS.copy())

    # Benchmarking
    benchmark_timeout: int = BENCHMARK_TIMEOUT_SECONDS
    benchmark_temperature: float = BENCHMARK_TEMPERATURE

    # Improvement
    improvement_threshold: float = IMPROVEMENT_SCORE_THRESHOLD
    max_candidate_features: int = MAX_CANDIDATE_FEATURES
    feature_complexity_limit: str = FEATURE_COMPLEXITY_LIMIT

    # API keys
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))

    # Paths
    db_path: str = "./prometheus.db"
    log_path: str = "./prometheus.log"

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "check_interval_hours": self.check_interval_hours,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "competitors": self.competitors,
            "benchmark_timeout": self.benchmark_timeout,
            "benchmark_temperature": self.benchmark_temperature,
            "improvement_threshold": self.improvement_threshold,
            "max_candidate_features": self.max_candidate_features,
            "feature_complexity_limit": self.feature_complexity_limit,
            "db_path": self.db_path,
            "log_path": self.log_path,
        }

    @classmethod
    def from_env(cls) -> "PrometheusConfig":
        """Load configuration from environment variables."""
        config = cls()
        if hours := os.environ.get("PROMETHEUS_CHECK_INTERVAL_HOURS"):
            config.check_interval_hours = int(hours)
        if threshold := os.environ.get("PROMETHEUS_IMPROVEMENT_THRESHOLD"):
            config.improvement_threshold = float(threshold)
        if max_features := os.environ.get("PROMETHEUS_MAX_CANDIDATE_FEATURES"):
            config.max_candidate_features = int(max_features)
        if db_path := os.environ.get("PROMETHEUS_DB_PATH"):
            config.db_path = db_path
        return config
