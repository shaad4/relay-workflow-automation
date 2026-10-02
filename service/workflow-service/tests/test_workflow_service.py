import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.workflow_edge import WorkflowEdgeUpdate
from app.schemas.workflow_node import WorkflowNodeUpdate
from app.services import workflow_service as service


WORKFLOW_ID = uuid4()
WORKSPACE_ID = uuid4()
VERSION_ID = uuid4()


class Result:
    def __init__(self, scalar=None, scalars=None):
        self.scalar = scalar
        self.values = scalars or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values, first=lambda: self.values[0] if self.values else None)


class FakeSession:
    def __init__(self, results=(), fail_commit=False):
        self.results = iter(results)
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    async def execute(self, statement):
        return next(self.results)

    def add(self, value):
        self.added.append(value)
        if getattr(value, "id", None) is None:
            value.id = uuid4()

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("commit failed")

    async def refresh(self, value):
        return None

    async def rollback(self):
        self.rollbacks += 1

    async def delete(self, value):
        self.deleted.append(value)


def test_create_workflow_creates_initial_draft():
    session = FakeSession()
    result = pytest.importorskip("asyncio").run(
        service.create_workflow(
            WorkflowCreate(name="Orders", description="Order flow"),
            WORKSPACE_ID,
            session,
        )
    )
    created_workflow, initial_version = session.added
    assert result is created_workflow
    assert created_workflow.name == "Orders"
    assert created_workflow.workspace_id == WORKSPACE_ID
    assert initial_version.version == 1
    assert initial_version.status == "draft"
    assert session.commits == 1


def test_create_workflow_rolls_back_when_commit_fails():
    import asyncio

    session = FakeSession(fail_commit=True)
    with pytest.raises(RuntimeError, match="commit failed"):
        asyncio.run(
            service.create_workflow(
                WorkflowCreate(name="Orders"), WORKSPACE_ID, session
            )
        )
    assert session.rollbacks == 1


def test_update_workflow_applies_only_provided_fields():
    import asyncio

    existing = SimpleNamespace(name="Old", description="Keep me")
    session = FakeSession([Result(scalar=existing)])
    updated = asyncio.run(
        service.update_workflow(
            WORKFLOW_ID,
            WORKSPACE_ID,
            WorkflowUpdate(name="New"),
            session,
        )
    )
    assert updated.name == "New"
    assert updated.description == "Keep me"
    assert session.commits == 1


def test_create_draft_version_copies_nodes_and_edges():
    import asyncio

    latest = SimpleNamespace(id=VERSION_ID, version=2, description="Latest")
    source_node = SimpleNamespace(
        node_id="start",
        node_type="trigger",
        label="Start",
        position_x=4,
        position_y=8,
        configuration={"key": "value"},
    )
    source_edge = SimpleNamespace(
        source_node_id="start", target_node_id="finish", condition="ok"
    )
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalars=[latest]),
            Result(scalars=[source_node]),
            Result(scalars=[source_edge]),
        ]
    )

    new_version = asyncio.run(
        service.create_draft_version(WORKFLOW_ID, WORKSPACE_ID, session)
    )
    copied_node, copied_edge = session.added[1:]
    assert new_version.version == 3
    assert new_version.status == "draft"
    assert copied_node.node_id == "start"
    assert copied_node.configuration == {"key": "value"}
    assert copied_edge.source_node_id == "start"
    assert copied_edge.condition == "ok"


def test_create_draft_version_requires_new_webhook_without_mutating_source():
    import asyncio

    latest = SimpleNamespace(id=VERSION_ID, version=1, description="Published setup")
    source_webhook_config = {
        "webhook_id": "v1-webhook-id",
        "public_token": "v1-public-token",
        "secret": "v1-secret",
        "endpoint": "https://relay.example/hooks/v1-token",
        "path": "/hooks/v1-token",
        "event_name": "orders.created",
        "authentication_type": "secret",
        "method": "POST",
        "custom_option": "keep this node setting",
    }
    webhook_node = SimpleNamespace(
        node_id="webhook-trigger",
        node_type="trigger.webhook",
        label="Order trigger",
        position_x=12,
        position_y=24,
        configuration=source_webhook_config,
    )
    action_node = SimpleNamespace(
        node_id="send-email",
        node_type="action.email",
        label="Send email",
        position_x=200,
        position_y=24,
        configuration={"to": "ops@example.com", "subject": "New order"},
    )
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalars=[latest]),
            Result(scalars=[webhook_node, action_node]),
            Result(scalars=[]),
        ]
    )

    new_version = asyncio.run(service.create_draft_version(WORKFLOW_ID, WORKSPACE_ID, session))
    copied_webhook, copied_action = session.added[1:]

    assert new_version.version == 2
    assert copied_webhook.workflow_version_id == new_version.id
    assert copied_webhook.node_type == "trigger.webhook"
    assert copied_webhook.label == webhook_node.label
    assert copied_webhook.position_x == webhook_node.position_x
    assert copied_webhook.configuration == {
        "method": "POST",
        "setup_required": True,
    }
    assert copied_action.configuration == action_node.configuration
    assert source_webhook_config["webhook_id"] == "v1-webhook-id"
    assert source_webhook_config["public_token"] == "v1-public-token"
    assert source_webhook_config["secret"] == "v1-secret"


