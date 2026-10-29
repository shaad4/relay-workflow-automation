import asyncio
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://relay:relay@localhost:5432/ci_test")

from app.api.routes import documents, knowledge_bases
from app.schemas.search import SearchRequest


def identity():
    return {"workspace_id": str(uuid.uuid4())}


def test_knowledge_base_routes_scope_requests(monkeypatch):
    service = SimpleNamespace(
        create=AsyncMock(return_value="created"),
        list_by_workspace=AsyncMock(return_value=["item"]),
        get_by_id=AsyncMock(return_value="item"),
        delete=AsyncMock(return_value=True),
    )
    monkeypatch.setattr(knowledge_bases, "KnowledgeBaseService", lambda db: service)
    workspace = identity()
    kb = uuid.uuid4()
    assert (
        asyncio.run(
            knowledge_bases.create_knowledge_base(
                SimpleNamespace(name="Synthetic"), workspace, object()
            )
        )
        == "created"
    )
    assert asyncio.run(knowledge_bases.list_knowledge_bases(workspace, object())) == ["item"]
    assert asyncio.run(knowledge_bases.get_knowledge_base(kb, workspace, object())) == "item"
    assert asyncio.run(knowledge_bases.delete_knowledge_base(kb, workspace, object())) is None
    service.get_by_id.assert_awaited_once_with(
        knowledge_base_id=kb, workspace_id=uuid.UUID(workspace["workspace_id"])
    )
    service.delete.assert_awaited_once_with(
        knowledge_base_id=kb, workspace_id=uuid.UUID(workspace["workspace_id"])
    )


def test_knowledge_base_routes_hide_missing_resources(monkeypatch):
    service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=None), delete=AsyncMock(return_value=False)
    )
    monkeypatch.setattr(knowledge_bases, "KnowledgeBaseService", lambda db: service)
    for operation in [knowledge_bases.get_knowledge_base, knowledge_bases.delete_knowledge_base]:
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation(uuid.uuid4(), identity(), object()))
        assert error.value.status_code == 404


def test_search_route_checks_ownership_before_embedding(monkeypatch):
    kb = uuid.uuid4()
    workspace = identity()
    service = SimpleNamespace(
        knowledge_base_repository=SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
        retrieve=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(knowledge_bases, "RetrievalService", lambda db: service)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            knowledge_bases.search_knowledge_base(
                kb, SearchRequest(query=" policy "), workspace, object()
            )
        )
    assert error.value.status_code == 404
    service.retrieve.assert_not_awaited()
    service.knowledge_base_repository.get_by_id.return_value = object()
    result = asyncio.run(
        knowledge_bases.search_knowledge_base(
            kb, SearchRequest(query=" policy ", top_k=3), workspace, object()
        )
    )
    assert result.query == "policy" and result.results == []
    service.retrieve.assert_awaited_once_with(
        workspace_id=uuid.UUID(workspace["workspace_id"]),
        knowledge_base_id=kb,
        query="policy",
        top_k=3,
    )


def test_document_routes_scope_operations_and_missing_document(monkeypatch):
    kb, doc = uuid.uuid4(), uuid.uuid4()
    workspace = identity()
    service = SimpleNamespace(
        list_documents=AsyncMock(return_value=["document"]),
        delete_document=AsyncMock(return_value=False),
        retry_document=AsyncMock(),
    )
    monkeypatch.setattr(documents, "DocumentService", lambda db: service)
    assert asyncio.run(documents.list_documents(kb, workspace, object())) == ["document"]
    with pytest.raises(HTTPException) as error:
        asyncio.run(documents.delete_document(kb, doc, workspace, object()))
    assert error.value.status_code == 404
    service.delete_document.return_value = True
    assert asyncio.run(documents.delete_document(kb, doc, workspace, object())) is None
    service.delete_document.assert_awaited_with(
        document_id=doc, workspace_id=uuid.UUID(workspace["workspace_id"]), knowledge_base_id=kb
    )


def test_document_upload_queue_failure_reports_pending_state(monkeypatch):
    kb, doc = uuid.uuid4(), uuid.uuid4()
    service = SimpleNamespace(upload_document=AsyncMock(return_value=SimpleNamespace(id=doc)))
    monkeypatch.setattr(documents, "DocumentService", lambda db: service)

    async def fail(*args, **kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(documents, "run_in_threadpool", fail)
    with pytest.raises(HTTPException) as error:
        asyncio.run(documents.upload_document(kb, object(), identity(), object()))
    assert error.value.status_code == 503
