import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.anthropic import AnthropicProvider


@pytest.mark.parametrize("provider", [OpenAIProvider, GeminiProvider, AnthropicProvider])
@pytest.mark.parametrize("key,model,prompt", [("", "model", "prompt"), ("key", "", "prompt"), ("key", "model", "")])
def test_provider_adapters_reject_missing_configuration(provider, key, model, prompt):
    with pytest.raises(ValueError):
        asyncio.run(provider().generate(key, model, "instructions", prompt))


def test_openai_adapter_validates_response_and_closes_client(monkeypatch):
    from app.ai.providers import openai
    client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(
        status="completed", output_text="Generated", model="test-model",
        usage=SimpleNamespace(input_tokens=4, output_tokens=2),
    ))), close=AsyncMock())
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: client)
    response = asyncio.run(OpenAIProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert (response.content, response.input_tokens, response.output_tokens) == ("Generated", 4, 2)
    client.close.assert_awaited_once()
    client.responses.create.return_value.status = "incomplete"
    with pytest.raises(RuntimeError):
        asyncio.run(OpenAIProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    client.responses.create.return_value.status = "completed"
    client.responses.create.return_value.output_text = ""
    with pytest.raises(RuntimeError):
        asyncio.run(OpenAIProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert client.close.await_count == 3


def test_gemini_adapter_validates_response_and_closes_client(monkeypatch):
    from app.ai.providers import gemini
    response = SimpleNamespace(text="Generated", usage_metadata=SimpleNamespace(prompt_token_count=4, candidates_token_count=2))
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(return_value=response)), aclose=AsyncMock()))
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: client)
    result = asyncio.run(GeminiProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert (result.content, result.input_tokens, result.output_tokens) == ("Generated", 4, 2)
    response.text = ""
    with pytest.raises(RuntimeError):
        asyncio.run(GeminiProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert client.aio.aclose.await_count == 2


def test_anthropic_adapter_validates_response_and_closes_client(monkeypatch):
    from app.ai.providers import anthropic
    response = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Generated")],
                               usage=SimpleNamespace(input_tokens=4, output_tokens=2), model="test-model")
    client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response)), close=AsyncMock())
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kwargs: client)
    result = asyncio.run(AnthropicProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert (result.content, result.input_tokens, result.output_tokens) == ("Generated", 4, 2)
    response.stop_reason = "max_tokens"
    with pytest.raises(RuntimeError):
        asyncio.run(AnthropicProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    response.stop_reason = "end_turn"
    response.content = []
    with pytest.raises(RuntimeError):
        asyncio.run(AnthropicProvider().generate("synthetic-key", "test-model", "instruction", "prompt"))
    assert client.close.await_count == 3
