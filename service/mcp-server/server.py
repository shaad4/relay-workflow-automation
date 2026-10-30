from mcp.server import MCPServer

from relay_client import RelayClient
from relay_session import RelaySession
from workflow_builder import create_complete_workflow


# MCP Server Initialization

mcp = MCPServer("Relay MCP Server")

relay_session = RelaySession()
relay_client = RelayClient(relay_session)


# Connection Test

@mcp.tool()
def relay_hello(name: str) -> str:
    """Test the Relay MCP server connection."""
    return f"Hello {name}! Relay MCP Server is working."


# Workflow Management

@mcp.tool()
async def relay_list_workflows() -> list[dict]:
    """List workflows belonging to the authenticated Relay workspace."""
    return await relay_client.list_workflows()


@mcp.tool()
async def relay_create_workflow(
    name: str,
    description: str = "",
) -> dict:
    """Create a new draft workflow in the authenticated Relay workspace."""
    return await relay_client.create_workflow(
        name=name,
        description=description,
    )


@mcp.tool()
async def relay_deactivate_workflow(workflow_id: str) -> dict:
    """Deactivate an existing Relay workflow."""
    return await relay_client.deactivate_workflow(workflow_id)


@mcp.tool()
async def relay_delete_workflow(workflow_id: str) -> dict:
    """Permanently delete a draft or inactive Relay workflow."""
    return await relay_client.delete_workflow(workflow_id)


# Node Management

@mcp.tool()
async def relay_add_node(
    workflow_id: str,
    version: int,
    node_id: str,
    node_type: str,
    configuration: dict,
) -> dict:
    """Add a node to an existing Relay draft workflow version."""
    return await relay_client.add_node(
        workflow_id=workflow_id,
        version=version,
        node_id=node_id,
        node_type=node_type,
        configuration=configuration,
    )


@mcp.tool()
async def relay_update_node(
    workflow_id: str,
    version: int,
    node_id: str,
    configuration: dict,
) -> dict:
    """Update the configuration of a node in a Relay draft workflow."""
    return await relay_client.update_node(
        workflow_id=workflow_id,
        version=version,
        node_id=node_id,
        configuration=configuration,
    )


@mcp.tool()
async def relay_delete_node(
    workflow_id: str,
    version: int,
    node_id: str,
) -> dict:
    """Delete a node from a draft workflow. Requires user confirmation."""
    return await relay_client.delete_node(
        workflow_id=workflow_id,
        version=version,
        node_id=node_id,
    )


# Edge Management

@mcp.tool()
async def relay_add_edge(
    workflow_id: str,
    version: int,
    source_node_id: str,
    target_node_id: str,
) -> dict:
    """Connect two nodes in an existing Relay draft workflow."""
    return await relay_client.add_edge(
        workflow_id=workflow_id,
        version=version,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
    )


@mcp.tool()
async def relay_delete_edge(
    workflow_id: str,
    version: int,
    edge_id: str,
) -> dict:
    """Delete an edge from a draft workflow. Requires user confirmation."""
    return await relay_client.delete_edge(
        workflow_id=workflow_id,
        version=version,
        edge_id=edge_id,
    )


# Workflow Validation and Publishing

@mcp.tool()
async def relay_validate_workflow(
    workflow_id: str,
    version: int,
) -> dict:
    """Validate a Relay workflow before publishing."""
    return await relay_client.validate_workflow(
        workflow_id=workflow_id,
        version=version,
    )


@mcp.tool()
async def relay_publish_workflow(
    workflow_id: str,
    version: int,
) -> dict:
    """Publish a validated Relay workflow after user approval."""
    return await relay_client.publish_workflow(
        workflow_id=workflow_id,
        version=version,
    )


# Workflow Execution

@mcp.tool()
async def relay_run_workflow(
    workflow_id: str,
    input_data: dict,
) -> dict:
    """Run a published Relay manual-trigger workflow with input data."""
    return await relay_client.run_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
    )


# Execution History

@mcp.tool()
async def relay_list_executions(page: int = 1) -> dict:
    """List recent Relay workflow executions and their statuses."""
    return await relay_client.list_executions(page=page)


@mcp.tool()
async def relay_get_execution_steps(execution_id: str) -> dict:
    """Get the steps and outputs of a Relay workflow execution."""
    return await relay_client.get_execution_steps(
        execution_id=execution_id,
    )


# Complete Workflow Creation

@mcp.tool()
async def relay_create_complete_workflow(
    name: str,
    description: str,
    nodes: list[dict],
    edges: list[dict],
) -> dict:
    """
    Create a complete Relay workflow from nodes and edges.

    Creates a draft and validates it.
    Does not publish or execute the workflow.
    """
    return await create_complete_workflow(
        client=relay_client,
        name=name,
        description=description,
        nodes=nodes,
        edges=edges,
    )


# Start MCP Server

if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        # RelaySession owns an async HTTP client.
        # Its cleanup will be handled through the MCP lifecycle
        # in a later improvement.
        pass
