#!/usr/bin/env python3
"""
Omega Super AI v10 — Launcher Script

Run with: py -3.11 omega.py

This launcher bootstraps the Omega Super AI system by delegating
to the omega package's main CLI module.
"""

import sys
from pathlib import Path

# Ensure the project root is on PYTHONPATH so 'omega' package resolves
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from omega.omega import main

if __name__ == "__main__":
    main()