def test_update_node_rejects_duplicate_id():
    import asyncio

    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    existing_node = SimpleNamespace(id=uuid4(), node_id="start")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalars=[existing_node]),
            Result(scalar=uuid4()),
        ]
    )
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(
            service.update_workflow_node(
                WORKFLOW_ID,
                1,
                "start",
                WORKSPACE_ID,
                WorkflowNodeUpdate(node_id="other"),
                session,
            )
        )
    assert session.commits == 0


def test_update_edge_rejects_missing_target_node():
    import asyncio

    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    existing_edge = SimpleNamespace(id=uuid4(), target_node_id="old")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalar=existing_edge),
            Result(scalar=None),
        ]
    )
    with pytest.raises(ValueError, match="Target node not found"):
        asyncio.run(
            service.update_workflow_edge(
                WORKFLOW_ID,
                1,
                existing_edge.id,
                WORKSPACE_ID,
                WorkflowEdgeUpdate(target_node_id="missing"),
                session,
            )
        )
    assert existing_edge.target_node_id == "old"
    assert session.commits == 0


def test_validate_workflow_reports_empty_workflow_and_invalid_edges():
    import asyncio

    draft = SimpleNamespace(id=VERSION_ID)
    bad_edge = SimpleNamespace(source_node_id="missing-source", target_node_id="missing-target")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalars=[]),
            Result(scalars=[bad_edge]),
        ]
    )
    result = asyncio.run(
        service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session)
    )
    assert result["valid"] is False
    assert {error["code"] for error in result["errors"]} == {
        "NO_NODES",
        "INVALID_EDGE_SOURCE",
        "INVALID_EDGE_TARGET",
    }


def test_publish_workflow_updates_version_and_workflow():
    import asyncio

    draft = SimpleNamespace(id=VERSION_ID, version=3, status="draft")
    active_workflow = SimpleNamespace(
        id=WORKFLOW_ID, status="inactive", published_version_id=None
    )
    session = FakeSession(
        [
            Result(scalar=active_workflow),
            Result(scalar=draft),
            Result(scalar=active_workflow),
            Result(scalar=draft),
            Result(scalars=[SimpleNamespace(node_id="start")]),
            Result(scalars=[]),
        ]
    )
    published = asyncio.run(
        service.publish_workflow(WORKFLOW_ID, 3, WORKSPACE_ID, session)
    )
    assert published["status"] == "published"
    assert draft.status == "published"
    assert active_workflow.status == "active"
    assert active_workflow.published_version_id == VERSION_ID
    assert session.commits == 1


def test_delete_workflow_returns_false_when_missing_and_deletes_when_found():
    missing_session = FakeSession([Result(scalar=None)])
    assert asyncio.run(
        service.delete_workflow(WORKFLOW_ID, WORKSPACE_ID, missing_session)
    ) is False

    found = SimpleNamespace(id=WORKFLOW_ID, status="draft")
    session = FakeSession([Result(scalar=found), Result(), Result(), Result(), Result()])
    assert asyncio.run(
        service.delete_workflow(WORKFLOW_ID, WORKSPACE_ID, session)
    ) is True
    assert session.deleted == [found]
    assert session.commits == 1


