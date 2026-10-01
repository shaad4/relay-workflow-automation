import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dependencies import get_current_identity
from app.kafka import producer as kafka
from app.schemas.events import WorkflowTriggeredEvent
from app.services import webhook_test_sessions as sessions


def test_test_sessions_create_get_publish_and_validate_scope():
    async def run():
        created = await sessions.create_session("webhook-a", "workspace-a")
        session_id = created["session_id"]
        assert created["timeout_seconds"] == 120
        assert (await sessions.get_session(session_id, "webhook-a", "workspace-a")) == {"status": "waiting", "result": None}
        assert await sessions.get_session(session_id, "webhook-b", "workspace-a") is None
        assert await sessions.get_session(session_id, "webhook-a", "workspace-b") is None
        assert await sessions.publish_result(session_id, "webhook-b", "success", {}) is False
        result = {"received": True, "payload": {"id": 3}}
        assert await sessions.publish_result(session_id, "webhook-a", "success", result) is True
        assert await sessions.publish_result(session_id, "webhook-a", "failed", {}) is False
        assert await sessions.get_session(session_id, "webhook-a", "workspace-a") == {"status": "success", "result": result}

    asyncio.run(run())


def test_test_sessions_publish_missing_webhook_and_expiration(monkeypatch):
    async def run():
        created = await sessions.create_session("webhook-a", "workspace-a")
        session_id = created["session_id"]
        assert await sessions.publish_session_result(session_id, "failed", {"status_code": 404}) is True
        assert await sessions.get_session(session_id, "webhook-a", "workspace-a") == {
            "status": "failed", "result": {"status_code": 404}
        }
        assert await sessions.publish_session_result(session_id, "failed", {}) is False

        expiring = await sessions.create_session("webhook-b", "workspace-a")
        entry = sessions._sessions[expiring["session_id"]]
        entry["expires_at"] = 0
        assert await sessions.get_session(expiring["session_id"], "webhook-b", "workspace-a") is None
        assert await sessions.publish_result(expiring["session_id"], "webhook-b", "failed", {}) is False

    asyncio.run(run())


def test_create_session_prunes_expired_sessions():
    async def run():
        expired_id = (await sessions.create_session("old", "workspace"))["session_id"]
        sessions._sessions[expired_id]["expires_at"] = 0
        new = await sessions.create_session("new", "workspace")
        assert expired_id not in sessions._sessions
        assert new["session_id"] in sessions._sessions

    asyncio.run(run())


def test_workflow_triggered_event_defaults_and_validation():
    event = WorkflowTriggeredEvent(
        event_id=uuid4(),
        workspace_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        webhook_id=uuid4(),
        payload={"order": "ORD-1"},
    )
    assert event.event_type == "workflow.triggered"
    assert event.payload == {"order": "ORD-1"}
    with pytest.raises(Exception):
        WorkflowTriggeredEvent(event_id="bad", workspace_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), webhook_id=uuid4(), payload={})


def test_kafka_lifecycle_and_publish(monkeypatch):
    calls = []

    class FakeProducer:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        async def start(self):
            calls.append(("start",))

        async def stop(self):
            calls.append(("stop",))

        async def send_and_wait(self, topic, value):
            calls.append((topic, json.loads(value)))

    monkeypatch.setattr(kafka, "AIOKafkaProducer", FakeProducer)
    monkeypatch.setattr(kafka, "producer", None)
    event = WorkflowTriggeredEvent(
        event_id=uuid4(), workspace_id=uuid4(), workflow_id=uuid4(),
        workflow_version_id=uuid4(), webhook_id=uuid4(), payload={"ok": True},
    )
    with pytest.raises(RuntimeError, match="not started"):
        asyncio.run(kafka.publish_workflow_triggered(event))
    asyncio.run(kafka.start_producer())
    asyncio.run(kafka.publish_workflow_triggered(event))
    asyncio.run(kafka.stop_producer())
    assert calls[0][0] == "init"
    assert calls[1] == ("start",)
    assert calls[2][0] == "workflow.triggered"
    assert calls[2][1]["payload"] == {"ok": True}
    assert calls[3] == ("stop",)
    assert kafka.producer is None


