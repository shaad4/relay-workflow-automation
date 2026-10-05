import asyncio
import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from pathlib import Path

import pytest
import grpc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grpc import server, workflow_server
from app.grpc.generated.workflow import workflow_pb2
from app.grpc.workflow_server import WorkflowInternalService


class FakeSession:
    def __init__(self, results):
        self.results = iter(results)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, _query):
        return next(self.results)


class FakeResult:
    def __init__(self, scalar=None, scalars=()):
        self.scalar = scalar
        self.values = list(scalars)

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class FakeContext:
    def __init__(self):
        self.code = None
        self.details = None

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


def install_session_factory(monkeypatch, *results):
    monkeypatch.setattr(
        workflow_server, "AsyncSessionLocal", lambda: FakeSession(results)
    )


def test_get_published_version_not_found(monkeypatch):
    install_session_factory(monkeypatch, FakeResult())
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetPublishedVersion(
            workflow_pb2.GetPublishedVersionRequest(
                workflow_id="missing", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.version_id == ""
    assert context.code == grpc.StatusCode.NOT_FOUND
    assert context.details == "Published workflow version not found"


def test_get_published_version_returns_version(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", published_version_id="version-id")
    version = SimpleNamespace(
        id="version-id", workflow_id="workflow-id", version=2, status="published"
    )
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult(version))
    response = asyncio.run(
        WorkflowInternalService().GetPublishedVersion(
            workflow_pb2.GetPublishedVersionRequest(
                workflow_id="workflow-id", workspace_id="workspace"
            ),
            FakeContext(),
        )
    )
    assert (response.version_id, response.version, response.status) == (
        "version-id",
        2,
        "published",
    )


def test_get_published_version_row_not_found(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", published_version_id="deleted-version")
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult())
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetPublishedVersion(
            workflow_pb2.GetPublishedVersionRequest(
                workflow_id="workflow-id", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.version_id == ""
    assert context.code == grpc.StatusCode.NOT_FOUND
    assert context.details == "Published workflow version not found"


def test_validate_workflow_version_checks_workspace_and_returns_version_status(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", status="active")
    version = SimpleNamespace(id="version-id", workflow_id="workflow-id", version=4, status="draft")
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult(version))
    response = asyncio.run(
        WorkflowInternalService().ValidateWorkflowVersion(
            workflow_pb2.ValidateWorkflowVersionRequest(
                workflow_id="workflow-id", version_id="version-id", workspace_id="workspace-id"
            ),
            FakeContext(),
        )
    )
    assert response.valid is True
    assert response.status == "draft"
    assert response.workflow_status == "active"


def test_validate_workflow_version_rejects_wrong_workspace(monkeypatch):
    install_session_factory(monkeypatch, FakeResult())
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().ValidateWorkflowVersion(
            workflow_pb2.ValidateWorkflowVersionRequest(
                workflow_id="workflow-id", version_id="version-id", workspace_id="wrong-workspace"
            ),
            context,
        )
    )
    assert response.valid is False
    assert context.code == grpc.StatusCode.NOT_FOUND


def test_get_workflow_definition_not_found(monkeypatch):
    install_session_factory(monkeypatch, FakeResult())
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetWorkflowDefinition(
            workflow_pb2.GetWorkflowDefinitionRequest(
                workflow_id="missing", version_id="version", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.workflow_id == ""
    assert context.code == grpc.StatusCode.NOT_FOUND
    assert context.details == "Workflow not found"


def test_get_workflow_definition_version_not_found(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", status="active")
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult())
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetWorkflowDefinition(
            workflow_pb2.GetWorkflowDefinitionRequest(
                workflow_id="workflow-id", version_id="missing", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.version_id == ""
    assert context.code == grpc.StatusCode.NOT_FOUND
    assert context.details == "Workflow version not found"


def test_get_workflow_definition_rejects_draft_version(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", status="active")
    version = SimpleNamespace(id="version-id", workflow_id="workflow-id", status="draft")
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult(version))
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetWorkflowDefinition(
            workflow_pb2.GetWorkflowDefinitionRequest(
                workflow_id="workflow-id", version_id="version-id", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.version_id == ""
    assert context.code == grpc.StatusCode.FAILED_PRECONDITION
    assert context.details == "Workflow version is not published"


def test_get_workflow_definition_serializes_nodes_and_edges(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", status="active")
    version = SimpleNamespace(
        id="version-id", workflow_id="workflow-id", version=3, status="published"
    )
    node = SimpleNamespace(
        id="node-id", workflow_version_id="version-id", node_id="start",
        node_type="trigger", label="Start", position_x=1, position_y=2,
        configuration={"key": "value"},
    )
    edge = SimpleNamespace(
        id="edge-id", workflow_version_id="version-id", source_node_id="start",
        target_node_id="finish", condition="ok",
    )
    install_session_factory(
        monkeypatch,
        FakeResult(workflow),
        FakeResult(version),
        FakeResult(scalars=[node]),
        FakeResult(scalars=[edge]),
    )
    response = asyncio.run(
        WorkflowInternalService().GetWorkflowDefinition(
            workflow_pb2.GetWorkflowDefinitionRequest(
                workflow_id="workflow-id", version_id="version-id", workspace_id="workspace"
            ),
            FakeContext(),
        )
    )
    assert (response.version, response.status) == (3, "published")
    assert json.loads(response.nodes_json)[0]["configuration"] == {"key": "value"}
    assert json.loads(response.edges_json)[0]["condition"] == "ok"


def test_get_workflow_definition_rejects_inactive_workflow(monkeypatch):
    workflow = SimpleNamespace(id="workflow-id", status="inactive")
    version = SimpleNamespace(
        id="version-id", workflow_id="workflow-id", version=3, status="published"
    )
    install_session_factory(monkeypatch, FakeResult(workflow), FakeResult(version))
    context = FakeContext()
    response = asyncio.run(
        WorkflowInternalService().GetWorkflowDefinition(
            workflow_pb2.GetWorkflowDefinitionRequest(
                workflow_id="workflow-id", version_id="version-id", workspace_id="workspace"
            ),
            context,
        )
    )
    assert response.version_id == ""
    assert context.code == grpc.StatusCode.FAILED_PRECONDITION
    assert context.details == "Workflow is inactive"


def test_start_grpc_server_registers_service_and_starts(monkeypatch):
    calls = []

    class FakeServer:
        def add_insecure_port(self, address):
            calls.append(("port", address))

        async def start(self):
            calls.append(("start",))

    fake_server = FakeServer()
    monkeypatch.setattr(server.grpc.aio, "server", lambda: fake_server)
    monkeypatch.setattr(
        server.workflow_pb2_grpc,
        "add_WorkflowInternalServiceServicer_to_server",
        lambda servicer, target: calls.append(("register", isinstance(servicer, WorkflowInternalService), target)),
    )
    result = asyncio.run(server.start_grpc_server())
    assert result is fake_server
    assert calls == [
        ("register", True, fake_server),
        ("port", "[::]:50052"),
        ("start",),
    ]
