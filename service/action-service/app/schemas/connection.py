from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_AUTH_TYPES = {
    "none",
    "bearer",
    "api_key",
    "api_key_header",
    "api_key_query",
    "oauth2",
}


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=100)
    auth_type: str = Field(min_length=1, max_length=100)
    credential: str | None = None
    config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_authentication(self):
        if self.auth_type not in SUPPORTED_AUTH_TYPES:
            raise ValueError(
                f"Unsupported auth_type: {self.auth_type}"
            )

        if self.auth_type != "none" and not self.credential:
            raise ValueError(
                "credential is required for this authentication type"
            )

        if self.auth_type == "api_key_header":
            if not self.config or not self.config.get("auth_header"):
                raise ValueError(
                    "config.auth_header is required for api_key_header"
                )

        if self.auth_type == "api_key_query":
            if not self.config or not self.config.get("auth_param"):
                raise ValueError(
                    "config.auth_param is required for api_key_query"
                )

        return self


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    provider: str
    auth_type: str
    config: dict[str, Any] | None
    created_at: Any


class ConnectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    provider: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    auth_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    credential: str | None = None
    config: dict[str, Any] | None = None


class ConnectionTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    message: str
    response: Any | None = None