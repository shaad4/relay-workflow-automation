import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select

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
from app.engine.handlers.rag_search import execute_rag_search
from app.engine.handlers.ai_decision import execute_ai_decision
from app.engine.handlers.condition import evaluate_condition
from app.engine.handlers.ai_generate import execute_ai_generate

from app.ai.exceptions import (
    AIDecisionValidationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIResponseError,
)


async def _commit_session(session, add=None, refresh=None):
    try:
        if add is not None:
            session.add(add)

        await session.commit()

        if refresh is not None:
            await session.refresh(refresh)

    except Exception:
        await session.rollback()
        raise

async def mark_step_failed(
    execution_step_id,
    error_message: str,
):
    async with AsyncSessionLocal() as session:
        step = await session.get(
            ExecutionStep,
            execution_step_id,
        )

        if step is None:
            return

        if step.status not in {ExecutionStepStatus.PENDING, ExecutionStepStatus.RUNNING}:
            return

        completed_at = datetime.now(timezone.utc)

        step.status = ExecutionStepStatus.FAILED
        step.completed_at = completed_at
        step.error = {
            "message": error_message,
        }

        if step.started_at:
            step.duration_ms = int(
                (completed_at - step.started_at).total_seconds()
                * 1000
            )

        await _commit_session(session)


