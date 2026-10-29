import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.ai.exceptions import AIAuthenticationError, AIResponseError, AIServiceUnavailableError
from app.engine.handlers.ai_generate import execute_ai_generate
from app.engine.handlers.condition import evaluate_condition

WORKSPACE = str(uuid4())
CONNECTION = str(uuid4())
BASE = {
    "connection_id": CONNECTION,
    "model": "test-model",
    "instructions": "Summarize",
    "prompt": "Write a summary",
}


@pytest.mark.parametrize(
    "configuration,workspace",
    [
        (None, WORKSPACE),
        ({}, WORKSPACE),
        (BASE, "invalid"),
        ({**BASE, "model": ""}, WORKSPACE),
        ({**BASE, "prompt": ""}, WORKSPACE),
        ({**BASE, "instructions": 1}, WORKSPACE),
        ({**BASE, "rag_context": 1}, WORKSPACE),
        ({**BASE, "prompt": "{{unresolved}}"}, WORKSPACE),
        ({**BASE, "rag_context": "{{unresolved}}"}, WORKSPACE),
    ],
)
def test_ai_generate_rejects_invalid_inputs_before_connection_lookup(configuration, workspace):
    with pytest.raises(ValueError):
        asyncio.run(execute_ai_generate(configuration, workspace, AsyncMock()))


def setup_handler(monkeypatch, response=None, error=None):
    from app.engine.handlers import ai_generate

    credentials = AsyncMock(return_value=("openai", "synthetic-secret"))
    monkeypatch.setattr(
        ai_generate,
        "AIProviderConnectionService",
        lambda session: SimpleNamespace(get_execution_credentials=credentials),
    )
    generate = AsyncMock(
        return_value=response
        or SimpleNamespace(content="Summary", model="test-model", input_tokens=5, output_tokens=3),
        side_effect=error,
    )
    monkeypatch.setattr(ai_generate, "AIService", lambda: SimpleNamespace(generate=generate))
    return credentials, generate


def test_ai_generate_scopes_connection_and_keeps_rag_untrusted(monkeypatch):
    credentials, generate = setup_handler(monkeypatch)
    output = asyncio.run(
        execute_ai_generate({**BASE, "rag_context": "Policy reference"}, WORKSPACE, AsyncMock())
    )
    assert output == {
        "content": "Summary",
        "model": "test-model",
        "input_tokens": 5,
        "output_tokens": 3,
    }
    credentials.assert_awaited_once_with(
        connection_id=UUID(CONNECTION), workspace_id=UUID(WORKSPACE)
    )
    assert "Policy reference" in generate.await_args.kwargs["prompt"]
    assert "untrusted" in generate.await_args.kwargs["prompt"]
    assert "synthetic-secret" not in str(output)


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(content="", model="model", input_tokens=1, output_tokens=1),
        SimpleNamespace(content="synthetic-secret", model="model", input_tokens=1, output_tokens=1),
        SimpleNamespace(content="ok", model="model", input_tokens=-1, output_tokens=1),
    ],
)
def test_ai_generate_rejects_invalid_or_leaked_provider_output(monkeypatch, response):
    setup_handler(monkeypatch, response=response)
    with pytest.raises(AIResponseError):
        asyncio.run(execute_ai_generate(BASE, WORKSPACE, AsyncMock()))


@pytest.mark.parametrize(
    "error,expected",
    [
        (AIAuthenticationError("secret"), AIAuthenticationError),
        (RuntimeError("secret"), AIServiceUnavailableError),
    ],
)
def test_ai_generate_masks_provider_errors(monkeypatch, error, expected):
    setup_handler(monkeypatch, error=error)
    with pytest.raises(expected) as result:
        asyncio.run(execute_ai_generate(BASE, WORKSPACE, AsyncMock()))
    assert "secret" not in str(result.value)


@pytest.mark.parametrize(
    "value,result",
    [(True, "true"), (False, "false"), (0, "0"), (2.5, "2.5"), (" APPROVE ", "APPROVE")],
)
def test_condition_resolves_supported_values(value, result):
    assert evaluate_condition({"value": value}) == result


@pytest.mark.parametrize(
    "configuration", [None, {}, {"value": []}, {"value": ""}, {"value": "{{nodes.decision}}"}]
)
def test_condition_rejects_missing_or_unresolved_values(configuration):
    with pytest.raises(ValueError):
        evaluate_condition(configuration)
