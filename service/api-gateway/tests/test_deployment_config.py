"""Cross-service environment contract; no databases, brokers or provider calls."""

import importlib.util
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
SERVICES = sorted(path.name for path in SERVICE_ROOT.iterdir() if (path / "app/config.py").exists())


def load_config(service):
    spec = importlib.util.spec_from_file_location(
        f"deployment_{service.replace('-', '_')}", SERVICE_ROOT / service / "app/config.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    names = {
        "RELAY_ENV",
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "FRONTEND_URL",
        "BACKEND_URL",
        "CORS_ALLOWED_ORIGINS",
        "COOKIE_SECURE",
        "COOKIE_SAMESITE",
        "GRPC_BIND_ADDRESS",
        "ACTION_CREDENTIAL_ENCRYPTION_KEY",
        "AI_CREDENTIAL_ENCRYPTION_KEY",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT",
        "DB_POOL_RECYCLE",
    }
    for name in names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://relay:test@localhost:5432/ci_test")
    monkeypatch.setenv("JWT_SECRET_KEY", "synthetic-test-signing-secret")


@pytest.mark.parametrize("service", SERVICES)
def test_existing_development_defaults_start(service):
    load_config(service).validate_startup()


@pytest.mark.parametrize("service", [s for s in SERVICES if s != "api-gateway"])
def test_database_contract_masks_invalid_values(service, monkeypatch):
    config = load_config(service)
    monkeypatch.setenv("DATABASE_URL", "not-a-url-with-secret-canary")
    with pytest.raises(RuntimeError, match="DATABASE_URL") as exc:
        config.database_url()
    assert "secret-canary" not in str(exc.value)
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        config.database_url()


@pytest.mark.parametrize("service", [s for s in SERVICES if s != "api-gateway"])
def test_pool_bounds_and_grpc_aliases(service, monkeypatch):
    config = load_config(service)
    monkeypatch.setenv("DB_MAX_OVERFLOW", "0")
    assert config.database_options()["max_overflow"] == 0
    assert config.database_options()["echo"] is False
    assert config.database_options()["hide_parameters"] is True
    monkeypatch.setenv("DB_POOL_SIZE", "sensitive-canary")
    with pytest.raises(RuntimeError, match="DB_POOL_SIZE") as exc:
        config.database_options()
    assert "sensitive-canary" not in str(exc.value)
    monkeypatch.setenv("AUTH_GRPC_TARGET", "legacy-auth:50051")
    monkeypatch.delenv("AUTH_GRPC_URL", raising=False)
    assert (
        config.grpc_target("AUTH_GRPC_URL", "auth-service:50051", "AUTH_GRPC_TARGET")
        == "legacy-auth:50051"
    )
    monkeypatch.setenv("AUTH_GRPC_URL", "auth.relay.svc:50051")
    assert (
        config.grpc_target("AUTH_GRPC_URL", "default", "AUTH_GRPC_TARGET") == "auth.relay.svc:50051"
    )
    monkeypatch.setenv("GRPC_BIND_ADDRESS", "127.0.0.1:60051")
    assert config.grpc_bind_address(50051) == "127.0.0.1:60051"
    monkeypatch.setenv("GRPC_BIND_ADDRESS", "invalid")
    with pytest.raises(RuntimeError, match="GRPC_BIND_ADDRESS"):
        config.grpc_bind_address(50051)


@pytest.mark.parametrize("service", ["api-gateway", "auth-service", "workflow-service"])
def test_origins_are_explicit_https_in_production(service, monkeypatch):
    config = load_config(service)
    assert config.allowed_origins() == ["http://localhost:3000", "http://127.0.0.1:3000"]
    monkeypatch.setenv("RELAY_ENV", "production")
    with pytest.raises(RuntimeError, match="HTTPS"):
        config.allowed_origins()
    monkeypatch.setenv("FRONTEND_URL", "https://relay.example")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://admin.example")
    assert config.allowed_origins() == ["https://relay.example", "https://admin.example"]
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="explicit origins"):
        config.allowed_origins()


def test_gateway_http_overrides_are_independent_from_grpc(monkeypatch):
    monkeypatch.setenv("WORKFLOW_SERVICE_URL", "http://workflow.relay.svc:8000/")
    monkeypatch.setenv("WORKFLOW_GRPC_URL", "workflow.relay.svc:60052")
    assert load_config("api-gateway").WORKFLOW_SERVICE_URL == "http://workflow.relay.svc:8000"
    monkeypatch.setenv("WORKFLOW_SERVICE_URL", "http://username:secret-canary@workflow:8000")
    with pytest.raises(RuntimeError, match="WORKFLOW_SERVICE_URL") as exc:
        load_config("api-gateway")
    assert "secret-canary" not in str(exc.value)


def test_production_rejects_insecure_cookie_settings(monkeypatch):
    config = load_config("auth-service")
    monkeypatch.setenv("RELAY_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://relay.example")
    monkeypatch.setenv("BACKEND_URL", "https://relay.example/api/relay")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        config.validate_startup()
    monkeypatch.setenv("COOKIE_SECURE", "true")
    config.validate_startup()


@pytest.mark.parametrize(
    "service,key",
    [
        ("action-service", "ACTION_CREDENTIAL_ENCRYPTION_KEY"),
        ("execution-service", "AI_CREDENTIAL_ENCRYPTION_KEY"),
    ],
)
def test_production_requires_existing_encryption_key(service, key, monkeypatch):
    config = load_config(service)
    monkeypatch.setenv("RELAY_ENV", "production")
    with pytest.raises(RuntimeError, match=key):
        config.validate_startup()
    monkeypatch.setenv(key, "not-a-fernet-secret-canary")
    with pytest.raises(RuntimeError, match=key) as exc:
        config.validate_startup()
    assert "secret-canary" not in str(exc.value)


@pytest.mark.parametrize(
    "service,canonical,legacy,default",
    [
        ("rag-service", "AUTH_GRPC_URL", "AUTH_GRPC_TARGET", "auth-service:50051"),
        ("execution-service", "RAG_GRPC_URL", "RAG_GRPC_ADDRESS", "rag-service:50056"),
    ],
)
def test_layered_development_template_preserves_existing_legacy_target(
    service, canonical, legacy, default, monkeypatch
):
    from dotenv import dotenv_values

    # Compose loads the committed example first, then the existing service .env.
    # A template canonical default must not shadow an existing legacy setting.
    monkeypatch.delenv(canonical, raising=False)
    monkeypatch.delenv(legacy, raising=False)
    template = dotenv_values(SERVICE_ROOT / service / ".env.example")
    for name, value in template.items():
        if value is not None:
            monkeypatch.setenv(name, value)
    existing_target = "existing-private-host:60051"
    monkeypatch.setenv(legacy, existing_target)
    config = load_config(service)
    assert config.grpc_target(canonical, default, legacy) == existing_target
    # An explicitly configured new canonical setting still has precedence.
    monkeypatch.setenv(canonical, "explicit-canonical-host:60052")
    assert config.grpc_target(canonical, default, legacy) == "explicit-canonical-host:60052"
