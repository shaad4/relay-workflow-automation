import json
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import grpc
from croniter import croniter
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.grpc.workflow_client import WorkflowGrpcClient
from app.models.workflow_schedule import WorkflowSchedule
from app.schemas.workflow_schedule import ScheduleCreate


def calculate_next_run(
    schedule_type: str,
    interval_minutes: int | None,
    cron_expression: str | None,
    timezone_name: str,
) -> datetime:
    """Calculate the next execution time in UTC."""

    now = datetime.now(timezone.utc)

    try:
        local_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="Invalid timezone",
        )

    if schedule_type == "interval":
        if interval_minutes is None or cron_expression is not None:
            raise HTTPException(
                status_code=422,
                detail="Invalid interval configuration",
            )

        from datetime import timedelta
        return now + timedelta(minutes=interval_minutes)

    if not cron_expression or interval_minutes is not None:
        raise HTTPException(
            status_code=422,
            detail="Invalid cron configuration",
        )

    if (
        len(cron_expression.split()) != 5
        or not croniter.is_valid(cron_expression)
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid five-field cron expression",
        )

    local_now = now.astimezone(local_timezone)
    next_local = croniter(
        cron_expression,
        local_now,
    ).get_next(datetime)

    return next_local.astimezone(timezone.utc)


async def create_schedule(
    data: ScheduleCreate,
    workspace_id: UUID,
    session: AsyncSession,
) -> WorkflowSchedule:
    """Create a schedule for a published workflow."""

    client = WorkflowGrpcClient()

    try:
        published = await client.get_published_version(
            workflow_id=str(data.workflow_id),
            workspace_id=str(workspace_id),
        )

        definition = await client.get_workflow_definition(
            workflow_id=str(data.workflow_id),
            version_id=published.version_id,
            workspace_id=str(workspace_id),
        )

    except grpc.aio.AioRpcError as exc:
        if exc.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(
                status_code=404,
                detail="Workflow or published version not found",
            ) from exc

        if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
            raise HTTPException(
                status_code=409,
                detail="Workflow is not executable",
            ) from exc

        if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise HTTPException(
                status_code=504,
                detail="Workflow Service timed out",
            ) from exc

        raise HTTPException(
            status_code=503,
            detail="Workflow Service unavailable",
        ) from exc

    finally:
        await client.close()

    try:
        nodes = json.loads(definition.nodes_json)
        if not isinstance(nodes, list):
            raise ValueError("Invalid node list")
    except (json.JSONDecodeError, ValueError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Invalid workflow definition",
        )

    triggers = [
        node
        for node in nodes
        if isinstance(node, dict)
        and isinstance(node.get("node_type"), str)
        and node["node_type"].startswith("trigger.")
    ]

    if (
        len(triggers) != 1
        or triggers[0]["node_type"] != "trigger.schedule"
    ):
        raise HTTPException(
            status_code=409,
            detail="Published workflow does not have a Scheduled Trigger",
        )

    next_run_at = (
        calculate_next_run(
            data.schedule_type,
            data.interval_minutes,
            data.cron_expression,
            data.timezone,
        )
        if data.enabled
        else None
    )

    schedule = WorkflowSchedule(
        workspace_id=workspace_id,
        workflow_id=data.workflow_id,
        workflow_version_id=UUID(published.version_id),
        schedule_type=data.schedule_type,
        interval_minutes=data.interval_minutes,
        cron_expression=data.cron_expression,
        timezone=data.timezone,
        input_data=data.input_data,
        enabled=data.enabled,
        next_run_at=next_run_at,
    )

    session.add(schedule)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A schedule already exists for this workflow",
        ) from exc

    await session.refresh(schedule)
    return schedule