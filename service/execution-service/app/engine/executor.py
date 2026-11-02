from app.engine.graph import ExecutionGraph


class SequentialExecutor:
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph

    def get_start_node(self) -> dict:
        start_node = self.graph.get_start_node()

        if start_node is None:
            raise ValueError("Workflow does not have a start node")

        return start_node

    def get_next_node(
        self,
        node_id: str,
        condition: str | None = None,
    ) -> dict | None:
        return self.graph.get_next_node(
            node_id=node_id,
            condition=condition,
        )

    def get_action_nodes(self) -> list[dict]:
        return [
            node
            for node in self.graph.nodes.values()
            if node.get("node_type", "").startswith("action.")
        ]
