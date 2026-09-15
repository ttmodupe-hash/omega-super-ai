"""
OMEGA-LUQI Classroom Mesh Signaling Relay

Transient SDP/ICE relay for the WebRTC classroom mesh. Each POST queues one
signal; the next GET for the room pops the oldest (simple queue, no auth -
signals are ephemeral handshake data valid for seconds).

Fully offline classrooms use mesh.js ManualSignalingTransport instead.
"""
import threading
from fastapi import APIRouter

router = APIRouter(prefix="/v1/mesh", tags=["Classroom Mesh Relay"])

_rooms: dict = {}
_lock = threading.Lock()
_MAX_QUEUE = 50


@router.post("/signal/{room_id}")
async def post_mesh_signal(room_id: str, signal: dict):
    with _lock:
        queue = _rooms.setdefault(room_id, [])
        if len(queue) >= _MAX_QUEUE:
            queue.pop(0)  # drop oldest under burst
        queue.append(signal)
    return {"queued": True}


@router.get("/signal/{room_id}")
async def get_mesh_signal(room_id: str):
    with _lock:
        queue = _rooms.get(room_id)
        if queue:
            return queue.pop(0)
    return None
