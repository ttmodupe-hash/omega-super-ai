#!/usr/bin/env python3
"""
Luqi AI - Reconstruct it_security_training.py from base64 chunks
===============================================================
Run this after pulling the chunks_security/ folder from GitHub.

Usage (Windows PowerShell):
    py reconstruct_security.py

Usage (Linux/Mac):
    python3 reconstruct_security.py
"""

import os
import json
import base64
from pathlib import Path

CHUNKS_DIR = Path("chunks_security")
OUTPUT_FILE = Path("backend") / "it_security_training.py"
MANIFEST_FILE = CHUNKS_DIR / "manifest.json"


def reconstruct():
    print("=" * 60)
    print("Reconstructing it_security_training.py from chunks")
    print("=" * 60)

    # Read manifest
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_FILE}")
        print("Make sure you pulled the chunks_security/ folder from GitHub.")
        return False

    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)

    total_chunks = manifest["total_chunks"]
    print(f"\nExpected chunks: {total_chunks}")

    # Read and combine all chunks
    b64_parts = []
    for i, chunk_name in enumerate(manifest["chunks"]):
        chunk_path = CHUNKS_DIR / chunk_name
        if not chunk_path.exists():
            print(f"  MISSING: {chunk_name}")
            return False
        with open(chunk_path) as f:
            part = f.read()
        b64_parts.append(part)
        print(f"  [OK] {chunk_name} ({len(part)} chars)")

    # Combine and decode
    print("\nDecoding base64...")
    full_b64 = "".join(b64_parts)
    decoded = base64.b64decode(full_b64)

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    # Write output
    with open(OUTPUT_FILE, "wb") as f:
        f.write(decoded)

    print(f"\nSUCCESS!")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Size: {len(decoded)/1024:.1f} KB")
    print(f"  Lines: {decoded.decode('utf-8').count(chr(10))}")

    # Verify the file
    print("\nVerifying...")
    try:
        with open(OUTPUT_FILE) as f:
            first_line = f.readline()
            print(f"  First line: {first_line.strip()[:80]}")
        print("  File is valid UTF-8 Python.")
    except Exception as e:
        print(f"  WARNING: Verification error: {e}")

    return True


if __name__ == "__main__":
    success = reconstruct()
    exit(0 if success else 1)
