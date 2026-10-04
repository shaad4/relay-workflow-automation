from app.engine.graph import ExecutionGraph


class SequentialExecutor:
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph

    def get_execution_order(self) -> list[dict]:
        start_node = self.graph.get_start_node()

        if start_node is None:
            raise ValueError("Workflow does not have a start node")

        execution_order: list[dict] = []
        visited: set[str] = set()

        current_node = start_node

        while current_node is not None:
            node_id = current_node["node_id"]

            if node_id in visited:
                raise ValueError(
                    f"Cycle detected in workflow at node: {node_id}"
                )

            visited.add(node_id)
            execution_order.append(current_node)

            next_edges = self.graph.get_next_nodes(node_id)

            if not next_edges:
                break

            if len(next_edges) > 1:
                raise ValueError(
                    f"Sequential execution found multiple outgoing "
                    f"edges from node: {node_id}"
                )

            next_node_id = next_edges[0].target_node_id

            current_node = self.graph.get_node(next_node_id)

            if current_node is None:
                raise ValueError(
                    f"Target node not found: {next_node_id}"
                )

        return execution_order

    def get_action_nodes(self) -> list[dict]:
        execution_order = self.get_execution_order()

        return [
            node
            for node in execution_order
            if node.get("node_type", "").startswith("action.")
        ]