"""Publication validation contracts, without external services or runtime inputs."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest
from app.schemas.workflow import WorkflowValidationResponse
from app.services import workflow_service as service
from app.services.workflow_validation import NODE_VALIDATORS, validate_cycles
from test_workflow_service import VERSION_ID, WORKFLOW_ID, WORKSPACE_ID, FakeSession, Result

IDENTIFIER = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
VALID_CONFIGS = {
    "trigger.webhook": {"webhook_id": IDENTIFIER, "method": "POST", "path": "/hooks/start"},
    "trigger.manual": {},
    "trigger.schedule": {"schedule_type": "interval", "interval_minutes": 30},
    "action.http_request": {
        "connection_id": IDENTIFIER,
        "url": "https://example.com",
        "headers": "X-User: {{trigger.data.user}}",
        "body": "{}",
    },
    "action.email": {
        "connection_id": IDENTIFIER,
        "to": "{{trigger.data.email}}",
        "subject": "Hello",
        "body": "Hello {{trigger.data.name}}",
    },
    "action.refund": {"connection_id": IDENTIFIER, "payment_id": "pi_example", "amount": "5.25"},
    "human.approval": {
        "approver_user_id": IDENTIFIER,
        "message": "Approve {{trigger.data.name}}?",
        "timeout_minutes": "30",
    },
    "ai.rag_search": {"knowledge_base_id": IDENTIFIER, "query": "{{trigger.data.question}}"},
    "ai.decision": {
        "connection_id": IDENTIFIER,
        "model": "test-model",
        "instructions": "Classify",
        "allowed_decisions": ["YES", "NO"],
    },
    "ai.generate": {
        "connection_id": IDENTIFIER,
        "model": "test-model",
        "prompt": "{{trigger.data.prompt}}",
    },
    "logic.condition": {"value": "{{trigger.data.result}}"},
}


def node(node_id, node_type, config=None):
    return NS(
        node_id=node_id,
        node_type=node_type,
        configuration=deepcopy(VALID_CONFIGS.get(node_type, {}) if config is None else config),
    )


def edge(source, target, condition=None):
    return NS(source_node_id=source, target_node_id=target, condition=condition)


def validate(nodes, edges=(), status="draft"):
    session = FakeSession(
        [
            Result(scalar=NS(id=WORKFLOW_ID)),
            Result(scalar=NS(id=VERSION_ID, status=status)),
            Result(scalars=nodes),
            Result(scalars=list(edges)),
        ]
    )
    result = asyncio.run(service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))
    assert session.commits == 0
    return result


def validate_config(node_type, config):
    target = node("target", node_type, config)
    if node_type.startswith("trigger."):
        return validate([target])
    nodes = [node("start", "trigger.manual"), target]
    edges = [edge("start", "target")]
    if node_type == "logic.condition":
        nodes.append(node("end", "action.email"))
        edges.append(edge("target", "end", "YES"))
    return validate(nodes, edges)


@pytest.mark.parametrize("node_type", VALID_CONFIGS)
def test_valid_configuration_for_every_supported_type(node_type):
    assert set(VALID_CONFIGS) == set(NODE_VALIDATORS)
    assert validate_config(node_type, VALID_CONFIGS[node_type]) == {
        "valid": True,
        "errors": [],
        "warnings": [],
    }


@pytest.mark.parametrize(
    "node_type,field",
    [
        ("trigger.webhook", "webhook_id"),
        ("trigger.schedule", "schedule_type"),
        ("action.http_request", "connection_id"),
        ("action.http_request", "url"),
        ("action.email", "connection_id"),
        ("action.email", "to"),
        ("action.email", "subject"),
        ("action.email", "body"),
        ("action.refund", "connection_id"),
        ("action.refund", "payment_id"),
        ("action.refund", "amount"),
        ("human.approval", "approver_user_id"),
        ("human.approval", "message"),
        ("ai.rag_search", "knowledge_base_id"),
        ("ai.rag_search", "query"),
        ("ai.decision", "connection_id"),
        ("ai.decision", "model"),
        ("ai.decision", "instructions"),
        ("ai.decision", "allowed_decisions"),
        ("ai.generate", "connection_id"),
        ("ai.generate", "model"),
        ("ai.generate", "prompt"),
        ("logic.condition", "value"),
    ],
)
def test_missing_required_field_identifies_node_and_field(node_type, field):
    config = deepcopy(VALID_CONFIGS[node_type])
    del config[field]
    result = validate_config(node_type, config)
    issue = next(error for error in result["errors"] if f"{field} -" in error["message"])
    assert issue["node_id"] == "target"
    assert issue["code"] == NODE_VALIDATORS[node_type][1]
    # Endpoint serialization must retain the identifiers in the message.
    serialized = WorkflowValidationResponse.model_validate(result).model_dump()
    assert any(
        "'target'" in error["message"] and field in error["message"]
        for error in serialized["errors"]
    )


@pytest.mark.parametrize(
    "node_type,field,value",
    [
        ("trigger.webhook", "webhook_id", "invalid"),
        ("trigger.webhook", "method", "GET"),
        ("trigger.webhook", "path", 42),
        ("trigger.manual", "description", []),
        ("trigger.manual", "input_schema", []),
        ("trigger.schedule", "interval_minutes", True),
        ("action.http_request", "connection_id", "bad"),
        ("action.http_request", "url", []),
        ("action.http_request", "url", " "),
        ("action.http_request", "method", "BAD METHOD"),
        ("action.http_request", "timeout", True),
        ("action.http_request", "timeout", "10"),
        ("action.http_request", "timeout", 0),
        ("action.http_request", "timeout", 121),
        ("action.http_request", "headers", 42),
        ("action.http_request", "params", 42),
        ("action.email", "to", []),
        ("action.email", "body_format", "markdown"),
        ("action.refund", "payment_id", {}),
        ("action.refund", "amount", True),
        ("action.refund", "amount", []),
        ("action.refund", "amount", "NaN"),
        ("action.refund", "amount", "Infinity"),
        ("action.refund", "amount", -1),
        ("action.refund", "amount", 0),
        ("action.refund", "amount", ""),
        ("human.approval", "approver_user_id", "invalid"),
        ("human.approval", "message", []),
        ("human.approval", "timeout_minutes", 0),
        ("human.approval", "timeout_minutes", True),
        ("human.approval", "timeout_minutes", "1.5"),
        ("human.approval", "approver_user_id", "{{trigger.data.user}}"),
        ("human.approval", "timeout_minutes", "{{trigger.data.timeout}}"),
        ("ai.rag_search", "top_k", True),
        ("ai.decision", "input_mappings", []),
        ("ai.generate", "prompt", 123),
        ("logic.condition", "value", False),
    ],
)
def test_invalid_types_and_values(node_type, field, value):
    result = validate_config(node_type, {**VALID_CONFIGS[node_type], field: value})
    assert not result["valid"]
    assert any(
        error.get("node_id") == "target" and field in error["message"] for error in result["errors"]
    )


@pytest.mark.parametrize("node_type", VALID_CONFIGS)
@pytest.mark.parametrize("config", [[], "", False, 0])
def test_configuration_must_be_an_object(node_type, config):
    result = validate_config(node_type, config)
    assert any(
        error.get("node_id") == "target" and "configuration -" in error["message"]
        for error in result["errors"]
    )


@pytest.mark.parametrize(
    "node_type,patch",
    [
        (
            "action.http_request",
            {
                "url": "https://{{trigger.data.host}}/path",
                "timeout": "{{trigger.data.timeout}}",
                "method": "{{trigger.data.method}}",
                "connection_id": "{{trigger.data.connection}}",
                "body": {"amount": "{{trigger.data.amount}}"},
            },
        ),
        (
            "action.refund",
            {"amount": "{{trigger.data.amount}}", "payment_id": "{{trigger.data.payment}}"},
        ),
        ("action.email", {"body_format": "{{trigger.data.format}}"}),
        (
            "ai.rag_search",
            {"knowledge_base_id": "{{trigger.data.kb}}", "top_k": "{{trigger.data.limit}}"},
        ),
        (
            "ai.decision",
            {
                "connection_id": "{{trigger.data.connection}}",
                "input_mappings": {"amount": "{{trigger.data.amount}}"},
            },
        ),
        ("ai.generate", {"connection_id": "{{trigger.data.connection}}"}),
        (
            "ai.decision",
            {
                "input_mappings": "{{trigger.data.inputs}}",
                "allowed_decisions": "{{trigger.data.decisions}}",
            },
        ),
        (
            "ai.decision",
            {"allowed_decisions": ["{{trigger.data.first}}", "{{trigger.data.second}}"]},
        ),
        ("human.approval", {"message": "{{trigger.data.message}}"}),
        ("logic.condition", {"value": "{{trigger.data.decision}}"}),
    ],
)
def test_dynamic_inputs_are_not_resolved_during_validation(node_type, patch):
    assert validate_config(node_type, {**VALID_CONFIGS[node_type], **patch})["valid"]


@pytest.mark.parametrize(
    "node_type,patch",
    [
        (
            "action.http_request",
            {"method": "head", "headers": {"X-Value": "{{trigger.data.value}}"}, "timeout": 1.5},
        ),
        ("action.http_request", {"method": "OPTIONS", "headers": "", "body": [1, 2]}),
        (
            "action.http_request",
            {"headers": [["X-User", "{{trigger.data.user}}"]], "params": [["q", "search"]]},
        ),
        ("action.refund", {"payment_id": "custom-provider-id", "amount": 1.25}),
        ("human.approval", {"timeout_minutes": None}),
        ("action.email", {"legacy_metadata": "retained"}),
    ],
)
def test_compatible_optional_and_legacy_values(node_type, patch):
    config = {**VALID_CONFIGS[node_type], **patch}
    assert validate_config(node_type, config)["valid"]


def test_unknown_node_type():
    result = validate(
        [node("start", "trigger.manual"), node("unknown", "custom.unknown")],
        [edge("start", "unknown")],
    )
    assert result["errors"] == [
        {
            "code": "UNSUPPORTED_NODE_TYPE",
            "node_id": "unknown",
            "message": "Node 'unknown' uses unsupported type 'custom.unknown'.",
        }
    ]


@pytest.mark.parametrize(
    "nodes,edges,code",
    [
        ([], [], "NO_NODES"),
        ([node("a", "action.email")], [], "INVALID_TRIGGER"),
        ([node("a", "trigger.manual"), node("b", "trigger.webhook")], [], "INVALID_TRIGGER"),
        ([node("a", "trigger.manual"), node("a", "action.email")], [], "DUPLICATE_NODE_ID"),
        ([node("a", "trigger.manual")], [edge("missing", "a")], "INVALID_EDGE_SOURCE"),
        ([node("a", "trigger.manual")], [edge("a", "missing")], "INVALID_EDGE_TARGET"),
        (
            [node("a", "trigger.manual"), node("b", "action.email"), node("c", "action.email")],
            [edge("a", "b"), edge("a", "c")],
            "INVALID_BRANCHING",
        ),
        (
            [node("a", "trigger.manual"), node("b", "action.email")],
            [edge("a", "b"), edge("b", "a")],
            "WORKFLOW_CYCLE",
        ),
        ([node("a", "trigger.manual")], [edge("a", "a")], "WORKFLOW_CYCLE"),
        ([node("a", "trigger.manual"), node("b", "action.email")], [], "DISCONNECTED_NODES"),
    ],
)
def test_graph_validation(nodes, edges, code):
    assert code in {error["code"] for error in validate(nodes, edges)["errors"]}


@pytest.mark.parametrize(
    "node_type,labels,valid",
    [
        ("human.approval", ["approved", "rejected"], True),
        ("human.approval", [], True),
        ("human.approval", ["approved", "approved"], False),
        ("human.approval", ["maybe"], False),
        ("logic.condition", ["YES", "NO"], True),
        ("logic.condition", [], False),
        ("logic.condition", [None], False),
        ("logic.condition", [" YES"], False),
        ("logic.condition", ["YES", "YES"], False),
    ],
)
def test_branching_contract(node_type, labels, valid):
    nodes = [node("start", "trigger.manual"), node("branch", node_type)]
    edges = [edge("start", "branch")]
    for index, label in enumerate(labels):
        nodes.append(node(str(index), "action.email"))
        edges.append(edge("branch", str(index), label))
    result = validate(nodes, edges)
    assert result["valid"] is valid
    if not valid:
        assert result["errors"][0]["node_id"] == "branch"
        assert result["errors"][0]["code"] == "INVALID_BRANCHING"


def test_existing_published_workflow_is_not_mutated():
    configs = deepcopy(VALID_CONFIGS)
    configs["trigger.webhook"] = {}
    configs["ai.rag_search"]["knowledge_base"] = configs["ai.rag_search"].pop("knowledge_base_id")
    types = [
        "trigger.webhook",
        "action.http_request",
        "ai.rag_search",
        "ai.generate",
        "action.email",
        "human.approval",
        "action.refund",
    ]
    nodes = [
        node(str(index), node_type, configs[node_type]) for index, node_type in enumerate(types)
    ]
    edges = [
        edge(str(index), str(index + 1), "approved" if types[index] == "human.approval" else None)
        for index in range(len(types) - 1)
    ]
    before = deepcopy([vars(item) for item in nodes])
    assert validate(nodes, edges, status="published")["valid"]
    assert [vars(item) for item in nodes] == before


def test_kahn_algorithm_does_not_mutate_indegree():
    indegree = {"a": 0, "b": 1}
    errors = []
    validate_cycles({"a": [edge("a", "b")], "b": []}, indegree, errors)
    assert errors == []
    assert indegree == {"a": 0, "b": 1}


@pytest.mark.parametrize("node_type", VALID_CONFIGS)
def test_all_schema_required_fields_are_enforced(node_type):
    schema = NODE_VALIDATORS[node_type][0]
    for field, definition in schema.model_fields.items():
        if not definition.is_required():
            continue
        for value in (None, "", "   "):
            config = {**VALID_CONFIGS[node_type], field: value}
            result = validate_config(node_type, config)
            assert not result["valid"], (node_type, field, value)
            assert any(issue.get("field") == field for issue in result["errors"])


@pytest.mark.parametrize(
    "node_type,field,value",
    [
        ("action.email", "to", "not-an-email"),
        ("action.email", "to", "user@example.com\nBcc: other@example.com"),
        ("action.email", "subject", "Hello\r\nInjected"),
        ("action.email", "connection_id", "prefix {{trigger.data.connection}}"),
        ("action.http_request", "timeout", "{{trigger.data.timeout}} seconds"),
        ("ai.rag_search", "top_k", "top {{trigger.data.limit}}"),
        ("ai.decision", "allowed_decisions", "prefix {{trigger.data.decisions}}"),
        ("action.refund", "amount", "{{trigger.data.amount}} dollars"),
    ],
)
def test_invalid_literal_or_partial_typed_template(node_type, field, value):
    result = validate_config(node_type, {**VALID_CONFIGS[node_type], field: value})
    assert not result["valid"]
    assert any(issue.get("field") == field for issue in result["errors"])


@pytest.mark.parametrize(
    "config,field",
    [
        ({"schedule_type": "interval"}, "interval_minutes"),
        ({"schedule_type": "cron"}, "cron_expression"),
        ({"schedule_type": "cron", "cron_expression": "   "}, "cron_expression"),
        ({"schedule_type": "interval", "interval_minutes": 1, "timezone": ""}, "timezone"),
    ],
)
def test_conditional_schedule_requirements_identify_field(config, field):
    result = validate_config("trigger.schedule", config)
    assert not result["valid"]
    assert any(issue.get("field") == field for issue in result["errors"])


def test_publish_rejects_incomplete_email_and_preserves_current_version(integration_client):
    workflow = NS(id=WORKFLOW_ID, status="active", published_version_id=WORKFLOW_ID)
    draft = NS(id=VERSION_ID, version=2, status="draft")
    nodes = [node("start", "trigger.manual"), node("email", "action.email", {})]
    session = FakeSession(
        [
            Result(scalar=workflow),
            Result(scalar=draft),
            Result(scalar=workflow),
            Result(scalar=draft),
            Result(scalars=nodes),
            Result(scalars=[edge("start", "email")]),
        ]
    )
    with pytest.raises(service.WorkflowPublicationValidationError) as raised:
        asyncio.run(service.publish_workflow(WORKFLOW_ID, 2, WORKSPACE_ID, session))
    assert {issue["field"] for issue in raised.value.validation["errors"]} == {
        "connection_id",
        "to",
        "subject",
        "body",
    }
    assert session.commits == 0
    assert draft.status == "draft"
    assert workflow.published_version_id == WORKFLOW_ID
    integration_client.sync_workflow_schedule.assert_not_awaited()
