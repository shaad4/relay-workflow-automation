"""PostgreSQL runner and approval route tests using the isolated ci_test database."""

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.database import DATABASE_URL, AsyncSessionLocal, engine
from app.engine.exceptions import HumanApprovalRequired
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from app.routes.approvals import approve, reject
from app.services import execution_queue
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url


def _assert_database_is_isolated():
    database = make_url(DATABASE_URL)
    assert database.database == "ci_test" and database.host in {"localhost", "127.0.0.1"}


async def run_automatic_case(decision):
    workspace_id, workflow_id, version_id, execution_id = (uuid4() for _ in range(4))
    nodes = [
        {"node_id": "webhook", "node_type": "trigger.webhook", "configuration": {}},
        {"node_id": "classify", "node_type": "ai.decision", "configuration": {}},
        {
            "node_id": "condition",
            "node_type": "logic.condition",
            "configuration": {"value": "{{nodes.classify.decision}}"},
        },
        {
            "node_id": "approve_email",
            "node_type": "action.email",
            "configuration": {"connection_id": "email", "to": "approved@example.test"},
        },
        {
            "node_id": "reject_email",
            "node_type": "action.email",
            "configuration": {"connection_id": "email", "to": "rejected@example.test"},
        },
    ]
    edges = [
        {"source_node_id": "webhook", "target_node_id": "classify"},
        {"source_node_id": "classify", "target_node_id": "condition"},
        {"source_node_id": "condition", "target_node_id": "approve_email", "condition": "APPROVE"},
        {"source_node_id": "condition", "target_node_id": "reject_email", "condition": "REJECT"},
    ]
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
                trigger_data={},
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
            workflow_class.return_value.get_workflow_definition = AsyncMock(return_value=definition)
            workflow_class.return_value.close = AsyncMock()
            action_class.return_value.execute_action = AsyncMock(
                return_value=SimpleNamespace(
                    success=True,
                    result_json='{"sent": true}',
                    error="",
                )
            )
            action_class.return_value.close = AsyncMock()
            ai_mock.return_value = {
                "decision": decision,
                "reason": "mock",
                "data": {},
                "model": "test",
                "input_tokens": 1,
                "output_tokens": 1,
            }
            result = await run_execution(
                execution_id, str(workflow_id), str(version_id), str(workspace_id)
            )
            async with AsyncSessionLocal() as session:
                steps = (
                    (
                        await session.execute(
                            select(ExecutionStep).where(
                                ExecutionStep.execution_id == execution_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            expected = "approve_email" if decision == "APPROVE" else "reject_email"
            assert result["context"]["nodes"]["condition"]["selected_branch"] == decision
            assert {step.node_id for step in steps} == {
                "webhook",
                "classify",
                "condition",
                expected,
            }
            assert action_class.return_value.execute_action.await_count == 1
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ExecutionStep).where(ExecutionStep.execution_id == execution_id)
            )
            await session.execute(delete(Execution).where(Execution.id == execution_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.parametrize("decision", ["APPROVE", "REJECT"])
def test_automatic_decision_branches_in_database(decision):
    _assert_database_is_isolated()
    asyncio.run(run_automatic_case(decision))


async def run_review_case(decision, generate_fails=False):
    workspace_id, workflow_id, version_id, execution_id, approver_id = (uuid4() for _ in range(5))
    next_node = "generate" if generate_fails and decision == "approved" else f"{decision}_email"
    nodes = [
        {"node_id": "webhook", "node_type": "trigger.webhook", "configuration": {}},
        {
            "node_id": "refund",
            "node_type": "action.refund",
            "configuration": {"connection_id": "stripe", "payment_id": "pi_test", "amount": 5},
        },
        {
            "node_id": "review",
            "node_type": "human.approval",
            "configuration": {"approver_user_id": str(approver_id), "message": "Review refund"},
        },
        {
            "node_id": "approved_email",
            "node_type": "action.email",
            "configuration": {"connection_id": "gmail", "body": "{{nodes.refund.status}}"},
        },
        {
            "node_id": "rejected_email",
            "node_type": "action.email",
            "configuration": {"connection_id": "gmail", "body": "{{nodes.refund.status}}"},
        },
        {"node_id": "generate", "node_type": "ai.generate", "configuration": {}},
    ]
    edges = [
        {"source_node_id": "webhook", "target_node_id": "refund"},
        {"source_node_id": "refund", "target_node_id": "review"},
        {
            "source_node_id": "review",
            "target_node_id": "generate" if generate_fails else "approved_email",
            "condition": "approved",
        },
        {"source_node_id": "review", "target_node_id": "rejected_email", "condition": "rejected"},
        *(
            [{"source_node_id": "generate", "target_node_id": "approved_email"}]
            if generate_fails
            else []
        ),
    ]
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
                trigger_data={},
                context={},
                started_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
    try:
        with (
            patch("app.engine.runner.WorkflowClient") as workflow_class,
            patch("app.engine.runner.ActionClient") as action_class,
            patch(
                "app.services.approval_service.resolve_approval_branch", new_callable=AsyncMock
            ) as branch_mock,
            patch("app.engine.runner.execute_ai_generate", new_callable=AsyncMock) as generate_mock,
        ):
            workflow_class.return_value.get_workflow_definition = AsyncMock(return_value=definition)
            workflow_class.return_value.close = AsyncMock()

            async def action(**kwargs):
                if kwargs["action"] == "refund_payment":
                    return SimpleNamespace(
                        success=True,
                        result_json='{"status":"succeeded","refund_id":"re_test"}',
                        error="",
                    )
                return SimpleNamespace(success=True, result_json='{"sent":true}', error="")

            action_class.return_value.execute_action = AsyncMock(side_effect=action)
            action_class.return_value.close = AsyncMock()
            branch_mock.return_value = next_node
            if generate_fails:
                generate_mock.side_effect = RuntimeError("private provider failure")
            with pytest.raises(HumanApprovalRequired):
                await run_execution(
                    execution_id, str(workflow_id), str(version_id), str(workspace_id)
                )
            async with AsyncSessionLocal() as session:
                execution = await session.get(Execution, execution_id)
                execution.status = ExecutionStatus.WAITING_FOR_APPROVAL
                await session.commit()
                approval = (
                    await session.execute(
                        select(HumanApproval).where(
                            HumanApproval.execution_id == execution_id,
                        )
                    )
                ).scalar_one()
                identity = {"workspace_id": str(workspace_id), "user_id": str(approver_id)}
                response = await (approve if decision == "approved" else reject)(
                    approval.id, identity, session
                )
                assert response.decision == decision
                await session.refresh(execution)
                assert execution.status == ExecutionStatus.PENDING
                context = (
                    json.loads(execution.context)
                    if isinstance(execution.context, str)
                    else execution.context
                )
                assert context["nodes"]["refund"]["status"] == "succeeded"
                await session.commit()

                with patch.object(
                    execution_queue, "publish_execution_lifecycle", new_callable=AsyncMock
                ):
                    assert await execution_queue.execute_pending_execution(execution_id)
                await session.refresh(approval)
                await session.refresh(execution)
                steps = (
                    (
                        await session.execute(
                            select(ExecutionStep).where(
                                ExecutionStep.execution_id == execution_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert approval.decision == decision
                assert execution.status == (
                    ExecutionStatus.FAILED if generate_fails else ExecutionStatus.COMPLETED
                )
                context = (
                    json.loads(execution.context)
                    if isinstance(execution.context, str)
                    else execution.context
                )
                assert context["nodes"]["refund"]["status"] == "succeeded"
                assert {step.node_id for step in steps} == {
                    "webhook",
                    "refund",
                    "review",
                    next_node,
                }
                with pytest.raises(HTTPException) as duplicate:
                    await (approve if decision == "approved" else reject)(
                        approval.id, identity, session
                    )
                assert duplicate.value.status_code == 409
                if generate_fails:
                    assert generate_mock.await_count == 1
                    assert action_class.return_value.execute_action.await_count == 1
                else:
                    assert action_class.return_value.execute_action.await_count == 2
                    assert (
                        json.loads(
                            action_class.return_value.execute_action.await_args.kwargs[
                                "input_data_json"
                            ]
                        )["body"]
                        == "succeeded"
                    )
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(DeadLetterEvent).where(DeadLetterEvent.execution_id == execution_id)
            )
            await session.execute(
                delete(HumanApproval).where(HumanApproval.execution_id == execution_id)
            )
            await session.execute(
                delete(ExecutionStep).where(ExecutionStep.execution_id == execution_id)
            )
            await session.execute(delete(Execution).where(Execution.id == execution_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.parametrize(
    "decision,generate_fails",
    [
        ("approved", False),
        ("rejected", False),
        ("approved", True),
    ],
)
def test_human_review_resume_keeps_refund_output(decision, generate_fails):
    _assert_database_is_isolated()
    asyncio.run(run_review_case(decision, generate_fails))
