import re
from copy import deepcopy
from typing import Any

PATH_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*|\.\d+|\[\d+\])*$"
)


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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "ExecutionContext":
        context = cls()
        context.data = deepcopy(data)
        return context

    def get(self, path: str) -> Any:
        """
        Resolve nested dictionary and list paths.

        Supported:
            trigger.data.student_id
            nodes.http_request_1.body.name
            nodes.http_request_1.body.subjects[0].subject
            nodes.http_request_1.body.subjects.0.subject

        Returns None for missing or invalid paths.
        """
        if not isinstance(path, str) or not path:
            return None

        if not PATH_PATTERN.fullmatch(path):
            return None

        # Convert bracket indexes into dot-separated segments.
        normalized_path = re.sub(
            r"\[(\d+)\]",
            r".\1",
            path,
        )

        current: Any = self.data

        for part in normalized_path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return None

                current = current[part]

            elif isinstance(current, list):
                if not part.isascii() or not part.isdigit():
                    return None

                index = int(part)

                if index >= len(current):
                    return None

                current = current[index]

            else:
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
