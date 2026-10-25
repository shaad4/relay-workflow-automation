import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from uuid import uuid4

import grpc
import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.workflow_schedule import ScheduleUpdate
from app.services import workflow_schedule_service as service


@pytest.mark.parametrize(
    "eligibility", ["active", "inactive", "missing", "wrong-trigger", "wrong-version"]
)
@pytest.mark.parametrize("operation", ["payload", "resume", "interval"])
def test_updates_respect_workflow_lifecycle(monkeypatch, eligibility, operation):
    workflow_id, workspace_id, version_id = uuid4(), uuid4(), uuid4()
    schedule = NS(
        id=uuid4(),
        workflow_id=workflow_id,
        workflow_version_id=version_id,
        enabled=True,
        next_run_at=None,
        schedule_type="interval",
        interval_minutes=30,
        cron_expression=None,
        timezone="Asia/Kolkata",
        input_data={},
    )
    calls = []

    class Client:
        async def get_published_version(self, **kwargs):
            assert kwargs == {"workflow_id": str(workflow_id), "workspace_id": str(workspace_id)}
            if eligibility == "missing":
                raise grpc.aio.AioRpcError(grpc.StatusCode.NOT_FOUND, (), (), "Missing")
            return NS(version_id=str(uuid4() if eligibility == "wrong-version" else version_id))

        async def get_workflow_definition(self, **kwargs):
            if eligibility == "inactive":
                raise grpc.aio.AioRpcError(grpc.StatusCode.FAILED_PRECONDITION, (), (), "Inactive")
            return NS(
                nodes_json=json.dumps(
                    [
                        {
                            "node_type": "trigger.manual"
                            if eligibility == "wrong-trigger"
                            else "trigger.schedule"
                        }
                    ]
                )
            )

        async def close(self):
            calls.append("close")

    class Session:
        async def commit(self):
            calls.append("commit")

        async def refresh(self, value):
            assert value is schedule

    async def get_schedule(**kwargs):
        assert kwargs["workspace_id"] == workspace_id
        return schedule

    monkeypatch.setattr(service, "WorkflowGrpcClient", Client)
    monkeypatch.setattr(service, "get_schedule", get_schedule)
    data = {
        "payload": {"input_data": {"report": "daily"}},
        "resume": {"enabled": True},
        "interval": {"interval_minutes": 5},
    }[operation]
    if operation == "resume" and eligibility != "active":
        with pytest.raises(HTTPException) as failure:
            asyncio.run(
                service.update_schedule(
                    schedule.id, workspace_id, ScheduleUpdate(**data), Session()
                )
            )
        assert failure.value.status_code == 409
        assert "commit" not in calls
    else:
        result = asyncio.run(
            service.update_schedule(schedule.id, workspace_id, ScheduleUpdate(**data), Session())
        )
        assert (result.next_run_at is not None) == (
            operation == "resume" and eligibility == "active"
        )
        assert result.enabled is True
        assert "commit" in calls
    assert "close" in calls


@pytest.mark.parametrize("enabled", [True, False])
def test_editing_live_or_paused_schedule_preserves_pause(monkeypatch, enabled):
    version_id = uuid4()
    schedule = NS(
        id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=version_id,
        enabled=enabled,
        next_run_at=datetime.now(timezone.utc) if enabled else None,
        schedule_type="interval",
        interval_minutes=30,
        cron_expression=None,
        timezone="UTC",
        input_data={},
    )

    class Client:
        async def get_published_version(self, **kwargs):
            return NS(version_id=str(version_id))

        async def get_workflow_definition(self, **kwargs):
            return NS(nodes_json='[{"node_type":"trigger.schedule"}]')

        async def close(self):
            pass

    class Session:
        async def commit(self):
            pass

        async def refresh(self, value):
            pass

    async def get_schedule(**kwargs):
        return schedule

    monkeypatch.setattr(service, "WorkflowGrpcClient", Client)
    monkeypatch.setattr(service, "get_schedule", get_schedule)
    result = asyncio.run(
        service.update_schedule(schedule.id, uuid4(), ScheduleUpdate(interval_minutes=5), Session())
    )
    assert result.enabled is enabled
    assert result.interval_minutes == 5
    assert (result.next_run_at is not None) is enabled


def test_unavailable_workflow_validation_never_mutates_schedule(monkeypatch):
    schedule = NS(id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), input_data={})

    class Client:
        async def get_published_version(self, **kwargs):
            raise grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE, (), (), "Unavailable")

        async def close(self):
            pass

    async def get_schedule(**kwargs):
        return schedule

    monkeypatch.setattr(service, "WorkflowGrpcClient", Client)
    monkeypatch.setattr(service, "get_schedule", get_schedule)
    with pytest.raises(HTTPException) as failure:
        asyncio.run(
            service.update_schedule(
                schedule.id, uuid4(), ScheduleUpdate(input_data={"changed": True}), NS()
            )
        )
    assert failure.value.status_code == 503
    assert schedule.input_data == {}
