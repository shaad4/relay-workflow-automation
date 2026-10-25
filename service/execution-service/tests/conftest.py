"""Shared SQL fixtures and event-loop isolation for execution-service tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.database import DATABASE_URL, engine
from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.repositories.execution import ExecutionRepository
from app.services.execution_history import ExecutionHistoryService
from session_adapter import SessionAdapter
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool, StaticPool

database = make_url(DATABASE_URL)
if database.database == "ci_test" and database.host in {"localhost", "127.0.0.1"}:
    # Several tests create their own event loop with asyncio.run(). A pooled
    # asyncpg connection cannot be reused by a later test's event loop.
    engine.sync_engine.pool = NullPool(engine.sync_engine.pool._creator)


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def history():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Execution.__table__.create(engine)
    DeadLetterEvent.__table__.create(engine)
    with Session(engine) as session:
        workspace, other_workspace, workflow, version = uuid4(), uuid4(), uuid4(), uuid4()
        start = datetime(2026, 10, 22, tzinfo=timezone.utc)

        def run(minute, status="failed", parent=None, workspace_id=None):
            item = Execution(
                id=uuid4(),
                workspace_id=workspace_id or workspace,
                workflow_id=workflow,
                workflow_version_id=version,
                workflow_name="Order processing",
                status=status,
                trigger_type="manual",
                created_at=start + timedelta(minutes=minute),
                started_at=start + timedelta(minutes=minute),
                completed_at=start + timedelta(minutes=minute, seconds=2),
                replay_of_execution_id=parent.id if parent else None,
                context={"secret": "never returned"},
                trigger_data={"password": "hidden"},
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
