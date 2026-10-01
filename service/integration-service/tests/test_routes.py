import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dependencies import get_current_identity
from app.routes import public_webhooks, webhooks


WORKSPACE_ID = uuid4()
WEBHOOK_ID = uuid4()
WORKFLOW_ID = uuid4()
VERSION_ID = uuid4()
NOW = "2026-01-01T00:00:00Z"


class FakeSession:
    pass


class Client:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(webhooks.router)
    app.include_router(public_webhooks.router)

    async def identity():
        return {"user_id": str(uuid4()), "workspace_id": str(WORKSPACE_ID)}

    async def db():
        yield FakeSession()

    app.dependency_overrides[get_current_identity] = identity
    app.dependency_overrides[webhooks.get_db] = db
    app.dependency_overrides[public_webhooks.get_db] = db
    return Client(app)


def webhook(**overrides):
    values = {
        "id": WEBHOOK_ID,
        "workspace_id": WORKSPACE_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version_id": VERSION_ID,
        "name": "Order events",
        "public_token": "public-token",
        "event_name": "order.created",
        "method": "POST",
        "authentication_type": "none",
        "secret_hash": None,
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return type("WebhookStub", (), values)()


def test_health_and_unknown_route(client):
    from app.main import app

    response = Client(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "integration-service"}
    assert app.title == "Relay Integration Service"


def test_create_webhook_validates_workspace_and_returns_secret(client, monkeypatch):
    created = webhook()
    secret = "rly_whsec_once"

    async def create(data, workspace_id, session):
        assert workspace_id == WORKSPACE_ID
        assert data.name == "Orders"
        return created, secret

    monkeypatch.setattr(webhooks, "create_webhook", create)
    response = client.post("/webhooks/", json={
        "workflow_id": str(WORKFLOW_ID),
        "workflow_version_id": str(VERSION_ID),
        "name": "Orders",
        "event_name": "order.created",
        "method": "POST",
        "authentication_type": "secret",
    })
    assert response.status_code == 201
    assert response.json()["secret"] == secret
    assert response.json()["public_token"] == "public-token"


@pytest.mark.parametrize("exception, expected", [("NOT_FOUND", 404), ("DEADLINE_EXCEEDED", 504), ("UNAVAILABLE", 503), ("OTHER", 502)])
def test_create_webhook_maps_workflow_service_errors(client, monkeypatch, exception, expected):
    import grpc

    codes = {
        "NOT_FOUND": grpc.StatusCode.NOT_FOUND,
        "DEADLINE_EXCEEDED": grpc.StatusCode.DEADLINE_EXCEEDED,
        "UNAVAILABLE": grpc.StatusCode.UNAVAILABLE,
        "OTHER": grpc.StatusCode.INTERNAL,
    }

    class RpcError(grpc.aio.AioRpcError):
        def __init__(self):
            super().__init__(codes[exception], None, None, "failure", None)

    async def fail(*_args, **_kwargs):
        raise RpcError()

    monkeypatch.setattr(webhooks, "create_webhook", fail)
    response = client.post("/webhooks/", json={
        "workflow_id": str(WORKFLOW_ID), "workflow_version_id": str(VERSION_ID),
        "name": "Orders", "event_name": "order.created", "method": "POST", "authentication_type": "none",
    })
    assert response.status_code == expected


def test_list_get_and_not_found_webhooks(client, monkeypatch):
    monkeypatch.setattr(webhooks, "list_webhooks", async_return([webhook()]))
    monkeypatch.setattr(webhooks, "get_webhook", async_return(webhook()))
    listed = client.get("/webhooks/")
    fetched = client.get(f"/webhooks/{WEBHOOK_ID}/")
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert fetched.status_code == 200 and fetched.json()["id"] == str(WEBHOOK_ID)

    monkeypatch.setattr(webhooks, "get_webhook", async_return(None))
    missing = client.get(f"/webhooks/{uuid4()}/")
    malformed = client.get("/webhooks/not-a-uuid/")
    assert missing.status_code == 404
    assert malformed.status_code == 422


def test_update_delete_and_regenerate_routes(client, monkeypatch):
    updated = webhook(name="Changed")
    monkeypatch.setattr(webhooks, "update_webhook", async_return(updated))
    response = client.patch(f"/webhooks/{WEBHOOK_ID}/", json={"name": "Changed"})
    assert response.status_code == 200 and response.json()["name"] == "Changed"

    monkeypatch.setattr(webhooks, "delete_webhook", async_return(True))
    deleted = client.delete(f"/webhooks/{WEBHOOK_ID}/")
    assert deleted.status_code == 204
    monkeypatch.setattr(webhooks, "delete_webhook", async_return(False))
    assert client.delete(f"/webhooks/{WEBHOOK_ID}/").status_code == 404

    regenerated = webhook(public_token="fresh-token")
    monkeypatch.setattr(webhooks, "regenerate_webhook_token", async_return(regenerated))
    response = client.post(f"/webhooks/{WEBHOOK_ID}/regenerate-token/")
    assert response.status_code == 200 and response.json()["public_token"] == "fresh-token"
    monkeypatch.setattr(webhooks, "regenerate_webhook_token", async_return(None))
    assert client.post(f"/webhooks/{WEBHOOK_ID}/regenerate-token/").status_code == 404


def test_webhook_update_delete_regenerate_reject_malformed_ids(client):
    assert client.patch("/webhooks/bad-id/", json={"name": "X"}).status_code == 400
    assert client.delete("/webhooks/bad-id/").status_code == 400
    assert client.post("/webhooks/bad-id/regenerate-token/").status_code == 400


def test_start_and_read_webhook_test_sessions(client, monkeypatch):
    monkeypatch.setattr(webhooks, "get_webhook", async_return(webhook()))
    response = client.post(f"/webhooks/{WEBHOOK_ID}/test-sessions/")
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    state = client.get(f"/webhooks/{WEBHOOK_ID}/test-sessions/{session_id}/")
    assert state.status_code == 200
    assert state.json() == {"status": "waiting", "result": None}
    assert client.get(f"/webhooks/{uuid4()}/test-sessions/{session_id}/").status_code == 404
    assert client.get(f"/webhooks/{WEBHOOK_ID}/test-sessions/bad-id/").status_code == 422


def test_test_session_routes_handle_missing_webhook_and_workspace(client, monkeypatch):
    monkeypatch.setattr(webhooks, "get_webhook", async_return(None))
    assert client.post(f"/webhooks/{WEBHOOK_ID}/test-sessions/").status_code == 404

    app = client.app
    async def invalid_identity():
        return {"workspace_id": "not-a-uuid"}
    app.dependency_overrides[get_current_identity] = invalid_identity
    assert client.post(f"/webhooks/{WEBHOOK_ID}/test-sessions/").status_code == 401
    assert client.get(f"/webhooks/{WEBHOOK_ID}/test-sessions/{uuid4()}/").status_code == 401


def async_return(value):
    async def result(*_args, **_kwargs):
        return value
    return result


def test_public_webhook_not_found_inactive_and_auth_errors(client, monkeypatch):
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(None))
    assert client.post("/hooks/missing", json={}).status_code == 404
    assert client.post("/hooks/missing/test", json={}).status_code == 404

    inactive = webhook(is_active=False)
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(inactive))
    assert client.post("/hooks/public-token", json={}).status_code == 403
    assert client.post("/hooks/public-token/test", json={}).status_code == 403

    protected = webhook(authentication_type="secret", secret_hash="hash")
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(protected))
    assert client.post("/hooks/public-token", json={}).status_code == 401
    assert client.post("/hooks/public-token/test", json={}).status_code == 401
    monkeypatch.setattr(public_webhooks, "verify_webhook_secret", lambda **_kwargs: False)
    assert client.post("/hooks/public-token", json={}, headers={"X-Relay-Secret": "wrong"}).status_code == 401
    assert client.post("/hooks/public-token/test", json={}, headers={"X-Relay-Secret": "wrong"}).status_code == 401


