import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository


def db_with_scalar(value):
    db = AsyncMock()
    db.add = Mock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: value,
        scalars=lambda: SimpleNamespace(all=lambda: [value] if value else []),
    )
    return db


def assert_scoped(statement, workspace, resource_id=None):
    values = list(statement.compile().params.values())
    assert workspace in values
    if resource_id is not None:
        assert resource_id in values


def test_document_repository_create_and_status_update():
    db = AsyncMock()
    db.add = Mock()
    repository = DocumentRepository(db)
    document, workspace, kb = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    record = asyncio.run(
        repository.create(
            document, workspace, kb, "synthetic.txt", "text/plain", 9, "synthetic/path"
        )
    )
    assert (
        record.id == document
        and record.workspace_id == workspace
        and record.knowledge_base_id == kb
    )
    assert record.status == "uploading"
    db.add.assert_called_once_with(record)
    asyncio.run(repository.update_status(record, "failed", "synthetic failure"))
    assert record.status == "failed" and record.error_message == "synthetic failure"
    assert db.flush.await_count == 2


@pytest.mark.parametrize(
    "method,extra",
    [
        ("get_by_id", lambda doc, kb: (doc,)),
        ("claim_for_ingestion", lambda doc, kb: (doc,)),
        ("list_by_knowledge_base", lambda doc, kb: (kb,)),
        ("delete", lambda doc, kb: (doc, kb)),
        ("reset_failed_document", lambda doc, kb: (doc,)),
        ("complete_ingestion", lambda doc, kb: (doc,)),
        ("fail_ingestion", lambda doc, kb: (doc,)),
    ],
)
def test_document_repository_queries_include_workspace(method, extra):
    workspace, document, kb = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db = db_with_scalar(None)
    db.add = Mock()
    repository = DocumentRepository(db)
    asyncio.run(
        getattr(repository, method)(*extra(document, kb), workspace_id=workspace)
    ) if method in {
        "get_by_id",
        "claim_for_ingestion",
        "reset_failed_document",
        "complete_ingestion",
        "fail_ingestion",
    } else None
    if method == "list_by_knowledge_base":
        asyncio.run(repository.list_by_knowledge_base(workspace, kb))
    if method == "delete":
        asyncio.run(repository.delete(document, workspace, kb))
    assert_scoped(
        db.execute.await_args.args[0],
        workspace,
        kb if method == "list_by_knowledge_base" else document,
    )


def test_document_status_transitions_validate_and_filter_workspace():
    document, workspace = uuid.uuid4(), uuid.uuid4()
    db = db_with_scalar(document)
    repository = DocumentRepository(db)
    assert (
        asyncio.run(
            repository.transition_ingestion_status(document, workspace, "parsing", "chunking")
        )
        is True
    )
    assert_scoped(db.execute.await_args.args[0], workspace, document)
    with pytest.raises(ValueError):
        asyncio.run(repository.transition_ingestion_status(document, workspace, "pending", "ready"))


def test_knowledge_base_repository_queries_include_workspace():
    workspace, kb = uuid.uuid4(), uuid.uuid4()
    db = db_with_scalar(None)
    repository = KnowledgeBaseRepository(db)
    asyncio.run(repository.list_by_workspace(workspace))
    assert_scoped(db.execute.await_args.args[0], workspace)
    asyncio.run(repository.get_by_id(kb, workspace))
    assert_scoped(db.execute.await_args.args[0], workspace, kb)
    assert asyncio.run(repository.delete(kb, workspace)) is False
    db.delete.assert_not_awaited()


def test_knowledge_base_repository_create_and_delete():
    db = db_with_scalar(None)
    repository = KnowledgeBaseRepository(db)
    workspace = uuid.uuid4()
    record = asyncio.run(
        repository.create(workspace, SimpleNamespace(name="Synthetic", description="Test"))
    )
    assert record.workspace_id == workspace and record.name == "Synthetic"
    db.add.assert_called_once_with(record)
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: record)
    assert asyncio.run(repository.delete(record.id, workspace)) is True
    db.delete.assert_awaited_once_with(record)
