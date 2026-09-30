"""packages/ — ARCH-RESTRUCTURE-1: unified monorepo facade over engine/core.

Strangler-fig migration: these packages wire REAL engine/core modules
(no stubs, no parallel reimplementation). Physical module moves happen in
later CI-gated phases. See plan.md ARCH-RESTRUCTURE-1.
"""
