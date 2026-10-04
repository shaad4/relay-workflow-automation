import re
from typing import Any

from app.engine.context import ExecutionContext


EXPRESSION_PATTERN = re.compile(
    r"^\{\{\s*(.*?)\s*\}\}$"
)


class ExpressionResolver:
    def __init__(self, context: ExecutionContext):
        self.context = context

    def resolve(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        match = EXPRESSION_PATTERN.match(value)

        if not match:
            return value

        path = match.group(1)

        return self.context.get(path)