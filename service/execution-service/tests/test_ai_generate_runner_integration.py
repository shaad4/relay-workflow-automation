"""Database-backed AI Generate runner tests. Opt in with RUN_AI_GENERATE_DB_TESTS=1."""

import asyncio
import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from app.ai.base import AIResponse
from app.ai.exceptions import AIAuthenticationError, AIResponseError, AITimeoutError, AIServiceUnavailableError
from app.db.database import AsyncSessionLocal, DATABASE_URL, engine
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.engine.step_status import ExecutionStepStatus
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_AI_GENERATE_DB_TESTS") != "1",
    reason="requires explicit opt-in to the execution development database",
)
API_KEY = "secret-test-key-never-persist"


async def run_case(prompt="{{trigger.data.message}}", rag_context="", response=None, provider_error=None):
    database = make_url(DATABASE_URL)
    if database.database != "relay_execution" or database.host not in {"execution-postgres", "localhost", "127.0.0.1"}:
        pytest.fail("Refusing to run against a non-development execution database")

    workspace_id, workflow_id, version_id, execution_id, connection_id = (uuid4() for _ in range(5))
    nodes = [
        {"node_id": "webhook", "node_type": "trigger.webhook", "configuration": {}},
        {"node_id": "generate_1", "node_type": "ai.generate", "configuration": {
            "connection_id": str(connection_id), "model": "test-model", "instructions": "Summarize",
            "prompt": prompt, "rag_context": rag_context,
        }},
        {"node_id": "gmail", "node_type": "action.email", "configuration": {
            "connection_id": "mock-gmail", "to": "test@example.test", "subject": "Result",
            "body": "{{nodes.generate_1.content}}",
        }},
    ]
    edges = [
        {"source_node_id": "webhook", "target_node_id": "generate_1"},
        {"source_node_id": "generate_1", "target_node_id": "gmail"},
    ]
    definition = SimpleNamespace(nodes_json=json.dumps(nodes), edges_json=json.dumps(edges))
    async with AsyncSessionLocal() as session:
        session.add(Execution(
            id=execution_id, workspace_id=workspace_id, workflow_id=workflow_id,
            workflow_version_id=version_id, status=ExecutionStatus.RUNNING,
            trigger_type="trigger.webhook", trigger_data={"message": "Write a summary"},
            context={}, started_at=datetime.now(timezone.utc),
        ))
        await session.commit()

    try:
        with (
            patch("app.engine.runner.WorkflowClient") as workflow_class,
            patch("app.engine.runner.ActionClient") as action_class,
            patch("app.engine.handlers.ai_generate.AIProviderConnectionService") as credentials_class,
            patch("app.engine.handlers.ai_generate.AIService") as ai_class,
        ):
            workflow_class.return_value.get_workflow_definition = AsyncMock(return_value=definition)
            workflow_class.return_value.close = AsyncMock()
            action = action_class.return_value
            action.execute_action = AsyncMock(return_value=SimpleNamespace(success=True, result_json='{"sent":true}', error=""))
            action.close = AsyncMock()
            credentials = credentials_class.return_value.get_execution_credentials = AsyncMock(return_value=("openai", API_KEY))
            provider = ai_class.return_value.generate = AsyncMock(
                return_value=response if response is not None else AIResponse("Validated summary", "test-model", 5, 2),
                side_effect=provider_error,
            )
            result = error = None
            try:
                result = await run_execution(
                    execution_id, str(workflow_id), str(version_id), str(workspace_id),
                    trigger_data={"message": "Write a summary"},
                )
            except Exception as exc:
                error = exc

            async with AsyncSessionLocal() as session:
                steps = (await session.execute(select(ExecutionStep).where(
                    ExecutionStep.execution_id == execution_id,
                ).order_by(ExecutionStep.sequence))).scalars().all()
                saved_execution = await session.get(Execution, execution_id)
                persisted_context = saved_execution.context

            return result, error, {step.node_id: step for step in steps}, action.execute_action.await_args_list, credentials.await_args_list, provider.await_args_list, persisted_context, workspace_id, connection_id
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ExecutionStep).where(ExecutionStep.execution_id == execution_id))
            await session.execute(delete(Execution).where(Execution.id == execution_id))
            await session.commit()
        await engine.dispose()


