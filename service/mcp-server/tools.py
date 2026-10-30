"""The same tool signatures and implementations for stdio and HTTP."""

import inspect
from contextvars import ContextVar
from functools import wraps

from workflow_builder import create_complete_workflow


def register_tools(mcp, client_context):
    current_client = ContextVar("relay_tool_client")

    def get_client():
        return current_client.get()

    def tool(fn):
        @wraps(fn)
        async def invoke(*args, **kwargs):
            async with client_context(fn.__name__) as client:
                binding = current_client.set(client)
                try:
                    result = fn(*args, **kwargs)
                    if inspect.isawaitable(result):
                        result = await result

                    if hasattr(client, "sanitize_result"):
                        return client.sanitize_result(result)

                    return result
                finally:
                    current_client.reset(binding)

        mcp.tool()(invoke)
        return invoke

    # Connection Test

    @tool
    def relay_hello(name: str) -> str:
        """Test the Relay MCP server connection."""
        return f"Hello {name}! Relay MCP Server is working."

    # Workflow Management

    @tool
    async def relay_list_workflows() -> list[dict]:
        """List workflows belonging to the authenticated Relay workspace."""
        return await get_client().list_workflows()

    @tool
    async def relay_create_workflow(
        name: str,
        description: str = "",
    ) -> dict:
        """Create a new draft workflow in the authenticated Relay workspace."""
        return await get_client().create_workflow(
            name=name,
            description=description,
        )

    @tool
    async def relay_deactivate_workflow(workflow_id: str) -> dict:
        """Deactivate an existing Relay workflow."""
        return await get_client().deactivate_workflow(workflow_id)

    @tool
    async def relay_delete_workflow(workflow_id: str) -> dict:
        """Permanently delete a draft or inactive Relay workflow."""
        return await get_client().delete_workflow(workflow_id)

    # Node Management

    @tool
    async def relay_add_node(
        workflow_id: str,
        version: int,
        node_id: str,
        node_type: str,
        configuration: dict,
    ) -> dict:
        """Add a node to an existing Relay draft workflow version."""
        return await get_client().add_node(
            workflow_id=workflow_id,
            version=version,
            node_id=node_id,
            node_type=node_type,
            configuration=configuration,
        )

    @tool
    async def relay_update_node(
        workflow_id: str,
        version: int,
        node_id: str,
        configuration: dict,
    ) -> dict:
        """Update the configuration of a node in a Relay draft workflow."""
        return await get_client().update_node(
            workflow_id=workflow_id,
            version=version,
            node_id=node_id,
            configuration=configuration,
        )

    @tool
    async def relay_delete_node(
        workflow_id: str,
        version: int,
        node_id: str,
    ) -> dict:
        """Delete a node from a draft workflow. Requires user confirmation."""
        return await get_client().delete_node(
            workflow_id=workflow_id,
            version=version,
            node_id=node_id,
        )

    # Edge Management

    @tool
    async def relay_add_edge(
        workflow_id: str,
        version: int,
        source_node_id: str,
        target_node_id: str,
    ) -> dict:
        """Connect two nodes in an existing Relay draft workflow."""
        return await get_client().add_edge(
            workflow_id=workflow_id,
            version=version,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
        )

    @tool
    async def relay_delete_edge(
        workflow_id: str,
        version: int,
        edge_id: str,
    ) -> dict:
        """Delete an edge from a draft workflow. Requires user confirmation."""
        return await get_client().delete_edge(
            workflow_id=workflow_id,
            version=version,
            edge_id=edge_id,
        )

    # Workflow Validation and Publishing

    @tool
    async def relay_validate_workflow(
        workflow_id: str,
        version: int,
    ) -> dict:
        """Validate a Relay workflow before publishing."""
        return await get_client().validate_workflow(
            workflow_id=workflow_id,
            version=version,
        )

    @tool
    async def relay_publish_workflow(
        workflow_id: str,
        version: int,
    ) -> dict:
        """Publish a validated Relay workflow after user approval."""
        return await get_client().publish_workflow(
            workflow_id=workflow_id,
            version=version,
        )

    # Workflow Execution

    @tool
    async def relay_run_workflow(
        workflow_id: str,
        input_data: dict,
    ) -> dict:
        """Run a published Relay manual-trigger workflow with input data."""
        return await get_client().run_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
        )

    # Execution History

    @tool
    async def relay_list_executions(page: int = 1) -> dict:
        """List recent Relay workflow executions and their statuses."""
        return await get_client().list_executions(page=page)

    @tool
    async def relay_get_execution_steps(execution_id: str) -> dict:
        """Get the steps and outputs of a Relay workflow execution."""
        return await get_client().get_execution_steps(
            execution_id=execution_id,
        )

    # Complete Workflow Creation

    @tool
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
            client=get_client(),
            name=name,
            description=description,
            nodes=nodes,
            edges=edges,
        )
