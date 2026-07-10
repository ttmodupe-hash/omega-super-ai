#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Quick Patch Script
Patches visual_learning.py to add missing methods.
"""

import os
import sys

def patch_file():
    filepath = os.path.join(os.path.dirname(__file__), "backend", "visual_learning.py")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "list_visual_aids" in content:
        print("list_visual_aids already exists — no patch needed")
        return
    
    # Find the insertion point — after create_flowchart method
    marker = "        decisions = decisions or []"
    if marker in content:
        # Add string list conversion after decisions = decisions or []
        old = "        decisions = decisions or []\n"
        new = """        decisions = decisions or []

        # Convert list[str] to list[dict] for convenience
        if steps and isinstance(steps, list) and len(steps) > 0 and isinstance(steps[0], str):
            steps = [{"text": s, "shape": "process"} for s in steps]
"""
        content = content.replace(old, new, 1)
        print("  Patched: flowchart string list conversion")
    
    # Add list_visual_aids before create_mindmap
    old2 = "    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #\n    # Mind map\n    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #"
    new2 = """    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    # Catalogue helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #

    def list_visual_aids(self, category=None):
        \"\"\"Return catalogue of built-in visual learning aids.\"\"\"
        aids = [
            {"visual_id": "va-osi-model", "title": "OSI 7-Layer Model", "category": "interactive", "description": "Interactive OSI model -- click each layer for protocols and details.", "endpoint": "/api/visual/osi-model"},
            {"visual_id": "va-tcp-handshake", "title": "TCP 3-Way Handshake", "category": "animation", "description": "Animated TCP handshake with packet flow and state transitions.", "endpoint": "/api/visual/tcp-handshake"},
            {"visual_id": "va-flowchart", "title": "Interactive Flowchart", "category": "flowchart", "description": "Create custom interactive flowcharts for any process.", "endpoint": "/api/visual/flowchart"},
            {"visual_id": "va-mindmap", "title": "Concept Mind Map", "category": "diagram", "description": "Radial mind map with expandable branches.", "endpoint": "/api/visual/mindmap"},
            {"visual_id": "va-process", "title": "Process Diagram", "category": "diagram", "description": "Horizontal or vertical process flow with animated progression.", "endpoint": "/api/visual/process"},
            {"visual_id": "va-quiz", "title": "Interactive Quiz", "category": "interactive", "description": "Multiple choice quiz with visual feedback and score badges.", "endpoint": "/api/visual/quiz"},
            {"visual_id": "va-security-framework", "title": "Security Framework (NIST/ISO)", "category": "diagram", "description": "NIST/ISO 27001 framework with domain breakdown and maturity levels.", "endpoint": "/api/visual/security-framework"},
            {"visual_id": "va-comparison", "title": "Comparison Table", "category": "infographic", "description": "Side-by-side comparison with visual indicators.", "endpoint": "/api/visual/comparison"},
            {"visual_id": "va-timeline", "title": "Event Timeline", "category": "infographic", "description": "Horizontal timeline with clickable event markers.", "endpoint": "/api/visual/timeline"},
        ]
        if category:
            aids = [a for a in aids if a.get("category") == category]
        return aids

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    # Mind map
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #"""
    
    content = content.replace(old2, new2, 1)
    print("  Patched: list_visual_aids added")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Verify
    import py_compile
    py_compile.compile(filepath, doraise=True)
    print(f"\nOK: {filepath} patched and verified")
    print("\nIMPORTANT: Restart the server to pick up changes!")
    print("  1. Press Ctrl+C in the server window")
    print("  2. Run: py -3.11 -m uvicorn backend.router:app --reload")

if __name__ == "__main__":
    patch_file()
