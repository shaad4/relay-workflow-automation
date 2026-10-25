"""UTC calendar buckets, including the current partial bucket; counts use creation time."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.models.human_approval import HumanApproval
from app.schemas.dashboard import DashboardRange


async def get_dashboard_summary(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID,
    time_range: DashboardRange = "7d",
    *,
    now: datetime | None = None,
) -> dict:
    # Include the current partial UTC hour or day in the selected window.
    now = now or datetime.now(timezone.utc)
    hourly = time_range == "24h"
    size = 24 if hourly else (7 if time_range == "7d" else 30)
    unit = timedelta(hours=1) if hourly else timedelta(days=1)
    anchor = now.replace(minute=0, second=0, microsecond=0)

    if not hourly:
        anchor = anchor.replace(hour=0)

    start = anchor - unit * (size - 1)
    scope = (
        Execution.workspace_id == workspace_id,
        Execution.created_at >= start,
        Execution.created_at <= now,
    )

    # Aggregate status counts without loading execution payloads.
    counts = dict(
        (
            await session.execute(
                select(Execution.status, func.count()).where(*scope).group_by(Execution.status)
            )
        ).all()
    )
    states = {
        key: counts.get(key, 0)
        for key in (
            "completed",
            "failed",
            "running",
            "waiting_for_approval",
            "pending",
            "cancelled",
        )
    }
    denominator = states["completed"] + states["failed"]

    bucket = func.date_trunc(
        "hour" if hourly else "day",
        func.timezone("UTC", Execution.created_at),
    )
    activity = (
        await session.execute(
            select(bucket.label("bucket"), Execution.status, func.count())
            .where(*scope, Execution.status.in_(["completed", "failed"]))
            .group_by(bucket, Execution.status)
        )
    ).all()

    def label(value):
        return value.strftime("%Y-%m-%dT%H:00:00Z" if hourly else "%Y-%m-%d")

    # Fill empty periods so the chart always has a complete time axis.
    buckets = {
        label(start + unit * i): {
            "bucket": label(start + unit * i),
            "completed": 0,
            "failed": 0,
        }
        for i in range(size)
    }

    for timestamp, status, count in activity:
        buckets[label(timestamp)][status] = count

    # Current backlogs are independent of the selected execution window.
    approvals = await session.scalar(
        select(func.count())
        .select_from(HumanApproval)
        .join(Execution, Execution.id == HumanApproval.execution_id)
        .where(
            HumanApproval.workspace_id == workspace_id,
            Execution.workspace_id == workspace_id,
            HumanApproval.approver_user_id == user_id,
            HumanApproval.status == "pending",
            Execution.status == "waiting_for_approval",
            Execution.cancel_requested_at.is_(None),
        )
    )
    dlq = await session.scalar(
        select(func.count())
        .select_from(DeadLetterEvent)
        .where(
            DeadLetterEvent.workspace_id == workspace_id,
            DeadLetterEvent.status == "pending",
        )
    )

    # Select public metadata only; never load payloads, context, or outputs.
    recent = (
        (
            await session.execute(
                select(
                    Execution.id,
                    Execution.workflow_id,
                    Execution.workflow_version_id,
                    Execution.workflow_name,
                    Execution.status,
                    Execution.trigger_type,
                    Execution.started_at,
                    Execution.completed_at,
                    Execution.created_at,
                )
                .where(Execution.workspace_id == workspace_id)
                .order_by(Execution.created_at.desc(), Execution.id.desc())
                .limit(5)
            )
        )
        .mappings()
        .all()
    )
    items = []

    for row in recent:
        item = dict(row)
        item["duration_ms"] = (
            max(
                0,
                int((row["completed_at"] - row["started_at"]).total_seconds() * 1000),
            )
            if row["completed_at"] and row["started_at"]
            else None
        )
        items.append(item)

    return dict(
        range=time_range,
        timezone="UTC",
        window_start=start,
        window_end=now,
        total_executions=sum(counts.values()),
        **states,
        success_rate=(round(states["completed"] / denominator * 100, 2) if denominator else None),
        pending_approvals=approvals,
        pending_dlq=dlq,
        execution_activity=list(buckets.values()),
        recent_executions=items,
    )
