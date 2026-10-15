import asyncio
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://relay:relay@localhost:5432/ci_test")

from app.dependencies import get_current_identity
from app.storage.supabase_storage import SupabaseStorage
from app.tasks import ingestion as task_module


def test_storage_operations_use_scoped_bucket_and_path(monkeypatch):
    from app.storage import supabase_storage
    bucket = SimpleNamespace(upload=Mock(), download=Mock(return_value=b"synthetic"), remove=Mock(), list=Mock(return_value=[{"name": "doc.txt"}]))
    client = SimpleNamespace(storage=SimpleNamespace(from_=Mock(return_value=bucket)))
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "synthetic-test-bucket")
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-secret")
    monkeypatch.setattr(supabase_storage, "create_client", lambda *args: client)
    storage = SupabaseStorage()
    assert storage.upload(b"synthetic", "workspace/doc.txt", "text/plain") == "workspace/doc.txt"
    assert storage.download("workspace/doc.txt") == b"synthetic"
    storage.delete("workspace/doc.txt")
    assert storage.exists("workspace/doc.txt") is True
    bucket.remove.assert_called_once_with(["workspace/doc.txt"])
    bucket.list.return_value = [{"name": "other.txt"}]
    assert storage.exists("workspace/doc.txt") is False
    client.storage.from_.assert_called_with("synthetic-test-bucket")


@pytest.mark.parametrize("authorization,cookie", [(None, None), ("Basic token", None), ("Bearer  ", None)])
def test_identity_rejects_missing_or_invalid_auth(authorization, cookie):
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_identity(authorization, cookie))
    assert error.value.status_code == 401


def test_identity_accepts_cookie_and_rejects_invalid_jwt(monkeypatch):
    from app import dependencies
    validate = AsyncMock(return_value=SimpleNamespace(valid=True, user_id="user", workspace_id=str(uuid.uuid4())))
    close = AsyncMock()
    monkeypatch.setattr(dependencies, "AuthGrpcClient", lambda: SimpleNamespace(validate_token=validate, close=close))
    result = asyncio.run(get_current_identity(None, "synthetic-cookie"))
    assert result["user_id"] == "user"
    validate.assert_awaited_with("synthetic-cookie")
    close.assert_awaited()
    validate.return_value.valid = False
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_identity("Bearer invalid", None))
    assert error.value.status_code == 401


def test_ingestion_task_passes_synthetic_ids_to_runner(monkeypatch):
    document, workspace = uuid.uuid4(), uuid.uuid4()
    runner = AsyncMock(return_value=3)
    monkeypatch.setattr(task_module, "run_ingestion", runner)
    assert task_module.ingest_document_task(str(document), str(workspace)) == 3
    runner.assert_awaited_once_with(document_id=document, workspace_id=workspace)
