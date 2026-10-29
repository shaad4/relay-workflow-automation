"""Dashboard aggregation against an isolated PostgreSQL database; no external actions."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.database import DATABASE_URL, AsyncSessionLocal, engine
from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from app.routes import dashboard
from app.services.dashboard import get_dashboard_summary

url = make_url(DATABASE_URL)
pytestmark = pytest.mark.skipif(
    url.database != "ci_test" or url.host not in ("localhost", "127.0.0.1"),
    reason="isolated PostgreSQL ci_test database required",
)
NOW = datetime(2026, 10, 24, 12, 30, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    await engine.dispose()


def execution(workspace, status="completed", created=NOW):
    return Execution(
        id=uuid4(),
        workspace_id=workspace,
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        workflow_name="Safe name",
        status=status,
        trigger_type="manual",
        created_at=created,
        started_at=created,
        completed_at=created + timedelta(seconds=2) if status in ("completed", "failed") else None,
        context={"password": "not exposed"},
        trigger_data={"secret": "not exposed"},
    )


@pytest.mark.parametrize(
    "range,size,start",
    [
        ("24h", 24, NOW.replace(day=23, hour=13, minute=0)),
        ("7d", 7, NOW.replace(day=18, hour=0, minute=0)),
        ("30d", 30, NOW.replace(month=9, day=25, hour=0, minute=0)),
    ],
)
async def test_empty_range_and_zero_buckets(db, range, size, start):
    data = await get_dashboard_summary(db, uuid4(), uuid4(), range, now=NOW)
    assert data["total_executions"] == 0 and data["success_rate"] is None
    assert data["pending_approvals"] == data["pending_dlq"] == 0
    assert data["window_start"] == start
    assert len(data["execution_activity"]) == size
    assert all(x["completed"] == x["failed"] == 0 for x in data["execution_activity"])
    assert data["recent_executions"] == []


async def test_counts_boundaries_isolation_recent_and_sanitization(db):
    workspace, other, user = uuid4(), uuid4(), uuid4()
    start = NOW.replace(day=18, hour=0, minute=0)
    rows = [
        execution(workspace, "completed", start),
        execution(workspace, "completed", NOW - timedelta(minutes=2)),
        execution(workspace, "failed", NOW - timedelta(minutes=1)),
    ]
    rows += [
        execution(workspace, status, NOW - timedelta(seconds=i))
        for i, status in enumerate(["cancelled", "pending", "running", "waiting_for_approval"], 1)
    ]
    rows += [
        execution(workspace, "failed", start - timedelta(microseconds=1)),
        execution(other, "failed"),
    ]
    db.add_all(rows)
    await db.flush()
    result = await get_dashboard_summary(db, workspace, user, "7d", now=NOW)
    assert result["total_executions"] == 7 and result["success_rate"] == 66.67
    assert result["failed"] == 1 and result["cancelled"] == 1
    assert result["execution_activity"][0]["completed"] == 1
    assert sum(x["completed"] for x in result["execution_activity"]) == 2
    assert len(result["recent_executions"]) == 5
    assert [x["created_at"] for x in result["recent_executions"]] == sorted(
        [x["created_at"] for x in result["recent_executions"]], reverse=True
    )
    assert all("context" not in x and "trigger_data" not in x for x in result["recent_executions"])
    assert "not exposed" not in str(result)
    short = await get_dashboard_summary(db, workspace, user, "24h", now=NOW)
    assert short["completed"] == 1 and short["total_executions"] == 6


async def test_current_backlogs_exclude_other_user_stale_and_cancelled(db):
    workspace, other, user, other_user = uuid4(), uuid4(), uuid4(), uuid4()
    old = NOW - timedelta(days=60)
    for owner, approver, status, cancel in [
        (workspace, user, "waiting_for_approval", False),
        (workspace, other_user, "waiting_for_approval", False),
        (other, user, "waiting_for_approval", False),
        (workspace, user, "failed", False),
        (workspace, user, "waiting_for_approval", True),
    ]:
        run = execution(owner, status, old)
        db.add(run)
        await db.flush()
        if cancel:
            run.cancel_requested_at = NOW
        step = ExecutionStep(
            id=uuid4(),
            execution_id=run.id,
            node_id="review",
            status="waiting_for_approval",
            sequence=1,
            attempt=1,
        )
        db.add(step)
        await db.flush()
        db.add(
            HumanApproval(
                id=uuid4(),
                workspace_id=owner,
                approver_user_id=approver,
                execution_id=run.id,
                execution_step_id=step.id,
                message="private",
                status="pending",
            )
        )
        db.add(
            DeadLetterEvent(
                workspace_id=owner,
                execution_id=run.id,
                status="pending" if status == "failed" or owner == other else "resolved",
                error={},
            )
        )
    await db.flush()
    result = await get_dashboard_summary(db, workspace, user, "24h", now=NOW)
    assert result["pending_approvals"] == 1 and result["pending_dlq"] == 1
    assert result["total_executions"] == 0


async def test_invalid_range_and_identity_scope(db):
    workspace, user, foreign = uuid4(), uuid4(), uuid4()
    db.add(execution(foreign))
    await db.flush()
    app = FastAPI()
    app.include_router(dashboard.router)
    app.dependency_overrides[dashboard.get_current_identity] = lambda: {
        "workspace_id": str(workspace),
        "user_id": str(user),
    }
    app.dependency_overrides[dashboard.get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/dashboard/summary?range=bad")).status_code == 422
        response = await client.get(f"/dashboard/summary?workspace_id={foreign}")
        assert response.status_code == 200 and response.json()["total_executions"] == 0
