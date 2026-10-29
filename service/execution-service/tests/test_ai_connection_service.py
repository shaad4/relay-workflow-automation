import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.services.ai_provider_connection import AIProviderConnectionService
from cryptography.fernet import Fernet


def service(monkeypatch):
    monkeypatch.setenv("AI_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = AsyncMock()
    instance = AIProviderConnectionService(db)
    connection = SimpleNamespace(
        provider="openai",
        encrypted_api_key=instance.encryption.encrypt("synthetic-key"),
        status="active",
    )
    instance.repository.create = AsyncMock(return_value=connection)
    instance.repository.get_by_id = AsyncMock(return_value=connection)
    instance.repository.list_by_workspace = AsyncMock(return_value=[connection])
    instance.repository.update = AsyncMock()
    instance.repository.delete = AsyncMock()
    return instance, connection


def test_connection_create_encrypts_key_and_commits(monkeypatch):
    instance, connection = service(monkeypatch)
    workspace = uuid4()
    assert (
        asyncio.run(instance.create(workspace, "  Primary  ", " OpenAI ", "synthetic-key"))
        is connection
    )
    args = instance.repository.create.await_args.kwargs
    assert args["workspace_id"] == workspace
    assert args["name"] == "Primary" and args["provider"] == "openai"
    assert "synthetic-key" not in args["encrypted_api_key"]
    instance.db.commit.assert_awaited_once()
    instance.db.refresh.assert_awaited_once_with(connection)


@pytest.mark.parametrize(
    "name,provider,key",
    [
        ("", "openai", "key"),
        ("x" * 101, "openai", "key"),
        ("name", "unknown", "key"),
        ("name", "openai", ""),
    ],
)
def test_connection_create_rejects_invalid_data(monkeypatch, name, provider, key):
    instance, _ = service(monkeypatch)
    with pytest.raises(ValueError):
        asyncio.run(instance.create(uuid4(), name, provider, key))
    instance.repository.create.assert_not_awaited()


def test_connection_reads_and_writes_are_workspace_scoped(monkeypatch):
    instance, connection = service(monkeypatch)
    workspace, connection_id = uuid4(), uuid4()
    assert asyncio.run(instance.get(connection_id, workspace)) is connection
    assert asyncio.run(instance.list(workspace)) == [connection]
    assert (
        asyncio.run(instance.update(connection_id, workspace, name=" Renamed ", status="inactive"))
        is connection
    )
    instance.repository.get_by_id.assert_awaited_with(
        connection_id=connection_id, workspace_id=workspace
    )
    instance.repository.update.assert_awaited_once_with(
        connection=connection, name="Renamed", encrypted_api_key=None, status="inactive"
    )
    assert asyncio.run(instance.delete(connection_id, workspace)) is True
    instance.repository.delete.assert_awaited_once_with(connection)


def test_connection_missing_or_inactive_cannot_be_used(monkeypatch):
    instance, connection = service(monkeypatch)
    instance.repository.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        asyncio.run(instance.get_execution_credentials(uuid4(), uuid4()))
    assert asyncio.run(instance.delete(uuid4(), uuid4())) is False
    instance.repository.get_by_id.return_value = connection
    connection.status = "inactive"
    with pytest.raises(ValueError, match="inactive"):
        asyncio.run(instance.get_execution_credentials(uuid4(), uuid4()))


def test_connection_execution_credentials_and_provider_queries(monkeypatch):
    from app.services import ai_provider_connection

    instance, _ = service(monkeypatch)
    connection_id, workspace = uuid4(), uuid4()
    assert asyncio.run(instance.get_execution_credentials(connection_id, workspace)) == (
        "openai",
        "synthetic-key",
    )
    check = AsyncMock(return_value=True)
    models = AsyncMock(return_value=[{"id": "synthetic-model", "name": "Synthetic"}])
    monkeypatch.setattr(ai_provider_connection, "test_ai_provider_connection", check)
    monkeypatch.setattr(ai_provider_connection, "list_provider_models", models)
    assert asyncio.run(instance.test_connection(connection_id, workspace)) is True
    assert asyncio.run(instance.list_models(connection_id, workspace))[0]["id"] == "synthetic-model"
    check.assert_awaited_once_with(provider="openai", api_key="synthetic-key")
    models.assert_awaited_once_with(provider="openai", api_key="synthetic-key")


def test_connection_database_failure_rolls_back(monkeypatch):
    instance, _ = service(monkeypatch)
    instance.repository.create.side_effect = RuntimeError("database failure")
    with pytest.raises(RuntimeError):
        asyncio.run(instance.create(uuid4(), "Primary", "openai", "synthetic-key"))
    instance.db.rollback.assert_awaited_once()
