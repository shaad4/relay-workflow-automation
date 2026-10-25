import asyncio
import tempfile
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.file_validator import MAX_FILE_SIZE, validate_document
from app.services.retrieval import RetrievalService
from fastapi import HTTPException, UploadFile


def synthetic_upload(name, mime, content):
    file = tempfile.SpooledTemporaryFile(max_size=MAX_FILE_SIZE + 2)
    file.write(content)
    file.seek(0)
    return UploadFile(file, filename=name, headers={"content-type": mime})


@pytest.mark.parametrize(
    "name,mime,content,status",
    [
        ("", "text/plain", b"text", 400),
        ("sample.png", "image/png", b"text", 400),
        ("sample.txt", "image/png", b"text", 400),
        ("sample.txt", "text/plain", b"", 400),
        ("sample.txt", "text/plain", b"\xff", 400),
        ("sample.txt", "text/plain", b"  \n", 400),
        ("sample.pdf", "application/pdf", b"not a pdf", 400),
        ("sample.txt", "text/plain", b"x" * (MAX_FILE_SIZE + 1), 413),
    ],
    ids=[
        "missing-name",
        "unsupported-extension",
        "mime-mismatch",
        "empty",
        "invalid-utf8",
        "blank",
        "invalid-pdf",
        "too-large",
    ],
)
def test_upload_validation_rejects_invalid_input(name, mime, content, status):
    upload = synthetic_upload(name, mime, content)
    with pytest.raises(HTTPException) as error:
        asyncio.run(validate_document(upload))
    assert error.value.status_code == status


@pytest.mark.parametrize(
    "name,mime,content",
    [
        ("sample.txt", "text/plain", b"text"),
        ("sample.md", "text/markdown", "Café".encode()),
        ("sample.pdf", "application/pdf", b"%PDF-synthetic"),
    ],
)
def test_upload_validation_accepts_supported_file(name, mime, content):
    upload = synthetic_upload(name, mime, content)
    assert asyncio.run(validate_document(upload)) == content


def retrieval_service(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    service = RetrievalService(AsyncMock())
    service.knowledge_base_repository.get_by_id = AsyncMock(return_value=object())
    service.embedding_provider.generate_embeddings = AsyncMock(return_value=[[0.1] * 1536])
    service.chunk_repository.search_similar = AsyncMock(return_value=[])
    return service


@pytest.mark.parametrize(
    "query,top_k", [("", 5), ("  ", 5), ("x" * 2001, 5), ("ok", 0), ("ok", 21)]
)
def test_retrieval_rejects_invalid_query_or_limit(monkeypatch, query, top_k):
    service = retrieval_service(monkeypatch)
    with pytest.raises(ValueError):
        asyncio.run(service.retrieve(uuid.uuid4(), uuid.uuid4(), query, top_k))
    service.embedding_provider.generate_embeddings.assert_not_awaited()


def test_retrieval_enforces_workspace_knowledge_base_ownership(monkeypatch):
    service = retrieval_service(monkeypatch)
    service.knowledge_base_repository.get_by_id.return_value = None
    with pytest.raises(ValueError, match="Knowledge base not found"):
        asyncio.run(service.retrieve(uuid.uuid4(), uuid.uuid4(), "query"))
    service.chunk_repository.search_similar.assert_not_awaited()


def test_retrieval_passes_tenant_filters_and_orders_results(monkeypatch):
    service = retrieval_service(monkeypatch)
    workspace, knowledge_base = uuid.uuid4(), uuid.uuid4()
    chunk = SimpleNamespace(
        id=uuid.uuid4(), document_id=uuid.uuid4(), chunk_index=2, content="answer"
    )
    service.chunk_repository.search_similar.return_value = [(chunk, 0.25)]
    result = asyncio.run(service.retrieve(workspace, knowledge_base, "  question  ", 3))
    assert result == [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "chunk_index": 2,
            "content": "answer",
            "score": 0.75,
        }
    ]
    service.knowledge_base_repository.get_by_id.assert_awaited_once_with(
        knowledge_base_id=knowledge_base, workspace_id=workspace
    )
    service.chunk_repository.search_similar.assert_awaited_once_with(
        workspace_id=workspace,
        knowledge_base_id=knowledge_base,
        query_embedding=[0.1] * 1536,
        top_k=3,
    )
