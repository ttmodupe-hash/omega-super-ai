#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Surgical Fix for visual_learning.py
Guaranteed to insert list_visual_aids at the correct location.
"""

import os

def fix():
    filepath = os.path.join(os.path.dirname(__file__), "backend", "visual_learning.py")
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Find the line number of "def create_mindmap"
    insert_line = None
    for i, line in enumerate(lines):
        if "def create_mindmap" in line:
            insert_line = i
            break
    
    if insert_line is None:
        print("ERROR: Could not find 'create_mindmap' method")
        return False
    
    # Check if list_visual_aids already exists
    for line in lines:
        if "def list_visual_aids" in line:
            print("list_visual_aids already exists — skipping")
            return True
    
    # New method to insert
    new_method = '''
    # ------------------------------------------------------------------ #
    # Catalogue helpers
    # ------------------------------------------------------------------ #

    def list_visual_aids(self, category=None):
        """Return catalogue of built-in visual learning aids."""
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

'''
    
    # Insert before create_mindmap
    lines.insert(insert_line, new_method)
    
    # Also fix create_flowchart to accept string lists
    for i, line in enumerate(lines):
        if "decisions = decisions or []" in line:
            # Insert string conversion after this line
            indent = "        "
            lines.insert(i + 1, f"\n{indent}# Convert list[str] to list[dict] for convenience\n")
            lines.insert(i + 2, f"{indent}if steps and isinstance(steps, list) and len(steps) > 0 and isinstance(steps[0], str):\n")
            lines.insert(i + 3, f"{indent}    steps = [{{\"text\": s, \"shape\": \"process\"}} for s in steps]\n")
            print(f"  Fixed: create_flowchart string list conversion at line {i+1}")
            break
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    # Verify
    import py_compile
    py_compile.compile(filepath, doraise=True)
    
    print(f"OK: Surgical fix applied to {filepath}")
    print(f"  - list_visual_aids inserted before create_mindmap")
    print(f"  - create_flowchart now accepts list[str]")
    print("\nRESTART the server: py -3.11 -m uvicorn backend.router:app --reload")
    return True

if __name__ == "__main__":
    fix()
