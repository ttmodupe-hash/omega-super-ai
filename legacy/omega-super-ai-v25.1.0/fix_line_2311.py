#!/usr/bin/env python3
"""Fix the unterminated string at line 2311 of it_security_training.py."""

import os

def fix():
    filepath = os.path.join(os.path.dirname(__file__), "backend", "it_security_training.py")
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Find the broken line
    fixed = False
    for i, line in enumerate(lines):
        # Look for the broken pattern: "Check for unusual section names like .vm
        # (missing closing quote and rest of string)
        if '"Check for unusual section names like .vm' in line and '.vmp0' not in line:
            # This is the broken line - replace with complete string
            lines[i] = '                    "Check for unusual section names like .vmp0, .upx",\n'
            print(f"  Fixed broken string at line {i+1}")
            fixed = True
            break
        # Also check for any line that has an unterminated string with .vm
        elif line.strip().startswith('"Check for unusual section names like .vm') and not line.rstrip().endswith('",'):
            lines[i] = '                    "Check for unusual section names like .vmp0, .upx",\n'
            print(f"  Fixed broken string at line {i+1}")
            fixed = True
            break
    
    if not fixed:
        # Nuclear option: search for any line containing the partial string
        for i, line in enumerate(lines):
            if 'unusual section names like' in line and '.vm' in line and '.vmp0' not in line:
                lines[i] = '                    "Check for unusual section names like .vmp0, .upx",\n'
                print(f"  Fixed broken string at line {i+1}")
                fixed = True
                break
    
    if not fixed:
        print("ERROR: Could not find the broken string. Manual inspection needed.")
        # Show context around line 2311
        if len(lines) >= 2311:
            print(f"\nContext around line 2311:")
            for j in range(max(0, 2308), min(len(lines), 2315)):
                print(f"  Line {j+1}: {lines[j].rstrip()}")
        return False
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    # Verify
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"\nOK: File compiles successfully after fix")
        return True
    except py_compile.PyCompileError as e:
        print(f"\nStill has errors: {e}")
        return False

if __name__ == "__main__":
    fix()
