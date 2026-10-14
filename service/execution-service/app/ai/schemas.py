
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class AIDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structured_data: dict[str, Any]

    rag_context: str = ""

    instructions: str = Field(
        min_length=1,
        max_length=10000,
    )

    allowed_decisions: list[str] = Field(
        min_length=2,
        max_length=20,
    )

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "AI instructions cannot be empty"
            )

        return value

    @field_validator("allowed_decisions")
    @classmethod
    def validate_allowed_decisions(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = [
            value.strip().upper()
            for value in values
        ]

        if any(not value for value in normalized):
            raise ValueError(
                "Decision values cannot be empty"
            )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Duplicate decision values are not allowed"
            )

        return normalized


class AIDecisionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(
        min_length=1,
        max_length=100,
    )

    reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError(
                "AI decision cannot be empty"
            )

        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "AI decision reason cannot be empty"
            )

        return value


def validate_ai_decision(
    output: AIDecisionOutput,
    allowed_decisions: list[str],
) -> AIDecisionOutput:
    """Validate an AI decision against configured outcomes."""

    allowed = {
        decision.strip().upper()
        for decision in allowed_decisions
    }

    if output.decision not in allowed:
        raise ValueError(
            "AI returned a decision that is not allowed"
        )

    return output
