import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from app.ai.encryption import CredentialEncryption
from app.ai.input_validation import validate_resolved_ai_inputs
from app.ai.model_catalog import list_provider_models
from app.ai.structured_generation import StructuredAIGeneration
from app.ai.schemas import AIDecisionInput
from app.ai.exceptions import AIDecisionValidationError
from app.ai.exceptions import AITimeoutError, AIResponseError
from app.ai.service import AIService


def test_resolved_ai_inputs_accept_nested_values():
    validate_resolved_ai_inputs({"customer": {"name": "Café", "orders": [1, False]}}, "Reference knowledge")


@pytest.mark.parametrize("mappings,rag", [
    (None, ""), ({}, None), ({"customer": None}, ""),
    ({"customer": {"name": "{{trigger.name}}"}}, ""),
    ({"orders": ["valid", "{{node.output}}"]}, ""),
    ({}, "{{rag.context}}"),
])
def test_unresolved_ai_inputs_are_rejected(mappings, rag):
    with pytest.raises(ValueError):
        validate_resolved_ai_inputs(mappings, rag)


def test_credential_encryption_round_trip_and_invalid_inputs(monkeypatch):
    monkeypatch.setenv("AI_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    cipher = CredentialEncryption()
    encrypted = cipher.encrypt("synthetic-provider-key")
    assert "synthetic-provider-key" not in encrypted
    assert cipher.decrypt(encrypted) == "synthetic-provider-key"
    with pytest.raises(ValueError):
        cipher.encrypt("  ")
    with pytest.raises(ValueError):
        cipher.decrypt("invalid ciphertext")


def test_credential_encryption_requires_valid_key(monkeypatch):
    monkeypatch.delenv("AI_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError):
        CredentialEncryption()
    monkeypatch.setenv("AI_CREDENTIAL_ENCRYPTION_KEY", "invalid")
    with pytest.raises(RuntimeError):
        CredentialEncryption()


def test_openai_model_catalog_closes_client(monkeypatch):
    from app.ai import model_catalog
    client = SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=SimpleNamespace(data=[
        SimpleNamespace(id="zeta"), SimpleNamespace(id="alpha")
    ]))), close=AsyncMock())
    monkeypatch.setattr(model_catalog, "AsyncOpenAI", lambda **kwargs: client)
    assert asyncio.run(list_provider_models("openai", "synthetic-key")) == [
        {"id": "alpha", "name": "alpha"}, {"id": "zeta", "name": "zeta"}
    ]
    client.close.assert_awaited_once()


def test_model_catalog_rejects_missing_key_or_provider():
    with pytest.raises(ValueError, match="API key"):
        asyncio.run(list_provider_models("openai", "  "))
    with pytest.raises(ValueError, match="Unsupported"):
        asyncio.run(list_provider_models("unknown", "synthetic-key"))


def test_anthropic_model_catalog_sorts_and_closes(monkeypatch):
    from app.ai import model_catalog
    client = SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=SimpleNamespace(data=[
        SimpleNamespace(id="zeta", display_name="Zeta"), SimpleNamespace(id="alpha", display_name="Alpha")
    ]))), close=AsyncMock())
    monkeypatch.setattr(model_catalog, "AsyncAnthropic", lambda **kwargs: client)
    assert [item["id"] for item in asyncio.run(list_provider_models("anthropic", "synthetic-key"))] == ["alpha", "zeta"]
    client.close.assert_awaited_once()


def test_gemini_model_catalog_removes_prefix_and_closes(monkeypatch):
    from app.ai import model_catalog
    class Models:
        async def list(self):
            async def iterator():
                yield SimpleNamespace(name="models/gemini-test", display_name="Gemini Test")
            return iterator()
    close = AsyncMock()
    client = SimpleNamespace(aio=SimpleNamespace(models=Models(), aclose=close))
    monkeypatch.setattr(model_catalog.genai, "Client", lambda **kwargs: client)
    assert asyncio.run(list_provider_models("gemini", "synthetic-key")) == [{"id": "gemini-test", "name": "Gemini Test"}]
    close.assert_awaited_once()


def decision_input():
    return AIDecisionInput(
        instructions="Classify", structured_data={"amount": 12}, rag_context="Policy", allowed_decisions=["APPROVE", "REJECT"]
    )


def test_structured_decision_preserves_usage_and_untrusted_context():
    generator = StructuredAIGeneration()
    generator.ai_service.generate = AsyncMock(return_value=SimpleNamespace(
        content=json.dumps({"decision": "APPROVE", "reason": "Within policy", "data": {"amount": 12}}),
        model="synthetic-model", input_tokens=8, output_tokens=4,
    ))
    result = asyncio.run(generator.generate_decision("openai", "synthetic-key", "synthetic-model", decision_input()))
    assert result["decision"] == "APPROVE"
    assert result["input_tokens"] == 8 and result["output_tokens"] == 4
    prompt = generator.ai_service.generate.await_args.kwargs["prompt"]
    assert json.loads(prompt)["rag_context"] == "Policy"
    assert "synthetic-key" not in str(result)


@pytest.mark.parametrize("content", [
    "not json", "{}", '{"decision":"UNKNOWN","reason":"No","data":{}}',
    '{"decision":"APPROVE","reason":"","data":{}}',
])
def test_structured_decision_rejects_invalid_provider_output(content):
    generator = StructuredAIGeneration()
    generator.ai_service.generate = AsyncMock(return_value=SimpleNamespace(content=content, model="test", input_tokens=0, output_tokens=0))
    with pytest.raises(AIDecisionValidationError):
        asyncio.run(generator.generate_decision("openai", "synthetic-key", "test", decision_input()))


def test_ai_service_normalizes_provider_and_translates_failures():
    service = AIService()
    service.providers["openai"].generate = AsyncMock(return_value=SimpleNamespace(content="ok"))
    assert asyncio.run(service.generate(" OpenAI ", "synthetic-key", "test", "instruction", "prompt")).content == "ok"
    with pytest.raises(ValueError):
        asyncio.run(service.generate("unsupported", "synthetic-key", "test", "instruction", "prompt"))
    service.providers["openai"].generate.side_effect = asyncio.TimeoutError()
    with pytest.raises(AITimeoutError):
        asyncio.run(service.generate("openai", "synthetic-key", "test", "instruction", "prompt"))
    service.providers["openai"].generate.side_effect = RuntimeError("provider raw error")
    with pytest.raises(AIResponseError) as error:
        asyncio.run(service.generate("openai", "synthetic-key", "test", "instruction", "prompt"))
    assert "provider raw error" not in str(error.value)
