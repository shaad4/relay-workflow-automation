import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.embeddings.provider import EmbeddingProvider


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    return EmbeddingProvider()


def test_batch_embeddings_are_ordered_by_provider_index(provider):
    provider.client.embeddings.create = AsyncMock(return_value=SimpleNamespace(data=[
        SimpleNamespace(index=1, embedding=[2.0] * 1536),
        SimpleNamespace(index=0, embedding=[1.0] * 1536),
    ]))
    result = asyncio.run(provider.generate_embeddings(["first", "second"]))
    assert len(result) == 2
    assert result[0][0] == 1.0 and result[1][0] == 2.0
    provider.client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-3-small", input=["first", "second"], encoding_format="float"
    )


@pytest.mark.parametrize("texts", [[], [""], ["valid", "   "]])
def test_empty_embedding_inputs_are_rejected(provider, texts):
    with pytest.raises(ValueError):
        asyncio.run(provider.generate_embeddings(texts))


@pytest.mark.parametrize("data", [[], [SimpleNamespace(index=0, embedding=[0.0] * 4)]])
def test_invalid_embedding_responses_are_rejected(provider, data):
    provider.client.embeddings.create = AsyncMock(return_value=SimpleNamespace(data=data))
    with pytest.raises(ValueError):
        asyncio.run(provider.generate_embeddings(["text"]))


def test_provider_failure_propagates_without_credentials_in_error(provider):
    provider.client.embeddings.create = AsyncMock(side_effect=TimeoutError("provider timeout"))
    with pytest.raises(TimeoutError, match="provider timeout"):
        asyncio.run(provider.generate_embeddings(["text"]))
