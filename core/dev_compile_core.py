"""
OMEGA-LUQI Sandbox Compile Core - pure functions.

The compile EXECUTOR needs a Docker daemon (CI/dev machines). These helpers
are deliberately side-effect free so the pipeline logic is fully unit-testable
without one. The route fails closed with 503 when Docker is unavailable.
"""
from typing import Dict, List, Tuple

# stack -> (container image, compile command template)
COMPILE_PROFILES = {
    "python-fastapi": ("luqi-lab-base:latest", "python -m py_compile {files}"),
    "python": ("luqi-lab-base:latest", "python -m py_compile {files}"),
}


def plan_compile(stack: str, files: Dict[str, str]) -> Tuple[str, str, List[str]]:
    """Resolve (image, command, file list) for a stack. Raises ValueError."""
    if stack not in COMPILE_PROFILES:
        raise ValueError(f"Unsupported stack '{stack}'. Supported: {sorted(COMPILE_PROFILES)}")
    if not files:
        raise ValueError("No source files supplied for compilation.")
    image, template = COMPILE_PROFILES[stack]
    file_list = sorted(files.keys())
    return image, template.format(files=" ".join(f"'/lab/{f}'" for f in file_list)), file_list


def analyze_compile_output(output: str) -> Dict[str, List[str]]:
    """Classify py_compile-style output into errors vs noise."""
    errors, notes = [], []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "Error" in stripped or "SyntaxError" in stripped or "Traceback" in stripped:
            errors.append(stripped)
        else:
            notes.append(stripped)
    return {"errors": errors, "notes": notes, "ok": not errors}
