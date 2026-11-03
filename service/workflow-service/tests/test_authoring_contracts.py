"""Authoring discovery and publication must use the same live contracts."""

import asyncio
from types import SimpleNamespace as NS

import pytest
from app.dependencies import get_current_identity
from app.routes import workflows
from app.schemas.node_registry import NODE_VALIDATORS
from app.services import workflow_service
from app.services.node_catalog import get_node_catalog
from app.services.workflow_validation import validate_definition
from test_workflow_routes import client as client
from test_workflow_service import VERSION_ID, WORKFLOW_ID, WORKSPACE_ID, FakeSession, Result
from test_workflow_validation import VALID_CONFIGS, edge, node, validate


def generate_graph(prompt="Report on {{trigger.data.research_topic}}"):
    return [
        node("trigger_1", "trigger.manual"),
        node("generate_1", "ai.generate", {**VALID_CONFIGS["ai.generate"], "prompt": prompt}),
    ], [edge("trigger_1", "generate_1")]


def definition_body(nodes, edges, **kwargs):
    return {
        "nodes": [vars(item) for item in nodes],
        "edges": [vars(item) for item in edges],
        **kwargs,
    }


def test_catalog_covers_real_validators_and_valid_examples(client):
    result = client.get("/workflows/node-types/")
    assert result.status_code == 200
    catalog = result.json()
    assert {item["node_type"] for item in catalog["nodes"]} == set(NODE_VALIDATORS)
    for item in catalog["nodes"]:
        schema = NODE_VALIDATORS[item["node_type"]][0]
        assert item["configuration_schema"] == schema.model_json_schema()
        schema.model_validate(item["example_configuration"])
    ai = client.get("/workflows/node-types/?node_type=ai.generate").json()["nodes"]
    assert len(ai) == 1
    assert ai[0]["configuration_schema"]["required"] == ["connection_id", "model", "prompt"]
    assert set(ai[0]["output_schema"]["properties"]) == {
        "content",
        "model",
        "input_tokens",
        "output_tokens",
    }
    assert client.get("/workflows/node-types/?node_type=unknown").status_code == 404
    # Clients cannot mutate the server's catalog through returned objects.
    catalog = get_node_catalog("ai.generate")
    catalog["nodes"][0]["example_configuration"].clear()
    assert get_node_catalog("ai.generate")["nodes"][0]["example_configuration"]


def test_original_incident_is_rejected_before_saving_or_publication(client):
    nodes, edges = generate_graph("Report on {{trigger_1.research_topic}}")
    response = client.post("/workflows/validate-definition/", json=definition_body(nodes, edges))
    assert response.status_code == 200
    result = response.json()
    assert not result["valid"]
    issue = result["errors"][0]
    assert issue["code"] == "INVALID_EXPRESSION_REFERENCE"
    assert issue["node_id"] == "generate_1"
    assert issue["field"] == "prompt"
    assert issue["expression"] == "{{trigger_1.research_topic}}"
    assert "{{trigger.data.research_topic}}" in issue["suggestion"]
    assert validate(nodes, edges)["errors"][0] == issue

    draft = NS(id=VERSION_ID, status="draft", version=1)
    workflow = NS(id=WORKFLOW_ID)
    session = FakeSession(
        [
            Result(scalar=workflow),
            Result(scalar=draft),
            Result(scalar=workflow),
            Result(scalar=draft),
            Result(scalars=nodes),
            Result(scalars=edges),
        ]
    )
    with pytest.raises(ValueError, match="validation failed"):
        asyncio.run(workflow_service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))
    assert draft.status == "draft" and session.commits == 0


def test_correct_trigger_reference_and_optional_sample(client):
    nodes, edges = generate_graph()
    for extra in ({}, {"sample_input": {"research_topic": "How RAG works"}}):
        result = client.post(
            "/workflows/validate-definition/", json=definition_body(nodes, edges, **extra)
        ).json()
        assert result == {"valid": True, "errors": [], "warnings": []}
    result = client.post(
        "/workflows/validate-definition/", json=definition_body(nodes, edges, sample_input={})
    ).json()
    assert result["errors"][0]["code"] == "MISSING_SAMPLE_INPUT"
    assert result["errors"][0]["field"] == "prompt"
    result = client.post(
        "/workflows/validate-definition/",
        json=definition_body(nodes, edges, sample_input={"research_topic": None}),
    ).json()
    assert result["errors"][0]["code"] == "MISSING_SAMPLE_INPUT"


@pytest.mark.parametrize(
    "expression",
    [
        "{{trigger.research_topic}}",
        "{{nodes.missing.content}}",
        "{{nodes.trigger_1.data}}",
        "{{nodes.generate_1.content}}",
        "{{nodes}}",
    ],
)
def test_invalid_reference_roots_and_self_references(expression):
    nodes, edges = generate_graph(expression)
    assert validate_definition(nodes, edges)["errors"][0]["code"] == "INVALID_EXPRESSION_REFERENCE"