@pytest.mark.parametrize("status", ["draft", "inactive"])
def test_delete_workflow_accepts_draft_and_inactive(status):
    workflow = SimpleNamespace(id=WORKFLOW_ID, status=status)
    session = FakeSession([Result(scalar=workflow), Result(), Result(), Result(), Result()])

    assert asyncio.run(
        service.delete_workflow(WORKFLOW_ID, WORKSPACE_ID, session)
    ) is True
    assert session.deleted == [workflow]
    assert session.commits == 1


def test_delete_workflow_rolls_back_if_cascade_delete_fails():
    workflow = SimpleNamespace(id=WORKFLOW_ID, status="draft")
    session = FakeSession([Result(scalar=workflow)], fail_commit=False)
    # The initial lookup succeeds; a subsequent dependent-row delete fails.
    calls = 0

    async def execute(statement):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Result(scalar=workflow)
        raise RuntimeError("cascade delete failed")

    session.execute = execute
    with pytest.raises(RuntimeError, match="cascade delete failed"):
        asyncio.run(service.delete_workflow(WORKFLOW_ID, WORKSPACE_ID, session))

    assert session.rollbacks == 1
    assert session.commits == 0


@pytest.mark.parametrize("status", ["active", "published"])
def test_delete_workflow_rejects_active_statuses(status):
    workflow = SimpleNamespace(id=WORKFLOW_ID, status=status)
    session = FakeSession([Result(scalar=workflow)])

    with pytest.raises(ValueError, match="Only draft or inactive"):
        asyncio.run(service.delete_workflow(WORKFLOW_ID, WORKSPACE_ID, session))

    assert session.deleted == []
    assert session.commits == 0


def test_create_workflow_node_rejects_non_draft_and_adds_valid_node():
    from app.schemas.workflow_node import WorkflowNodeCreate

    workflow_row = SimpleNamespace(id=WORKFLOW_ID)
    published = SimpleNamespace(id=VERSION_ID, status="published")
    session = FakeSession([Result(scalar=workflow_row), Result(scalar=published)])
    with pytest.raises(ValueError, match="Only draft"):
        asyncio.run(
            service.create_workflow_node(
                WORKFLOW_ID,
                1,
                WORKSPACE_ID,
                WorkflowNodeCreate(node_id="start", node_type="trigger"),
                session,
            )
        )

    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    session = FakeSession(
        [Result(scalar=workflow_row), Result(scalar=draft), Result(scalar=None)]
    )
    created = asyncio.run(
        service.create_workflow_node(
            WORKFLOW_ID,
            1,
            WORKSPACE_ID,
            WorkflowNodeCreate(node_id="start", node_type="trigger"),
            session,
        )
    )
    assert created.node_id == "start"
    assert created.workflow_version_id == VERSION_ID
    assert session.commits == 1


def test_update_workflow_node_applies_fields():
    node = SimpleNamespace(id=uuid4(), node_id="start", label="Before")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=SimpleNamespace(id=VERSION_ID, status="draft")),
            Result(scalars=[node]),
        ]
    )
    updated = asyncio.run(
        service.update_workflow_node(
            WORKFLOW_ID,
            1,
            "start",
            WORKSPACE_ID,
            WorkflowNodeUpdate(label="After"),
            session,
        )
    )
    assert updated.label == "After"
    assert session.commits == 1


def test_create_workflow_edge_checks_nodes_then_creates_edge():
    from app.schemas.workflow_edge import WorkflowEdgeCreate

    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalar=SimpleNamespace(node_id="start")),
            Result(scalar=SimpleNamespace(node_id="finish")),
        ]
    )
    created = asyncio.run(
        service.create_workflow_edge(
            WORKFLOW_ID,
            1,
            WORKSPACE_ID,
            WorkflowEdgeCreate(source_node_id="start", target_node_id="finish"),
            session,
        )
    )
    assert created.source_node_id == "start"
    assert created.target_node_id == "finish"
    assert session.commits == 1


def test_validate_workflow_reports_duplicate_node_ids():
    nodes = [
        SimpleNamespace(node_id="start"),
        SimpleNamespace(node_id="start"),
    ]
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=SimpleNamespace(id=VERSION_ID)),
            Result(scalars=nodes),
            Result(scalars=[]),
        ]
    )
    result = asyncio.run(
        service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session)
    )
    assert result["valid"] is False
    assert result["errors"][0]["code"] == "DUPLICATE_NODE_ID"


