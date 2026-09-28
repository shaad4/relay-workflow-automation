import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dependencies import get_current_identity
from app.grpc.generated.auth import auth_pb2
from app.routes import workflows


WORKFLOW_ID = uuid4()
WORKSPACE_ID = uuid4()
VERSION_ID = uuid4()
NODE_ID = uuid4()
EDGE_ID = uuid4()
NOW = datetime.now(timezone.utc)

workflow = SimpleNamespace(
    id=WORKFLOW_ID,
    workspace_id=WORKSPACE_ID,
    name="Example workflow",
    description="A test workflow",
    status="inactive",
    created_at=NOW,
    updated_at=NOW,
    published_version_id=None,
)
version = SimpleNamespace(
    id=VERSION_ID,
    workflow_id=WORKFLOW_ID,
    version=1,
    status="draft",
    description="Initial version",
    created_at=NOW,
)
node = SimpleNamespace(
    id=NODE_ID,
    workflow_version_id=VERSION_ID,
    node_id="start",
    node_type="trigger",
    label="Start",
    position_x=0,
    position_y=0,
    configuration={},
    created_at=NOW,
)
edge = SimpleNamespace(
    id=EDGE_ID,
    workflow_version_id=VERSION_ID,
    source_node_id="start",
    target_node_id="finish",
    condition=None,
    created_at=NOW,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(workflows.router)
    app.dependency_overrides[get_current_identity] = lambda: {
        "user_id": str(uuid4()),
        "workspace_id": str(WORKSPACE_ID),
    }

    async def fake_get_db():
        yield object()

    app.dependency_overrides[workflows.get_db] = fake_get_db
    with TestClient(app) as test_client:
        yield test_client


def test_create_workflow(client, monkeypatch):
    async def create_workflow(data, workspace_id, session):
        return workflow

    monkeypatch.setattr(workflows, "create_workflow", create_workflow)
    response = client.post(
        "/workflows/", json={"name": "Example workflow", "description": "A test workflow"}
    )
    assert response.status_code == 201
    assert response.json()["id"] == str(WORKFLOW_ID)


def test_list_workflows(client, monkeypatch):
    async def list_workflows(workspace_id, session):
        return [workflow]

    monkeypatch.setattr(workflows, "list_workflows", list_workflows)
    response = client.get("/workflows/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_workflow_and_not_found(client, monkeypatch):
    async def get_workflow(workflow_id, workspace_id, session):
        return workflow if workflow_id == WORKFLOW_ID else None

    monkeypatch.setattr(workflows, "get_workflow", get_workflow)
    found = client.get(f"/workflows/{WORKFLOW_ID}/")
    missing = client.get(f"/workflows/{uuid4()}/")
    assert found.status_code == 200
    assert missing.status_code == 404


def test_update_workflow(client, monkeypatch):
    async def update_workflow(workflow_id, workspace_id, data, session):
        return workflow

    monkeypatch.setattr(workflows, "update_workflow", update_workflow)
    response = client.patch(f"/workflows/{WORKFLOW_ID}/", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == workflow.name


def test_delete_workflow(client, monkeypatch):
    async def delete_workflow(workflow_id, workspace_id, session):
        return True

    monkeypatch.setattr(workflows, "delete_workflow", delete_workflow)
    response = client.delete(f"/workflows/{WORKFLOW_ID}/")
    assert response.status_code == 204


def test_workflow_versions(client, monkeypatch):
    async def list_workflow_versions(workflow_id, workspace_id, session):
        return [version]

    async def get_workflow_version(workflow_id, version_number, workspace_id, session):
        return workflow, version

    async def create_draft_version(workflow_id, workspace_id, session):
        return version

    monkeypatch.setattr(workflows, "list_workflow_versions", list_workflow_versions)
    monkeypatch.setattr(workflows, "get_workflow_version", get_workflow_version)
    monkeypatch.setattr(workflows, "create_draft_version", create_draft_version)

    listed = client.get(f"/workflows/{WORKFLOW_ID}/versions/")
    fetched = client.get(f"/workflows/{WORKFLOW_ID}/versions/1/")
    drafted = client.post(f"/workflows/{WORKFLOW_ID}/draft/")
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert fetched.status_code == 200
    assert drafted.status_code == 201


def test_create_list_update_delete_nodes(client, monkeypatch):
    async def create_workflow_node(workflow_id, version_number, workspace_id, data, session):
        return node

    async def list_workflow_nodes(workflow_id, version_number, workspace_id, session):
        return [node]

    async def update_workflow_node(workflow_id, version_number, node_id, workspace_id, data, session):
        return node

    async def delete_workflow_node(workflow_id, version_number, node_id, workspace_id, session):
        return True

    monkeypatch.setattr(workflows, "create_workflow_node", create_workflow_node)
    monkeypatch.setattr(workflows, "list_workflow_nodes", list_workflow_nodes)
    monkeypatch.setattr(workflows, "update_workflow_node", update_workflow_node)
    monkeypatch.setattr(workflows, "delete_workflow_node", delete_workflow_node)

    base = f"/workflows/{WORKFLOW_ID}/versions/1/nodes/"
    created = client.post(
        base,
        json={"node_id": "start", "node_type": "trigger", "configuration": {}},
    )
    listed = client.get(base)
    updated = client.patch(f"{base}start/", json={"label": "Updated"})
    deleted = client.delete(f"{base}start/")
    assert created.status_code == 201
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert updated.status_code == 200
    assert deleted.status_code == 204


def test_create_node_maps_value_error_to_bad_request(client, monkeypatch):
    async def create_workflow_node(workflow_id, version_number, workspace_id, data, session):
        raise ValueError("Only draft versions can be modified")

    monkeypatch.setattr(workflows, "create_workflow_node", create_workflow_node)
    response = client.post(
        f"/workflows/{WORKFLOW_ID}/versions/1/nodes/",
        json={"node_id": "start", "node_type": "trigger"},
    )
    assert response.status_code == 400


def test_create_list_update_delete_edges(client, monkeypatch):
    async def create_workflow_edge(workflow_id, version_number, workspace_id, data, session):
        return edge

    async def list_workflow_edges(workflow_id, version_number, workspace_id, session):
        return [edge]

    async def update_workflow_edge(workflow_id, version_number, edge_id, workspace_id, data, session):
        return edge

    async def delete_workflow_edge(workflow_id, version_number, edge_id, workspace_id, session):
        return True

    monkeypatch.setattr(workflows, "create_workflow_edge", create_workflow_edge)
    monkeypatch.setattr(workflows, "list_workflow_edges", list_workflow_edges)
    monkeypatch.setattr(workflows, "update_workflow_edge", update_workflow_edge)
    monkeypatch.setattr(workflows, "delete_workflow_edge", delete_workflow_edge)

    base = f"/workflows/{WORKFLOW_ID}/versions/1/edges/"
    created = client.post(
        base,
        json={"source_node_id": "start", "target_node_id": "finish"},
    )
    listed = client.get(base)
    updated = client.patch(f"{base}{EDGE_ID}/", json={"condition": "approved"})
    deleted = client.delete(f"{base}{EDGE_ID}/")
    assert created.status_code == 201
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert updated.status_code == 200
    assert deleted.status_code == 204


def test_validate_and_publish_workflow(client, monkeypatch):
    async def validate_workflow(workflow_id, version_number, workspace_id, session):
        return {"valid": True, "errors": [], "warnings": []}

    async def publish_workflow(workflow_id, version_number, workspace_id, session):
        return {
            "id": VERSION_ID,
            "workflow_id": WORKFLOW_ID,
            "version": 1,
            "status": "published",
        }

    monkeypatch.setattr(workflows, "validate_workflow", validate_workflow)
    monkeypatch.setattr(workflows, "publish_workflow", publish_workflow)
    base = f"/workflows/{WORKFLOW_ID}/versions/1"
    validated = client.post(f"{base}/validate/")
    published = client.post(f"{base}/publish/")
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    assert published.status_code == 200
    assert published.json()["status"] == "published"


@pytest.mark.parametrize(
    ("route", "service_name", "status"),
    [("activate", "activate_workflow", "active"), ("deactivate", "deactivate_workflow", "inactive")],
)
def test_activate_and_deactivate_workflow(client, monkeypatch, route, service_name, status):
    result = SimpleNamespace(
        id=WORKFLOW_ID,
        status=status,
        published_version_id=VERSION_ID,
    )

    async def update_status(workflow_id, workspace_id, session):
        return result

    monkeypatch.setattr(workflows, service_name, update_status)
    response = client.post(f"/workflows/{WORKFLOW_ID}/{route}/")
    assert response.status_code == 200
    assert response.json()["status"] == status


def test_health_and_protected_route(client):
    from app.main import app

    app.dependency_overrides[get_current_identity] = lambda: {
        "user_id": "user-123",
        "workspace_id": str(WORKSPACE_ID),
    }
    with TestClient(app) as main_client:
        health = main_client.get("/health")
        protected = main_client.get("/protected-test")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "workflow-service"}
    assert protected.status_code == 200
    assert protected.json()["user_id"] == "user-123"


def test_workflow_route_uses_auth_service_grpc(monkeypatch):
    from app.main import app

    class AuthClient:
        async def validate_token(self, token):
            assert token == "valid-access-token"
            return auth_pb2.ValidateTokenResponse(
                valid=True,
                user_id="user-123",
                workspace_id=str(WORKSPACE_ID),
            )

        async def close(self):
            pass

    monkeypatch.setattr("app.dependencies.AuthGrpcClient", AuthClient)

    async def list_workflows(workspace_id, session):
        assert workspace_id == str(WORKSPACE_ID)
        return [workflow]

    monkeypatch.setattr(workflows, "list_workflows", list_workflows)

    async def fake_get_db():
        yield object()

    app.dependency_overrides[workflows.get_db] = fake_get_db
    with TestClient(app) as test_client:
        response = test_client.get(
            "/workflows/",
            headers={"Authorization": "Bearer valid-access-token"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(WORKFLOW_ID)


@pytest.mark.parametrize(
    ("authorization", "expected_detail"),
    [
        (None, "Authorization header is required"),
        ("Basic token", "Invalid authorization header"),
        ("Bearer ", "Invalid authorization header"),
    ],
)
def test_auth_dependency_rejects_missing_or_malformed_header(
    authorization, expected_detail
):
    from fastapi import HTTPException
    import asyncio

    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_identity(authorization=authorization))
    assert error.value.status_code == 401
    assert error.value.detail == expected_detail


def test_auth_dependency_rejects_invalid_token_and_closes_client(monkeypatch):
    from fastapi import HTTPException
    import asyncio

    calls = {"token": None, "closed": False}

    class AuthClient:
        async def validate_token(self, token):
            calls["token"] = token
            return auth_pb2.ValidateTokenResponse(valid=False)

        async def close(self):
            calls["closed"] = True

    monkeypatch.setattr("app.dependencies.AuthGrpcClient", AuthClient)
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_identity(authorization="Bearer bad-token"))
    assert error.value.status_code == 401
    assert error.value.detail == "Invalid or expired access token"
    assert calls == {"token": "bad-token", "closed": True}
