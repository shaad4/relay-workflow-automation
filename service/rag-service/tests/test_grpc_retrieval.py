import asyncio
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import grpc
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://relay:relay@localhost:5432/ci_test")

from app.grpc.generated.rag import rag_pb2
from app.grpc.rag_server import RagInternalServicer


class Aborted(Exception):
    def __init__(self, code, details):
        self.code = code
        self.details = details


class Context:
    async def abort(self, code, details):
        raise Aborted(code, details)


def request(**changes):
    values = dict(workspace_id=str(uuid.uuid4()), knowledge_base_id=str(uuid.uuid4()), query="policy", top_k=5)
    values.update(changes)
    return rag_pb2.RetrieveRequest(**values)


@pytest.mark.parametrize("changes,code", [
    ({"workspace_id": "invalid"}, grpc.StatusCode.INVALID_ARGUMENT),
    ({"knowledge_base_id": "invalid"}, grpc.StatusCode.INVALID_ARGUMENT),
    ({"query": "  "}, grpc.StatusCode.INVALID_ARGUMENT),
    ({"query": "x" * 2001}, grpc.StatusCode.INVALID_ARGUMENT),
    ({"top_k": 0}, grpc.StatusCode.INVALID_ARGUMENT),
    ({"top_k": 21}, grpc.StatusCode.INVALID_ARGUMENT),
])
def test_grpc_retrieval_rejects_invalid_requests(changes, code):
    with pytest.raises(Aborted) as error:
        asyncio.run(RagInternalServicer().Retrieve(request(**changes), Context()))
    assert error.value.code == code


def setup_retrieval(monkeypatch, result=None, error=None):
    from app.grpc import rag_server
    class Session:
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *_):
            return False
    monkeypatch.setattr(rag_server, "AsyncSessionLocal", Session)
    retrieve = AsyncMock(return_value=result or [], side_effect=error)
    monkeypatch.setattr(rag_server, "RetrievalService", lambda db: SimpleNamespace(retrieve=retrieve))
    return retrieve


def test_grpc_retrieval_returns_chunks_and_scope(monkeypatch):
    item = dict(chunk_id=str(uuid.uuid4()), document_id=str(uuid.uuid4()), chunk_index=1, content="policy", score=0.8)
    retrieve = setup_retrieval(monkeypatch, [item])
    query = request()
    response = asyncio.run(RagInternalServicer().Retrieve(query, Context()))
    assert len(response.chunks) == 1
    assert response.chunks[0].content == "policy"
    assert retrieve.await_args.kwargs["workspace_id"] == uuid.UUID(query.workspace_id)
    assert retrieve.await_args.kwargs["knowledge_base_id"] == uuid.UUID(query.knowledge_base_id)


@pytest.mark.parametrize("error,code", [
    (ValueError("Knowledge base not found"), grpc.StatusCode.NOT_FOUND),
    (ValueError("top_k must be between 1 and 20"), grpc.StatusCode.INVALID_ARGUMENT),
    (TimeoutError("database timeout"), grpc.StatusCode.INTERNAL),
])
def test_grpc_retrieval_maps_service_errors(monkeypatch, error, code):
    setup_retrieval(monkeypatch, error=error)
    with pytest.raises(Aborted) as result:
        asyncio.run(RagInternalServicer().Retrieve(request(), Context()))
    assert result.value.code == code
