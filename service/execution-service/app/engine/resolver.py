from typing import Any

from app.contracts.expressions import EXPRESSION_PATTERN, expression_matches
from app.engine.context import ExecutionContext
from app.engine.exceptions import ExpressionResolutionError


class ExpressionResolver:
    def __init__(self, context: ExecutionContext):
        self.context = context

    def resolve(self, value: Any, *, strict: bool = False, field: str = "") -> Any:
        if isinstance(value, dict):
            return {
                key: self.resolve(
                    item, strict=strict, field=f"{field}.{key}" if field else str(key)
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self.resolve(item, strict=strict, field=f"{field}[{index}]")
                for index, item in enumerate(value)
            ]

        if not isinstance(value, str):
            return value

        try:
            matches = (
                expression_matches(value) if strict else list(EXPRESSION_PATTERN.finditer(value))
            )
        except ValueError:
            raise ExpressionResolutionError(field) from None
        if not matches:
            return value

        # A whole-value expression preserves the underlying data type.
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            resolved = self.context.get(matches[0].group(1))
            if strict and resolved is None:
                raise ExpressionResolutionError(field, matches[0].group(0))
            return resolved

        # Embedded expressions are text fragments. Keep unresolved expressions
        # intact so a missing context path does not turn into the word "None".
        parts: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(value[cursor : match.start()])
            resolved = self.context.get(match.group(1))
            if strict and resolved is None:
                raise ExpressionResolutionError(field, match.group(0))
            parts.append(match.group(0) if resolved is None else str(resolved))
            cursor = match.end()
        parts.append(value[cursor:])
        return "".join(parts)
