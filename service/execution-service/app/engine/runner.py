import json
from datetime import datetime, timedelta, timezone
from uuid import UUID


from app.db.database import AsyncSessionLocal
from app.engine.context import ExecutionContext
from app.engine.executor import SequentialExecutor
from app.engine.exceptions import HumanApprovalRequired, ActionExecutionFailed
from app.engine.graph import ExecutionGraph
from app.engine.resolver import ExpressionResolver
from app.engine.step_status import ExecutionStepStatus
from app.grpc.action_client import ActionClient
from app.grpc.workflow_client import WorkflowClient
from app.models.execution_step import ExecutionStep
from app.engine.approval_status import HumanApprovalStatus
from app.models.human_approval import HumanApproval
from app.models.execution import Execution

async def run_execution(
    execution_id,
    workflow_id: str,
    workflow_version_id: str,
    workspace_id: str,
    trigger_data: dict | None = None,
    resume_from_sequence: int | None = None,
    context_data: dict | None = None,
):
    workflow_client = WorkflowClient()
    action_client = ActionClient()

    try:
        response = await workflow_client.get_workflow_definition(
            workflow_id=workflow_id,
            version_id=workflow_version_id,
            workspace_id=workspace_id,
        )

        nodes = json.loads(response.nodes_json)
        edges = json.loads(response.edges_json)

        graph = ExecutionGraph(
            nodes=nodes,
            edges=edges,
        )

        if context_data is not None:
            context = ExecutionContext.from_dict(context_data)
        else:
            context = ExecutionContext(
                trigger_data=trigger_data,
            )
        resolver = ExpressionResolver(context)

        executor = SequentialExecutor(graph)

        execution_order = executor.get_execution_order()
        action_nodes = executor.get_action_nodes()

        print(
            "Action node definitions:",
            json.dumps(action_nodes, indent=2),
            flush=True,
        )

        print(
            "Workflow execution order:",
            [node["node_id"] for node in execution_order],
            flush=True,
        )

        print(
            "Action nodes:",
            [node["node_id"] for node in action_nodes],
            flush=True,
        )

        for sequence, node in enumerate(execution_order, start=1):
            if resume_from_sequence is not None and sequence <= resume_from_sequence:
                continue

            configuration = node.get("configuration", {})

            # Create execution step
            async with AsyncSessionLocal() as session:
                execution_step = ExecutionStep(
                    execution_id=execution_id,
                    node_id=node["node_id"],
                    status=ExecutionStepStatus.PENDING,
                    sequence=sequence,
                )

                session.add(execution_step)
                await session.commit()
                await session.refresh(execution_step)

            execution_step_id = execution_step.id

            # Mark step as running
            async with AsyncSessionLocal() as session:
                execution_step = await session.get(
                    ExecutionStep,
                    execution_step_id,
                )

                execution_step.status = ExecutionStepStatus.RUNNING
                execution_step.started_at = datetime.now(timezone.utc)

                await session.commit()

            node_type = node.get("node_type", "")

            print(
                "Processing node:",
                node["node_id"],
                node_type,
                flush=True,
            )

            if node_type.startswith("trigger."):
                # Trigger nodes do not execute an action.
                # Mark the step as completed.
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = ExecutionStepStatus.COMPLETED
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at - execution_step.started_at
                            ).total_seconds()
                            * 1000
                        )

                    await session.commit()

                continue

            if (
                node_type == "action.http_request"
                and isinstance(configuration.get("headers"), str)
            ):
                headers = {}

                for line in configuration["headers"].splitlines():
                    if ":" not in line:
                        continue

                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

                configuration["headers"] = headers

            resolved_configuration = resolver.resolve(configuration)

            # Human Approval does not use Action Service or a connection.
            if node_type == "human.approval":
                print(
                    f"Human approval reached: {node['node_id']}",
                    flush=True,
                )

                approver_user_id = configuration.get("approver_user_id")
                message = resolver.resolve(
                    configuration.get("message", "")
                )
                timeout_minutes = configuration.get("timeout_minutes")

                if not approver_user_id:
                    raise ValueError(
                        f"Human approval node {node['node_id']} has no approver_user_id"
                    )

                if not message:
                    raise ValueError(
                        f"Human approval node {node['node_id']} has no message"
                    )

                timeout_at = None

                if timeout_minutes is not None:
                    timeout_at = datetime.now(timezone.utc) + timedelta(
                        minutes=int(timeout_minutes)
                    )

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution = await session.get(
                        Execution,
                        execution_id,
                    )

                    if execution is None:
                        raise ValueError(f"Execution {execution_id} not found")

                    execution_step.status = ExecutionStepStatus.WAITING_FOR_APPROVAL

                    execution.context = context.to_dict()
                    
                    approval = HumanApproval(
                        execution_id=execution_id,
                        execution_step_id=execution_step_id,
                        workspace_id=UUID(workspace_id),
                        approver_user_id=UUID(approver_user_id),
                        message=message,
                        status=HumanApprovalStatus.PENDING,
                        decision=None,
                        timeout_at=timeout_at,
                        decided_at=None,
                    )

                    session.add(approval)
                    await session.commit()

                    print(
                        f"Created human approval: {approval.id}",
                        flush=True,
                    )

                raise HumanApprovalRequired(node["node_id"])

            print(
                f"Executing action node: {node['node_id']}",
                flush=True,
            )

            connection_id = resolved_configuration.get("connection_id")

            if not connection_id:
                raise ValueError(
                    f"Action node {node['node_id']} has no connection_id configured"
                )

            if node_type == "action.http_request":
                provider, action = "http", "request"
            elif node_type == "action.email":
                provider, action = "gmail", "send_email"
            elif node_type == "action.refund":
                provider, action = "mock_payment", "refund_payment"
            else:
                raise ValueError(
                    f"Unsupported action node type: {node_type}"
                )

            print(
                "Action request:",
                {
                    "workspace_id": workspace_id,
                    "connection_id": connection_id,
                    "provider": provider,
                    "action": action,
                },
                flush=True,
            )

            response = await action_client.execute_action(
                workspace_id=workspace_id,
                connection_id=connection_id,
                provider=provider,
                action=action,
                config_json=json.dumps({}),
                input_data_json=json.dumps(resolved_configuration),
            )

            print(
                "Action result:",
                {
                    "success": response.success,
                    "result": response.result_json,
                    "error": response.error,
                },
                flush=True,
            )

            if response.success:
                try:
                    result = (
                        json.loads(response.result_json)
                        if response.result_json
                        else {}
                    )
                except (json.JSONDecodeError, TypeError):
                    result = {}

                if not isinstance(result, dict):
                    result = {}

                # HTTP connector results wrap the API payload under `body`.
                # Expose object fields at the node root as convenient aliases
                # while retaining status_code, headers, body, and success.
                if (
                    node_type == "action.http_request"
                    and isinstance(result.get("body"), dict)
                ):
                    result = {
                        **result["body"],
                        **result,
                    }

                context.set_node_output(
                    node["node_id"],
                    result,
                )

                print(
                    f"Stored output for node: {node['node_id']}",
                    flush=True,
                )

                # Mark action step as completed
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = ExecutionStepStatus.COMPLETED
                    execution_step.output = result
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at - execution_step.started_at
                            ).total_seconds()
                            * 1000
                        )

                    await session.commit()
            else:
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = ExecutionStepStatus.FAILED
                    execution_step.completed_at = completed_at
                    execution_step.error = {
                        "message": response.error or "Action execution failed",
                    }

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at - execution_step.started_at
                            ).total_seconds()
                            * 1000
                        )

                    await session.commit()

                    raise ActionExecutionFailed(
                        node_id=node["node_id"],
                        error=response.error or "Action execution failed",
                    )

        return {
            "workflow_id": workflow_id,
            "workflow_version_id": workflow_version_id,
            "execution_order": execution_order,
            "action_nodes": action_nodes,
            "context": context.to_dict(),
        }

    finally:
        await workflow_client.close()
        await action_client.close()