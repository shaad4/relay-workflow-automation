from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNodeCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=100)
    node_type: str = Field(min_length=1, max_length=100)
    label: str | None = Field(default=None, max_length=255)
    position_x: int = 0
    position_y: int = 0
    configuration: dict = {}


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_version_id: UUID
    node_id: str
    node_type: str
    label: str | None
    position_x: int
    position_y: int
    configuration: dict
    created_at: datetime
    

class WorkflowNodeUpdate(BaseModel):
    node_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    node_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    label: str | None = Field(
        default=None,
        max_length=255,
    )
    position_x: int | None = None
    position_y: int | None = None
    configuration: dict | None = None