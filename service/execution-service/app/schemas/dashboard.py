from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.executions import ExecutionListItem

DashboardRange = Literal["24h", "7d", "30d"]


class ActivityBucket(BaseModel):
    bucket: str
    completed: int
    failed: int


class DashboardSummary(BaseModel):
    range: DashboardRange
    timezone: str = "UTC"
    window_start: datetime
    window_end: datetime
    total_executions: int
    completed: int
    failed: int
    running: int
    waiting_for_approval: int
    pending: int
    cancelled: int
    success_rate: float | None
    pending_approvals: int
    pending_dlq: int
    execution_activity: list[ActivityBucket]
    recent_executions: list[ExecutionListItem]
