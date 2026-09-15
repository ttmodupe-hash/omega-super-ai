"""
Luqi-AI Voice Integration Module
Streams agent text responses as compressed audio chunks.
Point api_url at ElevenLabs or your own TTS service hosting the
licensed Madiba / Nomzamo foundational voice models.
"""
import os
import requests
from typing import Generator


class LuqiVoiceService:
    def __init__(self):
        self.api_url = "https://api.elevenlabs.io/v1/text-to-speech"
        self.headers = {
            "Content-Type": "application/json",
            "xi-api-key": os.getenv("XI_API_KEY", "LOCAL_VOICE_SERVICE_TOKEN_GOES_HERE"),
        }
        self.voice_matrix = {
            "madiba_male": "nelson_mandela_clone_id",
            "nomzamo_female": "winnie_mandela_clone_id",
            "nairobi_professional": "east_african_swahili_english_id",
            "lagos_expressive": "west_african_nigerian_english_id",
        }

    def stream_voice_response(
        self, text_payload: str, selected_voice: str = "madiba_male"
    ) -> Generator[bytes, None, None]:
        voice_id = self.voice_matrix.get(selected_voice, self.voice_matrix["madiba_male"])
        endpoint = f"{self.api_url}/{voice_id}/stream"

        payload = {
            "text": text_payload,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.85, "similarity_boost": 0.75},
        }

        response = requests.post(endpoint, json=payload, headers=self.headers, stream=True, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(f"Voice Streaming Endpoint Failure: Code {response.status_code}")

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk
