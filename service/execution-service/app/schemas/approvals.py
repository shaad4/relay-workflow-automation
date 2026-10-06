from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    id: UUID
    execution_id: UUID
    execution_step_id: UUID
    message: str
    status: str
    decision: str | None
    timeout_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]