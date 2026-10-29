"""Resolved data may contain closing braces without being a workflow expression."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.ai.input_validation import validate_resolved_ai_inputs
from app.engine.handlers import rag_search
from app.engine.handlers.condition import evaluate_condition

KB = "a4fc6a99-ef5c-406e-92ec-7d7e48197dbb"


@pytest.mark.parametrize("value", ['{"student": {"score": 90}}', "literal }}", "normal text"])
def test_resolved_content_is_accepted(monkeypatch, value):
    validate_resolved_ai_inputs({"students": [{"report": value}]}, value)
    assert evaluate_condition({"value": f"  {value}  "}) == value

    client = SimpleNamespace(
        retrieve=AsyncMock(return_value=SimpleNamespace(chunks=[])), close=AsyncMock()
    )
    monkeypatch.setattr(rag_search, "RagClient", lambda: client)
    result = asyncio.run(
        rag_search.execute_rag_search({"knowledge_base_id": KB, "query": value}, "workspace")
    )
    assert result == {"chunks": [], "context": ""}
    client.retrieve.assert_awaited_once_with(
        workspace_id="workspace", knowledge_base_id=KB, query=value, top_k=5
    )
    client.close.assert_awaited_once()


@pytest.mark.parametrize("value", ["{{nodes.http.body}}", "prefix {{missing", "{{", "{{broken}"])
def test_opening_markers_are_rejected_before_retrieval(monkeypatch, value):
    with pytest.raises(ValueError, match=r"Unresolved AI expression: students\[0\].report"):
        validate_resolved_ai_inputs({"students": [{"report": value}]}, "")
    with pytest.raises(ValueError, match="Unresolved RAG context expression"):
        validate_resolved_ai_inputs({}, value)
    with pytest.raises(ValueError, match="Condition contains unresolved expression"):
        evaluate_condition({"value": value})

    factory = Mock(side_effect=AssertionError("Retrieval must not be reached"))
    monkeypatch.setattr(rag_search, "RagClient", factory)
    with pytest.raises(ValueError, match="RAG query contains unresolved expressions"):
        asyncio.run(
            rag_search.execute_rag_search({"knowledge_base_id": KB, "query": value}, "workspace")
        )
    factory.assert_not_called()


@pytest.mark.parametrize(
    "mappings,context,message",
    [
        ([], "", "AI input mappings must be an object"),
        ({}, None, "RAG context must be a string"),
        ({"students": [{"score": None}]}, "", r"Missing AI input: students\[0\].score"),
    ],
)
def test_existing_ai_input_errors_are_preserved(mappings, context, message):
    with pytest.raises(ValueError, match=message):
        validate_resolved_ai_inputs(mappings, context)


@pytest.mark.parametrize(
    "value,message",
    [
        (None, "Condition value is missing"),
        ("  ", "Condition value cannot be empty"),
        ({}, "Condition value must be a string, number, or boolean"),
    ],
)
def test_existing_condition_errors_are_preserved(value, message):
    with pytest.raises(ValueError, match=message):
        evaluate_condition({"value": value})


@pytest.mark.parametrize(
    "value,message",
    [
        (None, "RAG query must be a string"),
        ("  ", "RAG query cannot be empty"),
        ("x" * 2001, "RAG query cannot exceed 2000 characters"),
    ],
)
def test_existing_rag_errors_are_preserved(monkeypatch, value, message):
    factory = Mock(side_effect=AssertionError("Retrieval must not be reached"))
    monkeypatch.setattr(rag_search, "RagClient", factory)
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            rag_search.execute_rag_search({"knowledge_base_id": KB, "query": value}, "workspace")
        )
    factory.assert_not_called()
