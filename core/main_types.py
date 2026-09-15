"""Shared orchestrator types - extracted so state_store can import without a cycle."""
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PROCESSING = "processing"
    PENDING_HUMAN_APPROVAL = "pending_human_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class LuqiState(BaseModel):
    task_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    student_tier: str
    action_type: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PROCESSING
    required_human_action: Optional[str] = None
