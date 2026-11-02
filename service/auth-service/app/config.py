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


def http_url(name: str, default: str) -> str:
    value = os.getenv(name, default).rstrip("/")
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and parsed.port != 0
        valid = valid and not (
            parsed.username or parsed.password or parsed.query or parsed.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError(f"{name} must be an HTTP(S) URL without credentials")
    return value


def allowed_origins() -> list[str]:
    frontend = http_url("FRONTEND_URL", "http://localhost:3000")
    origins = [frontend]
    extra = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if extra:
        origins.extend(item.strip().rstrip("/") for item in extra.split(","))
    parsed = urlsplit(frontend)
    if not production() and parsed.hostname in {"localhost", "127.0.0.1"}:
        other = "127.0.0.1" if parsed.hostname == "localhost" else "localhost"
        origins.append(frontend.replace(parsed.hostname, other, 1))
    for origin in origins:
        try:
            item = urlsplit(origin)
            valid = item.scheme in {"http", "https"} and item.hostname and item.port != 0
            valid = valid and not (
                item.username or item.password or item.path or item.query or item.fragment
            )
            valid = valid and (not production() or item.scheme == "https")
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError(
                "FRONTEND_URL/CORS_ALLOWED_ORIGINS must contain explicit origins; HTTPS is required in production"
            )
    return list(dict.fromkeys(origins))


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
    key = required("JWT_SECRET_KEY")
    if production() and key in {
        "your-secret-key",
        "relay-development-only-jwt-secret-do-not-use-in-production",
        "changeme",
        "replace-me",
    }:
        raise RuntimeError("JWT_SECRET_KEY must not be a development placeholder in production")
    allowed_origins()
    if production() and not http_url("BACKEND_URL", "http://localhost:8001").startswith("https://"):
        raise RuntimeError("BACKEND_URL must use HTTPS in production")
    secure = os.getenv("COOKIE_SECURE", "true").lower()
    same_site = os.getenv("COOKIE_SAMESITE", "lax").lower()
    if secure not in {"true", "false"}:
        raise RuntimeError("COOKIE_SECURE must be true or false")
    if same_site not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE must be lax, strict or none")
    if (production() or same_site == "none") and secure != "true":
        raise RuntimeError("COOKIE_SECURE must be true in production and with SameSite=None")
