"""The same tool signatures and implementations for stdio and HTTP."""

import inspect
from contextvars import ContextVar
from functools import wraps

from mcp.types import ToolAnnotations
from oauth.scopes import TOOL_SCOPES, InsufficientScopeError
from user_session import ReauthorizationRequired
from workflow_builder import create_complete_workflow

AUTHORING_INSTRUCTIONS = """Before building or modifying workflows, call relay_get_node_schema
for the node types involved. Use the returned schemas, examples, and output fields.
Discover connections with relay_list_connections or relay_list_ai_provider_connections;
discover model IDs with relay_list_ai_models. Do not ask users to copy IDs or invent them.
Trigger inputs use {{trigger.data.<field>}} regardless of the trigger node ID.
Node outputs use {{nodes.<node_id>.<field>}}, with no .output wrapper.
Validate definitions with relay_validate_workflow_definition and fix structured errors.
Create a draft, validate the saved version, and publish or run only when authorized.
"""


def register_tools(mcp, client_context, *, oauth_resource=None):
    current_client = ContextVar("relay_tool_client")

    def get_client():
        return current_client.get()

    def tool(fn):
        @wraps(fn)
        async def invoke(*args, **kwargs):
            try:
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
            except (InsufficientScopeError, ReauthorizationRequired) as error:
                if oauth_resource is None:
                    raise
                # An ordinary ToolError loses the metadata ChatGPT needs to reauthorize.
                return error.as_tool_result(oauth_resource)

        meta = None
        if oauth_resource is not None:
            scope = TOOL_SCOPES[fn.__name__]
            # SDK 2.3 exposes extension fields through _meta. ChatGPT supports this
            # securitySchemes mirror; stdio tools keep their existing descriptors.
            meta = {"securitySchemes": [{"type": "oauth2", "scopes": [scope] if scope else []}]}
        annotations = None
        if TOOL_SCOPES[fn.__name__] == "relay:read":
            annotations = ToolAnnotations(
                read_only_hint=True, destructive_hint=False, idempotent_hint=True
            )
        mcp.tool(meta=meta, annotations=annotations)(invoke)
        return invoke

    # Connection Test

    @tool
    def relay_hello(name: str) -> str:
        """Test the Relay MCP server connection."""
        return f"Hello {name}! Relay MCP Server is working."

    @tool
    async def relay_get_node_schema(node_type: str | None = None) -> dict:
        """Read Relay's live node configuration schemas before authoring a workflow.

        Pass a node_type such as ai.generate, or omit it to discover all supported
        types. Returns configuration/output schemas, examples, expression rules,
        edge conditions, and authoring steps. Example IDs/models are placeholders.
        Use trigger.data for inputs and nodes.<id>.<field> for upstream outputs.
        """
        return await get_client().get_node_schema(node_type=node_type)

    @tool
    async def relay_validate_workflow_definition(
        nodes: list[dict], edges: list[dict], sample_input: dict | None = None
    ) -> dict:
        """Validate a proposed graph without saving it or executing any nodes.

        Returns errors with node_id, field, expression, and correction guidance.
        Checks configuration schemas, graph structure, expression paths and known
        outputs. Optional sample_input is the raw trigger data object and checks
        whether referenced trigger fields exist. It does not call AI providers,
        verify credentials, or guarantee future input values. Fix errors before
        creating or publishing the workflow.
        """
        return await get_client().validate_workflow_definition(nodes, edges, sample_input)

    @tool
    async def relay_list_ai_models(connection_id: str) -> dict:
        """List model IDs available through an active workspace AI connection.

        First discover connection_id with relay_list_ai_provider_connections.
        Use a returned model ID supporting the intended text/structured generation
        task; provider catalogs can include models for other tasks. No generation
        is performed and credentials are never returned.
        """
        return await get_client().list_ai_models(connection_id)

    # Connection Discovery

    @tool
    async def relay_list_connections(provider: str | None = None) -> list[dict]:
        """Find saved app connections in the authenticated Relay workspace.

        Call before configuring Gmail, HTTP, or other app action nodes; do not ask
        the user to copy connection IDs. Optionally filter by provider, e.g. gmail
        or http (case-insensitive); omit to list all app connections.
        Returns id, name, provider, auth_type, Gmail account email (otherwise null),
        and status=configured. Configured means saved, not a live health check.
        Use the selected id as the node's configuration.connection_id. If multiple
        accounts match, use the requested name/email or ask which account to use.
        An empty list means no matching saved connection; ask the user to connect
        it in Relay. Credentials are never returned. For AI nodes, use
        relay_list_ai_provider_connections instead.
        """
        return await get_client().list_connections(provider=provider)

    @tool
    async def relay_list_ai_provider_connections(provider: str | None = None) -> list[dict]:
        """Find saved AI provider connections in the authenticated Relay workspace.

        Call before configuring AI nodes; do not ask the user to copy connection
        IDs. Optionally filter by provider: openai, gemini, or anthropic
        (case-insensitive); omit to list all AI provider connections.
        Returns id, name, provider, and saved status (active or inactive), never
        API keys. Select an active connection and use its id as the AI node's
        configuration.connection_id. Active is not a live provider health check.
        If multiple active connections match, use the requested name or ask which
        to use. An empty list means no matching saved connection; ask the user to
        connect the provider in Relay. For Gmail/HTTP, use relay_list_connections.
        """
        return await get_client().list_ai_provider_connections(provider=provider)

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
        """Add a node to an existing Relay draft workflow version.

        First read relay_get_node_schema(node_type) for supported fields and
        expressions. Trigger inputs use {{trigger.data.<field>}} and previous
        outputs use {{nodes.<node_id>.<field>}}.
        For nodes needing configuration.connection_id, discover it first with
        relay_list_connections (apps) or relay_list_ai_provider_connections (AI).
        """
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
        """Update the configuration of a node in a Relay draft workflow.

        Read relay_get_node_schema for the node type before changing fields.
        Resolve connection IDs with relay_list_connections (apps) or
        relay_list_ai_provider_connections (AI) when changing a node's connection.
        """
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
        condition: str | None = None,
    ) -> dict:
        """Connect nodes in a draft. For logic.condition, set condition to the
        exact branch value; for human.approval, use approved or rejected.
        """
        return await get_client().add_edge(
            workflow_id=workflow_id,
            version=version,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            condition=condition,
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
        sample_input: dict | None = None,
    ) -> dict:
        """
        Create a complete Relay workflow from nodes and edges.

        First read relay_get_node_schema for each node type. Trigger inputs use
        {{trigger.data.<field>}}, never a trigger node ID. Previous outputs use
        {{nodes.<node_id>.<field>}}, without an extra .output level.
        Validates the definition before saving, then creates and validates a draft.
        Optional sample_input checks trigger references without executing nodes.
        Does not publish or execute the workflow.
        Before creating nodes that need configuration.connection_id, call
        relay_list_connections for apps (including Gmail) or
        relay_list_ai_provider_connections for AI providers to find IDs by name.
        Use relay_list_ai_models to discover model IDs for the selected connection.
        """
        return await create_complete_workflow(
            client=get_client(),
            name=name,
            description=description,
            nodes=nodes,
            edges=edges,
            sample_input=sample_input,
        )
