from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowEdgeCreate(BaseModel):
    source_node_id: str = Field(min_length=1, max_length=100)
    target_node_id: str = Field(min_length=1, max_length=100)
    condition: str | None = Field(default=None, max_length=255)


class WorkflowEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_version_id: UUID
    source_node_id: str
    target_node_id: str
    condition: str | None
    created_at: datetime