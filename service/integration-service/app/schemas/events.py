from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkflowTriggeredEvent(BaseModel):
    event_id: UUID
    event_type: str = "workflow.triggered"
    workspace_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    webhook_id: UUID
    payload: dict[str, Any]