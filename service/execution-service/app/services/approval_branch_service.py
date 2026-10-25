
import json

from app.engine.graph import ExecutionGraph
from app.grpc.workflow_client import WorkflowClient


async def resolve_approval_branch(
    workflow_id: str,
    workflow_version_id: str,
    workspace_id: str,
    approval_node_id: str,
    decision: str,
) -> str | None:
    """
    Resolve the next node after a human approval decision.

    Returns:
        Target node ID, or None if the approval node
        has no outgoing edges.

    Raises:
        ValueError for invalid decisions, missing nodes,
        or ambiguous branch configurations.
    """

    if decision not in {"approved", "rejected"}:
        raise ValueError(
            f"Unsupported approval decision: {decision}"
        )

    workflow_client = WorkflowClient()

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

        approval_node = graph.get_node(approval_node_id)

        if approval_node is None:
            raise ValueError(
                f"Approval node not found: {approval_node_id}"
            )

        if approval_node.get("node_type") != "human.approval":
            raise ValueError(
                f"Node {approval_node_id} is not a human approval node"
            )

        branches = graph.get_next_nodes(approval_node_id)
        conditions = [edge.condition for edge in branches]
        if any(value not in {"approved", "rejected"} for value in conditions) or len(set(conditions)) != len(conditions):
            raise ValueError("Invalid human approval branch configuration")

        # Publishing permits either decision branch to be unconnected.
        # That decision finishes this path instead of selecting another branch.
        if decision not in conditions:
            return None

        next_node = graph.get_next_node(
            node_id=approval_node_id,
            condition=decision,
        )

        if next_node is None:
            return None

        return next_node["node_id"]

    finally:
        await workflow_client.close()
