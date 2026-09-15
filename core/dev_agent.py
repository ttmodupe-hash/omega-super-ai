"""
OMEGA-LUQI Ground-Up Software Engineering Matrix

Generates production-grade application codebases from raw requirements using
Moonshot's 1M-token context, forcing JSON output (architecture manifest +
source files) at temperature 0.1 for architectural stability.

Phase 2 (your engineers): pipe generated files into the Docker sandbox
(luqi-lab-base) for automated compile + test passes inside an isolated container.
"""
import os
import asyncio
from typing import Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .dev_compile_core import plan_compile, analyze_compile_output

router = APIRouter()

_docker_client = None


def _get_docker():
    """Lazy Docker client - never connects at import or route-registration time."""
    global _docker_client
    if _docker_client is None:
        import docker
        _docker_client = docker.from_env()
    return _docker_client


SYSTEM_INSTRUCTION = (
    "You are the Master Luqi-AI Principal Software Engineer Swarm. Your task is to develop "
    "production-grade code from the absolute ground up. Even if no baseline documentation "
    "exists for this concept globally, you must use advanced programmatic engineering first "
    "principles to design the file schemas, architectural models, and edge-case security "
    "boundaries. Output your response strictly in a clean, valid JSON structure containing "
    "two keys: 'project_architecture_manifest' and 'complete_source_code_files'."
)


class DevBuildRequest(BaseModel):
    project_requirements: str
    target_stack: str = "python-fastapi"


def _call_dev_engine(requirements: str, stack: str) -> dict:
    """Multipolar route: codegen prefers Claude, falls back Gemini -> Kimi.
    Runs via the route's thread-pool offload (no running loop here), so a
    fresh event loop drives the async router. Shape preserved for the API."""
    from .model_router import route_chat
    from .pii_scrub import scrub_pii
    import asyncio as _asyncio
    result = _asyncio.new_event_loop().run_until_complete(
        route_chat("codegen", SYSTEM_INSTRUCTION,
                   f"Target Stack: {stack}. Build requirements: {scrub_pii(requirements)}",
                   timeout=90))
    return {"choices": [{"message": {"content": result["content"]}}]}


def _routed_dev_build_sync(requirements: str, stack: str) -> dict:
    from .model_router import route_chat, plan_chain
    from .pii_scrub import scrub_pii
    # Sync context (thread pool): run the async router on a fresh loop.
    import asyncio as _asyncio
    result = _asyncio.new_event_loop().run_until_complete(
        route_chat("codegen", SYSTEM_INSTRUCTION,
                   f"Target Stack: {stack}. Build requirements: {scrub_pii(requirements)}",
                   timeout=90))
    return {"choices": [{"message": {"content": result["content"]}}]}


class CompileRequest(BaseModel):
    stack: str = "python-fastapi"
    source_files: Dict[str, str]   # path -> content
    verification: Optional[dict] = None  # optional VerificationSpec (requirement-derived)


@router.post("/v1/agent/dev-compile")
async def compile_in_sandbox(req: CompileRequest):
    """Compile generated code inside an isolated luqi-lab-base container.

    Fail-closed: no Docker daemon -> 503 (never fake a compile result).
    Files are written via base64 to avoid shell-quoting breakage.
    """
    import base64
    try:
        image, command, _ = plan_compile(req.stack, req.source_files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        client = _get_docker()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sandbox engine unavailable: {e}")

    name = f"luqi-compile-{os.urandom(4).hex()}"
    container = None
    try:
        container = client.containers.run(
            image=image, name=name, command="sleep 300", detach=True,
            mem_limit="256m", nano_cpus=250000000, cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
        )
        for path, content in req.source_files.items():
            b64 = base64.b64encode(content.encode()).decode()
            container.exec_run(
                f"/bin/sh -c 'mkdir -p /lab/$(dirname {path}) && echo {b64} | base64 -d > /lab/{path}'",
                user="luqistudent",
            )
        exit_code, output = container.exec_run(f"/bin/sh -c '{command}'", user="luqistudent")
        analysis = analyze_compile_output(output.decode("utf-8", errors="replace"))
        compiled_ok = exit_code == 0 and analysis["ok"]

        # Executable verification (the post's insight: green build != done).
        # Status is honest: without a spec, the build is UNVERIFIED.
        verification_report = None
        if req.verification:
            from .dev_verify import VerificationSpec, run_verification
            try:
                spec = VerificationSpec(**req.verification)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid verification spec: {e}")
            if spec.cases or spec.negative_cases:
                verification_report = run_verification(container, spec)

        if verification_report is not None:
            status = "verified" if (compiled_ok and verification_report["verified"]) else "failed"
        else:
            status = "success_unverified" if compiled_ok else "failed"
        return {
            "compile_status": status,
            "exit_code": exit_code,
            "analysis": analysis,
            "verification": verification_report or "not_provided - syntax checked only, behavior unverified",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sandbox compile failure: {e}")
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass


@router.post("/v1/agent/dev-build")
async def build_software_from_scratch(req: DevBuildRequest):
    """Ground-up codebase generation. Fail-closed without KIMI_API_KEY."""
    try:
        return await asyncio.to_thread(_call_dev_engine, req.project_requirements, req.target_stack)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Dev Matrix Bridge Failure: {str(e)}")
