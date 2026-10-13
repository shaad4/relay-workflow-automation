import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.schemas.node_configuration import RagSearchConfig
from app.services import workflow_service as service
from test_workflow_service import FakeSession, Result, WORKFLOW_ID, WORKSPACE_ID, VERSION_ID

KB = str(uuid4())
VALID = {"knowledge_base_id": KB, "query": "{{trigger.data.question}}", "top_k": 5}

@pytest.mark.parametrize("value", [1, 5, 20])
def test_top_k_valid(value):
    assert RagSearchConfig.model_validate({**VALID, "top_k": value}).top_k == value

@pytest.mark.parametrize("patch", [
    {"top_k": value} for value in [0, 21, 1.5, "5", True, None]
] + [{"query": value} for value in ["", " \n", "x" * 2001, None, 4]] + [
    {"knowledge_base_id": "bad"}, {"unexpected": 1},
    {"knowledge_base": "different"},
    {"knowledge_base_id": "", "knowledge_base": KB},
    {"knowledge_base_id": None, "knowledge_base": KB},
    {"knowledge_base": None},
])
def test_invalid_config(patch):
    with pytest.raises(ValidationError):
        RagSearchConfig.model_validate({**VALID, **patch})

def test_legacy_matching_and_input_immutability():
    legacy = {"knowledge_base": KB, "query": "Question"}
    before = dict(legacy)
    value = RagSearchConfig.model_validate(legacy)
    assert str(value.knowledge_base_id) == KB and value.top_k == 5
    assert legacy == before
    assert RagSearchConfig.model_validate({**VALID, "knowledge_base": KB}).knowledge_base_id == value.knowledge_base_id

def node(id, type, config=None):
    return NS(node_id=id, node_type=type, configuration=config or {})

def edge(source, target, condition=None):
    return NS(source_node_id=source, target_node_id=target, condition=condition)

def validate(nodes, edges):
    session = FakeSession([Result(scalar=NS(id=WORKFLOW_ID)), Result(scalar=NS(id=VERSION_ID)), Result(scalars=nodes), Result(scalars=edges)])
    return asyncio.run(service.validate_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))

@pytest.mark.parametrize("type", ["ai.rag_search", "action.http_request", "action.email", "action.refund"])
def test_supported_paths(type):
    assert validate([node("t", "trigger.webhook"), node("a", type, VALID if type == "ai.rag_search" else {})], [edge("t", "a")])["valid"]

@pytest.mark.parametrize("nodes,edges,code", [
    ([node("x", "ai.generate")], [], "UNSUPPORTED_NODE_TYPE"),
    ([node("x", "ai.decision")], [], "UNSUPPORTED_NODE_TYPE"),
    ([node("x", "logic.condition")], [], "UNSUPPORTED_NODE_TYPE"),
    ([node("x", "action.email")], [], "INVALID_TRIGGER"),
    ([node("t", "trigger.webhook")], [edge("t", "missing")], "INVALID_EDGE_TARGET"),
    ([node("t", "trigger.webhook"), node("a", "ai.rag_search", VALID)], [edge("t", "a"), edge("a", "t")], "WORKFLOW_CYCLE"),
    ([node("t", "trigger.webhook"), node("a", "action.email")], [], "DISCONNECTED_NODES"),
    ([node("t", "trigger.webhook"), node("a", "action.email"), node("b", "action.refund")], [edge("t", "a"), edge("t", "b")], "INVALID_BRANCHING"),
    ([node("t", "trigger.webhook"), node("r", "ai.rag_search", {**VALID, "top_k": 0})], [edge("t", "r")], "INVALID_RAG_CONFIGURATION"),
])
def test_publish_validation_errors(nodes, edges, code):
    assert code in {error["code"] for error in validate(nodes, edges)["errors"]}

def test_approval_branching_preserved_and_ambiguous_branch_rejected():
    nodes = [node("t", "trigger.webhook"), node("h", "human.approval"), node("a", "action.email"), node("r", "ai.rag_search", VALID)]
    edges = [edge("t", "h"), edge("h", "a", "approved"), edge("h", "r", "rejected")]
    assert validate(nodes, edges)["valid"]
    edges[-1].condition = "approved"
    assert "INVALID_BRANCHING" in {error["code"] for error in validate(nodes, edges)["errors"]}

@pytest.mark.parametrize("valid", [True, False])
def test_publish_gates_actual_rag_configuration(valid):
    workflow = NS(id=WORKFLOW_ID, status="inactive", published_version_id=None)
    version = NS(id=VERSION_ID, version=1, status="draft")
    nodes = [node("t", "trigger.webhook"), node("r", "ai.rag_search", {**VALID, "top_k": 5 if valid else 0})]
    session = FakeSession([Result(scalar=workflow), Result(scalar=version), Result(scalar=workflow), Result(scalar=version), Result(scalars=nodes), Result(scalars=[edge("t", "r")])])
    if valid:
        assert asyncio.run(service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))["status"] == "published"
    else:
        with pytest.raises(ValueError, match="validation failed"):
            asyncio.run(service.publish_workflow(WORKFLOW_ID, 1, WORKSPACE_ID, session))
        assert session.commits == 0 and version.status == "draft"
