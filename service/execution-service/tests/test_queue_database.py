"""Real independent PostgreSQL transactions for claiming, leases and replay."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.engine import make_url

from app.db.database import engine, DATABASE_URL, AsyncSessionLocal
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.dead_letter_event import DeadLetterEvent
from app.models.idempotency_key import IdempotencyKey
from app.repositories.execution_queue import ExecutionQueueRepository
from app.repositories.dead_letter import DeadLetterRepository
from app.services import execution_queue as queue
from app.services import dead_letter


@pytest_asyncio.fixture
async def workspace():
    url = make_url(DATABASE_URL)
    assert url.database == 'ci_test' and url.host in {'localhost', '127.0.0.1'}, 'isolated ci_test database required'
    workspace_id = uuid4()
    try:
        yield workspace_id
    finally:
        async with AsyncSessionLocal() as session:
            ids = select(Execution.id).where(Execution.workspace_id == workspace_id)
            await session.execute(delete(DeadLetterEvent).where(DeadLetterEvent.workspace_id == workspace_id))
            await session.execute(delete(IdempotencyKey).where(IdempotencyKey.workspace_id == workspace_id))
            await session.execute(delete(ExecutionStep).where(ExecutionStep.execution_id.in_(ids)))
            await session.execute(delete(Execution).where(Execution.workspace_id == workspace_id))
            await session.commit()
        await engine.dispose()


async def pending(workspace):
    async with AsyncSessionLocal() as session:
        item = await ExecutionQueueRepository(session).create_pending(workspace_id=workspace, workflow_id=uuid4(), workflow_version_id=uuid4(), trigger_type='manual', trigger_data={}, event_key=str(uuid4()))
        await session.commit()
        return item.id


async def test_concurrent_claim_owner_renewal_expiry_and_finalization(workspace):
    execution_id = await pending(workspace)
    claims = await asyncio.gather(*(queue.claim_pending_execution(execution_id, f'worker-{i}') for i in range(25)))
    assert sum(claims) == 1
    owner = f'worker-{claims.index(True)}'
    assert not await queue.renew_execution_lease(execution_id, 'intruder')
    assert await queue.renew_execution_lease(execution_id, owner, 300)
    assert not await queue.finalize_execution(execution_id, 'intruder', 'completed')
    async with AsyncSessionLocal() as session:
        await session.execute(update(Execution).where(Execution.id == execution_id).values(lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
        await session.commit()
        expired = await ExecutionQueueRepository(session).list_expired_executions()
        assert execution_id in {item.id for item in expired}
    assert not await queue.renew_execution_lease(execution_id, owner)
    assert not await queue.finalize_execution(execution_id, owner, 'completed')


async def test_duplicate_events_have_one_execution_and_workspace_key(monkeypatch, workspace):
    client = SimpleNamespace(validate_workflow_version=AsyncMock(return_value=SimpleNamespace(valid=True, status='published', workflow_status='active')), close=AsyncMock())
    monkeypatch.setattr(queue, 'WorkflowClient', lambda: client)
    event = dict(event_id=str(uuid4()), workspace_id=str(workspace), workflow_id=str(uuid4()), workflow_version_id=str(uuid4()), trigger_type='manual', payload={})
    ids = await asyncio.gather(*(queue.create_pending_execution(event) for _ in range(10)))
    assert len(set(ids)) == 1
    async with AsyncSessionLocal() as session:
        repo = ExecutionQueueRepository(session)
        assert (await repo.get_by_event_key(workspace, 'workflow.triggered:'+event['event_id'])).id == ids[0]
        assert await repo.get_by_event_key(uuid4(), 'workflow.triggered:'+event['event_id']) is None
        assert ids[0] in {item.id for item in await repo.list_pending_executions()}


@pytest.mark.parametrize('method', ['GET', 'HEAD', 'POST'])
async def test_dlq_creation_safe_replay_duplicate_and_resolution(monkeypatch, workspace, method):
    execution_id = await pending(workspace)
    assert await queue.claim_pending_execution(execution_id, 'owner')
    async with AsyncSessionLocal() as session:
        execution = await session.get(Execution, execution_id)
        execution.context = {'trigger': {}, 'variables': {}, 'nodes': {}}
        session.add(ExecutionStep(id=uuid4(), execution_id=execution_id, node_id='http', node_type='action.http_request', status='failed', sequence=1, attempt=2))
        await session.commit()
    assert await queue.finalize_execution(execution_id, 'owner', 'failed', error={'message': 'timeout'})
    nodes = [{'node_id': 'http', 'node_type': 'action.http_request', 'configuration': {'method': method}}]
    client = SimpleNamespace(get_workflow_definition=AsyncMock(return_value=SimpleNamespace(nodes_json=json.dumps(nodes), edges_json='[]')), close=AsyncMock())
    monkeypatch.setattr(dead_letter, 'WorkflowClient', lambda: client)
    async with AsyncSessionLocal() as session:
        service = dead_letter.DeadLetterService(DeadLetterRepository(session))
        page = await service.list_events(workspace, status='pending')
        assert page['total'] == 1 and page['items'][0]['attempts'] == 2
        event_id = page['items'][0]['id']
        assert (await service.get_event(event_id, workspace))['failed_node_type'] == 'action.http_request'
        assert await service.get_event(event_id, uuid4()) is None
        if method == 'POST':
            with pytest.raises(ValueError, match='unsafe_replay'):
                await service.replay_event(event_id, workspace)
            assert (await service.resolve_event(event_id, workspace))['status'] == 'resolved'
            assert await service.resolve_event(event_id, workspace) is None
        else:
            result = await service.replay_event(event_id, workspace)
            assert result['status'] == 'accepted'
            replay = await session.get(Execution, result['execution_id'])
            assert replay.status == 'pending' and replay.replay_start_node_id == 'http'
            assert replay.replay_of_execution_id == execution_id
        with pytest.raises(ValueError, match='already_handled'):
            await service.replay_event(event_id, workspace)
        with pytest.raises(ValueError, match='not_found'):
            await service.replay_event(event_id, uuid4())


@pytest.mark.parametrize('outcome', ['completed', 'failed'])
@pytest.mark.parametrize('cancel_requested', [False, True])
async def test_terminal_finalization_persists_status_error_and_dlq(workspace, outcome, cancel_requested):
    execution_id = await pending(workspace)
    assert await queue.claim_pending_execution(execution_id, 'owner')
    error = {'message': 'Refund failed', 'details': {'code': 'declined'}} if outcome == 'failed' else None
    context = {'trigger': {}, 'variables': {}, 'nodes': {'last': {'success': True}}}
    async with AsyncSessionLocal() as session:
        execution = await session.get(Execution, execution_id)
        if cancel_requested:
            execution.cancel_requested_at = datetime.now(timezone.utc)
        session.add(ExecutionStep(
            id=uuid4(), execution_id=execution_id, node_id='last',
            node_type='action.http_request', status=outcome, sequence=1, attempt=1,
        ))
        await session.commit()

    expected = 'cancelled' if cancel_requested else outcome
    assert await queue.finalize_execution(
        execution_id, 'owner', outcome, context_data=context, error=error,
    ) == expected
    async with AsyncSessionLocal() as session:
        execution = await session.get(Execution, execution_id)
        assert execution.status == expected
        assert execution.completed_at is not None
        assert execution.claimed_by is None and execution.lease_expires_at is None
        assert execution.heartbeat_at is None
        assert execution.error == (None if cancel_requested else error)
        assert execution.context == context
        events = (await session.execute(select(DeadLetterEvent).where(
            DeadLetterEvent.execution_id == execution_id,
        ))).scalars().all()
        assert len(events) == (1 if expected == 'failed' else 0)
        if events:
            assert events[0].error == error
            assert events[0].execution_step_id is not None
    # A stale worker cannot overwrite a terminal result or create another DLQ entry.
    assert await queue.finalize_execution(execution_id, 'owner', 'failed', error=error) is None