async def run_execution(
    execution_id,
    workflow_id: str,
    workflow_version_id: str,
    workspace_id: str,
    trigger_data: dict | None = None,
    resume_from_sequence: int | None = None,
    context_data: dict | None = None,
    start_node_id: str | None = None,
):
    workflow_client = WorkflowClient()
    action_client = ActionClient()
    context = None
    execution_step_id = None

    try:
        response = await workflow_client.get_workflow_definition(
            workflow_id=workflow_id,
            version_id=workflow_version_id,
            workspace_id=workspace_id,
        )

        workflow_name = response.workflow_name

        async with AsyncSessionLocal() as session:
            execution = await session.get(
                Execution,
                execution_id,
            )

            if execution is None:
                raise ValueError(
                    "Execution not found"
                )

            if execution.workspace_id != UUID(workspace_id):
                raise ValueError(
                    "Execution does not belong to workspace"
                )

            if execution.workflow_name is None:
                execution.workflow_name = workflow_name

                await _commit_session(session)


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

        action_nodes = executor.get_action_nodes()

        if resume_from_sequence is not None:
            raise ValueError(
                "Sequence-based resume is deprecated. "
                "Use start_node_id instead."
            )

        if start_node_id is not None:
            current_node = graph.get_node(start_node_id)

            if current_node is None:
                raise ValueError(
                    f"Resume node not found: {start_node_id}"
                )
        else:
            current_node = executor.get_start_node()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(
                    func.coalesce(
                        func.max(ExecutionStep.sequence),
                        0,
                    )
                ).where(
                    ExecutionStep.execution_id == execution_id
                )
            )

            sequence = result.scalar_one() + 1

        visited: set[str] = set()
        execution_order: list[dict] = []

        print(
            "Action node definitions:",
            json.dumps(action_nodes, indent=2),
            flush=True,
        )

        print(
            "Starting execution from:",
            current_node["node_id"],
            flush=True,
        )

        while current_node is not None:
            execution_step_id = None
            node = current_node
            node_id = node["node_id"]

            if node_id in visited:
                raise ValueError(
                    f"Cycle detected in workflow at node: {node_id}"
                )

            visited.add(node_id)
            execution_order.append(node)

            configuration = node.get("configuration", {})

            # Allocate the ID before commit so even refresh failures can close the step.
            execution_step_id = uuid4()
            # Create execution step
            async with AsyncSessionLocal() as session:
                execution_step = ExecutionStep(
                    id=execution_step_id,
                    execution_id=execution_id,
                    node_id=node["node_id"],
                    status=ExecutionStepStatus.PENDING,
                    sequence=sequence,
                )

                await _commit_session(
                    session,
                    add=execution_step,
                    refresh=execution_step,
                )

            execution_step_id = execution_step.id

            # Mark step as running
            async with AsyncSessionLocal() as session:
                execution_step = await session.get(
                    ExecutionStep,
                    execution_step_id,
                )

                execution_step.status = ExecutionStepStatus.RUNNING
                execution_step.started_at = datetime.now(timezone.utc)

                await _commit_session(session)

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

                    await _commit_session(session)

                current_node = executor.get_next_node(node_id)
                sequence += 1

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


            # Execute RAG Search node
            if node_type == "ai.rag_search":
                result = await execute_rag_search(
                    configuration=resolved_configuration,
                    workspace_id=workspace_id,
                )

                # Store output for downstream nodes
                context.set_node_output(
                    node_id,
                    result,
                )

                # Persist execution step result
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = (
                        ExecutionStepStatus.COMPLETED
                    )
                    execution_step.output = result
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at
                                - execution_step.started_at
                            ).total_seconds() * 1000
                        )

                    await _commit_session(session)

                # Continue to the next workflow node
                current_node = executor.get_next_node(node_id)
                sequence += 1

                continue


            # Execute AI Decision node
            if node_type == "ai.decision":
                async with AsyncSessionLocal() as session:
                    result = await execute_ai_decision(
                        configuration=resolved_configuration,
                        workspace_id=workspace_id,
                        session=session,
                    )

                # Store validated AI output for downstream nodes
                context.set_node_output(
                    node_id,
                    result,
                )

                # Persist AI Decision execution step
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = (
                        ExecutionStepStatus.COMPLETED
                    )

                    execution_step.output = result
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at
                                - execution_step.started_at
                            ).total_seconds() * 1000
                        )

                    await _commit_session(session)

                # Continue to the next workflow node
                current_node = executor.get_next_node(node_id)
                sequence += 1

                continue



            # Execute AI Generate node
            if node_type == "ai.generate":
                async with AsyncSessionLocal() as session:
                    result = await execute_ai_generate(
                        configuration=resolved_configuration,
                        workspace_id=workspace_id,
                        session=session,
                    )

                # Store generated output for downstream nodes
                context.set_node_output(
                    node_id,
                    result,
                )

                # Persist AI Generate execution step
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    if execution_step is None:
                        raise RuntimeError(
                            "AI Generate execution step not found"
                        )

                    execution_step.status = (
                        ExecutionStepStatus.COMPLETED
                    )

                    execution_step.output = result
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at
                                - execution_step.started_at
                            ).total_seconds() * 1000
                        )

                    await _commit_session(session)

                # Continue to the next workflow node
                current_node = executor.get_next_node(node_id)
                sequence += 1

                continue



            # Execute Condition node
            if node_type == "logic.condition":
                # Read the resolved value
                selected_condition = evaluate_condition(
                    resolved_configuration
                )

                # Find the matching outgoing edge
                next_node = executor.get_next_node(
                    node_id=node_id,
                    condition=selected_condition,
                )

                if next_node is None:
                    raise ValueError(
                        "Condition node has no matching branch"
                    )

                # Store the selected branch
                result = {
                    "value": selected_condition,
                    "selected_branch": selected_condition,
                    "next_node_id": next_node["node_id"],
                }

                context.set_node_output(
                    node_id,
                    result,
                )

                # Mark Condition step completed
                completed_at = datetime.now(timezone.utc)

                async with AsyncSessionLocal() as session:
                    execution_step = await session.get(
                        ExecutionStep,
                        execution_step_id,
                    )

                    execution_step.status = (
                        ExecutionStepStatus.COMPLETED
                    )

                    execution_step.output = result
                    execution_step.completed_at = completed_at

                    if execution_step.started_at:
                        execution_step.duration_ms = int(
                            (
                                completed_at
                                - execution_step.started_at
                            ).total_seconds() * 1000
                        )

                    await _commit_session(session)

                # Continue only through the selected edge
                current_node = next_node
                sequence += 1

                continue




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
                        raise ValueError(
                            f"Execution {execution_id} not found"
                        )

                    execution_step.status = (
                        ExecutionStepStatus.WAITING_FOR_APPROVAL
                    )

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

                    await _commit_session(
                        session,
                        add=approval,
                    )

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
                resolved_configuration.setdefault("body_format", "plain")

            elif node_type == "action.refund":
                provider, action = "", "refund_payment"

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

                    await _commit_session(session)

                current_node = executor.get_next_node(node_id)
                sequence += 1

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

                    await _commit_session(session)

                    raise ActionExecutionFailed(
                        node_id=node["node_id"],
                        error=response.error or "Action execution failed",
                    )

        return {
            "workflow_id": workflow_id,
            "workflow_version_id": workflow_version_id,
            "workflow_name": workflow_name,
            "execution_order": execution_order,
            "action_nodes": action_nodes,
            "context": context.to_dict(),
        }

    except HumanApprovalRequired:
        # The approval transaction already saved context and the waiting step.
        raise
    except Exception as exc:
        print(
            "\n========== WORKFLOW EXECUTION ERROR ==========",
            flush=True,
        )
        print("Node ID:", node_id, flush=True)
        print("Node Type:", node_type, flush=True)
        print("Exception Type:", type(exc).__name__, flush=True)
        print("==============================================\n", flush=True)

         # Classify failures using safe messages.
        if isinstance(exc, ActionExecutionFailed):
            message = "Action execution failed"

        elif isinstance(exc, AIDecisionValidationError):
            message = "AI Decision returned an invalid response"

        elif isinstance(exc, AIAuthenticationError):
            message = "AI provider authentication failed"

        elif isinstance(exc, AIRateLimitError):
            message = "AI provider rate limit exceeded"

        elif isinstance(exc, AITimeoutError):
            message = "AI provider request timed out"

        elif isinstance(exc, AIServiceUnavailableError):
            message = "AI provider unavailable"

        elif isinstance(exc, AIResponseError):
            message = "AI provider returned an invalid response"

        else:
            message = "Node execution failed"

        try:
            if execution_step_id is not None:
                await mark_step_failed(
                    execution_step_id,
                    message,
                )

        finally:
            if context is not None:
                async with AsyncSessionLocal() as session:
                    execution = await session.get(
                        Execution,
                        execution_id,
                    )

                    if execution is not None:
                        execution.context = context.to_dict()
                        await _commit_session(session)

        raise
    finally:
        try:
            await workflow_client.close()
        finally:
            await action_client.close()
