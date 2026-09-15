#!/usr/bin/env python3
"""Diagnose visual_learning.py patch status."""

import os

filepath = os.path.join(os.path.dirname(__file__), "backend", "visual_learning.py")

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

print(f"File size: {len(content)} bytes")
print(f"Has list_visual_aids: {'list_visual_aids' in content}")
print(f"Has flowchart string conversion: {'isinstance(steps[0], str)' in content}")

# Find the class definition
lines = content.split("\n")
for i, line in enumerate(lines):
    if "def list_visual_aids" in line:
        print(f"\nlist_visual_aids at line {i+1}")
    if "def create_mindmap" in line:
        print(f"create_mindmap at line {i+1}")
    if "def create_flowchart" in line:
        print(f"create_flowchart at line {i+1}")
