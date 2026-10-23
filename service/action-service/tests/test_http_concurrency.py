"""Use real action service semaphore; replace only external connector and DB."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.grpc import action_server as server
from app.grpc.generated.action import action_pb2


@pytest.mark.parametrize('outcome', ['success', 'exception', 'cancel'])
async def test_http_capacity_and_other_connectors(monkeypatch, outcome):
    monkeypatch.setattr(server, 'MAX_CONCURRENT_HTTP_REQUESTS', 10)
    session = AsyncMock()
    monkeypatch.setattr(server, 'AsyncSessionLocal', lambda: session)
    async def connection(**kwargs):
        return SimpleNamespace(provider='http' if kwargs['connection_id'].int != 0 else 'mock_payment', auth_type='none', credential=None)
    monkeypatch.setattr(server, 'get_connection', connection)
    gate, saturated = asyncio.Event(), asyncio.Event()
    active = peak = entered = 0
    async def execute(**kwargs):
        nonlocal active, peak, entered
        active += 1
        entered += 1
        peak = max(peak, active)
        if active == 10:
            saturated.set()
        try:
            await gate.wait()
            if outcome == 'exception':
                raise RuntimeError('controlled failure')
            return {'success': True, 'status_code': 200}
        finally:
            active -= 1
    connector = SimpleNamespace(execute=execute)
    other = SimpleNamespace(execute=AsyncMock(return_value={'ok': True}))
    monkeypatch.setattr(server, 'connector_registry', {'http': connector, 'mock_payment': other})
    service = server.ActionInternalService()
    def request(connection_id):
        return action_pb2.ExecuteActionRequest(workspace_id=str(uuid4()), connection_id=str(connection_id), action='request')
    tasks = [asyncio.create_task(service.ExecuteAction(request(uuid4()), None)) for _ in range(25)]
    await asyncio.wait_for(saturated.wait(), 2)
    await asyncio.sleep(0)
    assert entered == 10 and not any(task.done() for task in tasks)
    assert (await asyncio.wait_for(service.ExecuteAction(request(UUID(int=0)), None), 2)).success
    other.execute.assert_awaited_once()
    if outcome == 'cancel':
        tasks[0].cancel()
        await asyncio.gather(tasks[0], return_exceptions=True)
    gate.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert peak == 10 and active == 0 and service.http_semaphore._value == 10
    if outcome == 'exception':
        assert all(not result.success for result in results)
    else:
        assert sum(getattr(result, 'success', False) for result in results) == (24 if outcome == 'cancel' else 25)
