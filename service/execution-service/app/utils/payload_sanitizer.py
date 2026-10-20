import json
import re
from typing import Any


REDACTED = "[REDACTED]"
TRUNCATED = "[TRUNCATED]"

MAX_DEPTH = 12
MAX_ITEMS = 200
MAX_STRING_LENGTH = 10000

SENSITIVE_KEYS = {
    "authorization",
    "proxy_authorization",
    "x_api_key",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "client_secret_key",
    "credential",
    "credentials",
    "private_key",
    "cookie",
    "set_cookie",
    "session_token",
    "bearer_token",
}

SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/\-=]+"
    ),
    re.compile(
        r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
        r"[\s\S]*?"
        r"-----END (?:[A-Z ]+ )?PRIVATE KEY-----"
    ),
)


def normalize_key(key: Any) -> str:
    """Normalize field names for sensitive-key detection."""
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(key).lower(),
    ).strip("_")


def is_sensitive_key(key: Any) -> bool:
    """Check whether a JSON field contains credentials."""
    normalized = normalize_key(key)

    if normalized in SENSITIVE_KEYS:
        return True

    return normalized.endswith(
        (
            "_password",
            "_secret",
            "_token",
            "_api_key",
            "_private_key",
            "_credential",
        )
    )


def sanitize_string(value: str) -> str:
    """Mask recognized secrets embedded inside strings."""
    result = value

    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(REDACTED, result)

    if len(result) > MAX_STRING_LENGTH:
        return result[:MAX_STRING_LENGTH] + TRUNCATED

    return result


def sanitize_payload(
    payload: Any,
    depth: int = 0,
) -> Any:
    """
    Return a sanitized JSON-compatible copy.

    The original payload is never modified.
    """

    if depth >= MAX_DEPTH:
        return TRUNCATED

    if payload is None:
        return None

    if isinstance(payload, dict):
        sanitized = {}

        for index, (key, value) in enumerate(
            payload.items()
        ):
            if index >= MAX_ITEMS:
                sanitized["_truncated"] = TRUNCATED
                break

            safe_key = str(key)

            if is_sensitive_key(key):
                sanitized[safe_key] = REDACTED
            else:
                sanitized[safe_key] = sanitize_payload(
                    value,
                    depth + 1,
                )

        return sanitized

    if isinstance(payload, (list, tuple)):
        sanitized = [
            sanitize_payload(item, depth + 1)
            for item in payload[:MAX_ITEMS]
        ]

        if len(payload) > MAX_ITEMS:
            sanitized.append(TRUNCATED)

        return sanitized

    if isinstance(payload, str):
        return sanitize_string(payload)

    if isinstance(payload, (int, float, bool)):
        return payload

    # Convert supported custom objects to JSON-safe values.
    try:
        converted = json.loads(
            json.dumps(payload, default=str)
        )
    except (TypeError, ValueError):
        return TRUNCATED

    return sanitize_payload(converted, depth + 1)
