"""AI Image Generation Module

Provides image creation, variation, and editing capabilities using
OpenAI's DALL-E 3 API with local file storage.

Classes:
    ImageGenerator: Generates, varies, and edits images via DALL-E.

Typical usage:
    from backend.images import ImageGenerator
    gen = ImageGenerator()
    path = gen.generate("A futuristic city at sunset")
    variations = gen.generate_variations("image.png", n=3)
"""

import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Optional

import requests
from openai import OpenAI

from backend.config import load_backend_config

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

VALID_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
VALID_QUALITIES = {"standard", "hd"}
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "standard"


class ImageGenerator:
    """Image generation using OpenAI DALL-E 3.

    Creates images from text prompts, generates variations of existing
    images, and performs inpainting edits with mask support.

    Attributes:
        config: Backend configuration dictionary.
        client: OpenAI client for DALL-E API calls.
        output_dir: Directory where generated images are saved.

    Example:
        >>> gen = ImageGenerator()
        >>> path = gen.generate("A serene mountain lake")
        >>> print(path)  # /path/to/uploads/img_abc123.png
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialize the image generator.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.client = OpenAI(api_key=self.config["openai_api_key"])
        self.output_dir = Path(str(self.config.get("upload_dir", "./uploads")))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ImageGenerator initialized")

    # ── Public API ──────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY,
        style: str = "vivid",
    ) -> str:
        """Generate an image from a text prompt using DALL-E 3.

        Args:
            prompt: Text description of the desired image.
            size: Image dimensions ("1024x1024", "1024x1792", "1792x1024").
            quality: "standard" or "hd" for higher quality.
            style: "vivid" or "natural".

        Returns:
            Absolute path to the saved image file.

        Raises:
            ValueError: If size or quality is invalid.
            RuntimeError: If generation fails.
        """
        if size not in VALID_SIZES:
            raise ValueError(
                f"Invalid size: {size}. Use: {VALID_SIZES}"
            )
        if quality not in VALID_QUALITIES:
            raise ValueError(
                f"Invalid quality: {quality}. Use: {VALID_QUALITIES}"
            )

        try:
            logger.info("Generating image: %s...", prompt[:60])
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,  # type: ignore[arg-type]
                quality=quality,  # type: ignore[arg-type]
                style=style,  # type: ignore[arg-type]
                n=1,
                response_format="url",
            )
            image_url = response.data[0].url
            if not image_url:
                raise RuntimeError("No image URL returned from API")
            return self._download_and_save(image_url)
        except Exception as exc:
            logger.error("Image generation error: %s", exc)
            raise RuntimeError(f"Image generation failed: {exc}") from exc

    def generate_variations(
        self,
        image_path: str,
        n: int = 3,
        size: str = DEFAULT_SIZE,
    ) -> List[str]:
        """Generate variations of an existing image using DALL-E 2.

        Args:
            image_path: Path to the source image.
            n: Number of variations (1-10).
            size: Output size ("256x256", "512x512", "1024x1024").

        Returns:
            List of paths to the saved variation images.

        Raises:
            RuntimeError: If variation generation fails.
        """
        valid_var_sizes = {"256x256", "512x512", "1024x1024"}
        if size not in valid_var_sizes:
            raise ValueError(f"Invalid size: {size}. Use: {valid_var_sizes}")

        try:
            path = Path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Convert to PNG if needed (DALL-E requires PNG)
            png_path = self._ensure_png(path)

            logger.info("Generating %d variations of %s", n, image_path)
            with open(png_path, "rb") as f:
                response = self.client.images.create_variation(
                    image=f,
                    n=min(n, 10),
                    size=size,  # type: ignore[arg-type]
                    response_format="url",
                )

            saved: List[str] = []
            for item in response.data:
                if item.url:
                    saved.append(self._download_and_save(item.url))
            return saved
        except Exception as exc:
            logger.error("Variation error: %s", exc)
            raise RuntimeError(f"Variation generation failed: {exc}") from exc

    def edit_image(
        self,
        image_path: str,
        prompt: str,
        mask_path: Optional[str] = None,
        size: str = DEFAULT_SIZE,
    ) -> str:
        """Edit an image using inpainting (DALL-E 2).

        The mask indicates which areas to replace. Transparent areas
        of the mask are replaced; opaque areas are preserved.

        Args:
            image_path: Path to the original image.
            prompt: Description of the desired edit.
            mask_path: Optional path to mask image. If None, edits entire image.
            size: Output size ("256x256", "512x512", "1024x1024").

        Returns:
            Path to the edited image.

        Raises:
            RuntimeError: If editing fails.
        """
        valid_edit_sizes = {"256x256", "512x512", "1024x1024"}
        if size not in valid_edit_sizes:
            raise ValueError(
                f"Invalid size: {size}. Use: {valid_edit_sizes}"
            )

        try:
            img_png = self._ensure_png(Path(image_path))

            logger.info("Editing image: %s", prompt[:60])
            kwargs = {
                "image": open(img_png, "rb"),
                "prompt": prompt,
                "size": size,  # type: ignore[arg-type]
                "n": 1,
                "response_format": "url",
            }
            if mask_path and Path(mask_path).exists():
                mask_png = self._ensure_png(Path(mask_path))
                kwargs["mask"] = open(mask_png, "rb")

            response = self.client.images.edit(**kwargs)

            # Close files
            kwargs["image"].close()
            if "mask" in kwargs:
                kwargs["mask"].close()

            image_url = response.data[0].url
            if not image_url:
                raise RuntimeError("No image URL returned")
            return self._download_and_save(image_url)
        except Exception as exc:
            logger.error("Edit error: %s", exc)
            raise RuntimeError(f"Image editing failed: {exc}") from exc

    # ── Private ─────────────────────────────────────────────────────────

    def _download_and_save(self, url: str) -> str:
        """Download image from URL and save to uploads directory."""
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            filename = f"img_{uuid.uuid4().hex[:12]}.png"
            dest = self.output_dir / filename
            dest.write_bytes(resp.content)
            logger.info("Saved image: %s (%d bytes)", dest, len(resp.content))
            return str(dest.resolve())
        except Exception as exc:
            logger.error("Download error: %s", exc)
            raise RuntimeError(f"Failed to download image: {exc}") from exc

    @staticmethod
    def _ensure_png(path: Path) -> str:
        """Convert image to PNG format if needed.

        DALL-E requires PNG images. Converts JPEG, WebP, etc. to PNG.

        Args:
            path: Path to the image file.

        Returns:
            Path to a PNG version of the image.
        """
        if path.suffix.lower() == ".png":
            return str(path)

        try:
            from PIL import Image

            img = Image.open(path)
            # Convert to RGBA for PNG
            if img.mode in ("P", "L", "RGB"):
                img = img.convert("RGBA")
            png_path = path.with_suffix(".png")
            img.save(png_path, "PNG")
            return str(png_path)
        except ImportError:
            raise RuntimeError(
                "Pillow not installed. Run: pip install Pillow"
            )
