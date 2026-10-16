from uuid import UUID
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.models.workflow_schedule import WorkflowSchedule
from app.services.workflow_schedule_service import calculate_next_run

async def find_due_schedules():
    """Find enabled schedules ready for execution."""

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkflowSchedule)
            .where(
                WorkflowSchedule.enabled.is_(True),
                WorkflowSchedule.next_run_at.is_not(None),
                WorkflowSchedule.next_run_at <= now,
            )
            .order_by(WorkflowSchedule.next_run_at)
        )

        schedules = result.scalars().all()

        return [
            {
                "id": str(schedule.id),
                "workflow_id": str(schedule.workflow_id),
                "workflow_version_id": str(
                    schedule.workflow_version_id
                ),
                "workspace_id": str(schedule.workspace_id),
                "schedule_type": schedule.schedule_type,
                "next_run_at": schedule.next_run_at.isoformat(),
            }
            for schedule in schedules
        ]


async def advance_due_schedules():
    """Advance due schedules to their next run time."""

    due_schedules = await find_due_schedules()
    advanced = []

    for item in due_schedules:
        async with AsyncSessionLocal() as session:
            schedule = await session.get(
                WorkflowSchedule,
                UUID(item["id"]),
            )

            if (
                schedule is None
                or not schedule.enabled
                or schedule.next_run_at is None
            ):
                continue

            due_at = schedule.next_run_at

            next_run = calculate_next_run(
                schedule_type=schedule.schedule_type,
                interval_minutes=schedule.interval_minutes,
                cron_expression=schedule.cron_expression,
                timezone_name=schedule.timezone,
            )

            result = await session.execute(
                update(WorkflowSchedule)
                .where(
                    WorkflowSchedule.id == schedule.id,
                    WorkflowSchedule.enabled.is_(True),
                    WorkflowSchedule.next_run_at == due_at,
                )
                .values(
                    last_run_at=due_at,
                    next_run_at=next_run,
                )
                .returning(WorkflowSchedule.id)
            )

            updated_id = result.scalar_one_or_none()
            await session.commit()

            if updated_id is not None:
                advanced.append(item)

    return advanced


@celery_app.task(name="integration.check_due_schedules")
def check_due_schedules():
    """Advance due workflow schedules."""

    return asyncio.run(advance_due_schedules())