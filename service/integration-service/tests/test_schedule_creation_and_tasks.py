import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import grpc
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.workflow_schedule import ScheduleCreate
from app.services import workflow_schedule_service as service
from app.tasks import schedule_tasks as tasks


class Session:
    def __init__(self, row=None):
        self.row = row
        self.add = Mock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.refresh = AsyncMock()
        self.delete = AsyncMock()
        self.execute = AsyncMock(return_value=NS(scalar_one_or_none=lambda: row, scalars=lambda: NS(all=lambda: [row] if row else []), rowcount=1))
        self.get = AsyncMock(return_value=row)
    async def __aenter__(self): return self
    async def __aexit__(self, *_args): pass


@pytest.fixture
def creation(monkeypatch):
    workspace, version = uuid4(), uuid4()
    data = ScheduleCreate(workflow_id=uuid4(), schedule_type="interval", interval_minutes=30, input_data={"report": "daily"})
    client = NS(get_published_version=AsyncMock(return_value=NS(version_id=str(version))), get_workflow_definition=AsyncMock(return_value=NS(nodes_json='[{"node_type":"trigger.schedule"}]')), close=AsyncMock())
    monkeypatch.setattr(service, "WorkflowGrpcClient", lambda: client)
    return NS(workspace=workspace, version=version, data=data, client=client, session=Session())


@pytest.mark.parametrize("enabled", [True, False])
def test_create_schedule_binds_workspace_and_published_version(creation, enabled):
    creation.data.enabled = enabled
    before = datetime.now(timezone.utc)
    row = asyncio.run(service.create_schedule(creation.data, creation.workspace, creation.session))
    assert row.workspace_id == creation.workspace and row.workflow_version_id == creation.version
    assert row.workflow_id == creation.data.workflow_id and row.input_data == {"report": "daily"}
    assert row.enabled is enabled
    if enabled:
        assert before + timedelta(minutes=30) <= row.next_run_at <= datetime.now(timezone.utc) + timedelta(minutes=30)
    else:
        assert row.next_run_at is None
    creation.session.add.assert_called_once_with(row)
    creation.session.commit.assert_awaited_once()
    creation.session.refresh.assert_awaited_once_with(row)
    creation.client.close.assert_awaited_once()


@pytest.mark.parametrize("code,status", [(grpc.StatusCode.NOT_FOUND,404),(grpc.StatusCode.FAILED_PRECONDITION,409),(grpc.StatusCode.DEADLINE_EXCEEDED,504),(grpc.StatusCode.UNAVAILABLE,503)])
def test_schedule_creation_workflow_errors(creation, code, status):
    creation.client.get_published_version.side_effect = grpc.aio.AioRpcError(code, (), (), "test")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_schedule(creation.data, creation.workspace, creation.session))
    assert exc.value.status_code == status
    creation.client.close.assert_awaited_once()
    creation.session.add.assert_not_called()


@pytest.mark.parametrize("nodes,status", [('bad',502), ('{}',502), ('[]',409), ('[{"node_type":"trigger.manual"}]',409), ('[{"node_type":"trigger.schedule"},{"node_type":"trigger.schedule"}]',409)])
def test_schedule_creation_requires_valid_scheduled_workflow(creation, nodes, status):
    creation.client.get_workflow_definition.return_value.nodes_json = nodes
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_schedule(creation.data, creation.workspace, creation.session))
    assert exc.value.status_code == status
    creation.session.commit.assert_not_awaited()


def test_duplicate_schedule_rolls_back_and_reports_conflict(creation):
    creation.session.commit.side_effect = IntegrityError("insert", {}, RuntimeError("duplicate"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_schedule(creation.data, creation.workspace, creation.session))
    assert exc.value.status_code == 409
    creation.session.rollback.assert_awaited_once()
    creation.session.refresh.assert_not_awaited()


@pytest.mark.parametrize("args", [
    ("interval", 5, None, "Invalid/Timezone"), ("interval", None, None, "UTC"),
    ("interval", 5, "* * * * *", "UTC"), ("cron", 5, "* * * * *", "UTC"),
    ("cron", None, None, "UTC"), ("cron", None, "* * * * * *", "UTC"), ("cron", None, "not cron", "UTC"),
])
def test_invalid_schedule_time_rejected(args):
    with pytest.raises(HTTPException) as exc:
        service.calculate_next_run(*args)
    assert exc.value.status_code == 422


def test_cron_returns_next_local_occurrence_in_utc():
    from zoneinfo import ZoneInfo
    before = datetime.now(timezone.utc)
    next_run = service.calculate_next_run("cron", None, "0 9 * * *", "Asia/Kolkata")
    assert before < next_run <= before + timedelta(days=1, seconds=1)
    assert next_run.tzinfo == timezone.utc
    assert next_run.astimezone(ZoneInfo("Asia/Kolkata")).hour == 9
    assert next_run.minute == 30


def test_schedule_reads_and_deletes_are_workspace_scoped():
    row = NS(id=uuid4())
    session = Session(row)
    workspace = uuid4()
    assert asyncio.run(service.list_schedules(workspace, session)) == [row]
    assert asyncio.run(service.get_schedule(row.id, workspace, session)) is row
    statement = session.execute.await_args.args[0]
    assert workspace in statement.compile().params.values()
    assert row.id in statement.compile().params.values()
    asyncio.run(service.delete_schedule(row.id, workspace, session))
    session.delete.assert_awaited_once_with(row)
    session.commit.assert_awaited_once()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.get_schedule(row.id, workspace, Session()))
    assert exc.value.status_code == 404


