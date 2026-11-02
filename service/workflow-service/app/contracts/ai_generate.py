"""AI Generate's authoring and resolved-value contracts. No provider dependencies."""

from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WithJsonSchema,
    WrapValidator,
    field_validator,
)

from .expressions import EXPRESSION_PATTERN, expression_matches


def connection_uuid(value, handler: ValidatorFunctionWrapHandler, info: ValidationInfo):
    if not (info.context or {}).get("resolved") and isinstance(value, str):
        if EXPRESSION_PATTERN.fullmatch(value):
            expression_matches(value)
            return value
    return handler(value)


class AIGenerateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: Annotated[
        UUID,
        WrapValidator(connection_uuid),
        WithJsonSchema(
            {
                "anyOf": [
                    {"type": "string", "format": "uuid"},
                    {"type": "string", "pattern": r"^\{\{\s*[^{}]+\s*\}\}$"},
                ]
            }
        ),
    ]
    model: str = Field(min_length=1, max_length=150)
    instructions: str = Field(default="", max_length=10000)
    prompt: str = Field(min_length=1, max_length=10000)
    rag_context: str = Field(default="", max_length=2000)

    @field_validator("model", "instructions", "prompt")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("model", "prompt")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("Field cannot be empty")
        return value


class AIGenerateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    content: str = Field(min_length=1)
    model: str = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @field_validator("content", "model")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value
