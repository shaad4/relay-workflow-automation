from app.engine.graph import ExecutionGraph


SAFE_NODE_TYPES = {
    "ai.rag_search",
    "ai.generate",
    "ai.decision",
    "logic.condition",
}

SAFE_HTTP_METHODS = {"GET", "HEAD"}


def validate_replay_path(
    graph: ExecutionGraph,
    start_node_id: str,
) -> bool:
    """Validate the replay node and all downstream paths."""

    visited = set()
    visiting = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return False

        if node_id in visited:
            return True

        node = graph.get_node(node_id)

        if node is None:
            return False

        node_type = node.get("node_type")

        if node_type == "action.http_request":
            config = node.get("configuration", {})

            if not isinstance(config, dict):
                return False

            method = config.get("method", "GET")

            if (
                not isinstance(method, str)
                or method.upper() not in SAFE_HTTP_METHODS
            ):
                return False

        elif node_type not in SAFE_NODE_TYPES:
            return False

        visiting.add(node_id)

        for edge in graph.get_next_nodes(node_id):
            if not visit(edge.target_node_id):
                return False

        visiting.remove(node_id)
        visited.add(node_id)

        return True

    return visit(start_node_id)
