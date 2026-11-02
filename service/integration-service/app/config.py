"""Environment contract for this independently deployable service.

Validation errors identify settings, never their values. Existing secret values
are consumed unchanged; this module never generates or rotates credentials.
"""

import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


def required(name: str) -> str:
    value = os.getenv(name, "")
    if not value.strip():
        raise RuntimeError(f"{name} is required")
    return value


def integer(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise RuntimeError(f"{name} must be an integer") from None
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


def production() -> bool:
    return os.getenv("RELAY_ENV", "development").lower() == "production"


def database_url() -> str:
    value = required("DATABASE_URL")
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "postgresql+asyncpg"
            and parsed.hostname
            and parsed.path not in {"", "/"}
        )
        valid = valid and parsed.port != 0
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError("DATABASE_URL must be a valid postgresql+asyncpg URL")
    if production() and parsed.password in {"relay_dev_only", "replace-me", "changeme"}:
        raise RuntimeError("DATABASE_URL must not use a development placeholder in production")
    return value


def database_options() -> dict:
    return {
        "echo": False,
        "hide_parameters": True,
        "pool_pre_ping": True,
        "pool_size": integer("DB_POOL_SIZE", 5),
        "max_overflow": integer("DB_MAX_OVERFLOW", 5, minimum=0),
        "pool_timeout": integer("DB_POOL_TIMEOUT", 30),
        "pool_recycle": integer("DB_POOL_RECYCLE", 1800),
    }


def grpc_target(name: str, default: str, *aliases: str) -> str:
    value = next((os.environ[key] for key in (name, *aliases) if key in os.environ), default)
    if not value.strip() or value.startswith(("http://", "https://")):
        raise RuntimeError(f"{name} must be a gRPC target, not an HTTP URL")
    return value


def grpc_bind_address(port: int) -> str:
    address = os.getenv("GRPC_BIND_ADDRESS", f"[::]:{port}")
    try:
        valid = address.rsplit(":", 1)[0] and 0 < int(address.rsplit(":", 1)[1]) < 65536
    except (ValueError, IndexError):
        valid = False
    if not valid:
        raise RuntimeError("GRPC_BIND_ADDRESS must be a host:port bind address")
    return address


def validate_startup() -> None:
    database_url()
    database_options()
