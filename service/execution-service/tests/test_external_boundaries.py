import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import grpc
import pytest
from app.ai import connection_test
from app.ai import service as ai
from app.dependencies import get_current_identity
from app.grpc import rag_client
from app.kafka import lifecycle_producer as kafka
from app.schemas.lifecycle_events import WorkflowLifecycleEvent


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
@pytest.mark.parametrize("fails", [False, True])
async def test_credential_probe_closes_client(monkeypatch, provider, fails):
    client = SimpleNamespace(models=SimpleNamespace(list=AsyncMock()), close=AsyncMock())

    async def models():
        yield object()

    client.aio = SimpleNamespace(
        models=SimpleNamespace(list=AsyncMock(return_value=models())), aclose=AsyncMock()
    )
    target = client.aio.models.list if provider == "gemini" else client.models.list
    if fails:
        target.side_effect = RuntimeError("provider down")
    if provider == "gemini":
        monkeypatch.setattr(connection_test.genai, "Client", lambda **kwargs: client)
    else:
        monkeypatch.setattr(
            connection_test,
            "AsyncOpenAI" if provider == "openai" else "AsyncAnthropic",
            lambda **kwargs: client,
        )
    if fails:
        with pytest.raises(RuntimeError):
            await connection_test.test_ai_provider_connection(provider, "fake")
    else:
        assert await connection_test.test_ai_provider_connection(provider, "fake")
    (client.aio.aclose if provider == "gemini" else client.close).assert_awaited_once()


@pytest.mark.parametrize("provider,key", [("unknown", "key"), ("openai", ""), ("gemini", " ")])
async def test_invalid_credential_probe(provider, key):
    with pytest.raises(ValueError):
        await connection_test.test_ai_provider_connection(provider, key)


@pytest.mark.parametrize(
    "authorization,cookie,valid,status",
    [
        (None, None, True, 401),
        ("Basic key", None, True, 401),
        ("Bearer ", None, True, 401),
        ("Bearer key", None, False, 401),
        (None, "cookie", True, 200),
        ("Bearer header", "cookie", True, 200),
    ],
)
async def test_identity_validation(monkeypatch, authorization, cookie, valid, status):
    client = SimpleNamespace(
        validate_token=AsyncMock(
            return_value=SimpleNamespace(valid=valid, user_id="u", workspace_id="w")
        ),
        close=AsyncMock(),
    )
    monkeypatch.setattr("app.dependencies.AuthGrpcClient", lambda: client)
    if status == 401:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as error:
            await get_current_identity(authorization, cookie)
        assert error.value.status_code == 401
    else:
        assert await get_current_identity(authorization, cookie) == {
            "user_id": "u",
            "workspace_id": "w",
        }
        client.validate_token.assert_awaited_once_with("header" if authorization else "cookie")
    if authorization and authorization.startswith("Bearer key") or cookie:
        client.close.assert_awaited_once()


@pytest.mark.parametrize(
    "code",
    [
        None,
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        grpc.StatusCode.NOT_FOUND,
        grpc.StatusCode.INVALID_ARGUMENT,
        grpc.StatusCode.INTERNAL,
    ],
)
async def test_rag_transport_classification(monkeypatch, code):
    channel = SimpleNamespace(close=AsyncMock())
    stub = SimpleNamespace(Retrieve=AsyncMock(return_value="response"))
    monkeypatch.setattr(rag_client.grpc.aio, "insecure_channel", lambda _: channel)
    monkeypatch.setattr(rag_client.rag_pb2_grpc, "RagInternalServiceStub", lambda _: stub)
    client = rag_client.RagClient()
    if code:
        error = grpc.aio.AioRpcError(code, (), (), "controlled")
        stub.Retrieve.side_effect = error
        expected = (
            grpc.aio.AioRpcError
            if code in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}
            else ValueError
            if code in {grpc.StatusCode.NOT_FOUND, grpc.StatusCode.INVALID_ARGUMENT}
            else RuntimeError
        )
        with pytest.raises(expected):
            await client.retrieve("w", "k", " query ", 5)
    else:
        assert await client.retrieve("w", "k", " query ", 5) == "response"
        assert stub.Retrieve.await_args.args[0].query == "query"
        assert stub.Retrieve.await_args.kwargs["timeout"] == 20
    await client.close()
    channel.close.assert_awaited_once()


@pytest.mark.parametrize(
    "workspace,kb,query,top",
    [
        ("", "k", "q", 5),
        ("w", "", "q", 5),
        ("w", "k", " ", 5),
        ("w", "k", "q" * 2001, 5),
        ("w", "k", "q", 0),
        ("w", "k", "q", 21),
    ],
)
async def test_rag_validation(workspace, kb, query, top):
    client = object.__new__(rag_client.RagClient)
    with pytest.raises(ValueError):
        await client.retrieve(workspace, kb, query, top)


@pytest.mark.parametrize("failure", [None, "start", "send", "stop"])
async def test_lifecycle_producer_cleanup_and_ack(monkeypatch, failure):
    producer = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), send_and_wait=AsyncMock())
    if failure:
        getattr(
            producer, {"start": "start", "send": "send_and_wait", "stop": "stop"}[failure]
        ).side_effect = RuntimeError("broker down")
    monkeypatch.setattr(kafka, "producer", None)
    monkeypatch.setattr(kafka, "AIOKafkaProducer", lambda **kwargs: producer)
    event = WorkflowLifecycleEvent(
        event_type="workflow.failed",
        execution_id=uuid4(),
        workspace_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
    )
    assert not await kafka.publish_lifecycle_event(event)
    if failure == "start":
        with pytest.raises(RuntimeError):
            await kafka.start_lifecycle_producer()
        assert kafka.producer is None
        return
    await kafka.start_lifecycle_producer()
    await kafka.start_lifecycle_producer()
    producer.start.assert_awaited_once()
    assert await kafka.publish_lifecycle_event(event) is (failure != "send")
    if failure == "stop":
        with pytest.raises(RuntimeError):
            await kafka.stop_lifecycle_producer()
    else:
        await kafka.stop_lifecycle_producer()
    assert kafka.producer is None


@pytest.mark.parametrize(
    "code,expected",
    [
        (401, ai.AIAuthenticationError),
        (403, ai.AIAuthenticationError),
        (429, ai.AIRateLimitError),
        (408, ai.AITimeoutError),
        (504, ai.AITimeoutError),
        (500, ai.AIServiceUnavailableError),
    ],
)
@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
async def test_provider_status_classification(monkeypatch, code, expected, provider):
    import anthropic
    import httpx
    import openai

    monkeypatch.setattr(ai, "ai_semaphore", asyncio.Semaphore(10))
    response = httpx.Response(code, request=httpx.Request("POST", "https://fake.test"))
    if provider == "gemini":
        error = ai.gemini_errors.ClientError(
            code, {"error": {"message": "controlled", "code": code}}
        )
    else:
        error = (openai.APIStatusError if provider == "openai" else anthropic.APIStatusError)(
            "controlled", response=response, body={}
        )
    service = ai.AIService()
    service.providers[provider] = SimpleNamespace(generate=AsyncMock(side_effect=error))
    with pytest.raises(expected):
        await service.generate(provider, "fake", "test", "", "prompt")
    assert ai.ai_semaphore._value == 10
