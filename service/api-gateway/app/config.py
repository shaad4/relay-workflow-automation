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


AUTH_SERVICE_URL = http_url("AUTH_SERVICE_URL", "http://auth-service:8000")
WORKFLOW_SERVICE_URL = http_url("WORKFLOW_SERVICE_URL", "http://workflow-service:8000")
INTEGRATION_SERVICE_URL = http_url("INTEGRATION_SERVICE_URL", "http://integration-service:8000")
ACTION_SERVICE_URL = http_url("ACTION_SERVICE_URL", "http://action-service:8000")
EXECUTION_SERVICE_URL = http_url("EXECUTION_SERVICE_URL", "http://execution-service:8000")
RAG_SERVICE_URL = http_url("RAG_SERVICE_URL", "http://rag-service:8000")


def validate_startup() -> None:
    key = required("JWT_SECRET_KEY")
    if production() and key in {
        "your-secret-key",
        "relay-development-only-jwt-secret-do-not-use-in-production",
        "changeme",
        "replace-me",
    }:
        raise RuntimeError("JWT_SECRET_KEY must not be a development placeholder in production")
    allowed_origins()
