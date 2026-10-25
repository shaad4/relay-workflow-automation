import re
from typing import Any

EXPRESSION_MARKERS = re.compile(r"\{\{|\}\}")


def validate_resolved_ai_inputs(
    input_mappings: dict[str, Any],
    rag_context: str,
) -> None:
    """Reject missing or unresolved AI inputs."""

    if not isinstance(input_mappings, dict):
        raise ValueError("AI input mappings must be an object")

    if not isinstance(rag_context, str):
        raise ValueError("RAG context must be a string")

    def validate_value(value: Any, path: str) -> None:
        if value is None:
            raise ValueError(f"Missing AI input: {path}")

        if isinstance(value, str):
            if EXPRESSION_MARKERS.search(value):
                raise ValueError(f"Unresolved AI expression: {path}")

        elif isinstance(value, dict):
            for key, item in value.items():
                validate_value(item, f"{path}.{key}")

        elif isinstance(value, list):
            for index, item in enumerate(value):
                validate_value(item, f"{path}[{index}]")

    for name, value in input_mappings.items():
        validate_value(value, name)

    if EXPRESSION_MARKERS.search(rag_context):
        raise ValueError("Unresolved RAG context expression")
