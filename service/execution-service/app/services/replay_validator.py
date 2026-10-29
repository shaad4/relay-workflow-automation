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

            if not isinstance(method, str) or method.upper() not in SAFE_HTTP_METHODS:
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


def get_downstream_node_ids(
    graph: ExecutionGraph,
    start_node_id: str,
) -> set[str] | None:
    """
    Collect nodes reachable after the failed node.

    Return None if the graph contains a missing node
    or a cycle along the replay path.
    """

    visited: set[str] = set()
    visiting: set[str] = set()
    downstream: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return False

        if node_id in visited:
            return True

        if graph.get_node(node_id) is None:
            return False

        visiting.add(node_id)

        for edge in graph.get_next_nodes(node_id):
            if not visit(edge.target_node_id):
                return False

            downstream.add(edge.target_node_id)

        visiting.remove(node_id)
        visited.add(node_id)

        return True

    if not visit(start_node_id):
        return None

    return downstream
