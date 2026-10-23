"""Exercise real dispatcher/provider semaphores with controlled async work."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.ai import service as ai
from app.services import execution_dispatcher as dispatcher


@pytest.mark.parametrize('count', [5, 10, 25])
@pytest.mark.parametrize('outcome', ['success', 'exception', 'cancel'])
async def test_dispatcher_capacity_and_cleanup(monkeypatch, count, outcome):
    monkeypatch.setattr(dispatcher, 'EXECUTION_MAX_CONCURRENCY', 5)
    pending = [uuid4() for _ in range(count)]
    started = asyncio.Queue()
    gate = asyncio.Event()
    active = peak = 0

    async def inspect(limit):
        return {'pending': [{'execution_id': str(x)} for x in pending[:limit]]}

    async def execute(execution_id):
        nonlocal active, peak
        pending.remove(execution_id)
        active += 1
        peak = max(peak, active)
        await started.put(execution_id)
        try:
            await gate.wait()
            if outcome == 'exception':
                raise RuntimeError('controlled worker failure')
        finally:
            active -= 1

    monkeypatch.setattr(dispatcher, 'inspect_recoverable_executions', inspect)
    monkeypatch.setattr(dispatcher, 'execute_pending_execution', execute)
    worker = dispatcher.ExecutionDispatcher()
    while pending:
        gate.clear()
        expected = min(5, len(pending))
        await worker.dispatch_pending()
        for _ in range(expected):
            await asyncio.wait_for(started.get(), 2)
        assert len(worker.active_tasks) == expected
        await worker.dispatch_pending()
        tasks = list(worker.active_tasks)
        if outcome == 'cancel':
            for task in tasks:
                task.cancel()
        gate.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0)
        assert worker.active_ids == set()
        assert worker.active_tasks == set()
        assert worker.wakeup_event.is_set()
        assert worker.semaphore._value == 5
    await worker.shutdown()
    assert peak == 5 and active == 0


@pytest.mark.parametrize('outcome', ['success', 'exception', 'cancel'])
async def test_ai_shared_capacity_across_instances_and_providers(monkeypatch, outcome):
    monkeypatch.setattr(ai, 'ai_semaphore', asyncio.Semaphore(10))
    gate = asyncio.Event()
    saturated = asyncio.Event()
    active = peak = entered = 0

    async def generate(**kwargs):
        nonlocal active, peak, entered
        active += 1
        entered += 1
        peak = max(peak, active)
        if active == 10:
            saturated.set()
        try:
            await gate.wait()
            if outcome == 'exception':
                raise RuntimeError('controlled provider failure')
            return ai.AIResponse('answer', 'test', 1, 1)
        finally:
            active -= 1

    services = [ai.AIService() for _ in range(3)]
    for service in services:
        service.providers = {name: SimpleNamespace(generate=generate) for name in ('openai', 'gemini', 'anthropic')}
    tasks = [asyncio.create_task(services[i % 3].generate(('openai', 'gemini', 'anthropic')[i % 3], 'fake', 'test', '', 'prompt')) for i in range(25)]
    await asyncio.wait_for(saturated.wait(), 2)
    await asyncio.sleep(0)
    assert entered == 10 and not any(task.done() for task in tasks)
    if outcome == 'cancel':
        tasks[0].cancel()
        await asyncio.gather(tasks[0], return_exceptions=True)
    gate.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert peak == 10 and active == 0
    assert ai.ai_semaphore._value == 10
    if outcome == 'exception':
        assert all(isinstance(result, ai.AIResponseError) for result in results)
    else:
        assert sum(isinstance(result, ai.AIResponse) for result in results) == (24 if outcome == 'cancel' else 25)


@pytest.mark.parametrize('failure', ['lost', 'exception', 'cancel'])
async def test_heartbeat_stops_owner_on_lease_loss(monkeypatch, failure):
    from app.services import execution_queue as queue
    owner = SimpleNamespace(cancel=lambda: cancellations.append(True))
    cancellations = []
    renew = AsyncMock(return_value=False)
    if failure == 'exception':
        renew.side_effect = RuntimeError('database unavailable')
    elif failure == 'cancel':
        renew.side_effect = asyncio.CancelledError()
    monkeypatch.setattr(queue, 'renew_execution_lease', renew)
    monkeypatch.setattr(queue.asyncio, 'sleep', AsyncMock())
    if failure == 'cancel':
        with pytest.raises(asyncio.CancelledError):
            await queue.execution_heartbeat(uuid4(), 'worker', owner, 1, 2)
        assert not cancellations
    else:
        await queue.execution_heartbeat(uuid4(), 'worker', owner, 1, 2)
        assert cancellations == [True]


async def test_dispatcher_polling_wakeup_shutdown_and_invalid_capacity(monkeypatch):
    monkeypatch.setattr(dispatcher, 'EXECUTION_MAX_CONCURRENCY', 0)
    with pytest.raises(ValueError):
        dispatcher.ExecutionDispatcher()
    monkeypatch.setattr(dispatcher, 'EXECUTION_MAX_CONCURRENCY', 5)
    worker = dispatcher.ExecutionDispatcher()
    polls = []
    async def dispatch():
        polls.append(True)
        if len(polls) == 2:
            worker.wakeup_event.set()
        if len(polls) == 3:
            worker.running = False
    monkeypatch.setattr(worker, 'dispatch_pending', dispatch)
    real_wait = asyncio.wait_for
    timeouts = []
    async def wait(awaitable, timeout):
        timeouts.append(timeout)
        return await real_wait(awaitable, timeout=0.001)
    monkeypatch.setattr(dispatcher.asyncio, 'wait_for', wait)
    await worker.run()
    assert len(polls) == 3 and timeouts == [2, 2]
    assert not worker.running
    blocked = asyncio.create_task(asyncio.Event().wait())
    worker.active_tasks.add(blocked)
    shutdown = asyncio.create_task(worker.shutdown())
    await asyncio.sleep(0)
    assert not shutdown.done()
    blocked.cancel()
    await shutdown


async def test_dispatcher_duplicate_id_does_not_consume_permit(monkeypatch):
    execution_id = uuid4()
    worker = dispatcher.ExecutionDispatcher()
    worker.active_ids.add(execution_id)
    inspect = AsyncMock(return_value={'pending': [{'execution_id': str(execution_id)}]})
    monkeypatch.setattr(dispatcher, 'inspect_recoverable_executions', inspect)
    before = worker.semaphore._value
    await worker.dispatch_pending()
    assert worker.semaphore._value == before and not worker.active_tasks
