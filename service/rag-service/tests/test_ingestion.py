import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.ingestion import IngestionService


def service(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(
        "app.services.ingestion.SupabaseStorage",
        lambda: SimpleNamespace(download=lambda path: b"Synthetic document"),
    )

    async def immediate(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr("app.services.ingestion.run_in_threadpool", immediate)
    db = AsyncMock()
    ingestion = IngestionService(db)
    ingestion.document_repository.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            status="pending", storage_path="synthetic/path.txt", content_type="text/plain"
        )
    )
    ingestion.document_repository.claim_for_ingestion = AsyncMock(return_value=True)
    ingestion.document_repository.transition_ingestion_status = AsyncMock(return_value=True)
    ingestion.document_repository.complete_ingestion = AsyncMock(return_value=True)
    ingestion.document_repository.fail_ingestion = AsyncMock(return_value=True)
    ingestion.chunk_repository.create_chunks = AsyncMock(return_value=[])
    ingestion.embedding_provider.generate_embeddings = AsyncMock(return_value=[[0.1] * 1536])
    return ingestion


def test_ingestion_tracks_status_and_stores_chunks(monkeypatch):
    ingestion = service(monkeypatch)
    document, workspace = uuid.uuid4(), uuid.uuid4()
    assert asyncio.run(ingestion.ingest_document(document, workspace)) == 1
    assert [
        call.kwargs["new_status"]
        for call in ingestion.document_repository.transition_ingestion_status.await_args_list
    ] == ["chunking", "embedding"]
    ingestion.chunk_repository.create_chunks.assert_awaited_once_with(
        document_id=document,
        workspace_id=workspace,
        chunks=["Synthetic document"],
        embeddings=[[0.1] * 1536],
    )
    ingestion.document_repository.complete_ingestion.assert_awaited_once_with(
        document_id=document, workspace_id=workspace
    )
    assert ingestion.db.commit.await_count == 4


def test_ingestion_rejects_cross_workspace_document(monkeypatch):
    ingestion = service(monkeypatch)
    ingestion.document_repository.get_by_id.return_value = None
    with pytest.raises(ValueError, match="Document not found"):
        asyncio.run(ingestion.ingest_document(uuid.uuid4(), uuid.uuid4()))
    ingestion.document_repository.claim_for_ingestion.assert_not_awaited()


def test_ingestion_skips_ready_or_unclaimed_documents(monkeypatch):
    ingestion = service(monkeypatch)
    ingestion.document_repository.get_by_id.return_value.status = "ready"
    assert asyncio.run(ingestion.ingest_document(uuid.uuid4(), uuid.uuid4())) == 0
    ingestion.document_repository.claim_for_ingestion.assert_not_awaited()
    ingestion.document_repository.get_by_id.return_value.status = "pending"
    ingestion.document_repository.claim_for_ingestion.return_value = False
    assert asyncio.run(ingestion.ingest_document(uuid.uuid4(), uuid.uuid4())) == 0
    ingestion.db.rollback.assert_awaited_once()


def test_ingestion_failure_rolls_back_and_marks_failed(monkeypatch):
    ingestion = service(monkeypatch)
    ingestion.embedding_provider.generate_embeddings.side_effect = TimeoutError("provider timeout")
    with pytest.raises(TimeoutError):
        asyncio.run(ingestion.ingest_document(uuid.uuid4(), uuid.uuid4()))
    assert ingestion.db.rollback.await_count >= 1
    ingestion.document_repository.fail_ingestion.assert_awaited_once()
    ingestion.chunk_repository.create_chunks.assert_not_awaited()


@pytest.mark.parametrize("chunks,embeddings", [([], []), (["one"], [])])
def test_prepare_embeddings_rejects_missing_or_mismatched_vectors(monkeypatch, chunks, embeddings):
    ingestion = service(monkeypatch)
    ingestion.embedding_provider.generate_embeddings.return_value = embeddings
    with pytest.raises(ValueError):
        asyncio.run(ingestion.prepare_embeddings(chunks))
