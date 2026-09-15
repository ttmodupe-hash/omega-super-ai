#!/usr/bin/env python3
"""
Luqi AI - Input Validators
===========================
Pydantic models and sanitization utilities for all API endpoints.
Prevents injection attacks, path traversal, and invalid input.

Part of Luqi AI v24.4.0 Security Hardening — Built by Limitless Telecoms
"""

import re
import uuid
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════

class AnalysisType(str, Enum):
    """Types of financial analysis."""
    GENERAL = "general"
    PROJECTION = "projection"
    RATIO = "ratio"
    CASHFLOW = "cashflow"


class CurrencyCode(str, Enum):
    """Supported currency codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    NGN = "NGN"  # Nigerian Naira
    ZAR = "ZAR"  # South African Rand
    KES = "KES"  # Kenyan Shilling
    GHS = "GHS"  # Ghanaian Cedi
    XOF = "XOF"  # West African CFA
    XAF = "XAF"  # Central African CFA
    AUD = "AUD"
    CAD = "CAD"
    JPY = "JPY"
    CNY = "CNY"


class DifficultyLevel(str, Enum):
    """Training difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProgrammingLanguage(str, Enum):
    """Supported programming languages for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    SQL = "sql"
    BASH = "bash"
    POWERSHELL = "powershell"


class FileCategory(str, Enum):
    """Categories of uploaded files."""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    DATA = "data"
    ARCHIVE = "archive"


# ═══════════════════════════════════════════════════════════════════
# PYDANTIC REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Validated chat request."""
    message: str = Field(..., min_length=1, max_length=10000,
                         description="User message to send to AI")
    model: Optional[str] = Field(default=None, max_length=100,
                                  description="AI model to use")
    system_prompt: Optional[str] = Field(default=None, max_length=5000,
                                          description="System instructions")
    context: Optional[List[Dict[str, str]]] = Field(default=None,
                                                     description="Previous messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0,
                                description="Creativity level (0-2)")
    max_tokens: int = Field(default=2000, ge=1, le=16000,
                            description="Maximum response tokens")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        if v is not None and len(v) > 100:
            raise ValueError("Context cannot exceed 100 messages")
        return v


class FinancialAnalysisRequest(BaseModel):
    """Validated financial analysis request."""
    data: Dict[str, Any] = Field(..., description="Financial data dict")
    analysis_type: AnalysisType = Field(default=AnalysisType.GENERAL,
                                        description="Type of analysis")
    currency: CurrencyCode = Field(default=CurrencyCode.USD,
                                   description="Currency code")
    projection_months: Optional[int] = Field(default=12, ge=1, le=60,
                                              description="Months to project")
    monthly_growth_rate: Optional[float] = Field(default=0.02, ge=-1.0, le=1.0,
                                                  description="Monthly growth rate")

    @model_validator(mode="after")
    def validate_financial_data(self):
        data = self.data
        for field in ["revenue", "expenses", "assets", "liabilities"]:
            if field in data:
                try:
                    float(data[field])
                except (TypeError, ValueError):
                    raise ValueError(f"Field '{field}' must be a valid number")
        return self


class FileUploadRequest(BaseModel):
    """Validated file upload metadata."""
    filename: str = Field(..., min_length=1, max_length=255,
                          description="Original filename")
    size: int = Field(..., ge=0, le=100 * 1024 * 1024,
                      description="File size in bytes (max 100MB)")
    content_type: Optional[str] = Field(default=None, max_length=100,
                                        description="MIME type")
    category: FileCategory = Field(default=FileCategory.DOCUMENT,
                                   description="File category")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path traversal sequences")
        if not re.match(r'^[A-Za-z0-9._-]+$', Path(v).name):
            raise ValueError("Filename contains invalid characters")
        return v


class UserRegistrationRequest(BaseModel):
    """Validated user registration request."""
    email: str = Field(..., min_length=5, max_length=254,
                       pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                       description="User email address")
    username: str = Field(..., min_length=3, max_length=50,
                          pattern=r'^[a-zA-Z0-9_-]+$',
                          description="Username (alphanumeric, underscores, hyphens)")
    password: str = Field(..., min_length=8, max_length=128,
                          description="Password (min 8 chars)")
    full_name: Optional[str] = Field(default=None, max_length=100,
                                     description="Full display name")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit")
        return v


