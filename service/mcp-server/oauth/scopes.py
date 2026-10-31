"""OAuth permissions supported by the remote Relay tools."""

from mcp.types import CallToolResult, TextContent
from user_session import RelayAccessError

SCOPES = ["relay:read", "relay:write", "relay:execute", "relay:delete"]
TOOL_SCOPES = {
    "relay_hello": None,
    "relay_list_workflows": "relay:read",
    "relay_list_executions": "relay:read",
    "relay_get_execution_steps": "relay:read",
    "relay_create_workflow": "relay:write",
    "relay_add_node": "relay:write",
    "relay_update_node": "relay:write",
    "relay_add_edge": "relay:write",
    "relay_validate_workflow": "relay:write",
    "relay_create_complete_workflow": "relay:write",
    "relay_publish_workflow": "relay:execute",
    "relay_deactivate_workflow": "relay:execute",
    "relay_run_workflow": "relay:execute",
    "relay_delete_workflow": "relay:delete",
    "relay_delete_node": "relay:delete",
    "relay_delete_edge": "relay:delete",
}


class InsufficientScopeError(RelayAccessError):
    """A denied tool call that a client can resolve through explicit OAuth consent."""

    def __init__(self, scope):
        # Scope names come only from TOOL_SCOPES, never request arguments.
        self.scope = scope
        super().__init__("Insufficient OAuth scope")

    def as_tool_result(self, resource):
        metadata_url = resource.removesuffix("/mcp") + "/.well-known/oauth-protected-resource/mcp"
        challenge = (
            f'Bearer resource_metadata="{metadata_url}", '
            'error="insufficient_scope", '
            f'error_description="Authorize {self.scope} to use this tool", '
            f'scope="{self.scope}"'
        )
        return CallToolResult(
            is_error=True,
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"Insufficient OAuth scope: this tool requires {self.scope}. "
                        "Authorize this permission in Relay and retry. If the OAuth client "
                        "was registered for read-only access, recreate its registration "
                        "with the required scope first; reconnecting with the same "
                        "read-only scopes cannot add permission."
                    ),
                )
            ],
            meta={"mcp/www_authenticate": [challenge]},
        )
