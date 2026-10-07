import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import execution_service
from app.engine.exceptions import ActionExecutionFailed, HumanApprovalRequired


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _value):
        _value.id = uuid4()
        return None

    async def rollback(self):
        self.rollbacks += 1


def event():
    return {
        "workspace_id": str(uuid4()),
        "workflow_id": str(uuid4()),
        "workflow_version_id": str(uuid4()),
        "event_type": "workflow.triggered",
        "payload": {"email": "test@example.com"},
    }


def test_unpublished_event_is_rejected_before_execution_record(monkeypatch):
    target = event()
    session = FakeSession()
    calls = []

    class WorkflowClient:
        async def validate_workflow_version(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(valid=True, status="draft", workflow_status="active")

        async def close(self):
            calls.append("closed")

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)
    runner_calls = []
    monkeypatch.setattr(execution_service, "run_execution", lambda **kwargs: runner_calls.append(kwargs))

    with pytest.raises(ValueError, match="Workflow version is not published"):
        asyncio.run(execution_service.create_execution(target))

    assert calls[0] == {
        "workflow_id": target["workflow_id"],
        "version_id": target["workflow_version_id"],
        "workspace_id": target["workspace_id"],
    }
    assert calls[-1] == "closed"
    assert session.added == []
    assert session.commits == 0
    assert runner_calls == []


def test_published_event_creates_record_and_runs_pinned_version(monkeypatch):
    target = event()
    session = FakeSession()
    calls = []
    runner_calls = []

    class WorkflowClient:
        async def validate_workflow_version(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(valid=True, status="published", workflow_status="active")

        async def close(self):
            calls.append("closed")

    async def run(**kwargs):
        runner_calls.append(kwargs)

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(execution_service, "run_execution", run)

    execution = asyncio.run(execution_service.create_execution(target))

    assert session.commits == 3
    assert session.added == [execution]
    assert execution.workflow_version_id.hex == target["workflow_version_id"].replace("-", "")
    assert execution.trigger_data == target["payload"]
    assert runner_calls == [{
        "execution_id": execution.id,
        "workflow_id": target["workflow_id"],
        "workflow_version_id": target["workflow_version_id"],
        "workspace_id": target["workspace_id"],
        "trigger_data": target["payload"],
    }]


def test_inactive_workflow_event_is_rejected_before_execution_record(monkeypatch):
    target = event()
    session = FakeSession()

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="published", workflow_status="inactive")

        async def close(self):
            return None

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)
    with pytest.raises(ValueError, match="Workflow is inactive"):
        asyncio.run(execution_service.create_execution(target))
    assert session.added == []
    assert session.commits == 0


def test_missing_workflow_version_is_rejected_and_client_is_closed(monkeypatch):
    target = event()
    calls = []

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=False, status="published", workflow_status="active")

        async def close(self):
            calls.append("closed")

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    with pytest.raises(ValueError, match="Workflow or workflow version not found"):
        asyncio.run(execution_service.create_execution(target))
    assert calls == ["closed"]


def test_execution_waits_for_human_approval(monkeypatch):
    target = event()
    session = FakeSession()

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="PUBLISHED", workflow_status="ACTIVE")

        async def close(self):
            return None

    async def run(**_kwargs):
        raise HumanApprovalRequired("approval-node")

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(execution_service, "run_execution", run)

    execution = asyncio.run(execution_service.create_execution(target))

    assert execution.status == execution_service.ExecutionStatus.WAITING_FOR_APPROVAL
    assert execution.completed_at is None
    assert session.commits == 3
    assert session.rollbacks == 0


def test_action_failure_is_recorded_on_execution(monkeypatch):
    target = event()
    session = FakeSession()

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="published", workflow_status="active")

        async def close(self):
            return None

    async def run(**_kwargs):
        raise ActionExecutionFailed("payment-node", "gateway unavailable")

    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(execution_service, "run_execution", run)

    execution = asyncio.run(execution_service.create_execution(target))

    assert execution.status == execution_service.ExecutionStatus.FAILED
    assert execution.completed_at is not None
    assert execution.error == {"node_id": "payment-node", "message": "gateway unavailable"}
    assert session.commits == 3
    assert session.rollbacks == 0


def test_unexpected_database_error_rolls_back_and_propagates(monkeypatch):
    target = event()
    session = FakeSession()

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="published", workflow_status="active")

        async def close(self):
            return None

    async def fail_commit():
        raise RuntimeError("database unavailable")

    session.commit = fail_commit
    monkeypatch.setattr(execution_service, "WorkflowClient", WorkflowClient)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", lambda: session)

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(execution_service.create_execution(target))

    assert session.rollbacks == 1
