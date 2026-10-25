"""Database-backed tests for Condition branch selection in the real runner.

Run against the isolated local ci_test database. Every test uses unique execution records
and removes them, including approval rows, in a finally block.
"""

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.database import DATABASE_URL, AsyncSessionLocal, engine
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.engine.step_status import ExecutionStepStatus
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

DECISIONS = ("TECHNICAL", "BILLING", "GENERAL")


def workflow(decision=..., duplicate=False):
    nodes = [
        {"node_id": "webhook", "node_type": "trigger.webhook", "configuration": {}},
        {
            "node_id": "ai_decision",
            "node_type": "ai.decision",
            "configuration": {
                "connection_id": str(uuid4()),
                "model": "test-model",
                "instructions": "Classify the request.",
                "input_mappings": {"message": "{{trigger.data.message}}"},
                "allowed_decisions": list(DECISIONS),
            },
        },
        {
            "node_id": "condition",
            "node_type": "logic.condition",
            "configuration": {"value": "{{nodes.ai_decision.decision}}"},
        },
    ]
    for value in DECISIONS:
        nodes.append(
            {
                "node_id": f"email_{value.lower()}",
                "node_type": "action.email",
                "configuration": {
                    "connection_id": f"mock-{value.lower()}",
                    "to": f"{value.lower()}@example.test",
                    "subject": "Mocked branch test",
                },
            }
        )

    edges = [
        {"source_node_id": "webhook", "target_node_id": "ai_decision"},
        {"source_node_id": "ai_decision", "target_node_id": "condition"},
        *[
            {
                "source_node_id": "condition",
                "target_node_id": f"email_{value.lower()}",
                "condition": value,
            }
            for value in DECISIONS
        ],
    ]
    if duplicate:
        edges.append(
            {
                "source_node_id": "condition",
                "target_node_id": "email_technical",
                "condition": "TECHNICAL",
            }
        )
    return nodes, edges


