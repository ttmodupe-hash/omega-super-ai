"""AI Image Generation Module

Provides image creation using OpenAI's DALL-E 3 API with local file storage.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

import requests
from openai import OpenAI

from backend.config import load_backend_config

logger = logging.getLogger(__name__)

VALID_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
VALID_QUALITIES = {"standard", "hd"}


class ImageGenerator:
    """Image generation using OpenAI DALL-E 3."""

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or load_backend_config()
        self.client = OpenAI(api_key=self.config["openai_api_key"])
        self.output_dir = Path(str(self.config.get("upload_dir", "./uploads")))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, size: str = "1024x1024", quality: str = "standard", style: str = "vivid") -> str:
        """Generate an image from a text prompt using DALL-E 3."""
        if size not in VALID_SIZES:
            raise ValueError(f"Invalid size: {size}")
        if quality not in VALID_QUALITIES:
            raise ValueError(f"Invalid quality: {quality}")
        logger.info("Generating image: %s...", prompt[:60])
        response = self.client.images.generate(model="dall-e-3", prompt=prompt, size=size, quality=quality, style=style, n=1, response_format="url")
        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("No image URL returned")
        return self._download_and_save(image_url)

    def _download_and_save(self, url: str) -> str:
        """Download image from URL and save to uploads directory."""
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        filename = f"img_{uuid.uuid4().hex[:12]}.png"
        dest = self.output_dir / filename
        dest.write_bytes(resp.content)
        logger.info("Saved image: %s (%d bytes)", dest, len(resp.content))
        return str(dest.resolve())
