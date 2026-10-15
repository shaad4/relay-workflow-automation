import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories.document_chunk import DocumentChunkRepository


def test_create_chunks_records_workspace_and_order():
    db = AsyncMock()
    repository = DocumentChunkRepository(db)
    document, workspace = uuid.uuid4(), uuid.uuid4()
    records = asyncio.run(repository.create_chunks(document, workspace, ["first", "second"], [[0.1] * 1536, [0.2] * 1536]))
    assert [item.chunk_index for item in records] == [0, 1]
    assert [item.workspace_id for item in records] == [workspace, workspace]
    assert [item.document_id for item in records] == [document, document]
    db.add_all.assert_called_once_with(records)
    db.flush.assert_awaited_once()


@pytest.mark.parametrize("chunks,embeddings", [
    ([], []), (["text"], []), ([""], [[0.0] * 1536]), (["text"], [[0.0] * 4]),
])
def test_create_chunks_rejects_invalid_data(chunks, embeddings):
    db = AsyncMock()
    with pytest.raises(ValueError):
        asyncio.run(DocumentChunkRepository(db).create_chunks(uuid.uuid4(), uuid.uuid4(), chunks, embeddings))
    db.add_all.assert_not_called()


@pytest.mark.parametrize("dimensions,top_k", [(4, 5), (1536, 0), (1536, 21)])
def test_search_rejects_invalid_vector_or_limit(dimensions, top_k):
    db = AsyncMock()
    with pytest.raises(ValueError):
        asyncio.run(DocumentChunkRepository(db).search_similar(uuid.uuid4(), uuid.uuid4(), [0.0] * dimensions, top_k))
    db.execute.assert_not_awaited()


def test_search_query_filters_workspace_knowledge_base_and_ready_documents():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [(SimpleNamespace(content="answer"), 0.2)])
    repository = DocumentChunkRepository(db)
    workspace, knowledge_base = uuid.uuid4(), uuid.uuid4()
    result = asyncio.run(repository.search_similar(workspace, knowledge_base, [0.0] * 1536, 3))
    assert result[0][1] == 0.2
    statement = db.execute.await_args.args[0]
    compiled = statement.compile()
    sql = str(compiled)
    values = list(compiled.params.values())
    assert values.count(workspace) == 2
    assert knowledge_base in values
    assert "ready" in values
    assert 3 in values
    assert "ORDER BY" in sql
