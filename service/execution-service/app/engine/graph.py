from dataclasses import dataclass


@dataclass(frozen=True)
class GraphEdge:
    target_node_id: str
    condition: str | None


class ExecutionGraph:
    def __init__(
        self,
        nodes: list[dict],
        edges: list[dict],
    ):
        self.nodes = {
            node["node_id"]: node
            for node in nodes
        }

        self.edges: dict[str, list[GraphEdge]] = {}

        for edge in edges:
            source_node_id = edge["source_node_id"]

            self.edges.setdefault(
                source_node_id,
                [],
            ).append(
                GraphEdge(
                    target_node_id=edge["target_node_id"],
                    condition=edge.get("condition"),
                )
            )

    def get_node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def get_next_nodes(
        self,
        node_id: str,
    ) -> list[GraphEdge]:
        return self.edges.get(node_id, [])

    def get_start_node(self) -> dict | None:
        for node in self.nodes.values():
            if node.get("node_type", "").startswith("trigger."):
                return node

        return None