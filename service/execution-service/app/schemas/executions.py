from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    workflow_name: str | None = None
    status: str
    trigger_type: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    duration_ms: int | None = Field(default=None, ge=0)


class ExecutionListResponse(BaseModel):
    items: list[ExecutionListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class ExecutionDetailResponse(ExecutionListItem):
    workspace_id: UUID
    error: dict | None = None


class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID

    # Node metadata snapshots
    node_id: str
    node_name: str | None = None
    node_type: str | None = None

    # Execution status
    status: str
    sequence: int = Field(ge=1)
    attempt: int = Field(ge=1)

    # Sanitized execution payloads
    input: Any | None = None
    output: Any | None = None
    error: Any | None = None

    # Execution timestamps
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None = Field(
        default=None,
        ge=0,
    )
    created_at: datetime


class ExecutionStepsListResponse(BaseModel):
    items: list[ExecutionStepResponse]
