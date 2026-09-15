"""
OMEGA-LUQI Real-Time Terminal Streaming Channel
Low-latency WebSocket pipe: student browser <-> isolated Docker sandbox.

Kept as a standalone module so the Docker dependency stays lazy - importing
this file never touches the Docker daemon, only the websocket route does.
"""
import json
import asyncio
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Commands that would damage the shared host or break out of the sandbox
FORBIDDEN_PATTERNS = [
    "rm -rf /", ":(){ :|:& };:", "mkfs", "dd if=", "shutdown", "reboot",
    "chmod 777 /", "/etc/passwd", "/etc/shadow", "curl ", "wget ",
    "nc ", "ncat ", "/dev/tcp", "fork", "while true",
]

_sandbox_manager = None


def get_sandbox_manager():
    """Lazy singleton - connects to the Docker daemon on first terminal use only."""
    global _sandbox_manager
    if _sandbox_manager is None:
        from .docker_sandbox import LabSandboxManager
        _sandbox_manager = LabSandboxManager()
    return _sandbox_manager


class TerminalConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.last_activity: Dict[str, float] = {}  # reaper: touched per packet

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.last_activity[session_id] = __import__("time").time()

    def touch(self, session_id: str) -> None:
        self.last_activity[session_id] = __import__("time").time()

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        self.last_activity.pop(session_id, None)

    async def stream_output(self, session_id: str, payload: str, node: str = "stdout"):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json({"stream_node": node, "content": payload})


terminal_manager = TerminalConnectionManager()


@router.websocket("/v1/labs/terminal/{student_id}/{container_name}")
async def live_terminal_stream(websocket: WebSocket, student_id: str, container_name: str):
    """
    Blocking docker exec runs in a thread pool so one slow container
    never blocks the event loop for other students.
    """
    session_id = f"{student_id}-{container_name}"
    await terminal_manager.connect(session_id, websocket)

    await websocket.send_json({
        "status": "connected",
        "message": f"OMEGA-LUQI Secure Terminal. Connected to sandbox: {container_name}",
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await terminal_manager.stream_output(session_id, "Invalid payload: expected JSON.", "stderr")
                continue

            student_command = str(payload.get("command", "")).strip()
            if not student_command:
                continue
            terminal_manager.touch(session_id)  # reaper: session is alive

            lowered = student_command.lower()
            if any(pattern in lowered for pattern in FORBIDDEN_PATTERNS):
                await terminal_manager.stream_output(
                    session_id,
                    "Execution Denied: Command violates core security policies.",
                    "stderr",
                )
                continue

            try:
                manager = get_sandbox_manager()
            except Exception as engine_err:
                # Honest failure - NEVER fabricate command output
                await terminal_manager.stream_output(
                    session_id,
                    f"Sandbox engine unavailable on this node ({engine_err}). Contact your administrator.",
                    "stderr",
                )
                continue

            execution_output = await asyncio.to_thread(
                manager.execute_student_command, container_name, student_command
            )
            await terminal_manager.stream_output(session_id, execution_output)

    except WebSocketDisconnect:
        terminal_manager.disconnect(session_id)
        print(f"[OMEGA-LUQI Terminal] Session {session_id} disconnected safely.")
