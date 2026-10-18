from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManualRunRequest(BaseModel):
    """Input supplied when manually starting a workflow."""

    model_config = ConfigDict(extra="forbid")

    input: dict[str, Any] = Field(
        default_factory=dict
    )