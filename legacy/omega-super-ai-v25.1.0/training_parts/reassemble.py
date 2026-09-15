#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — Chunk Reassembler
=====================================
Reassembles part files from chunks pushed to GitHub.

Usage (Windows):
    cd training_parts
    py reassemble.py

Usage (Linux/Mac):
    cd training_parts
    python3 reassemble.py
"""
import os
import sys
import glob

BASE = os.path.dirname(os.path.abspath(__file__))

def find_chunks(filename):
    """Find all chunk files for a given filename."""
    pattern = os.path.join(BASE, f"{filename}.chunk*")
    chunks = sorted(glob.glob(pattern))
    chunks = [c for c in chunks if not c.endswith('.manifest')]
    return chunks

def reassemble_file(filename):
    """Reassemble a file from its chunks."""
    chunks = find_chunks(filename)
    if not chunks:
        print(f"  [SKIP] No chunks found for {filename}")
        return False
    
    print(f"\n[+] Reassembling {filename} ({len(chunks)} chunks)...")
    
    parts = []
    for chunk_path in chunks:
        with open(chunk_path, "r", encoding="utf-8") as f:
            parts.append(f.read())
        print(f"  OK: {os.path.basename(chunk_path)}")
    
    full = "".join(parts)
    output_path = os.path.join(BASE, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full)
    
    size_kb = len(full) / 1024
    print(f"  => {filename} ({len(full)} chars, {size_kb:.1f} KB)")
    return True

def verify_file(filename):
    """Verify file compiles as valid Python."""
    filepath = os.path.join(BASE, filename)
    try:
        import py_compile
        py_compile.compile(filepath, doraise=True)
        print(f"  [PASS] Valid Python: {filename}")
        return True
    except py_compile.PyCompileError as e:
        print(f"  [FAIL] Syntax error: {e}")
        return False

def main():
    print("=" * 60)
    print("Luqi AI v24.4.0 — Reassemble Part Files from Chunks")
    print("=" * 60)
    
    files = [
        "it_security_training_part1.py",
        "it_security_training_part2.py",
        "it_security_training_part3.py",
        "it_security_training_part4.py",
        "digital_wellness_part1.py",
        "digital_wellness_part2.py",
    ]
    
    all_ok = True
    for fname in files:
        if reassemble_file(fname):
            all_ok &= verify_file(fname)
        else:
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("SUCCESS! All files reassembled and verified.")
        print("\nNext step: Run 'py merge_all.py' to merge into backend modules")
    else:
        print("Some files failed. Check output above.")
    print("=" * 60)
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
