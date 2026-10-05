import re
from typing import Any

from app.engine.context import ExecutionContext


EXPRESSION_PATTERN = re.compile(r"\{\{\s*(.*?)\s*\}\}")


class ExpressionResolver:
    def __init__(self, context: ExecutionContext):
        self.context = context

    def resolve(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.resolve(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self.resolve(item) for item in value]

        if not isinstance(value, str):
            return value

        matches = list(EXPRESSION_PATTERN.finditer(value))
        if not matches:
            return value

        # A whole-value expression preserves the underlying data type.
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            return self.context.get(matches[0].group(1))

        # Embedded expressions are text fragments. Keep unresolved expressions
        # intact so a missing context path does not turn into the word "None".
        parts: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(value[cursor:match.start()])
            resolved = self.context.get(match.group(1))
            parts.append(match.group(0) if resolved is None else str(resolved))
            cursor = match.end()
        parts.append(value[cursor:])
        return "".join(parts)
