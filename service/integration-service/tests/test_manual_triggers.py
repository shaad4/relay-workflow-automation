import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4

import grpc
import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.routes import manual_triggers as routes


@pytest.fixture
def manual(monkeypatch):
    workflow_id, workspace_id, version_id = uuid4(), uuid4(), uuid4()
    client = NS(
        get_published_version=AsyncMock(return_value=NS(version_id=str(version_id))),
        get_workflow_definition=AsyncMock(
            return_value=NS(nodes_json='[{"node_type":"trigger.manual"}]')
        ),
        close=AsyncMock(),
    )
    publish = AsyncMock()
    monkeypatch.setattr(routes, "WorkflowGrpcClient", lambda: client)
    monkeypatch.setattr(routes, "publish_workflow_triggered", publish)
    return NS(
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        version_id=version_id,
        client=client,
        publish=publish,
    )


def request(body=b'{"input":{"report":"daily"}}', headers=None):
    headers = headers if headers is not None else {"content-type": "application/json"}
    chunks = iter([body[:10], body[10:]])

    async def receive():
        chunk = next(chunks)
        return {"type": "http.request", "body": chunk, "more_body": len(chunk) == 10}

    return Request(
        {"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers.items()]}, receive
    )


def run(manual, req=None, identity=None):
    return asyncio.run(
        routes.run_workflow_manually(
            manual.workflow_id,
            req or request(),
            identity if identity is not None else {"workspace_id": str(manual.workspace_id)},
        )
    )


def test_manual_dispatch_uses_authenticated_workspace_and_published_version(manual):
    result = run(manual, request(headers={"content-type": "Application/JSON; charset=utf-8"}))
    event = manual.publish.await_args.args[0]
    assert result["status"] == "accepted" and result["execution_started"] is False
    assert result["event_id"] == str(event.event_id)
    assert event.workspace_id == manual.workspace_id
    assert (
        event.workflow_id == manual.workflow_id and event.workflow_version_id == manual.version_id
    )
    assert event.trigger_type == "manual" and event.payload == {"report": "daily"}
    manual.client.get_workflow_definition.assert_awaited_once_with(
        workflow_id=str(manual.workflow_id),
        version_id=str(manual.version_id),
        workspace_id=str(manual.workspace_id),
    )
    manual.client.close.assert_awaited_once()


@pytest.mark.parametrize(
    "body,headers,status",
    [
        (b"{}", {}, 415),
        (b"{}", {"content-type": "text/plain"}, 415),
        (b"{}", {"content-type": "application/json", "content-length": "bad"}, 400),
        (b"{}", {"content-type": "application/json", "content-length": "-1"}, 400),
        (b"{}", {"content-type": "application/json", "content-length": "65537"}, 413),
        (b"x" * 65537, {"content-type": "application/json"}, 413),
        (b"{", {"content-type": "application/json"}, 422),
        (b"\xff", {"content-type": "application/json"}, 422),
        (b'{"input":[]}', {"content-type": "application/json"}, 422),
        (b'{"input":{},"workspace_id":"spoofed"}', {"content-type": "application/json"}, 422),
    ],
)
def test_manual_rejects_invalid_payload_before_dispatch(manual, body, headers, status):
    with pytest.raises(HTTPException) as exc:
        run(manual, request(body, headers))
    assert exc.value.status_code == status
    manual.publish.assert_not_awaited()
    manual.client.get_published_version.assert_not_awaited()


@pytest.mark.parametrize("identity", [{}, {"workspace_id": "invalid"}, {"workspace_id": None}])
def test_manual_rejects_invalid_workspace(manual, identity):
    with pytest.raises(HTTPException) as exc:
        run(manual, identity=identity)
    assert exc.value.status_code == 401
    manual.publish.assert_not_awaited()


@pytest.mark.parametrize(
    "code,status",
    [
        (grpc.StatusCode.NOT_FOUND, 404),
        (grpc.StatusCode.FAILED_PRECONDITION, 409),
        (grpc.StatusCode.DEADLINE_EXCEEDED, 504),
        (grpc.StatusCode.UNAVAILABLE, 503),
    ],
)
def test_manual_workflow_errors_close_client_without_dispatch(manual, code, status):
    manual.client.get_workflow_definition.side_effect = grpc.aio.AioRpcError(code, (), (), "test")
    with pytest.raises(HTTPException) as exc:
        run(manual)
    assert exc.value.status_code == status
    manual.client.close.assert_awaited_once()
    manual.publish.assert_not_awaited()


@pytest.mark.parametrize(
    "nodes,status",
    [
        ("bad-json", 502),
        ("{}", 502),
        ("[null]", 502),
        ("[]", 409),
        ('[{"node_type":"trigger.webhook"}]', 409),
        ('[{"node_type":"trigger.manual"},{"node_type":"trigger.schedule"}]', 409),
    ],
)
def test_manual_requires_one_manual_trigger(manual, nodes, status):
    manual.client.get_workflow_definition.return_value.nodes_json = nodes
    with pytest.raises(HTTPException) as exc:
        run(manual)
    assert exc.value.status_code == status
    manual.publish.assert_not_awaited()
    manual.client.close.assert_awaited_once()


def test_manual_publish_failure_reports_unavailable(manual):
    manual.publish.side_effect = RuntimeError("Kafka unavailable")
    with pytest.raises(HTTPException) as exc:
        run(manual)
    assert exc.value.status_code == 503
    assert "dispatch" in exc.value.detail