@pytest.mark.parametrize("has_trigger,active,enabled", [(True,True,True),(True,True,False),(True,False,True),(False,True,True)])
def test_publication_sync_preserves_pause_and_suspends_ineligible_schedules(has_trigger, active, enabled):
    original_version, new_version = uuid4(), uuid4()
    row = NS(workflow_version_id=original_version, enabled=enabled, next_run_at=datetime.now(timezone.utc), schedule_type="interval", interval_minutes=5, cron_expression=None, timezone="UTC")
    session = Session(row)
    assert asyncio.run(service.sync_workflow_schedule(uuid4(), uuid4(), new_version, has_trigger, active, session)) == 1
    assert row.enabled is enabled
    assert row.workflow_version_id == (new_version if has_trigger else original_version)
    assert (row.next_run_at is not None) == (has_trigger and active and enabled)
    session.commit.assert_awaited_once()


def test_lifecycle_missing_schedule_and_bulk_cleanup():
    session = Session()
    workflow, workspace, version = uuid4(), uuid4(), uuid4()
    assert asyncio.run(service.sync_workflow_schedule(workflow, workspace, version, True, True, session)) == 0
    session.commit.assert_not_awaited()
    for operation in [service.suspend_workflow_schedule, service.delete_workflow_schedule]:
        assert asyncio.run(operation(workflow, workspace, session)) == 1
        assert {workflow, workspace} <= set(session.execute.await_args.args[0].compile().params.values())
    assert session.commit.await_count == 2


def schedule():
    return NS(id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), workspace_id=uuid4(), schedule_type="interval", interval_minutes=5, cron_expression=None, timezone="UTC", enabled=True, next_run_at=datetime.now(timezone.utc)-timedelta(seconds=30), input_data={"report": "daily"})


def test_due_lookup_returns_serializable_payload_and_filters(monkeypatch):
    row = schedule()
    session = Session(row)
    monkeypatch.setattr(tasks, "AsyncSessionLocal", lambda: session)
    due = asyncio.run(tasks.find_due_schedules())
    assert due == [{"id":str(row.id), "workflow_id":str(row.workflow_id), "workflow_version_id":str(row.workflow_version_id), "workspace_id":str(row.workspace_id), "schedule_type":"interval", "next_run_at":row.next_run_at.isoformat(), "input_data":row.input_data}]
    query = str(session.execute.await_args.args[0])
    assert "enabled IS true" in query and "next_run_at IS NOT NULL" in query and "next_run_at <=" in query


@pytest.mark.parametrize("state", ["eligible", "missing", "paused", "suspended", "claimed-by-other-worker"])
def test_due_advance_only_dispatches_successful_claims(monkeypatch, state):
    row = schedule()
    due_at = row.next_run_at
    due = {"id":str(row.id)}
    if state == "paused": row.enabled = False
    if state == "suspended": row.next_run_at = None
    session = Session(None if state == "missing" else row)
    updated_id = None if state == "claimed-by-other-worker" else row.id
    session.execute.return_value = NS(scalar_one_or_none=lambda: updated_id)
    monkeypatch.setattr(tasks, "find_due_schedules", AsyncMock(return_value=[due]))
    monkeypatch.setattr(tasks, "AsyncSessionLocal", lambda: session)
    result = asyncio.run(tasks.advance_due_schedules())
    assert result == ([due] if state == "eligible" else [])
    if state in {"missing","paused","suspended"}:
        session.commit.assert_not_awaited()
    else:
        session.commit.assert_awaited_once()
        statement = session.execute.await_args.args[0]
        values = statement.compile().params
        assert due_at in values.values() and row.id in values.values()
        assert "next_run_at =" in str(statement) and "RETURNING" in str(statement)
        assert any(isinstance(value, datetime) and value > due_at for value in values.values())


@pytest.mark.parametrize("fails", [False,True])
def test_scheduled_events_preserve_payload_and_close_producer(monkeypatch, fails):
    row = schedule()
    item = {key:str(getattr(row,key)) for key in ["workspace_id","workflow_id","workflow_version_id"]}
    item["input_data"] = row.input_data
    start, stop = AsyncMock(), AsyncMock()
    publish = AsyncMock(side_effect=RuntimeError("Kafka unavailable") if fails else None)
    monkeypatch.setattr(tasks,"start_producer",start)
    monkeypatch.setattr(tasks,"stop_producer",stop)
    monkeypatch.setattr(tasks,"publish_workflow_triggered",publish)
    if fails:
        with pytest.raises(RuntimeError,match="Kafka unavailable"):
            asyncio.run(tasks.publish_scheduled_events([item]))
    else:
        assert asyncio.run(tasks.publish_scheduled_events([item,item])) == 2
        assert publish.await_args_list[0].args[0].event_id != publish.await_args_list[1].args[0].event_id
    event = publish.await_args_list[0].args[0]
    assert event.trigger_type == "schedule" and event.payload == row.input_data
    assert event.workspace_id == row.workspace_id and event.workflow_version_id == row.workflow_version_id
    start.assert_awaited_once()
    stop.assert_awaited_once()


def test_periodic_task_processes_due_schedules_without_broker(monkeypatch):
    advance = AsyncMock(return_value=[])
    start = AsyncMock()
    monkeypatch.setattr(tasks,"advance_due_schedules",advance)
    monkeypatch.setattr(tasks,"start_producer",start)
    assert tasks.check_due_schedules.run() == 0
    advance.assert_awaited_once()
    start.assert_not_awaited()