def test_activate_and_deactivate_require_published_version():
    unpublished = SimpleNamespace(published_version_id=None, status="inactive")
    session = FakeSession([Result(scalar=unpublished)])
    with pytest.raises(ValueError, match="no published version"):
        asyncio.run(service.activate_workflow(WORKFLOW_ID, WORKSPACE_ID, session))

    published = SimpleNamespace(published_version_id=VERSION_ID, status="active")
    session = FakeSession([Result(scalar=published)])
    with pytest.raises(ValueError, match="already active"):
        asyncio.run(service.activate_workflow(WORKFLOW_ID, WORKSPACE_ID, session))

    published.status = "active"
    session = FakeSession([Result(scalar=published)])
    deactivated = asyncio.run(
        service.deactivate_workflow(WORKFLOW_ID, WORKSPACE_ID, session)
    )
    assert deactivated.status == "inactive"
    assert session.commits == 1


def test_publish_rejects_invalid_workflow():
    draft = SimpleNamespace(id=VERSION_ID, version=1, status="draft")
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=draft),
            Result(scalars=[]),
            Result(scalars=[]),
        ]
    )
    with pytest.raises(ValueError, match="validation failed"):
        asyncio.run(service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))
    assert session.commits == 0


@pytest.mark.parametrize(
    ("function", "results", "args"),
    [
        (service.update_workflow, [Result(scalar=None)], (WorkflowUpdate(name="X"),)),
        (service.list_workflow_versions, [Result(scalar=None)], ()),
        (service.get_workflow_version, [Result(scalar=None)], (1,)),
        (service.create_draft_version, [Result(scalar=None)], ()),
        (service.list_workflow_nodes, [Result(scalar=None)], (1,)),
        (service.list_workflow_edges, [Result(scalar=None)], (1,)),
    ],
)
def test_service_returns_none_for_missing_workflow(function, results, args):
    session = FakeSession(results)
    result = asyncio.run(function(WORKFLOW_ID, WORKSPACE_ID, *args, session=session))
    assert result is None or result == (None, None)


def test_get_and_list_versions_missing_version():
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    get_session = FakeSession([Result(scalar=workflow), Result(scalar=None)])
    assert asyncio.run(
        service.get_workflow_version(WORKFLOW_ID, 4, WORKSPACE_ID, get_session)
    ) == (workflow, None)

    list_session = FakeSession([Result(scalar=workflow), Result(scalars=[])])
    assert asyncio.run(
        service.list_workflow_versions(WORKFLOW_ID, WORKSPACE_ID, list_session)
    ) == []


def test_create_draft_version_returns_none_when_no_previous_version():
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalars=[]),
        ]
    )
    assert asyncio.run(
        service.create_draft_version(WORKFLOW_ID, WORKSPACE_ID, session)
    ) is None


@pytest.mark.parametrize("function", [service.update_workflow_node, service.delete_workflow_node])
def test_node_mutations_reject_ambiguous_duplicate_ids(function):
    nodes = [SimpleNamespace(id=uuid4(), node_id="same"), SimpleNamespace(id=uuid4(), node_id="same")]
    session = FakeSession(
        [
            Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
            Result(scalar=SimpleNamespace(id=VERSION_ID, status="draft")),
            Result(scalars=nodes),
        ]
    )
    with pytest.raises(ValueError, match="ambiguous"):
        if function is service.update_workflow_node:
            asyncio.run(
                function(WORKFLOW_ID, 1, "same", WORKSPACE_ID, WorkflowNodeUpdate(label="x"), session)
            )
        else:
            asyncio.run(function(WORKFLOW_ID, 1, "same", WORKSPACE_ID, session))


def test_create_edge_rejects_missing_source_and_target():
    from app.schemas.workflow_edge import WorkflowEdgeCreate

    base_results = [
        Result(scalar=SimpleNamespace(id=WORKFLOW_ID)),
        Result(scalar=SimpleNamespace(id=VERSION_ID, status="draft")),
    ]
    with pytest.raises(ValueError, match="Source node not found"):
        asyncio.run(
            service.create_workflow_edge(
                WORKFLOW_ID, 1, WORKSPACE_ID,
                WorkflowEdgeCreate(source_node_id="missing", target_node_id="target"),
                FakeSession([*base_results, Result(scalar=None)]),
            )
        )
    with pytest.raises(ValueError, match="Target node not found"):
        asyncio.run(
            service.create_workflow_edge(
                WORKFLOW_ID, 1, WORKSPACE_ID,
                WorkflowEdgeCreate(source_node_id="source", target_node_id="missing"),
                FakeSession([*base_results, Result(scalar=object()), Result(scalar=None)]),
            )
        )


