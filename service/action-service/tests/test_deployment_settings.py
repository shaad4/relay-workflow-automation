"""Service-local deployment config and health regression tests (no live dependencies)."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, main
from app.db import database


def test_database_settings_are_bounded_and_errors_do_not_reveal_values(monkeypatch):
    monkeypatch.setenv("RELAY_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        config.database_url()
    for value in ("invalid-secret-canary", "postgresql+asyncpg://user:secret-canary@[bad/db"):
        monkeypatch.setenv("DATABASE_URL", value)
        with pytest.raises(RuntimeError, match="DATABASE_URL") as exc:
            config.database_url()
        assert "secret-canary" not in str(exc.value)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://relay:relay_dev_only@localhost/db")
    monkeypatch.setenv("RELAY_ENV", "production")
    with pytest.raises(RuntimeError, match="development placeholder"):
        config.database_url()
    for value in ("0", "secret-canary"):
        monkeypatch.setenv("DB_POOL_SIZE", value)
        with pytest.raises(RuntimeError, match="DB_POOL_SIZE") as exc:
            config.database_options()
        assert "secret-canary" not in str(exc.value)
    monkeypatch.setenv("DB_POOL_SIZE", "2")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "0")
    assert config.database_options()["pool_size"] == 2
    assert config.database_options()["max_overflow"] == 0
    assert config.database_options()["hide_parameters"] is True
    assert config.database_options()["echo"] is False


def test_grpc_configuration_validates_and_retains_defaults(monkeypatch):
    monkeypatch.delenv("GRPC_BIND_ADDRESS", raising=False)
    assert config.grpc_bind_address(50051) == "[::]:50051"
    monkeypatch.setenv("GRPC_BIND_ADDRESS", "127.0.0.1:60051")
    assert config.grpc_bind_address(50051) == "127.0.0.1:60051"
    monkeypatch.setenv("GRPC_BIND_ADDRESS", "bad")
    with pytest.raises(RuntimeError, match="GRPC_BIND_ADDRESS"):
        config.grpc_bind_address(50051)
    monkeypatch.delenv("AUTH_GRPC_URL", raising=False)
    monkeypatch.setenv("AUTH_GRPC_TARGET", "legacy:50051")
    assert config.grpc_target("AUTH_GRPC_URL", "default", "AUTH_GRPC_TARGET") == "legacy:50051"
    monkeypatch.setenv("AUTH_GRPC_URL", "custom:50051")
    assert config.grpc_target("AUTH_GRPC_URL", "default", "AUTH_GRPC_TARGET") == "custom:50051"
    monkeypatch.setenv("AUTH_GRPC_URL", "https://not-grpc")
    with pytest.raises(RuntimeError, match="AUTH_GRPC_URL"):
        config.grpc_target("AUTH_GRPC_URL", "default")


def test_readiness_checks_database_and_sanitizes_failures(monkeypatch):
    class Connection:
        fail = False

        async def __aenter__(self):
            if self.fail:
                raise RuntimeError("secret-canary")
            return self

        async def __aexit__(self, *_args):
            return False

        async def execute(self, statement):
            assert str(statement) == "SELECT 1"

    connection = Connection()
    monkeypatch.setattr(database, "engine", SimpleNamespace(connect=lambda: connection))
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                consumer_task=SimpleNamespace(done=lambda: False),
                dispatcher_task=SimpleNamespace(done=lambda: False),
            )
        )
    )
    arguments = (request,) if "request" in main.readiness.__annotations__ else ()
    assert asyncio.run(main.readiness(*arguments)) == {"status": "ready"}
    connection.fail = True
    response = asyncio.run(main.readiness(*arguments))
    assert response.status_code == 503
    assert b"secret-canary" not in response.body
    # A database outage must not fail the independent process-only probe.
    assert asyncio.run(main.liveness()) == {"status": "ok"}


def test_production_preserves_and_validates_existing_encryption_keys(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("RELAY_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://relay:synthetic@localhost/db")
    monkeypatch.delenv("ACTION_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ACTION_CREDENTIAL_ENCRYPTION_KEY"):
        config.validate_startup()
    monkeypatch.setenv("ACTION_CREDENTIAL_ENCRYPTION_KEY", "secret-canary")
    with pytest.raises(RuntimeError, match="ACTION_CREDENTIAL_ENCRYPTION_KEY") as exc:
        config.validate_startup()
    assert "secret-canary" not in str(exc.value)
    existing_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ACTION_CREDENTIAL_ENCRYPTION_KEY", existing_key)
    config.validate_startup()
    assert config.required("ACTION_CREDENTIAL_ENCRYPTION_KEY") == existing_key
