from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=100)
    auth_type: str = Field(min_length=1, max_length=100)
    credential: str | None = None
    config: dict[str, Any] | None = None



class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    provider: str
    auth_type: str
    config: dict[str, Any] | None
    created_at: Any


class ConnectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    provider: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    auth_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    credential: str | None = None
    config: dict[str, Any] | None = None


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str