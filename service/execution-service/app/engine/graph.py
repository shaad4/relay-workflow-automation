
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

    def get_next_node(
        self,
        node_id: str,
        condition: str | None = None,
    ) -> dict | None:
        edges = self.get_next_nodes(node_id)

        if not edges:
            return None

        if condition is None:
            if len(edges) != 1:
                raise ValueError(
                    f"Node {node_id} has multiple outgoing edges "
                    "but no condition was provided"
                )

            selected_edge = edges[0]

        else:
            matching_edges = [
                edge
                for edge in edges
                if edge.condition == condition
            ]

            if len(matching_edges) != 1:
                raise ValueError(
                    f"Expected exactly one edge for condition "
                    f"'{condition}' on node {node_id}, "
                    f"found {len(matching_edges)}"
                )

            selected_edge = matching_edges[0]

        next_node = self.get_node(
            selected_edge.target_node_id
        )

        if next_node is None:
            raise ValueError(
                f"Target node not found: "
                f"{selected_edge.target_node_id}"
            )

        return next_node

    def get_start_node(self) -> dict | None:
        for node in self.nodes.values():
            if node.get("node_type", "").startswith("trigger."):
                return node

        return None
