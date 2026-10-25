import asyncio
from datetime import datetime
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, ValidationError

from app.dependencies import get_current_identity

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
EXECUTION_URL = "http://execution-service:8000/dashboard/summary"
WORKFLOW_URL = "http://workflow-service:8000/dashboard/summary"


class RecentExecution(BaseModel):
    id: UUID
    workflow_id: UUID
    workflow_name: str | None = None
    status: str
    trigger_type: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    duration_ms: int | None = Field(default=None, ge=0)


class ActivityBucket(BaseModel):
    bucket: str
    completed: int = Field(ge=0)
    failed: int = Field(ge=0)


class ExecutionSummary(BaseModel):
    range: Literal["24h", "7d", "30d"]
    timezone: Literal["UTC"]
    window_start: datetime
    window_end: datetime
    total_executions: int = Field(ge=0)
    completed: int = Field(ge=0)
    failed: int = Field(ge=0)
    running: int = Field(ge=0)
    waiting_for_approval: int = Field(ge=0)
    pending: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    success_rate: float | None = Field(ge=0, le=100)
    pending_approvals: int = Field(ge=0)
    pending_dlq: int = Field(ge=0)
    execution_activity: list[ActivityBucket]
    recent_executions: list[RecentExecution] = Field(max_length=5)


class WorkflowSummary(BaseModel):
    total_workflows: int = Field(ge=0)
    active_workflows: int = Field(ge=0)


class Overview(ExecutionSummary, WorkflowSummary):
    pass


@router.get("/overview", response_model=Overview)
async def overview(
    request: Request,
    range: Literal["24h", "7d", "30d"] = Query(default="7d"),
    identity: dict = Depends(get_current_identity),
):
    # Forward only the credential that the existing dependency validated.
    authorization = (
        request.headers.get("authorization")
        or f"Bearer {request.cookies.get('relay_access_token', '')}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            responses = await asyncio.gather(
                client.get(
                    EXECUTION_URL,
                    headers={"Authorization": authorization},
                    params={"range": range},
                ),
                client.get(
                    WORKFLOW_URL,
                    headers={"Authorization": authorization},
                ),
            )

    except httpx.TimeoutException as exc:
        raise HTTPException(
            504,
            "Dashboard request timed out. Please retry.",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            502,
            "Dashboard is temporarily unavailable.",
        ) from exc

    for response in responses:
        if response.status_code in (401, 403):
            raise HTTPException(
                response.status_code,
                "Dashboard access could not be authorized.",
            )

        if response.status_code != 200:
            raise HTTPException(
                502,
                "Dashboard is temporarily unavailable.",
            )

    try:
        execution = ExecutionSummary.model_validate(responses[0].json())
        workflows = WorkflowSummary.model_validate(responses[1].json())

    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            502,
            "Dashboard returned an invalid response.",
        ) from exc

    return {**execution.model_dump(), **workflows.model_dump()}