def test_success_context_persistence_gmail_and_workspace_scope():
    result, error, steps, calls, credential_calls, provider_calls, _, workspace_id, connection_id = asyncio.run(run_case())
    assert error is None
    assert result["context"]["nodes"]["generate_1"] == {
        "content": "Validated summary", "model": "test-model", "input_tokens": 5, "output_tokens": 2,
    }
    assert steps["generate_1"].status == ExecutionStepStatus.COMPLETED
    assert steps["generate_1"].output == result["context"]["nodes"]["generate_1"]
    assert len(calls) == 1
    assert calls[0].kwargs["provider"] == "gmail"
    assert json.loads(calls[0].kwargs["input_data_json"])["body"] == "Validated summary"
    assert credential_calls[0].kwargs == {"connection_id": connection_id, "workspace_id": workspace_id}
    assert provider_calls[0].kwargs["api_key"] == API_KEY
    assert API_KEY not in json.dumps(result) + json.dumps(steps["generate_1"].output)


@pytest.mark.parametrize("prompt,rag_context", [
    ("{{trigger.data.missing}}", ""),
    ("", ""),
    ("{{trigger.data.message}}", "{{nodes.missing.context}}"),
])
def test_invalid_inputs_fail_before_provider_and_gmail(prompt, rag_context):
    result, error, steps, calls, credential_calls, provider_calls, context, *_ = asyncio.run(run_case(prompt, rag_context))
    assert result is None and error is not None
    assert steps["generate_1"].status == ExecutionStepStatus.FAILED
    assert "gmail" not in steps and not calls and not credential_calls and not provider_calls
    assert "generate_1" not in context.get("nodes", {})


def test_optional_empty_rag_context_succeeds():
    result, error, steps, calls, _, provider_calls, _, *_ = asyncio.run(run_case(rag_context=""))
    assert error is None and steps["generate_1"].status == ExecutionStepStatus.COMPLETED
    assert len(calls) == 1 and len(provider_calls) == 1
    assert provider_calls[0].kwargs["prompt"] == "Write a summary"


@pytest.mark.parametrize("provider_error,expected", [
    (AITimeoutError("AI provider request timed out"), "AI provider request timed out"),
    (AIAuthenticationError(f"provider rejected {API_KEY}"), "AI provider authentication failed"),
    (RuntimeError(f"raw provider failure {API_KEY}"), "AI provider unavailable"),
])
def test_provider_failures_stop_gmail_without_persisting_secrets(provider_error, expected):
    result, error, steps, calls, _, _, context, *_ = asyncio.run(run_case(provider_error=provider_error))
    assert result is None and error is not None
    assert expected in str(error)
    assert API_KEY not in str(error)
    assert steps["generate_1"].status == ExecutionStepStatus.FAILED
    assert steps["generate_1"].error["message"] == expected
    assert "gmail" not in steps and not calls
    assert "generate_1" not in context.get("nodes", {})
    assert API_KEY not in json.dumps(context) + json.dumps(steps["generate_1"].error)


@pytest.mark.parametrize("invalid_response", [
    AIResponse("", "test-model", 0, 0),
    AIResponse("text", "test-model", -1, 0),
    AIResponse(API_KEY, "test-model", 1, 1),
    SimpleNamespace(content=API_KEY),
])
def test_invalid_response_is_not_available_downstream(invalid_response):
    result, error, steps, calls, _, _, context, *_ = asyncio.run(run_case(response=invalid_response))
    assert result is None and isinstance(error, AIResponseError)
    assert steps["generate_1"].status == ExecutionStepStatus.FAILED
    assert steps["generate_1"].error["message"] == "AI provider returned an invalid response"
    assert steps["generate_1"].output is None
    assert "gmail" not in steps and not calls
    assert "generate_1" not in context.get("nodes", {})
    assert API_KEY not in json.dumps(context) + json.dumps(steps["generate_1"].error)
