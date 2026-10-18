from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: UUID
    schedule_type: Literal["interval", "cron"]

    interval_minutes: int | None = Field(
        default=None,
        ge=1,
        le=10080,
        strict=True,
    )

    cron_expression: str | None = Field(
        default=None,
        max_length=100,
    )

    timezone: str = "UTC"
    enabled: bool = True

    input_data: dict[str, Any] = Field(
        default_factory=dict,
    )


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_type: Literal["interval", "cron"] | None = None
    interval_minutes: int | None = Field(
        default=None,
        ge=1,
        le=10080,
    )
    cron_expression: str | None = None
    timezone: str | None = None
    enabled: bool | None = None
    input_data: dict[str, Any] | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID

    schedule_type: str
    interval_minutes: int | None
    cron_expression: str | None
    timezone: str
    enabled: bool
    input_data: dict[str, Any]

    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime