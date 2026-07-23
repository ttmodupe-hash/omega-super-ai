#!/usr/bin/env python3
"""Reassemble api_server.py and omega_ai.py from their parts.

Run this script from the repo root:
    python reassemble_v37.py

This reconstructs the two large files that could not be pushed
as single files due to MCP content-size limits.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "api_server.py": ["api_server.part1.py", "api_server.part2.py"],
    "omega_ai.py":   ["omega_ai.part1.py",   "omega_ai.part2.py"],
}


def reassemble(target_name, parts):
    target_path = os.path.join(REPO_ROOT, target_name)
    content_parts = []
    
    for part_name in parts:
        part_path = os.path.join(REPO_ROOT, part_name)
        if not os.path.exists(part_path):
            print(f"ERROR: Missing part file: {part_name}")
            return False
        with open(part_path, 'r', encoding='utf-8') as f:
            content_parts.append(f.read())
    
    full_content = ''.join(content_parts)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    size_kb = len(full_content.encode('utf-8')) / 1024
    print(f"  Reassembled {target_name}: {size_kb:.1f} KB ({len(full_content):,} chars)")
    return True


def main():
    print("=" * 60)
    print("Omega AI v3.7.0 -- File Reassembler")
    print("=" * 60)
    
    all_ok = True
    for target_name, parts in FILES.items():
        if reassemble(target_name, parts):
            # Verify basic sanity
            with open(os.path.join(REPO_ROOT, target_name), 'r') as f:
                content = f.read()
            if content.count('\n') < 10:
                print(f"  WARNING: {target_name} looks suspiciously small!")
                all_ok = False
        else:
            all_ok = False
    
    print("-" * 60)
    if all_ok:
        print("SUCCESS: All files reassembled correctly.")
        print("You can now delete the .part*.py files if desired.")
        return 0
    else:
        print("FAILED: Some files could not be reassembled.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
