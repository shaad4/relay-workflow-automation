from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime