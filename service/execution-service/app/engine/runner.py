import json

from app.engine.context import ExecutionContext
from app.engine.executor import SequentialExecutor
from app.engine.graph import ExecutionGraph
from app.grpc.action_client import ActionClient
from app.grpc.workflow_client import WorkflowClient


async def run_execution(
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

        for node in action_nodes:
            configuration = node.get("configuration", {})

            print(
                f"Executing action node: {node['node_id']}",
                flush=True,
            )

            response = await action_client.execute_action(
                workspace_id=workspace_id,
                connection_id="00000000-0000-0000-0000-000000000000",
                provider="http",
                action="request",
                config_json=json.dumps(configuration),
                input_data_json=json.dumps(
                    context.to_dict()
                ),
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