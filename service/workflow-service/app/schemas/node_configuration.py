from typing import Any
import re
from uuid import UUID


from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RagSearchConfig(BaseModel):
    """Configuration schema for the RAG Search node."""

    model_config = ConfigDict(extra="forbid")

    knowledge_base_id: UUID

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        strict=True,
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_config(cls, data):
        """Support older RAG node configurations."""

        if not isinstance(data, dict):
            return data

        data = data.copy()

        if "knowledge_base" in data:
            legacy_id = data.pop("knowledge_base")
            if "knowledge_base_id" in data:
                if data["knowledge_base_id"] != legacy_id:
                    raise ValueError("Conflicting knowledge base identifiers")
            else:
                data["knowledge_base_id"] = legacy_id

        return data

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Validate the RAG query template."""

        value = value.strip()

        if not value:
            raise ValueError(
                "RAG query cannot be empty"
            )

        return value




class AIDecisionConfig(BaseModel):
    """Configuration for a generic AI Decision node."""

    model_config = ConfigDict(extra="forbid")

    connection_id: UUID

    model: str = Field(
        min_length=1,
        max_length=150,
    )

    instructions: str = Field(
        min_length=1,
        max_length=10000,
    )

    input_mappings: dict[str, Any] = Field(
        default_factory=dict,
    )

    rag_context: str = Field(
        default="",
        max_length=2000,
    )

    allowed_decisions: list[str] = Field(
        min_length=2,
        max_length=20,
    )

    @field_validator("model", "instructions")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value

    @field_validator("allowed_decisions")
    @classmethod
    def validate_decisions(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = []

        for value in values:
            decision = value.strip().upper()

            if not re.fullmatch(
                r"[A-Z][A-Z0-9_]*",
                decision,
            ):
                raise ValueError(
                    "Decision must contain only letters, "
                    "numbers, and underscores"
                )

            if len(decision) > 100:
                raise ValueError(
                    "Decision cannot exceed 100 characters"
                )

            normalized.append(decision)

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Duplicate decisions are not allowed"
            )

        return normalized

    @field_validator("input_mappings")
    @classmethod
    def validate_input_mappings(
        cls,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        for key in values:
            if not key.strip():
                raise ValueError(
                    "Input mapping names cannot be empty"
                )

        return values
