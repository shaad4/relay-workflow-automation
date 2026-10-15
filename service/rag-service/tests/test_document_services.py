import asyncio
import tempfile
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

from app.services.document import DocumentService
from app.services.knowledge_base import KnowledgeBaseService


def document_service(monkeypatch):
    from app.services import document
    storage = SimpleNamespace(upload=lambda **kwargs: None, delete=lambda path: None)
    monkeypatch.setattr(document, "SupabaseStorage", lambda: storage)
    async def immediate(function, *args, **kwargs):
        return function(*args, **kwargs)
    monkeypatch.setattr(document, "run_in_threadpool", immediate)
    db = AsyncMock()
    service = DocumentService(db)
    service.knowledge_base_repository.get_by_id = AsyncMock(return_value=object())
    record = SimpleNamespace(knowledge_base_id=None, status="pending", storage_path="synthetic/path.txt")
    service.repository.create = AsyncMock(return_value=record)
    service.repository.update_status = AsyncMock()
    service.repository.get_by_id = AsyncMock(return_value=record)
    service.repository.delete = AsyncMock(return_value=True)
    service.repository.reset_failed_document = AsyncMock(return_value=True)
    service.repository.list_by_knowledge_base = AsyncMock(return_value=[record])
    return service, storage, record


def upload(content=b"Synthetic document"):
    file = tempfile.SpooledTemporaryFile()
    file.write(content)
    file.seek(0)
    return UploadFile(file, filename="synthetic.txt", headers={"content-type": "text/plain"})


def test_document_upload_scopes_storage_and_status(monkeypatch):
    service, storage, record = document_service(monkeypatch)
    workspace, knowledge_base = uuid.uuid4(), uuid.uuid4()
    asyncio.run(service.upload_document(upload(), workspace, knowledge_base))
    args = service.repository.create.await_args.kwargs
    assert args["workspace_id"] == workspace and args["knowledge_base_id"] == knowledge_base
    assert args["storage_path"].startswith(f"workspaces/{workspace}/knowledge-bases/{knowledge_base}/")
    assert args["status"] == "uploading"
    service.repository.update_status.assert_awaited_once_with(document=record, status="pending")
    assert service.db.commit.await_count == 2


def test_document_upload_rejects_other_workspace(monkeypatch):
    service, _, _ = document_service(monkeypatch)
    service.knowledge_base_repository.get_by_id.return_value = None
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.upload_document(upload(), uuid.uuid4(), uuid.uuid4()))
    assert error.value.status_code == 404
    service.repository.create.assert_not_awaited()


def test_document_upload_storage_failure_preserves_uploading_record(monkeypatch):
    service, storage, _ = document_service(monkeypatch)
    def fail(**kwargs):
        raise TimeoutError("storage timeout")
    storage.upload = fail
    with pytest.raises(TimeoutError):
        asyncio.run(service.upload_document(upload(), uuid.uuid4(), uuid.uuid4()))
    service.repository.update_status.assert_not_awaited()
    service.db.rollback.assert_awaited_once()


def test_document_listing_and_deletion_scope(monkeypatch):
    service, storage, record = document_service(monkeypatch)
    workspace, knowledge_base, document = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    record.knowledge_base_id = knowledge_base
    assert asyncio.run(service.list_documents(workspace, knowledge_base)) == [record]
    assert asyncio.run(service.delete_document(document, workspace, knowledge_base)) is True
    service.repository.delete.assert_awaited_once_with(document_id=document, workspace_id=workspace, knowledge_base_id=knowledge_base)
    service.db.commit.assert_awaited_once()


@pytest.mark.parametrize("status,code", [("uploading", 409), ("parsing", 409), ("chunking", 409), ("embedding", 409)])
def test_document_deletion_blocks_processing(monkeypatch, status, code):
    service, _, record = document_service(monkeypatch)
    knowledge_base = uuid.uuid4()
    record.knowledge_base_id, record.status = knowledge_base, status
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.delete_document(uuid.uuid4(), uuid.uuid4(), knowledge_base))
    assert error.value.status_code == code
    service.repository.delete.assert_not_awaited()


def test_document_retry_requires_failed_status(monkeypatch):
    service, _, record = document_service(monkeypatch)
    knowledge_base = uuid.uuid4()
    record.knowledge_base_id = knowledge_base
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.retry_document(uuid.uuid4(), uuid.uuid4(), knowledge_base))
    assert error.value.status_code == 409
    record.status = "failed"
    assert asyncio.run(service.retry_document(uuid.uuid4(), uuid.uuid4(), knowledge_base)) is True
    service.repository.reset_failed_document.assert_awaited_once()


def test_knowledge_base_service_commits_and_rolls_back():
    db = AsyncMock()
    service = KnowledgeBaseService(db)
    workspace, knowledge_base = uuid.uuid4(), uuid.uuid4()
    data = SimpleNamespace(name="Synthetic")
    service.repository.create = AsyncMock(return_value=knowledge_base)
    service.repository.list_by_workspace = AsyncMock(return_value=[knowledge_base])
    service.repository.get_by_id = AsyncMock(return_value=knowledge_base)
    service.repository.delete = AsyncMock(return_value=True)
    assert asyncio.run(service.create(workspace, data)) == knowledge_base
    assert asyncio.run(service.list_by_workspace(workspace)) == [knowledge_base]
    assert asyncio.run(service.get_by_id(knowledge_base, workspace)) == knowledge_base
    assert asyncio.run(service.delete(knowledge_base, workspace)) is True
    service.repository.get_by_id.assert_awaited_once_with(knowledge_base_id=knowledge_base, workspace_id=workspace)
    service.repository.delete.side_effect = RuntimeError("database failure")
    with pytest.raises(RuntimeError):
        asyncio.run(service.delete(knowledge_base, workspace))
    db.rollback.assert_awaited_once()