class CodeGenerationRequest(BaseModel):
    """Validated code generation request."""
    prompt: str = Field(..., min_length=10, max_length=50000,
                        description="Code generation prompt")
    language: ProgrammingLanguage = Field(default=ProgrammingLanguage.PYTHON,
                                          description="Target programming language")
    framework: Optional[str] = Field(default=None, max_length=100,
                                     description="Framework or library")
    context: Optional[str] = Field(default=None, max_length=50000,
                                   description="Additional context or existing code")

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("Prompt must be at least 10 characters")
        return v.strip()


class SearchRequest(BaseModel):
    """Validated search request."""
    query: str = Field(..., min_length=1, max_length=500,
                       description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(default=None,
                                               description="Optional filters")
    page: int = Field(default=1, ge=1, le=10000,
                      description="Page number")
    per_page: int = Field(default=20, ge=1, le=100,
                          description="Results per page")

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Search query cannot be empty")
        return v


class TrainingEnrollmentRequest(BaseModel):
    """Validated training enrollment request."""
    course_id: str = Field(..., min_length=1, max_length=100,
                           pattern=r'^[a-zA-Z0-9_-]+$',
                           description="Course identifier")
    user_id: str = Field(..., min_length=1, max_length=100,
                         description="User identifier")
    track: Optional[str] = Field(default=None, max_length=100,
                                 description="Certification track")


class AssessmentSubmissionRequest(BaseModel):
    """Validated assessment submission."""
    user_id: str = Field(..., min_length=1, max_length=100,
                         description="User identifier")
    quiz_id: str = Field(..., min_length=1, max_length=100,
                         description="Quiz identifier")
    answers: Dict[str, Union[str, int, List[str]]] = Field(
        ..., description="Question ID to answer mapping")
    time_taken: Optional[int] = Field(default=None, ge=0,
                                      description="Time taken in seconds")

    @field_validator("answers")
    @classmethod
    def answers_not_empty(cls, v: Dict) -> Dict:
        if not v:
            raise ValueError("Answers cannot be empty")
        return v


class WebhookPayload(BaseModel):
    """Validated webhook payload."""
    event: str = Field(..., min_length=1, max_length=100,
                       description="Event type")
    timestamp: Optional[str] = Field(default=None,
                                     description="Event timestamp (ISO 8601)")
    signature: Optional[str] = Field(default=None, max_length=500,
                                     description="Webhook signature for verification")
    data: Dict[str, Any] = Field(default_factory=dict,
                                  description="Event payload data")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                age = (datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds()
                if abs(age) > 300:  # 5 minutes
                    raise ValueError(f"Webhook timestamp is stale ({age:.0f}s old)")
            except (ValueError, TypeError) as e:
                if "stale" in str(e):
                    raise
                raise ValueError(f"Invalid timestamp format: {e}")
        return v


class RateLimitConfig(BaseModel):
    """Validated rate limit configuration."""
    requests_per_minute: int = Field(default=60, ge=1, le=10000,
                                     description="Max requests per minute")
    burst_size: int = Field(default=10, ge=1, le=1000,
                            description="Burst allowance")
    key_prefix: str = Field(default="rl", max_length=50,
                            description="Rate limit key prefix")


class SecurityConfig(BaseModel):
    """Validated security configuration."""
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"],
                                     description="Allowed CORS origins")
    max_upload_size: int = Field(default=10 * 1024 * 1024, ge=1024,
                                  description="Max upload size in bytes")
    allowed_file_types: Set[str] = Field(
        default_factory=lambda: {
            ".txt", ".md", ".pdf", ".doc", ".docx",
            ".png", ".jpg", ".jpeg", ".gif", ".svg",
            ".mp4", ".mp3", ".wav",
            ".py", ".js", ".ts", ".html", ".css", ".json",
            ".csv", ".xlsx", ".zip",
        },
        description="Allowed file extensions"
    )
    enable_security_headers: bool = Field(default=True,
                                          description="Add security headers to responses")

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one CORS origin must be specified")
        for origin in v:
            if "*" in origin and origin != "*":
                raise ValueError(f"Invalid CORS origin pattern: {origin}")
        return v


# ═══════════════════════════════════════════════════════════════════
# SANITIZATION UTILITIES
# ═══════════════════════════════════════════════════════════════════

# Characters dangerous for filenames
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
# Path traversal patterns
_PATH_TRAVERSAL_RE = re.compile(r'\.{2,}[/\\]|[/\\]\.{2,}')
# Shell metacharacters
_SHELL_META_RE = re.compile(r'[;|&$`\\]')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".doc", ".docx", ".odt",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".mp4", ".webm", ".mp3", ".wav", ".ogg",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".xml", ".yaml", ".yml",
    ".csv", ".xlsx", ".xls", ".ods",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
}


