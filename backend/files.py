"""File Upload & Processing Module

Handles extraction, summarization, and Q&A over uploaded files including
PDFs, images, text files, Word documents, and more.

Classes:
    FileProcessor: Secure file handling with AI-powered analysis.

Typical usage:
    from backend.files import FileProcessor
    fp = FileProcessor()
    text = fp.process_file("document.pdf")
    summary = fp.summarize_file("document.pdf")
    answer = fp.answer_from_file("document.pdf", "What is the main topic?")
"""

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from backend.ai_engine import AIEngine
from backend.config import load_backend_config

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".py",
    ".js",
    ".html",
    ".css",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
}

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "text/x-python",
    "application/javascript",
    "text/html",
    "text/css",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/svg+xml",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# ── File Processor ─────────────────────────────────────────────────────


class FileProcessor:
    """Secure file processor with extraction and AI-powered analysis.

    Handles multiple file types with validation, extracts text content,
    generates summaries, and answers questions using RAG-style retrieval.

    Attributes:
        config: Backend configuration dictionary.
        upload_dir: Directory for storing uploaded files.
        ai_engine: AIEngine for vision and text analysis.
        max_size: Maximum allowed file size in bytes.

    Example:
        >>> fp = FileProcessor()
        >>> fp.validate_file("doc.pdf")
        True
        >>> text = fp.process_file("doc.pdf")
        >>> summary = fp.summarize_file("doc.pdf")
    """

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        """Initialize the file processor.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.upload_dir = Path(str(self.config.get("upload_dir", "./uploads")))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.ai_engine = AIEngine(self.config)
        self.max_size = int(self.config.get("max_upload_size", MAX_FILE_SIZE))
        logger.info("FileProcessor ready, upload_dir=%s", self.upload_dir)

    # ── Validation ──────────────────────────────────────────────────────

    def validate_file(self, filepath: str) -> bool:
        """Validate a file for security (extension + MIME + size).

        Args:
            filepath: Path to the file to validate.

        Returns:
            True if the file passes all checks.

        Raises:
            ValueError: If validation fails with a descriptive message.
        """
        path = Path(filepath)

        # Check existence
        if not path.exists():
            raise ValueError(f"File not found: {filepath}")

        # Check size
        size = path.stat().st_size
        if size > self.max_size:
            raise ValueError(
                f"File too large: {size} bytes (max {self.max_size})"
            )

        # Check extension
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
            )

        # Check MIME type
        mime, _ = mimetypes.guess_type(str(path))
        if mime and mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported MIME type: {mime}")

        return True

    # ── Extraction ──────────────────────────────────────────────────────

    def process_file(self, filepath: str) -> str:
        """Extract text content from a file.

        Automatically detects file type and uses the appropriate extractor.

        Args:
            filepath: Path to the file.

        Returns:
            Extracted text content as a string.

        Raises:
            ValueError: If file validation fails.
            RuntimeError: If extraction fails.
        """
        self.validate_file(filepath)
        ext = Path(filepath).suffix.lower()

        try:
            if ext == ".pdf":
                return self._extract_pdf(filepath)
            elif ext == ".docx":
                return self._extract_docx(filepath)
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
                return self._extract_image(filepath)
            elif ext == ".svg":
                return self._extract_text(filepath)  # SVG is XML text
            elif ext in (
                ".txt",
                ".md",
                ".csv",
                ".json",
                ".py",
                ".js",
                ".html",
                ".css",
            ):
                return self._extract_text(filepath)
            else:
                raise ValueError(f"No extractor for: {ext}")
        except Exception as exc:
            logger.error("Extraction error for %s: %s", filepath, exc)
            raise RuntimeError(f"Failed to extract {filepath}: {exc}") from exc

    def summarize_file(self, filepath: str) -> str:
        """Generate an AI-powered summary of a file's content.

        Args:
            filepath: Path to the file.

        Returns:
            Summary text generated by the AI.
        """
        try:
            text = self.process_file(filepath)
            # Truncate if too long
            truncated = text[:12000] if len(text) > 12000 else text
            prompt = (
                f"Please provide a comprehensive summary of the following content. "
                f"Include key points, main topics, and important details:\n\n{truncated}"
            )
            return self.ai_engine.chat_sync(
                [{"role": "user", "content": prompt}],
                mode="expert",
            )
        except Exception as exc:
            logger.error("Summarize error: %s", exc)
            return f"[Summarization Error: {exc}]"

    def answer_from_file(
        self, filepath: str, question: str
    ) -> str:
        """Answer a question based on file content (RAG-style).

        Extracts file content and uses AI to answer the specific question.

        Args:
            filepath: Path to the file.
            question: Question to answer about the file.

        Returns:
            AI-generated answer based on file content.
        """
        try:
            text = self.process_file(filepath)
            # Truncate long documents
            truncated = text[:12000] if len(text) > 12000 else text
            prompt = (
                f"Based on the following document content, answer this question:\n\n"
                f"Question: {question}\n\n"
                f"Document content:\n{truncated}\n\n"
                f"Provide a clear, accurate answer based only on the document. "
                f"If the answer isn't in the document, say so."
            )
            return self.ai_engine.chat_sync(
                [{"role": "user", "content": prompt}],
                mode="expert",
            )
        except Exception as exc:
            logger.error("Answer from file error: %s", exc)
            return f"[Q&A Error: {exc}]"

    def save_upload(self, file_content: bytes, original_filename: str) -> str:
        """Save uploaded file content securely.

        Generates a unique filename to prevent collisions and overwrites.

        Args:
            file_content: Raw bytes of the uploaded file.
            original_filename: Original filename from the upload.

        Returns:
            Full path to the saved file.

        Raises:
            ValueError: If file is too large or has invalid extension.
        """
        if len(file_content) > self.max_size:
            raise ValueError(
                f"File too large: {len(file_content)} bytes (max {self.max_size})"
            )

        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = self.upload_dir / unique_name
        dest.write_bytes(file_content)
        logger.info("Saved upload: %s -> %s", original_filename, dest)
        return str(dest)

    # ── Private Extractors ──────────────────────────────────────────────

    @staticmethod
    def _extract_pdf(filepath: str) -> str:
        """Extract text from a PDF file."""
        text_parts: List[str] = []

        # Try pdfplumber first (better quality)
        try:
            import pdfplumber

            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            logger.debug("pdfplumber not installed, trying PyPDF2")

        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(filepath)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            raise RuntimeError(
                "No PDF library available. Install pdfplumber or PyPDF2."
            )

    @staticmethod
    def _extract_docx(filepath: str) -> str:
        """Extract text from a Word document."""
        try:
            from docx import Document

            doc = Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except ImportError:
            raise RuntimeError(
                "python-docx not installed. Run: pip install python-docx"
            )

    def _extract_image(self, filepath: str) -> str:
        """Describe an image using GPT-4o vision."""
        return self.ai_engine.vision(
            filepath,
            prompt=(
                "Describe this image in detail. Include all visible text, "
                "objects, people, charts, tables, and any notable elements."
            ),
        )

    @staticmethod
    def _extract_text(filepath: str) -> str:
        """Extract text from a plain text file."""
        path = Path(filepath)
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        raise RuntimeError(f"Could not decode file with any encoding: {filepath}")