def test_public_webhook_validates_secret_configuration_and_json(client, monkeypatch):
    broken = webhook(authentication_type="secret", secret_hash=None)
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(broken))
    assert client.post("/hooks/public-token", json={}, headers={"X-Relay-Secret": "secret"}).status_code == 500
    assert client.post("/hooks/public-token/test", json={}, headers={"X-Relay-Secret": "secret"}).status_code == 500

    valid = webhook(authentication_type="secret", secret_hash="hash")
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(valid))
    monkeypatch.setattr(public_webhooks, "verify_webhook_secret", lambda **_kwargs: True)
    invalid_json = client.post("/hooks/public-token", content="bad json", headers={"X-Relay-Secret": "secret", "Content-Type": "application/json"})
    invalid_test_json = client.post("/hooks/public-token/test", content="bad json", headers={"X-Relay-Secret": "secret", "Content-Type": "application/json"})
    assert invalid_json.status_code == invalid_test_json.status_code == 400


def test_public_webhook_accepts_and_publishes_workflow_event(client, monkeypatch):
    target = webhook()
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(target))
    events = []

    async def publish(event):
        events.append(event)

    monkeypatch.setattr(public_webhooks, "publish_workflow_triggered", publish)
    response = client.post("/hooks/public-token", json={"order_id": "ORD-1"})
    assert response.status_code == 202
    assert response.json()["webhook_id"] == str(WEBHOOK_ID)
    assert len(events) == 1
    assert events[0].payload == {"order_id": "ORD-1"}
    assert events[0].workflow_id == WORKFLOW_ID


def test_public_test_webhook_returns_payload_and_updates_session(client, monkeypatch):
    target = webhook()
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(target))
    from app.services.webhook_test_sessions import create_session, get_session

    async def run():
        created = await create_session(str(WEBHOOK_ID), str(WORKSPACE_ID))
        return created

    test_session = asyncio.run(run())["session_id"]
    response = client.post(f"/hooks/public-token/test?relay_test_session={test_session}", json={"amount": 99})
    assert response.status_code == 200
    assert response.json()["received"] is True
    assert response.json()["payload"] == {"amount": 99}

    async def state():
        return await get_session(test_session, str(WEBHOOK_ID), str(WORKSPACE_ID))

    assert asyncio.run(state())["status"] == "success"


def test_public_test_webhook_reports_invalid_json_into_session(client, monkeypatch):
    target = webhook()
    monkeypatch.setattr(public_webhooks, "get_webhook_by_public_token", async_return(target))
    from app.services.webhook_test_sessions import create_session, get_session

    created = asyncio.run(create_session(str(WEBHOOK_ID), str(WORKSPACE_ID)))
    session_id = created["session_id"]
    response = client.post(f"/hooks/public-token/test?relay_test_session={session_id}", content="not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    state = asyncio.run(get_session(session_id, str(WEBHOOK_ID), str(WORKSPACE_ID)))
    assert state["status"] == "failed"
    assert state["result"]["status_code"] == 400