async def run_database_case(decision=..., duplicate=False):
    database = make_url(DATABASE_URL)
    if database.database != "ci_test" or database.host not in {"localhost", "127.0.0.1"}:
        pytest.fail("Database integration tests require the isolated local ci_test database")

    workspace_id, workflow_id, version_id, execution_id = (uuid4() for _ in range(4))
    nodes, edges = workflow(decision, duplicate)
    definition = SimpleNamespace(
        workflow_name="Test workflow", nodes_json=json.dumps(nodes), edges_json=json.dumps(edges)
    )

    async with AsyncSessionLocal() as session:
        session.add(
            Execution(
                id=execution_id,
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                status=ExecutionStatus.RUNNING,
                trigger_type="trigger.webhook",
                trigger_data={"message": "Example request"},
                context={},
                started_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    try:
        with (
            patch("app.engine.runner.WorkflowClient") as workflow_class,
            patch("app.engine.runner.ActionClient") as action_class,
            patch("app.engine.runner.execute_ai_decision", new_callable=AsyncMock) as ai_mock,
        ):
            workflow_client = workflow_class.return_value
            workflow_client.get_workflow_definition = AsyncMock(return_value=definition)
            workflow_client.close = AsyncMock()

            action_client = action_class.return_value
            action_client.execute_action = AsyncMock(
                return_value=SimpleNamespace(
                    success=True,
                    result_json='{"sent": true}',
                    error="",
                )
            )
            action_client.close = AsyncMock()

            if decision is ...:
                ai_mock.return_value = {
                    "decision": "TECHNICAL",
                    "reason": "Software issue",
                    "data": {},
                    "model": "test-model",
                    "input_tokens": 2,
                    "output_tokens": 1,
                }
            elif decision is None:
                ai_mock.return_value = {"reason": "No decision returned"}
            else:
                ai_mock.return_value = {
                    "decision": decision,
                    "reason": "Mocked result",
                    "data": {},
                    "model": "test-model",
                    "input_tokens": 2,
                    "output_tokens": 1,
                }

            error = None
            result = None
            try:
                result = await run_execution(
                    execution_id=execution_id,
                    workflow_id=str(workflow_id),
                    workflow_version_id=str(version_id),
                    workspace_id=str(workspace_id),
                    trigger_data={"message": "Example request"},
                )
            except ValueError as exc:
                error = exc

            async with AsyncSessionLocal() as session:
                steps = (
                    (
                        await session.execute(
                            select(ExecutionStep)
                            .where(ExecutionStep.execution_id == execution_id)
                            .order_by(ExecutionStep.sequence)
                        )
                    )
                    .scalars()
                    .all()
                )
                persisted = {step.node_id: step for step in steps}

            action_calls = action_client.execute_action.await_args_list
            return result, error, persisted, action_calls
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(HumanApproval).where(HumanApproval.execution_id == execution_id)
            )
            await session.execute(
                delete(ExecutionStep).where(ExecutionStep.execution_id == execution_id)
            )
            await session.execute(delete(Execution).where(Execution.id == execution_id))
            await session.commit()
        # The test functions use asyncio.run independently; don't carry asyncpg
        # pooled connections across event loops.
        await engine.dispose()


@pytest.mark.parametrize("decision", DECISIONS)
def test_runner_executes_only_the_matching_email_and_persists_condition(decision):
    result, error, steps, calls = asyncio.run(run_database_case(decision))
    expected_node = f"email_{decision.lower()}"
    assert error is None
    assert result["context"]["nodes"]["condition"] == {
        "value": decision,
        "selected_branch": decision,
        "next_node_id": expected_node,
    }
    assert steps["condition"].status == ExecutionStepStatus.COMPLETED
    assert json.loads(steps["condition"].output) == result["context"]["nodes"]["condition"]
    assert steps[expected_node].status == ExecutionStepStatus.COMPLETED
    assert not (set(steps) & {f"email_{other.lower()}" for other in DECISIONS if other != decision})
    assert len(calls) == 1
    assert calls[0].kwargs["connection_id"] == f"mock-{decision.lower()}"
    assert (
        json.loads(calls[0].kwargs["input_data_json"])["to"] == f"{decision.lower()}@example.test"
    )


@pytest.mark.parametrize("decision", ["UNKNOWN", None])
def test_runner_fails_safely_without_email_for_unknown_or_missing_decision(decision):
    result, error, steps, calls = asyncio.run(run_database_case(decision))
    assert result is None and error is not None
    assert calls == []
    assert steps["condition"].status == ExecutionStepStatus.FAILED
    assert steps["condition"].error
    assert not any(node_id.startswith("email_") for node_id in steps)


def test_runner_rejects_duplicate_matching_edges_without_email():
    result, error, steps, calls = asyncio.run(run_database_case(duplicate=True))
    assert result is None and isinstance(error, ValueError)
    assert "found 2" in str(error)
    assert calls == []
    assert steps["condition"].status == ExecutionStepStatus.FAILED
    assert not any(node_id.startswith("email_") for node_id in steps)


def test_human_approval_edges_still_resolve_approved_and_rejected(monkeypatch):
    from app.services import approval_branch_service

    definition = SimpleNamespace(
        workflow_name="Test workflow",
        nodes_json=json.dumps(
            [
                {"node_id": "approval", "node_type": "human.approval"},
                {"node_id": "approved", "node_type": "action.email"},
                {"node_id": "rejected", "node_type": "action.email"},
            ]
        ),
        edges_json=json.dumps(
            [
                {
                    "source_node_id": "approval",
                    "target_node_id": "approved",
                    "condition": "approved",
                },
                {
                    "source_node_id": "approval",
                    "target_node_id": "rejected",
                    "condition": "rejected",
                },
            ]
        ),
    )

    class WorkflowClient:
        async def get_workflow_definition(self, **_kwargs):
            return definition

        async def close(self):
            pass

    monkeypatch.setattr(approval_branch_service, "WorkflowClient", WorkflowClient)
    assert (
        asyncio.run(
            approval_branch_service.resolve_approval_branch("w", "v", "x", "approval", "approved")
        )
        == "approved"
    )
    assert (
        asyncio.run(
            approval_branch_service.resolve_approval_branch("w", "v", "x", "approval", "rejected")
        )
        == "rejected"
    )
