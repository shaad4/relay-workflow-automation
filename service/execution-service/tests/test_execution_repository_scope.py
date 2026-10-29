"""Guard repository scope and cancellation behavior without external actions."""

import ast
import asyncio
import inspect
from pathlib import Path
from uuid import uuid4

import pytest
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from app.repositories.execution import ExecutionRepository
from sqlalchemy.dialects import postgresql

REQUIRED = (
    "list_executions",
    "get_execution_by_id",
    "list_execution_steps",
    "request_cancellation",
    "replay_tree",
    "list_execution_groups",
    "list_execution_attempts",
    "get_execution_lineage",
    "get_recovery_events",
)


def test_required_methods_are_defined_directly_on_repository():
    tree = ast.parse(Path(inspect.getfile(ExecutionRepository)).read_text())
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ExecutionRepository"
    )
    methods = [
        node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for name in REQUIRED:
        method = getattr(ExecutionRepository, name, None)
        assert callable(method), name
        assert method.__qualname__ == f"ExecutionRepository.{name}"
        assert methods.count(name) == 1


@pytest.mark.parametrize(
    "status,expected",
    [
        ("pending", "cancelled"),
        ("running", "cancellation_requested"),
        ("completed", "not_cancellable"),
        ("failed", "not_cancellable"),
        ("cancelled", "already_cancelled"),
    ],
)
def test_cancellation_states_and_workspace_lock(history, status, expected):
    execution = history["run"](10, status=status)
    repo = history["service"].repository
    statements = []
    execute = repo.session.execute

    async def record(statement):
        statements.append(statement)
        return await execute(statement)

    repo.session.execute = record
    previous = (execution.status, execution.cancel_requested_at, execution.completed_at)
    assert asyncio.run(repo.request_cancellation(execution.id, history["other_workspace"])) is None
    assert (execution.status, execution.cancel_requested_at, execution.completed_at) == previous
    assert asyncio.run(repo.request_cancellation(execution.id, history["workspace"])) == expected
    sql = str(statements[-1].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql and "executions.workspace_id" in sql
    if status == "running":
        assert execution.status == "running"
        requested = execution.cancel_requested_at
        assert requested is not None
        assert (
            asyncio.run(repo.request_cancellation(execution.id, history["workspace"])) == expected
        )
        assert execution.cancel_requested_at == requested
    elif status == "pending":
        assert execution.status == "cancelled" and execution.completed_at is not None
        assert execution.claimed_by is execution.heartbeat_at is execution.lease_expires_at is None
    else:
        assert (execution.status, execution.cancel_requested_at, execution.completed_at) == previous
    # The adapter has no commit method: transaction ownership remains in the service.


def test_waiting_cancellation_preserves_completed_steps_and_other_approvals(history):
    session = history["session"]
    ExecutionStep.__table__.create(history["engine"])
    HumanApproval.__table__.create(history["engine"])
    execution = history["run"](10, status="waiting_for_approval")
    completed = ExecutionStep(
        id=uuid4(), execution_id=execution.id, node_id="done", status="completed", sequence=1
    )
    waiting = ExecutionStep(
        id=uuid4(),
        execution_id=execution.id,
        node_id="review",
        status="waiting_for_approval",
        sequence=2,
    )
    session.add_all([completed, waiting])
    approvals = []
    for status, workspace in [
        ("pending", history["workspace"]),
        ("approved", history["workspace"]),
        ("pending", history["other_workspace"]),
    ]:
        row = HumanApproval(
            id=uuid4(),
            execution_id=execution.id,
            execution_step_id=waiting.id,
            workspace_id=workspace,
            approver_user_id=uuid4(),
            message="Review",
            status=status,
        )
        session.add(row)
        approvals.append(row)
    session.commit()
    repo = history["service"].repository
    assert asyncio.run(repo.request_cancellation(execution.id, history["workspace"])) == "cancelled"
    assert [row.status for row in approvals] == ["cancelled", "approved", "pending"]
    assert completed.status == "completed" and waiting.status == "cancelled"
    assert (
        asyncio.run(repo.request_cancellation(execution.id, history["workspace"]))
        == "already_cancelled"
    )
    steps = asyncio.run(repo.list_execution_steps(execution.id, history["workspace"]))
    assert [step.id for step in steps] == [completed.id, waiting.id]
    assert asyncio.run(repo.list_execution_steps(execution.id, history["other_workspace"])) is None
    assert (
        asyncio.run(repo.list_execution_steps(history["original"].id, history["workspace"])) == []
    )


def test_lineage_and_dlq_metadata_remain_workspace_scoped(history):
    from app.models.dead_letter_event import DeadLetterEvent

    session = history["session"]
    events = []
    for key, workspace in [
        ("original", history["workspace"]),
        ("foreign", history["other_workspace"]),
    ]:
        event = DeadLetterEvent(
            id=uuid4(), execution_id=history[key].id, workspace_id=workspace, status="pending"
        )
        session.add(event)
        events.append(event)
    session.commit()
    repo = history["service"].repository
    lineage = asyncio.run(repo.get_execution_lineage(history["workspace"], history["latest"].id))
    assert lineage == {
        "execution_group_id": history["original"].id,
        "attempt_count": 3,
        "attempt_number": 3,
    }
    assert (
        asyncio.run(repo.get_execution_lineage(history["workspace"], history["foreign"].id)) == {}
    )
    recovery = asyncio.run(
        repo.get_recovery_events(history["workspace"], [event.execution_id for event in events])
    )
    assert recovery == {
        history["original"].id: {"dead_letter_event_id": events[0].id, "recovery_status": "pending"}
    }
    detail = asyncio.run(
        history["service"].get_execution_by_id(history["original"].id, history["workspace"])
    )
    assert detail["dead_letter_event_id"] == events[0].id