def test_stop_kafka_when_not_started(monkeypatch):
    monkeypatch.setattr(kafka, "producer", None)
    asyncio.run(kafka.stop_producer())
    assert kafka.producer is None


def test_auth_identity_validation_paths(monkeypatch):
    with pytest.raises(Exception) as missing:
        asyncio.run(get_current_identity(authorization=None, access_cookie=None))
    assert getattr(missing.value, "status_code", None) == 401
    with pytest.raises(Exception) as bad_scheme:
        asyncio.run(get_current_identity(authorization="Basic token"))
    assert getattr(bad_scheme.value, "status_code", None) == 401
    with pytest.raises(Exception) as empty_bearer:
        asyncio.run(get_current_identity(authorization="Bearer "))
    assert getattr(empty_bearer.value, "status_code", None) == 401

    class AuthClient:
        async def validate_token(self, token):
            assert token == "good-token"
            return SimpleNamespace(valid=True, user_id="user", workspace_id="workspace")

        async def close(self):
            pass

    monkeypatch.setattr("app.dependencies.AuthGrpcClient", AuthClient)
    result = asyncio.run(get_current_identity(authorization="Bearer good-token"))
    assert result == {"user_id": "user", "workspace_id": "workspace"}

    class InvalidClient(AuthClient):
        async def validate_token(self, _token):
            return SimpleNamespace(valid=False)

    monkeypatch.setattr("app.dependencies.AuthGrpcClient", InvalidClient)
    with pytest.raises(Exception) as invalid:
        asyncio.run(get_current_identity(authorization="Bearer bad-token"))
    assert getattr(invalid.value, "status_code", None) == 401


def test_auth_identity_uses_access_cookie_and_closes_client(monkeypatch):
    calls = []

    class AuthClient:
        async def validate_token(self, token):
            calls.append(("validate", token))
            raise RuntimeError("grpc down")

        async def close(self):
            calls.append(("close",))

    monkeypatch.setattr("app.dependencies.AuthGrpcClient", AuthClient)
    with pytest.raises(RuntimeError, match="grpc down"):
        asyncio.run(get_current_identity(authorization=None, access_cookie="cookie-token"))
    assert calls == [("validate", "cookie-token"), ("close",)]


def test_grpc_clients_forward_requests_and_close_channels(monkeypatch):
    from app.grpc import auth_client, workflow_client

    calls = []

    class Channel:
        async def close(self):
            calls.append(("channel-close",))

    channel = Channel()
    monkeypatch.setattr(auth_client.grpc.aio, "insecure_channel", lambda address: calls.append(("auth-channel", address)) or channel)
    class AuthStub:
        def __init__(self, received):
            assert received is channel
        async def ValidateToken(self, request):
            calls.append(("validate", request.access_token))
            return "valid"
        async def ResolveWorkspace(self, request):
            calls.append(("resolve", request.user_id))
            return "workspace"
    monkeypatch.setattr(auth_client.auth_pb2_grpc, "AuthInternalServiceStub", AuthStub)
    auth = auth_client.AuthGrpcClient()
    assert asyncio.run(auth.validate_token("token")) == "valid"
    assert asyncio.run(auth.resolve_workspace("user")) == "workspace"
    asyncio.run(auth.close())

    monkeypatch.setattr(workflow_client.grpc.aio, "insecure_channel", lambda address: calls.append(("workflow-channel", address)) or channel)
    class WorkflowStub:
        def __init__(self, received):
            assert received is channel
        async def ValidateWorkflowVersion(self, request):
            calls.append(("workflow-validate", request.workflow_id, request.version_id, request.workspace_id))
            return "ok"
    monkeypatch.setattr(workflow_client.workflow_pb2_grpc, "WorkflowInternalServiceStub", WorkflowStub)
    workflow = workflow_client.WorkflowGrpcClient()
    assert asyncio.run(workflow.validate_workflow_version("w", "v", "ws")) == "ok"
    asyncio.run(workflow.close())
    assert ("validate", "token") in calls
    assert ("resolve", "user") in calls
    assert ("workflow-validate", "w", "v", "ws") in calls
