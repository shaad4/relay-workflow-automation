import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import delete, select

from app.ai.exceptions import AIDecisionValidationError
from app.db.database import AsyncSessionLocal
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep


async def run_case(should_fail: bool):
    workspace_id = uuid4()
    workflow_id = uuid4()
    version_id = uuid4()
    execution_id = uuid4()

    nodes = [
        {
            "node_id": "webhook_test",
            "node_type": "trigger.webhook",
            "configuration": {},
        },
        {
            "node_id": "ai_decision_test",
            "node_type": "ai.decision",
            "configuration": {
                "connection_id": str(uuid4()),
                "model": "test-model",
                "instructions": "Classify the request.",
                "input_mappings": {
                    "message": "{{trigger.data.message}}"
                },
                "allowed_decisions": [
                    "TECHNICAL",
                    "BILLING",
                ],
            },
        },
        {
            "node_id": "http_test",
            "node_type": "action.http_request",
            "configuration": {
                "connection_id": str(uuid4()),
                "url": "https://example.com",
                "method": "GET",
            },
        },
    ]

    edges = [
        {
            "source_node_id": "webhook_test",
            "target_node_id": "ai_decision_test",
        },
        {
            "source_node_id": "ai_decision_test",
            "target_node_id": "http_test",
        },
    ]

    definition = SimpleNamespace(
        nodes_json=json.dumps(nodes),
        edges_json=json.dumps(edges),
    )

    ai_result = {
        "decision": "TECHNICAL",
        "reason": "Software issue",
        "data": {"priority": "HIGH"},
        "model": "test-model",
        "input_tokens": 10,
        "output_tokens": 5,
    }

    async with AsyncSessionLocal() as session:
        session.add(
            Execution(
                id=execution_id,
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                status=ExecutionStatus.RUNNING,
                trigger_type="trigger.webhook",
                trigger_data={"message": "App crashes"},
                context={},
                started_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    try:
        with (
            patch(
                "app.engine.runner.WorkflowClient"
            ) as workflow_class,
            patch(
                "app.engine.runner.ActionClient"
            ) as action_class,
            patch(
                "app.engine.runner.execute_ai_decision",
                new_callable=AsyncMock,
            ) as ai_mock,
        ):
            workflow_client = workflow_class.return_value
            workflow_client.get_workflow_definition = AsyncMock(
                return_value=definition
            )
            workflow_client.close = AsyncMock()

            action_client = action_class.return_value
            action_client.execute_action = AsyncMock(
                return_value=SimpleNamespace(
                    success=True,
                    result_json='{"success":true}',
                    error="",
                )
            )
            action_client.close = AsyncMock()

            if should_fail:
                ai_mock.side_effect = AIDecisionValidationError(
                    "Invalid decision"
                )
            else:
                ai_mock.return_value = ai_result

            if should_fail:
                try:
                    await run_execution(
                        execution_id=execution_id,
                        workflow_id=str(workflow_id),
                        workflow_version_id=str(version_id),
                        workspace_id=str(workspace_id),
                        trigger_data={"message": "App crashes"},
                    )
                except AIDecisionValidationError:
                    pass
                else:
                    raise AssertionError(
                        "Expected AI validation failure"
                    )
            else:
                result = await run_execution(
                    execution_id=execution_id,
                    workflow_id=str(workflow_id),
                    workflow_version_id=str(version_id),
                    workspace_id=str(workspace_id),
                    trigger_data={"message": "App crashes"},
                )

                assert (
                    result["context"]["nodes"]
                    ["ai_decision_test"]["decision"]
                    == "TECHNICAL"
                )

            async with AsyncSessionLocal() as session:
                statement = (
                    select(ExecutionStep)
                    .where(
                        ExecutionStep.execution_id
                        == execution_id
                    )
                    .order_by(ExecutionStep.sequence)
                )

                steps = (
                    await session.execute(statement)
                ).scalars().all()

                ai_step = next(
                    step for step in steps
                    if step.node_id == "ai_decision_test"
                )

                if should_fail:
                    assert ai_step.status == "failed"
                    assert ai_step.error is not None

                    action_client.execute_action.assert_not_awaited()

                    assert not any(
                        step.node_id == "http_test"
                        for step in steps
                    )

                    print(
                        "Invalid AI decision blocked downstream action: PASSED"
                    )

                else:
                    assert ai_step.status == "completed"
                    assert ai_step.output["decision"] == "TECHNICAL"
                    assert ai_step.output["data"]["priority"] == "HIGH"

                    action_client.execute_action.assert_awaited_once()

                    print(
                        "AI Decision PostgreSQL persistence: PASSED"
                    )
                    print(
                        "Downstream action execution: PASSED"
                    )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ExecutionStep).where(
                    ExecutionStep.execution_id == execution_id
                )
            )
            await session.execute(
                delete(Execution).where(
                    Execution.id == execution_id
                )
            )
            await session.commit()


async def main():
    await run_case(should_fail=False)
    await run_case(should_fail=True)

    print("STEP 143/144 runner integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
