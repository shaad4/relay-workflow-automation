"""Authentication diagnostics containing no credentials or personal identity."""

import hashlib
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id = ContextVar("oauth_request_id", default=None)
logger = logging.getLogger("relay.mcp.oauth")


def configure_audit_logging():
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False


def audit_event(event, *, client_id=None, grant_id=None, **fields):
    # Call sites supply fixed categories/status codes, never exception strings,
    # HTTP bodies, headers, URLs, token values or user/workspace identifiers.
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": request_id.get(),
        **fields,
    }
    for name, value in (("client_ref", client_id), ("grant_ref", grant_id)):
        if isinstance(value, str) and value:
            record[name] = hashlib.sha256(value.encode()).hexdigest()[:16]
    logger.info(json.dumps(record, separators=(",", ":")))