def test_delete_node_and_edge_return_none_when_not_found():
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    node_session = FakeSession(
        [Result(scalar=workflow), Result(scalar=draft), Result(scalars=[])]
    )
    assert asyncio.run(
        service.delete_workflow_node(WORKFLOW_ID, 1, "missing", WORKSPACE_ID, node_session)
    ) is None

    edge_session = FakeSession(
        [Result(scalar=workflow), Result(scalar=draft), Result(scalar=None)]
    )
    assert asyncio.run(
        service.delete_workflow_edge(WORKFLOW_ID, 1, uuid4(), WORKSPACE_ID, edge_session)
    ) is None


@pytest.mark.parametrize(
    ("operation", "result_count"),
    [("workflow", 1), ("node", 1), ("edge", 1), ("draft", 4), ("publish", 6)],
)
def test_mutation_failures_roll_back(operation, result_count):
    from app.schemas.workflow_edge import WorkflowEdgeCreate
    from app.schemas.workflow_node import WorkflowNodeCreate

    workflow = SimpleNamespace(
        id=WORKFLOW_ID,
        workspace_id=WORKSPACE_ID,
        name="Before",
        description=None,
        status="inactive",
        published_version_id=None,
    )
    draft = SimpleNamespace(id=VERSION_ID, version=1, status="draft", description=None)
    results_by_operation = {
        "workflow": [Result(scalar=workflow)],
        "node": [Result(scalar=workflow), Result(scalar=draft), Result(scalar=None)],
        "edge": [Result(scalar=workflow), Result(scalar=draft), Result(scalar=object()), Result(scalar=object())],
        "draft": [Result(scalar=workflow), Result(scalars=[draft]), Result(scalars=[]), Result(scalars=[])],
        "publish": [Result(scalar=workflow), Result(scalar=draft), Result(scalar=workflow), Result(scalar=draft), Result(scalars=[SimpleNamespace(node_id="ok")]), Result(scalars=[])],
    }
    session = FakeSession(results_by_operation[operation], fail_commit=True)
    with pytest.raises(RuntimeError, match="commit failed"):
        if operation == "workflow":
            asyncio.run(service.update_workflow(WORKFLOW_ID, WORKSPACE_ID, WorkflowUpdate(name="After"), session))
        elif operation == "node":
            asyncio.run(service.create_workflow_node(WORKFLOW_ID, 1, WORKSPACE_ID, WorkflowNodeCreate(node_id="x", node_type="task"), session))
        elif operation == "edge":
            asyncio.run(service.create_workflow_edge(WORKFLOW_ID, 1, WORKSPACE_ID, WorkflowEdgeCreate(source_node_id="a", target_node_id="b"), session))
        elif operation == "draft":
            asyncio.run(service.create_draft_version(WORKFLOW_ID, WORKSPACE_ID, session))
        else:
            asyncio.run(service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))
    assert session.rollbacks == 1


def test_list_get_workflows_and_missing_update():
    rows = [SimpleNamespace(id=WORKFLOW_ID), SimpleNamespace(id=uuid4())]
    list_session = FakeSession([Result(scalars=rows)])
    assert asyncio.run(service.list_workflows(WORKSPACE_ID, list_session)) == rows

    found_session = FakeSession([Result(scalar=rows[0])])
    assert asyncio.run(service.get_workflow(WORKFLOW_ID, WORKSPACE_ID, found_session)) is rows[0]

    missing_session = FakeSession([Result(scalar=None)])
    assert asyncio.run(
        service.update_workflow(WORKFLOW_ID, WORKSPACE_ID, WorkflowUpdate(name="X"), missing_session)
    ) is None


def test_list_nodes_and_missing_version():
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    version = SimpleNamespace(id=VERSION_ID)
    node_rows = [SimpleNamespace(node_id="start")]
    session = FakeSession(
        [Result(scalar=workflow), Result(scalar=version), Result(scalars=node_rows)]
    )
    assert asyncio.run(service.list_workflow_nodes(WORKFLOW_ID, 1, WORKSPACE_ID, session)) == node_rows

    missing_version = FakeSession([Result(scalar=workflow), Result(scalar=None)])
    assert asyncio.run(
        service.list_workflow_nodes(WORKFLOW_ID, 1, WORKSPACE_ID, missing_version)
    ) is None


