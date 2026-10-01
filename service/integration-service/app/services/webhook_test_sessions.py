"""Short-lived handoff state for an open webhook test drawer.

Sessions are intentionally ephemeral, workspace-scoped, and expire quickly. The
public test request remains the source of truth; this only mirrors its response
to the authenticated browser that started that test.
"""

import asyncio
import time
import uuid

SESSION_TTL_SECONDS = 150
_sessions: dict[str, dict] = {}
_lock = asyncio.Lock()


async def create_session(webhook_id: str, workspace_id: str) -> dict:
    now = time.monotonic()
    async with _lock:
        for key, item in list(_sessions.items()):
            if item["expires_at"] <= now:
                _sessions.pop(key, None)
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "webhook_id": webhook_id,
            "workspace_id": workspace_id,
            "status": "waiting",
            "result": None,
            "expires_at": now + SESSION_TTL_SECONDS,
            "event": asyncio.Event(),
        }
        _sessions[session_id] = session
        return {"session_id": session_id, "timeout_seconds": 120}


async def get_session(session_id: str, webhook_id: str, workspace_id: str) -> dict | None:
    async with _lock:
        session = _sessions.get(session_id)
        if not session or session["expires_at"] <= time.monotonic():
            _sessions.pop(session_id, None)
            return None
        if session["webhook_id"] != webhook_id or session["workspace_id"] != workspace_id:
            return None
        return {"status": session["status"], "result": session["result"]}


async def publish_result(session_id: str, webhook_id: str, status: str, result: dict) -> bool:
    async with _lock:
        session = _sessions.get(session_id)
        if not session or session["expires_at"] <= time.monotonic():
            _sessions.pop(session_id, None)
            return False
        if session["webhook_id"] != webhook_id or session["status"] != "waiting":
            return False
        session["status"] = status
        session["result"] = result
        session["event"].set()
        return True


async def publish_session_result(session_id: str, status: str, result: dict) -> bool:
    async with _lock:
        session = _sessions.get(session_id)
        if not session or session["expires_at"] <= time.monotonic() or session["status"] != "waiting":
            return False
        session["status"] = status
        session["result"] = result
        session["event"].set()
        return True
