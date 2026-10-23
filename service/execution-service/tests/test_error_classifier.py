"""Focused failure reporting checks; retry policy stays in the existing helper."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import grpc
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.engine.error_classifier import classify_error, action_failure
from app.engine.exceptions import RetryExhaustedError
from app.ai.exceptions import AIRateLimitError
from app.engine import retry

@pytest.mark.parametrize('status,code', [(404, 'HTTP_NOT_FOUND'), (503, 'HTTP_SERVICE_UNAVAILABLE'), (401, 'HTTP_UNAUTHORIZED'), (418, 'HTTP_ERROR')])
def test_http_metadata_is_allowlisted(status, code):
    response = SimpleNamespace(result_json=json.dumps({'status_code': status, 'body': 'secret-token', 'headers': {'Authorization': 'secret-token'}}), error='secret-token')
    exc = action_failure('http_1', response, retryable=status == 503, attempts_used=3)
    error = classify_error(exc, 'http_1', 'action.http_request')
    assert error['code'] == code
    assert error['status_code'] == status
    assert error['attempts_used'] == 3
    assert 'secret-token' not in json.dumps(error)

def test_ai_and_unknown_are_safe():
    assert classify_error(AIRateLimitError('secret-token'), 'ai_1', 'ai.generate')['code'] == 'AI_RATE_LIMITED'
    error = classify_error(RuntimeError('postgres://password@private'))
    assert error['code'] == 'EXECUTION_FAILED'
    assert 'password' not in json.dumps(error)

def test_rag_wrapped_error_keeps_attempts():
    cause = grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE, None, None, 'secret document')
    exc = RetryExhaustedError(3)
    exc.__cause__ = cause
    error = classify_error(exc, 'rag_1', 'ai.rag_search')
    assert error['code'] == 'RAG_UNAVAILABLE'
    assert error['attempts_used'] == 3
    assert 'secret document' not in json.dumps(error)

def test_retry_policy_and_count_unchanged(monkeypatch):
    async def no_sleep(_): pass
    monkeypatch.setattr(retry.asyncio, 'sleep', no_sleep)
    for method, expected in [('GET', 3), ('POST', 1)]:
        calls = []
        async def operation():
            calls.append(1)
            raise action_failure('http', SimpleNamespace(result_json='{"status_code":503}', error='failure'), retryable=True)
        with pytest.raises(Exception) as failure:
            asyncio.run(retry.execute_with_retry(operation, node_id='http', method=method))
        assert len(calls) == expected
        assert classify_error(failure.value, 'http', 'action.http_request')['attempts_used'] == expected

@pytest.mark.parametrize("kind", ["http503", "http404", "ai", "rag"])
def test_step_execution_and_dlq_keep_same_failure(monkeypatch, kind):
    from datetime import datetime, timezone
    from uuid import uuid4
    from unittest.mock import AsyncMock, MagicMock
    from app.engine import runner
    from app.services import execution_queue
    from app.engine.step_status import ExecutionStepStatus
    from app.engine.status import ExecutionStatus
    response = SimpleNamespace(result_json='{"status_code":503}', error='secret-token')
    exc = action_failure('http_1', response, retryable=True, attempts_used=3)
    exc.failed_node_type = 'action.http_request'
    if kind == "http404":
        exc = action_failure('http_1', SimpleNamespace(result_json='{"status_code":404}', error='secret-token'))
        exc.failed_node_type = 'action.http_request'
    elif kind == "ai":
        exc = AIRateLimitError('secret-token')
        exc.node_id, exc.failed_node_type, exc.attempts_used = 'ai_1', 'ai.generate', 3
    elif kind == "rag":
        exc = RetryExhaustedError(3)
        exc.__cause__ = grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE, None, None, 'secret-token')
        exc.node_id, exc.failed_node_type = 'rag_1', 'ai.rag_search'
    error = classify_error(exc)
    assert error['code'] == {'http503': 'HTTP_SERVICE_UNAVAILABLE', 'http404': 'HTTP_NOT_FOUND', 'ai': 'AI_RATE_LIMITED', 'rag': 'RAG_UNAVAILABLE'}[kind]
    assert error['automatic_retries_exhausted'] == (kind != 'http404')
    step = SimpleNamespace(id=uuid4(), status=ExecutionStepStatus.RUNNING, started_at=datetime.now(timezone.utc))
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = AsyncMock(return_value=step)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    monkeypatch.setattr(runner, 'AsyncSessionLocal', lambda: session)
    asyncio.run(runner.mark_step_failed(step.id, error, error['attempts_used']))
    assert step.error == error and step.attempt == error['attempts_used']
    execution_id = uuid4()
    results = [MagicMock(), MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = execution_id
    results[1].scalar_one.return_value = SimpleNamespace(workspace_id=uuid4())
    results[2].scalar_one_or_none.return_value = step
    session.execute = AsyncMock(side_effect=results)
    monkeypatch.setattr(execution_queue, 'AsyncSessionLocal', lambda: session)
    assert asyncio.run(execution_queue.finalize_execution(execution_id, 'worker', ExecutionStatus.FAILED, error=classify_error(exc)))
    assert session.execute.call_args_list[0].args[0].compile().params['error'] == error
    dlq = session.add.call_args.args[0]
    assert dlq.error == error and dlq.attempts == error['attempts_used']
    assert session.commit.await_count == 2

@pytest.mark.parametrize('status,attempts', [(404, 1), (503, 3), (401, 1)])
def test_http_runner_preserves_error_through_failure_paths(monkeypatch, status, attempts):
    from test_execution_components import runner_setup, RUNNER_WORKSPACE_ID
    from app.engine import runner
    from app.engine.exceptions import ActionExecutionFailed
    nodes = [{'node_id': 't', 'node_type': 'trigger.manual'}, {'node_id': 'http', 'node_type': 'action.http_request', 'configuration': {'connection_id': 'c', 'url': 'https://example.test'}}]
    response = SimpleNamespace(success=False, result_json=json.dumps({'status_code': status}), error='safe failure')
    state = runner_setup(monkeypatch, nodes, [{'source_node_id': 't', 'target_node_id': 'http'}], response)
    async def no_sleep(_): pass
    monkeypatch.setattr(retry.asyncio, 'sleep', no_sleep)
    with pytest.raises(ActionExecutionFailed) as failure:
        asyncio.run(runner.run_execution(state['execution'].id, 'w', 'v', RUNNER_WORKSPACE_ID))
    step = state['steps'][-1]
    assert step.error == classify_error(failure.value)
    assert step.error['status_code'] == status
    assert step.attempt == attempts
