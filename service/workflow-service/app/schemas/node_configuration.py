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

        legacy_id = data.pop("knowledge_base", None)
        current_id = data.get("knowledge_base_id")

        if legacy_id is not None:
            if (
                current_id is not None
                and str(current_id) != str(legacy_id)
            ):
                raise ValueError(
                    "Conflicting knowledge base identifiers"
                )

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
