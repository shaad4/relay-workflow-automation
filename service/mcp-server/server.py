import os

from mcp.server import MCPServer
from relay_client import RelayClient

mcp = MCPServer("Relay MCP Server")


@mcp.tool()
def relay_hello(name: str) -> str:
    """Test the Relay MCP server connection."""
    return f"Hello {name}! Relay MCP Server is working."


@mcp.tool()
async def relay_list_workflows() -> list[dict]:
    """List workflows belonging to the authenticated Relay workspace."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.list_workflows()


@mcp.tool()
async def relay_create_workflow(
    name: str,
    description: str = "",
) -> dict:
    """Create a new draft workflow in the authenticated Relay workspace."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.create_workflow(
        name=name,
        description=description,
    )


@mcp.tool()
async def relay_add_node(
    workflow_id: str,
    version: int,
    node_id: str,
    node_type: str,
    configuration: dict,
) -> dict:
    """Add a node to an existing Relay draft workflow version."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.add_node(
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

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.update_node(
        workflow_id=workflow_id,
        version=version,
        node_id=node_id,
        configuration=configuration,
    )

@mcp.tool()
async def relay_add_edge(
    workflow_id: str,
    version: int,
    source_node_id: str,
    target_node_id: str,
) -> dict:
    """Connect two nodes in an existing Relay draft workflow."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.add_edge(
        workflow_id=workflow_id,
        version=version,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
    )

@mcp.tool()
async def relay_validate_workflow(
    workflow_id: str,
    version: int,
) -> dict:
    """Validate a Relay workflow before publishing."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.validate_workflow(
        workflow_id=workflow_id,
        version=version,
    )

@mcp.tool()
async def relay_publish_workflow(
    workflow_id: str,
    version: int,
) -> dict:
    """Publish a validated Relay workflow after user approval."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.publish_workflow(
        workflow_id=workflow_id,
        version=version,
    )

@mcp.tool()
async def relay_run_workflow(
    workflow_id: str,
    input_data: dict,
) -> dict:
    """Run a published Relay manual-trigger workflow with input data."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.run_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
    )

@mcp.tool()
async def relay_list_executions(page: int = 1) -> dict:
    """List recent Relay workflow executions and their statuses."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.list_executions(page=page)


@mcp.tool()
async def relay_get_execution_steps(execution_id: str) -> dict:
    """Get the steps and outputs of a Relay workflow execution."""

    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    return await client.get_execution_steps(
        execution_id=execution_id,
    )

if __name__ == "__main__":
    mcp.run()