"""
OMEGA-LUQI Voice Playback API

Streams ElevenLabs voice synthesis to the browser as audio/mpeg.
Costs money per character - therefore AUTHENTICATED and fail-closed:
no XI_API_KEY -> 500, unauthenticated -> 401/403.

Frontend: app.js speakWithJarvis() fetches this endpoint and plays the
returned blob through an <audio> element.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .voice_service import LuqiVoiceService

router = APIRouter(tags=["Voice Synthesis"])


class SpeakRequest(BaseModel):
    text: str
    voice: str = "madiba_male"


@router.post("/v1/voice/speak")
async def speak_with_jarvis(
    req: SpeakRequest,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Stream Madiba/Nomzamo voice audio. Fail-closed without XI_API_KEY."""
    if not os.getenv("XI_API_KEY"):
        raise HTTPException(status_code=500, detail="Voice engine unconfigured: XI_API_KEY not defined.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    if len(req.text) > 3000:
        raise HTTPException(status_code=400, detail="Text exceeds 3000-character streaming limit.")

    service = LuqiVoiceService()

    def byte_stream():
        try:
            yield from service.stream_voice_response(req.text, req.voice)
        except Exception as e:
            raise RuntimeError(f"Voice synthesis failed: {e}")

    return StreamingResponse(byte_stream(), media_type="audio/mpeg")
