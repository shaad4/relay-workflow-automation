from typing import Any


class ExecutionContext:
    def __init__(
        self,
        trigger_data: dict | None = None,
    ):
        self.data: dict[str, Any] = {
            "trigger": {
                "data": trigger_data or {},
            },
            "variables": {},
            "nodes": {},
        }

    def get(self, path: str) -> Any:
        current: Any = self.data

        for part in path.split("."):
            if not isinstance(current, dict):
                return None

            current = current.get(part)

            if current is None:
                return None

        return current

    def set_node_output(
        self,
        node_id: str,
        output: dict | None,
    ) -> None:
        self.data["nodes"][node_id] = output or {}

    def set_variable(
        self,
        name: str,
        value: Any,
    ) -> None:
        self.data["variables"][name] = value

    def to_dict(self) -> dict[str, Any]:
        return self.data