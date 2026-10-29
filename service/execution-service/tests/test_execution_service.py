import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.status import ExecutionStatus
from app.services import execution_queue


@pytest.fixture
def session(monkeypatch):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(execution_queue, "AsyncSessionLocal", lambda: session)
    return session


@pytest.mark.parametrize("duplicate", [False, True], ids=["pending", "duplicate"])
def test_create_pending_execution(monkeypatch, session, duplicate):
    event = {
        key: str(uuid4())
        for key in ("event_id", "workspace_id", "workflow_id", "workflow_version_id")
    }
    event.update(trigger_type="manual", payload={"email": "test@example.com"})
    client = SimpleNamespace(
        validate_workflow_version=AsyncMock(
            return_value=SimpleNamespace(
                valid=True,
                status="published",
                workflow_status="active",
            )
        ),
        close=AsyncMock(),
    )
    monkeypatch.setattr(execution_queue, "WorkflowClient", lambda: client)
    execution_id = uuid4()

    async def flush():
        session.add.call_args_list[0].args[0].id = execution_id

    session.flush.side_effect = flush
    existing_id = uuid4()
    if duplicate:
        session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
        session.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(
            id=existing_id
        )

    expected_id = existing_id if duplicate else execution_id
    assert asyncio.run(execution_queue.create_pending_execution(event)) == expected_id
    execution, key = [call.args[0] for call in session.add.call_args_list]
    assert execution.status == ExecutionStatus.PENDING
    assert execution.workspace_id == UUID(event["workspace_id"])
    assert execution.workflow_id == UUID(event["workflow_id"])
    assert execution.workflow_version_id == UUID(event["workflow_version_id"])
    assert execution.trigger_type == "manual"
    assert execution.trigger_data == event["payload"]
    assert key.key == f"workflow.triggered:{event['event_id']}"
    assert key.execution_id == execution_id
    session.commit.assert_awaited_once()
    if duplicate:
        session.rollback.assert_awaited_once()
        session.execute.assert_awaited_once()
    else:
        session.rollback.assert_not_awaited()


@pytest.mark.parametrize("claimed", [True, False], ids=["pending", "already-claimed"])
def test_claim_pending_execution(session, claimed):
    execution_id = uuid4()
    session.execute.return_value.scalar_one_or_none.return_value = execution_id if claimed else None

    assert asyncio.run(execution_queue.claim_pending_execution(execution_id, "worker-1")) is claimed
    session.execute.assert_awaited_once()
    statement = session.execute.call_args.args[0]
    sql = str(statement)
    assert "UPDATE executions SET" in sql
    assert "executions.status =" in sql.split("WHERE")[1]
    params = statement.compile().params
    assert ExecutionStatus.PENDING in params.values()
    assert params["status"] == ExecutionStatus.RUNNING
    assert params["claimed_by"] == "worker-1"
    if claimed:
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()
    else:
        session.commit.assert_not_awaited()
        session.rollback.assert_awaited_once()


def test_failed_execution_is_persisted(session):
    execution_id = uuid4()
    error = {"node_id": "payment-node", "message": "Action execution failed"}
    session.execute.return_value.one_or_none.return_value = SimpleNamespace(
        status=ExecutionStatus.FAILED, workspace_id=uuid4()
    )
    session.execute.return_value.scalar_one_or_none.return_value = None

    assert (
        asyncio.run(
            execution_queue.finalize_execution(
                execution_id,
                "worker-1",
                ExecutionStatus.FAILED,
                error=error,
            )
        )
        == ExecutionStatus.FAILED
    )
    assert session.execute.await_count == 2
    params = session.execute.await_args_list[0].args[0].compile().params
    assert ExecutionStatus.FAILED in params.values()
    assert error in params.values()
    statement = str(session.execute.await_args_list[0].args[0])
    assert "completed_at=now()" in statement
    assert "claimed_by=:claimed_by" in statement
    assert "heartbeat_at=:heartbeat_at" in statement
    assert "lease_expires_at=:lease_expires_at" in statement
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
