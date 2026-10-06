import json

from app.engine.context import ExecutionContext
from app.engine.executor import SequentialExecutor
from app.engine.graph import ExecutionGraph
from app.engine.resolver import ExpressionResolver
from app.grpc.action_client import ActionClient
from app.grpc.workflow_client import WorkflowClient

from app.db.database import AsyncSessionLocal
from app.models.execution_step import ExecutionStep
from app.engine.status import ExecutionStatus


async def run_execution(
    execution_id,
    workflow_id: str,
    workflow_version_id: str,
    workspace_id: str,
    trigger_data: dict | None = None,
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
            configuration = node.get("configuration", {})

            async with AsyncSessionLocal() as session:
                execution_step = ExecutionStep(
                    execution_id=execution_id,
                    node_id=node["node_id"],
                    status=ExecutionStatus.PENDING,
                    sequence=sequence,
                )

                session.add(execution_step)
                await session.commit()
                await session.refresh(execution_step)


            node_type = node.get("node_type", "")

            print(
                "Processing node:",
                node["node_id"],
                node_type,
                flush=True,
            )

            if node_type.startswith("trigger."):
                continue

            if node_type == "action.http_request" and isinstance(configuration.get("headers"), str):
                headers = {}

                for line in configuration["headers"].splitlines():
                    if ":" not in line:
                        continue

                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

                configuration["headers"] = headers

            resolved_configuration = resolver.resolve(configuration)

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
                raise ValueError(f"Unsupported action node type: {node_type}")

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
                    result = json.loads(response.result_json) if response.result_json else {}
                except (json.JSONDecodeError, TypeError):
                    result = {}

                if not isinstance(result, dict):
                    result = {}

                # HTTP connector results wrap the API payload under `body`.
                # Expose object fields at the node root as convenient aliases
                # while retaining status_code, headers, body, and success.
                if node_type == "action.http_request" and isinstance(result.get("body"), dict):
                    result = {**result["body"], **result}

                context.set_node_output(node["node_id"], result)
                print(
                    f"Stored output for node: {node['node_id']}",
                    flush=True,
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
