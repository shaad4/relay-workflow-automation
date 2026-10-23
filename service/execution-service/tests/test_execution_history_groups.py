"""Exercise grouping queries against a real SQL database, without external services."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/relay_test")

from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.repositories.execution import ExecutionRepository
from app.services.execution_history import ExecutionHistoryService


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    return "JSON"


class SessionAdapter:
    """Use the production SQL queries with an in-memory synchronous driver."""
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def rollback(self):
        self.session.rollback()


@pytest.fixture
def history():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Execution.__table__.create(engine)
    DeadLetterEvent.__table__.create(engine)
    with Session(engine) as session:
        workspace, other_workspace, workflow, version = uuid4(), uuid4(), uuid4(), uuid4()
        start = datetime(2026, 10, 22, tzinfo=timezone.utc)

        def run(minute, status="failed", parent=None, workspace_id=None):
            item = Execution(
                id=uuid4(), workspace_id=workspace_id or workspace, workflow_id=workflow,
                workflow_version_id=version, workflow_name="Order processing", status=status,
                trigger_type="manual", created_at=start + timedelta(minutes=minute),
                started_at=start + timedelta(minutes=minute), completed_at=start + timedelta(minutes=minute, seconds=2),
                replay_of_execution_id=parent.id if parent else None,
                context={"secret": "never returned"}, trigger_data={"password": "hidden"},
            )
            session.add(item)
            session.commit()
            return item

        original = run(0)
        replay = run(1, parent=original)
        latest = run(3, "completed", replay)
        unrelated = run(2)  # Same workflow is deliberately a different group.
        foreign = run(4, workspace_id=other_workspace)
        adapter = SessionAdapter(session)
        service = ExecutionHistoryService(ExecutionRepository(adapter))
        yield locals()
    engine.dispose()


def query(history, **kwargs):
    return asyncio.run(history["service"].list_executions(workspace_id=history["workspace"], **kwargs))


def test_replays_of_replays_form_one_group_and_totals_count_groups(history):
    data = query(history, group_replays=True)
    assert data["total"] == 2
    latest, unrelated = data["items"]
    assert latest["id"] == history["latest"].id
    assert latest["execution_group_id"] == history["original"].id
    assert latest["replay_of_execution_id"] == history["replay"].id
    assert latest["attempt_count"] == 3
    assert latest["status"] == "completed"
    assert unrelated["execution_group_id"] == history["unrelated"].id
    assert unrelated["attempt_count"] == 1
    for item in data["items"]:
        assert "context" not in item and "trigger_data" not in item


def test_group_pagination_never_splits_a_run(history):
    first = query(history, group_replays=True, page_size=1)
    second = query(history, group_replays=True, page_size=1, page=2)
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["attempt_count"] == 3
    assert second["items"][0]["execution_group_id"] == history["unrelated"].id
    assert query(history, group_replays=True, page=3, page_size=1)["items"] == []


def test_filters_use_latest_attempt_not_historical_failures(history):
    failed = query(history, group_replays=True, status="failed")
    assert failed["total"] == 1
    assert failed["items"][0]["id"] == history["unrelated"].id
    completed = query(history, group_replays=True, status="completed")
    assert completed["total"] == 1
    assert completed["items"][0]["attempt_count"] == 3
    assert query(history, group_replays=True, status="running")["total"] == 0


def test_attempts_resolve_any_member_and_are_paginated_oldest_first(history):
    for member in ["original", "replay", "latest"]:
        first = query(history, group_id=history[member].id, page_size=2)
        second = query(history, group_id=history[member].id, page_size=2, page=2)
        assert first["total"] == second["total"] == 3
        assert [row["id"] for row in first["items"]] == [history["original"].id, history["replay"].id]
        assert [row["id"] for row in second["items"]] == [history["latest"].id]


def test_workspace_isolation_and_unknown_groups(history):
    assert query(history, group_id=history["foreign"].id) is None
    assert query(history, group_id=uuid4()) is None
    # Even malformed cross-workspace parent links must not reveal another tenant.
    cross = history["run"](5, parent=history["foreign"])
    data = query(history, group_id=cross.id)
    assert data["total"] == 1
    assert data["items"][0]["execution_group_id"] == cross.id


def test_flat_history_remains_backward_compatible(history):
    flat = query(history)
    assert flat["total"] == 4
    assert len(flat["items"]) == 4
    assert query(history, status="failed")["total"] == 3
    assert all("execution_group_id" not in row for row in flat["items"])


def test_http_contract_validation_and_authorized_workspace(history):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import executions

    app = FastAPI()
    app.include_router(executions.router)
    app.dependency_overrides[executions.get_current_identity] = lambda: {"workspace_id": str(history["workspace"])}
    app.dependency_overrides[executions.get_db] = lambda: history["adapter"]
    with TestClient(app) as client:
        response = client.get("/executions/?group_replays=true&page_size=1")
        assert response.status_code == 200
        assert response.json()["items"][0]["attempt_count"] == 3
        assert response.json()["total"] == 2
        for suffix in ["page_size=101", "group_id=bad-id", f"group_id={history['original'].id}&status=failed", f"group_id={history['original'].id}&group_replays=true"]:
            assert client.get(f"/executions/?{suffix}").status_code == 422
        assert client.get(f"/executions/?group_id={history['foreign'].id}").status_code == 404
        assert client.get(f"/executions/?group_id={history['latest'].id}").json()["total"] == 3
        assert client.get(f"/executions/{history['latest'].id}/").json()["replay_of_execution_id"] == str(history["replay"].id)
        assert client.get("/executions/").json()["total"] == 4
