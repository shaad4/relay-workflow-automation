from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeadLetterEventResponse(BaseModel):
    id: UUID
    execution_id: UUID
    execution_step_id: UUID | None
    event_type: str
    attempts: int
    status: str
    error: dict | None
    created_at: datetime
    resolved_at: datetime | None


class DeadLetterListResponse(BaseModel):
    items: list[DeadLetterEventResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
