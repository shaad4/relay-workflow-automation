
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class AIProviderConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    provider: str
    api_key: str = Field(min_length=1)

    @field_validator("name", "api_key")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in {"openai", "gemini", "anthropic"}:
            raise ValueError("Unsupported AI provider")

        return value


class AIProviderConnectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, min_length=1)
    status: str | None = None

    @field_validator("name", "api_key")
    @classmethod
    def validate_optional_text(cls, value: str | None):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Field cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None):
        if value is not None:
            value = value.strip().lower()
            if value not in {"active", "inactive"}:
                raise ValueError("Invalid connection status")
        return value


class AIProviderConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider: str
    status: str
    created_at: datetime
    updated_at: datetime
