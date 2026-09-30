from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    workflow_id: UUID
    workflow_version_id: UUID
    name: str = Field(min_length=1, max_length=255)
    event_name: str = Field(min_length=1, max_length=255)
    method: str = Field(min_length=1, max_length=20)
    authentication_type: str = Field(min_length=1, max_length=100)
    secret_ref: str | None = None
    is_active: bool = True


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    name: str
    public_token: str
    event_name: str
    method: str
    authentication_type: str
    secret_ref: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime



class WebhookUpdate(BaseModel):
    workflow_id: UUID | None = None
    workflow_version_id: UUID | None = None
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    event_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    method: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )
    authentication_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    secret_ref: str | None = None
    is_active: bool | None = None
