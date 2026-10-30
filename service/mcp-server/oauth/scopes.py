"""OAuth permissions supported by the remote Relay tools."""

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
