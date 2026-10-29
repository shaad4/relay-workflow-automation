from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkflowLifecycleEvent(BaseModel):
    """Standard event schema for workflow lifecycle events."""

    event_id: UUID = Field(default_factory=uuid4)

    event_type: Literal[
        "workflow.started",
        "workflow.completed",
        "workflow.failed",
    ]

    execution_id: UUID
    workspace_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: dict[str, Any] = Field(default_factory=dict)
