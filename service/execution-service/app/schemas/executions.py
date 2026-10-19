from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
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