def test_update_and_delete_node_missing_and_readonly_cases():
    import_node = SimpleNamespace(id=uuid4(), node_id="start")
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    draft = SimpleNamespace(id=VERSION_ID, status="draft")

    missing_node_session = FakeSession(
        [Result(scalar=workflow), Result(scalar=draft), Result(scalars=[])]
    )
    assert asyncio.run(
        service.update_workflow_node(
            WORKFLOW_ID, 1, "missing", WORKSPACE_ID, WorkflowNodeUpdate(label="X"), missing_node_session
        )
    ) is None

    readonly = SimpleNamespace(id=VERSION_ID, status="published")
    readonly_session = FakeSession([Result(scalar=workflow), Result(scalar=readonly)])
    with pytest.raises(ValueError, match="Only draft"):
        asyncio.run(service.delete_workflow_node(WORKFLOW_ID, 1, "start", WORKSPACE_ID, readonly_session))

    delete_session = FakeSession(
        [Result(scalar=workflow), Result(scalar=draft), Result(scalars=[import_node])]
    )
    assert asyncio.run(
        service.delete_workflow_node(WORKFLOW_ID, 1, "start", WORKSPACE_ID, delete_session)
    ) is True
    assert delete_session.deleted == [import_node]


def test_update_and_delete_edge_successful_paths():
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    draft = SimpleNamespace(id=VERSION_ID, status="draft")
    edge = SimpleNamespace(id=uuid4(), source_node_id="old", target_node_id="old")
    update_session = FakeSession(
        [
            Result(scalar=workflow),
            Result(scalar=draft),
            Result(scalar=edge),
            Result(scalar=SimpleNamespace(node_id="start")),
            Result(scalar=SimpleNamespace(node_id="finish")),
        ]
    )
    updated = asyncio.run(
        service.update_workflow_edge(
            WORKFLOW_ID,
            1,
            edge.id,
            WORKSPACE_ID,
            WorkflowEdgeUpdate(source_node_id="start", target_node_id="finish"),
            update_session,
        )
    )
    assert updated.source_node_id == "start"
    assert updated.target_node_id == "finish"
    assert update_session.commits == 1

    delete_session = FakeSession(
        [Result(scalar=workflow), Result(scalar=draft), Result(scalar=edge)]
    )
    assert asyncio.run(
        service.delete_workflow_edge(WORKFLOW_ID, 1, edge.id, WORKSPACE_ID, delete_session)
    ) is True
    assert delete_session.deleted == [edge]


def test_list_edges_and_validation_missing_workflow_or_version():
    workflow = SimpleNamespace(id=WORKFLOW_ID)
    version = SimpleNamespace(id=VERSION_ID)
    edge_rows = [SimpleNamespace(source_node_id="a", target_node_id="b")]
    session = FakeSession(
        [Result(scalar=workflow), Result(scalar=version), Result(scalars=edge_rows)]
    )
    assert asyncio.run(service.list_workflow_edges(WORKFLOW_ID, 1, WORKSPACE_ID, session)) == edge_rows

    missing_workflow = FakeSession([Result(scalar=None)])
    assert asyncio.run(service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, missing_workflow)) is None
    missing_version = FakeSession([Result(scalar=workflow), Result(scalar=None)])
    assert asyncio.run(service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, missing_version)) is None


def test_publish_requires_draft_and_activation_transitions():
    workflow = SimpleNamespace(id=WORKFLOW_ID, status="inactive", published_version_id=VERSION_ID)
    published = SimpleNamespace(id=VERSION_ID, version=1, status="published")
    session = FakeSession([Result(scalar=workflow), Result(scalar=published)])
    with pytest.raises(ValueError, match="Only draft versions"):
        asyncio.run(service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))

    inactive = SimpleNamespace(id=WORKFLOW_ID, status="inactive", published_version_id=VERSION_ID)
    session = FakeSession([Result(scalar=inactive)])
    with pytest.raises(ValueError, match="already inactive"):
        asyncio.run(service.deactivate_workflow(WORKFLOW_ID, WORKSPACE_ID, session))

    inactive.status = "inactive"
    session = FakeSession([Result(scalar=inactive)])
    activated = asyncio.run(service.activate_workflow(WORKFLOW_ID, WORKSPACE_ID, session))
    assert activated.status == "active"
    assert session.commits == 1
