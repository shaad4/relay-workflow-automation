from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class WorkflowTriggeredEvent(BaseModel):
    event_id: UUID
    event_type: Literal["workflow.triggered"] = "workflow.triggered"

    workspace_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID

    trigger_type: Literal[
        "webhook", "manual", "schedule"
    ] = "webhook"

    webhook_id: UUID | None = None

    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_trigger(self):
        if self.trigger_type == "webhook" and self.webhook_id is None:
            raise ValueError(
                "webhook_id is required for webhook triggers"
            )

        if self.trigger_type != "webhook" and self.webhook_id is not None:
            raise ValueError(
                "webhook_id is only allowed for webhook triggers"
            )

        return self