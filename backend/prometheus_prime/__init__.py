#!/usr/bin/env python3
"""
Prometheus Prime — Auto-Implementation Engine for Luqi AI

A complete system that doesn't just recommend improvements, but actually
implements them.  Comprises six subsystems:

1. **Code Generation** (:mod:`code_generator`) — AI-powered code generation
   with built-in review and safe integration.

2. **Safe Experimentation** (:mod:`safe_experiment`) — Isolated experiment
   environments with canary deployments and automatic rollback.

3. **Test Harness** (:mod:`test_harness`) — Automated unit, integration,
   regression testing and performance benchmarking.

4. **Deployment Manager** (:mod:`deployment_manager`) — Git-based safe
   deployments with canary, blue-green, and immediate strategies.

5. **Self-Repair** (:mod:`self_repair`) — Continuous health monitoring,
   anomaly detection, and automatic remediation.

6. **CLI** (:mod:`prime_cli`) — Unified command-line interface.

Usage::

    from prometheus_prime import CodeGenerator, SafeExperiment

    cg = CodeGenerator()
    spec = cg.generate_feature_spec("Add sentiment analysis")
    code = cg.generate_code(spec)

Quick start from the command line::

    $ python -m prometheus_prime.prime_cli status
    $ python -m prometheus_prime.prime_cli generate "Add emotion detection"
    $ python -m prometheus_prime.prime_cli experiment
    $ python -m prometheus_prime.prime_cli deploy --strategy canary
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Luqi AI Engineering"

# Re-export primary public APIs for convenience
from prometheus_prime.code_generator import (
    CodeGenerator,
    CodeReviewResult,
    FeatureSpec,
    IntegrationResult,
    quick_generate,
)
from prometheus_prime.safe_experiment import (
    SafeExperiment,
    ExperimentResults,
    CanaryStatus,
    Sandbox,
)
from prometheus_prime.test_harness import (
    TestHarness,
    TestResults,
    BenchmarkMetrics,
)
from prometheus_prime.deployment_manager import (
    DeploymentManager,
    DeploymentStatus,
    DeploymentRecord,
)
from prometheus_prime.self_repair import (
    SelfRepair,
    HealthStatus,
    Anomaly,
    RepairAction,
)

__all__ = [
    # Version
    "__version__",
    # Code generation
    "CodeGenerator",
    "CodeReviewResult",
    "FeatureSpec",
    "IntegrationResult",
    "quick_generate",
    # Safe experimentation
    "SafeExperiment",
    "ExperimentResults",
    "CanaryStatus",
    "Sandbox",
    # Test harness
    "TestHarness",
    "TestResults",
    "BenchmarkMetrics",
    # Deployment
    "DeploymentManager",
    "DeploymentStatus",
    "DeploymentRecord",
    # Self-repair
    "SelfRepair",
    "HealthStatus",
    "Anomaly",
    "RepairAction",
]