def sanitize_filename(filename: str, allowed_extensions: set = None) -> str:
    """Sanitize a filename to prevent path traversal and injection.

    Steps:
        1. Reject null bytes and control characters
        2. Strip path traversal sequences
        3. Remove shell metacharacters
        4. Normalize to basename
        5. Validate extension against allowlist
        6. Prefix with UUID to prevent overwrites

    Args:
        filename: The original filename.
        allowed_extensions: Set of allowed extensions (default: ALLOWED_EXTENSIONS).

    Returns:
        Sanitized filename safe for filesystem use.

    Raises:
        ValueError: If the filename is empty or has a disallowed extension.
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")

    # Step 1: Reject null bytes
    if "\x00" in filename:
        raise ValueError("Filename contains null bytes")

    # Step 2: Check for path traversal
    if _PATH_TRAVERSAL_RE.search(filename):
        raise ValueError("Filename contains path traversal sequences")

    # Step 3: Remove shell metacharacters
    filename = _SHELL_META_RE.sub("", filename)

    # Step 4: Normalize to basename only
    basename = Path(filename).name
    if not basename or basename in (".", ".."):
        raise ValueError("Filename resolves to empty or unsafe basename")

    # Step 5: Remove unsafe characters
    basename = _UNSAFE_FILENAME_CHARS.sub("", basename)
    basename = basename.strip(". ")

    if not basename:
        raise ValueError("Filename is empty after sanitization")

    # Step 6: Validate extension
    ext = Path(basename).suffix.lower()
    allowed = allowed_extensions or ALLOWED_EXTENSIONS
    if ext and ext not in allowed:
        raise ValueError(
            f"File extension {ext!r} is not allowed. "
            f"Allowed: {sorted(allowed)}"
        )

    # Step 7: Prefix with UUID to prevent overwrites and predictability
    unique_prefix = uuid.uuid4().hex[:8]
    safe_name = f"{unique_prefix}_{basename}"

    # Final length check
    if len(safe_name) > 255:
        # Truncate basename, keep prefix and extension
        name_part = Path(basename).stem[:200]
        safe_name = f"{unique_prefix}_{name_part}{ext}"

    logger.debug("Sanitized filename: %r -> %r", filename, safe_name)
    return safe_name


def validate_sql_table(table: str, allowed_tables: set) -> str:
    """Validate a SQL table name against a whitelist.

    Args:
        table: Table name to validate.
        allowed_tables: Set of allowed table names.

    Returns:
        The validated table name.

    Raises:
        ValueError: If the table is not in the whitelist.
    """
    if not table or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table):
        raise ValueError(f"Invalid SQL table name: {table!r}")
    if table not in allowed_tables:
        raise ValueError(
            f"Table {table!r} is not allowed. "
            f"Allowed tables: {sorted(allowed_tables)}"
        )
    return table


def validate_file_path(file_path: str, base_dir: Path) -> Path:
    """Validate that a file path is within a base directory.

    Resolves both paths and ensures the resolved path is a subpath
    of the resolved base directory.

    Args:
        file_path: The file path to validate.
        base_dir: The allowed base directory.

    Returns:
        The validated Path object.

    Raises:
        ValueError: If the path escapes the base directory.
    """
    try:
        base = base_dir.resolve()
        target = (base / file_path).resolve()
        target.relative_to(base)
        return target
    except (ValueError, RuntimeError) as e:
        raise ValueError(
            f"File path {file_path!r} is outside allowed directory {str(base_dir)!r}"
        ) from e