@pytest.mark.parametrize(
    "value",
    [
        "prefix {{missing",
        "{{}}",
        "{{trigger.data.a + 1}}",
        "{{trigger.data.get()}}",
        "{{trigger.data['a']}}",
        "{{secret prompt {{trigger.data.a}}",
    ],
)
def test_invalid_syntax_does_not_echo_entire_prompt(value):
    nodes, edges = generate_graph(value)
    issue = validate_definition(nodes, edges)["errors"][0]
    assert issue["code"] == "INVALID_EXPRESSION_SYNTAX" and issue["field"] == "prompt"
    assert "secret prompt" not in str(issue)


@pytest.mark.parametrize(
    "path,valid",
    [
        ("nodes.generate_1.content", True),
        ("nodes.generate_1.output.content", False),
        ("nodes.generate_1.content.foo", False),
        ("nodes.generate_1.missing", False),
    ],
)
def test_known_output_fields(path, valid):
    nodes, edges = generate_graph()
    nodes.append(
        node("email", "action.email", {**VALID_CONFIGS["action.email"], "body": "{{" + path + "}}"})
    )
    edges.append(edge("generate_1", "email"))
    assert validate_definition(nodes, edges)["valid"] is valid


@pytest.mark.parametrize(
    "path,valid",
    [
        ("nodes.search.chunks[0].content", True),
        ("nodes.search.chunks.0.score", True),
        ("nodes.search.chunks.content", False),
        ("nodes.search.chunks[0].missing", False),
    ],
)
def test_array_output_paths(path, valid):
    nodes = [
        node("t", "trigger.manual"),
        node("search", "ai.rag_search"),
        node(
            "generate",
            "ai.generate",
            {**VALID_CONFIGS["ai.generate"], "prompt": "{{" + path + "}}"},
        ),
    ]
    edges = [edge("t", "search"), edge("search", "generate")]
    assert validate_definition(nodes, edges)["valid"] is valid


def test_http_dynamic_body_and_legacy_root_aliases_are_supported():
    nodes = [
        node("t", "trigger.manual"),
        node("http", "action.http_request"),
        node(
            "generate",
            "ai.generate",
            {
                **VALID_CONFIGS["ai.generate"],
                "prompt": "{{nodes.http.custom_field}} {{nodes.http.body.items[0].name}}",
            },
        ),
    ]
    edges = [edge("t", "http"), edge("http", "generate")]
    assert validate_definition(nodes, edges)["valid"]


def test_branch_only_and_future_outputs_are_not_available_at_merge():
    nodes = [
        node("t", "trigger.manual"),
        node("branch", "logic.condition"),
        node("left", "ai.generate"),
        node("right", "ai.generate"),
        node(
            "merge",
            "action.email",
            {**VALID_CONFIGS["action.email"], "body": "{{nodes.left.content}}"},
        ),
    ]
    edges = [
        edge("t", "branch"),
        edge("branch", "left", "YES"),
        edge("branch", "right", "NO"),
        edge("left", "merge"),
        edge("right", "merge"),
    ]
    issue = validate_definition(nodes, edges)["errors"][0]
    assert issue["node_id"] == "merge" and "every incoming path" in issue["suggestion"]
    nodes[-1].configuration["body"] = "{{nodes.branch.selected_branch}}"
    assert validate_definition(nodes, edges)["valid"]
    nodes[2].configuration["prompt"] = "{{nodes.right.content}}"
    assert not validate_definition(nodes, edges)["valid"]


def test_nested_fields_report_paths_and_dynamic_values_remain_deferred():
    nodes = [
        node("t", "trigger.manual"),
        node(
            "decision",
            "ai.decision",
            {
                **VALID_CONFIGS["ai.decision"],
                "input_mappings": {"items": [{"value": "{{bad.amount}}"}]},
            },
        ),
    ]
    edges = [edge("t", "decision")]
    assert (
        validate_definition(nodes, edges)["errors"][0]["field"] == "input_mappings.items[0].value"
    )
    nodes[1].configuration["input_mappings"] = "{{trigger.data.items}}"
    assert validate_definition(nodes, edges)["valid"]


def test_discovery_and_preflight_require_authentication(client):
    client.app.dependency_overrides.pop(get_current_identity)
    assert client.get("/workflows/node-types/").status_code == 401
    assert (
        client.post("/workflows/validate-definition/", json={"nodes": [], "edges": []}).status_code
        == 401
    )


def test_saved_validation_response_keeps_structured_details(client, monkeypatch):
    async def invalid(**kwargs):
        nodes, edges = generate_graph("{{trigger_1.research_topic}}")
        return validate_definition(nodes, edges)

    monkeypatch.setattr(workflows, "validate_workflow", invalid)
    issue = client.post(f"/workflows/{WORKFLOW_ID}/versions/1/validate/").json()["errors"][0]
    assert issue["node_id"] == "generate_1" and issue["field"] == "prompt"
    assert issue["expression"] == "{{trigger_1.research_topic}}" and issue["suggestion"]
