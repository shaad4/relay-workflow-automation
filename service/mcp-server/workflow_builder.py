from relay_client import RelayClient


async def create_complete_workflow(
    client: RelayClient,
    name: str,
    description: str,
    nodes: list[dict],
    edges: list[dict],
) -> dict:
    if not nodes:
        return {
            "success": False,
            "error": "At least one node is required",
        }

    workflow = await client.create_workflow(
        name=name,
        description=description,
    )

    workflow_id = workflow["id"]
    version = 1

    try:
        for node in nodes:
            await client.add_node(
                workflow_id=workflow_id,
                version=version,
                node_id=node["node_id"],
                node_type=node["node_type"],
                configuration=node.get("configuration", {}),
            )

        for edge in edges:
            await client.add_edge(
                workflow_id=workflow_id,
                version=version,
                source_node_id=edge["source_node_id"],
                target_node_id=edge["target_node_id"],
            )

        validation = await client.validate_workflow(
            workflow_id=workflow_id,
            version=version,
        )

        return {
            "success": validation["valid"],
            "workflow_id": workflow_id,
            "version": version,
            "status": "draft",
            "validation": validation,
        }

    except Exception as exc:
        return {
            "success": False,
            "workflow_id": workflow_id,
            "status": "incomplete_draft",
            "error": str(exc),
        }
