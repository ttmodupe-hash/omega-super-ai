"""File Upload & Processing Module

Handles extraction, summarization, and Q&A over uploaded files including
PDFs, images, text files, Word documents, and more.
"""

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from backend.ai_engine import AIEngine
from backend.config import load_backend_config

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
ALLOWED_MIME_TYPES = {"text/plain", "text/markdown", "text/csv", "application/json", "text/x-python", "application/javascript", "text/html", "text/css", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/svg+xml"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class FileProcessor:
    """Secure file processor with extraction and AI-powered analysis."""

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        self.config = config or load_backend_config()
        self.upload_dir = Path(str(self.config.get("upload_dir", "./uploads")))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.ai_engine = AIEngine(self.config)
        self.max_size = int(self.config.get("max_upload_size", MAX_FILE_SIZE))

    def validate_file(self, filepath: str) -> bool:
        """Validate a file for security."""
        path = Path(filepath)
        if not path.exists():
            raise ValueError(f"File not found: {filepath}")
        if path.stat().st_size > self.max_size:
            raise ValueError(f"File too large")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        mime, _ = mimetypes.guess_type(str(path))
        if mime and mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported MIME type: {mime}")
        return True

    def process_file(self, filepath: str) -> str:
        """Extract text content from a file."""
        self.validate_file(filepath)
        ext = Path(filepath).suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(filepath)
        elif ext == ".docx":
            return self._extract_docx(filepath)
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            return self._extract_image(filepath)
        elif ext in (".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css", ".svg"):
            return self._extract_text(filepath)
        raise ValueError(f"No extractor for: {ext}")

    def answer_from_file(self, filepath: str, question: str) -> str:
        """Answer a question based on file content."""
        try:
            text = self.process_file(filepath)
            truncated = text[:12000] if len(text) > 12000 else text
            prompt = f"Based on the following document, answer this question:\n\nQuestion: {question}\n\nDocument:\n{truncated}\n\nProvide a clear, accurate answer based only on the document."
            return self.ai_engine.chat_sync([{"role": "user", "content": prompt}], mode="expert")
        except Exception as exc:
            return f"[Q&A Error: {exc}]"

    def save_upload(self, file_content: bytes, original_filename: str) -> str:
        """Save uploaded file content securely."""
        if len(file_content) > self.max_size:
            raise ValueError(f"File too large: {len(file_content)} bytes")
        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = self.upload_dir / unique_name
        dest.write_bytes(file_content)
        return str(dest)

    def _extract_pdf(self, filepath: str) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_docx(self, filepath: str) -> str:
        from docx import Document
        doc = Document(filepath)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _extract_image(self, filepath: str) -> str:
        return self.ai_engine.vision(filepath, prompt="Describe this image in detail including all visible text, objects, and elements.")

    @staticmethod
    def _extract_text(filepath: str) -> str:
        path = Path(filepath)
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        raise RuntimeError(f"Could not decode file: {filepath}")
