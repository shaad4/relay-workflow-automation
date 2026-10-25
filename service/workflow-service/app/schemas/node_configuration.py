import re
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    field_validator,
    model_validator,
)


def validate_required_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Field cannot be empty")
    return value


def is_expression(value: Any) -> bool:
    return isinstance(value, str) and bool(re.search(r"\{\{\s*[^{}\s]+.*?\}\}", value))


def validate_runtime_value(value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
    """Defer expression values until the executor has resolved their inputs."""
    return value if is_expression(value) else handler(value)


RequiredText = Annotated[str, AfterValidator(validate_required_text)]
RuntimeUUID = Annotated[UUID, WrapValidator(validate_runtime_value)]


class WebhookTriggerConfig(BaseModel):
    # Endpoints live in Integration Service. Older nodes have {} or method/path.
    model_config = ConfigDict(extra="allow")

    webhook_id: UUID | None = None
    method: Literal["POST"] = "POST"
    path: str | None = None


class HttpRequestConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    connection_id: RuntimeUUID
    url: RequiredText
    method: str = "GET"
    timeout: Annotated[
        float, Field(strict=True, ge=1, le=120), WrapValidator(validate_runtime_value)
    ] = 10
    headers: dict[str, str] | list[tuple[str, str]] | str | None = None
    params: Annotated[
        dict[str, Any] | str | list[tuple[str, Any]] | None,
        WrapValidator(validate_runtime_value),
    ] = None
    body: Any = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        # HTTPX also accepts HEAD, OPTIONS and extension methods.
        if not is_expression(value) and not re.fullmatch(
            r"[!#$%&'*+.^_`|~0-9A-Za-z-]+",
            value,
        ):
            raise ValueError("HTTP method must be a valid HTTP token")
        return value


class EmailConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    connection_id: RuntimeUUID
    to: RequiredText
    subject: RequiredText
    body: RequiredText
    body_format: Annotated[Literal["plain", "html"], WrapValidator(validate_runtime_value)] = (
        "plain"
    )


class RefundConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    connection_id: RuntimeUUID
    # The selected connector determines the payment identifier format.
    payment_id: RequiredText
    amount: StrictStr | StrictInt | StrictFloat
    reason: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str | int | float) -> str | int | float:
        if is_expression(value):
            return value
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError("Refund amount must be a valid number")
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Refund amount must be greater than zero")
        return value


class HumanApprovalConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    # The executor reads these two fields before expression resolution.
    approver_user_id: UUID
    timeout_minutes: int | None = None
    message: RequiredText

    @field_validator("timeout_minutes", mode="before")
    @classmethod
    def validate_timeout(cls, value: Any) -> int | None:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("Timeout must be a positive whole number of minutes")
        try:
            minutes = int(value)
        except ValueError:
            raise ValueError("Timeout must be a positive whole number of minutes")
        if minutes <= 0:
            raise ValueError("Timeout must be a positive whole number of minutes")
        return minutes


class RagSearchConfig(BaseModel):
    """Configuration schema for the RAG Search node."""

    model_config = ConfigDict(extra="forbid")

    knowledge_base_id: RuntimeUUID

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    top_k: Annotated[
        int, Field(ge=1, le=20, strict=True), WrapValidator(validate_runtime_value)
    ] = 5

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
            raise ValueError("RAG query cannot be empty")

        return value


class AIDecisionConfig(BaseModel):
    """Configuration for a generic AI Decision node."""

    model_config = ConfigDict(extra="forbid")

    connection_id: RuntimeUUID

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
            if is_expression(value):
                normalized.append(value)
                continue
            decision = value.strip().upper()

            if not re.fullmatch(
                r"[A-Z][A-Z0-9_]*",
                decision,
            ):
                raise ValueError("Decision must contain only letters, numbers, and underscores")

            if len(decision) > 100:
                raise ValueError("Decision cannot exceed 100 characters")

            normalized.append(decision)

        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate decisions are not allowed")

        return normalized

    @field_validator("input_mappings")
    @classmethod
    def validate_input_mappings(
        cls,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        for key in values:
            if not key.strip():
                raise ValueError("Input mapping names cannot be empty")

        return values

    @field_validator("input_mappings", "allowed_decisions", mode="wrap")
    @classmethod
    def validate_runtime_inputs(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        return validate_runtime_value(value, handler)


class AIGenerateConfig(BaseModel):
    """Configuration for a generic AI Generate node."""

    model_config = ConfigDict(extra="forbid")

    connection_id: RuntimeUUID

    model: str = Field(
        min_length=1,
        max_length=150,
    )

    instructions: str = Field(
        default="",
        max_length=10000,
    )

    prompt: str = Field(
        min_length=1,
        max_length=10000,
    )

    rag_context: str = Field(
        default="",
        max_length=2000,
    )

    @field_validator("model", "instructions", "prompt")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()

        if not value and cls.__name__ == "AIGenerateConfig":
            # Instructions may be empty, but model and
            # prompt must be checked separately.
            return value

        return value

    @field_validator("model", "prompt")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("Field cannot be empty")

        return value


class ConditionConfig(BaseModel):
    """Configuration for exact-value branch routing."""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Condition value cannot be empty")

        return value


class ManualTriggerConfig(BaseModel):
    """Configuration for a manual workflow trigger."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        default="",
        max_length=500,
    )

    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})

    @field_validator("input_schema")
    @classmethod
    def validate_input_schema(
        cls,
        value: dict[str, Any],
    ) -> dict[str, Any]:

        if value != {"type": "object"}:
            raise ValueError("Manual Trigger MVP supports only an unrestricted JSON object schema")

        return value


class ScheduledTriggerConfig(BaseModel):
    """Configuration for a scheduled workflow trigger."""

    model_config = ConfigDict(extra="forbid")

    schedule_type: Literal["interval", "cron"]

    interval_minutes: int | None = Field(
        default=None,
        ge=1,
        le=10080,
        strict=True,
    )

    cron_expression: str | None = Field(
        default=None,
        max_length=100,
    )

    timezone: str = Field(
        default="UTC",
        max_length=100,
    )

    enabled: bool = True

    @model_validator(mode="after")
    def validate_schedule(self):
        # Validate timezone
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Invalid timezone")

        if self.schedule_type == "interval":
            if self.interval_minutes is None:
                raise ValueError("interval_minutes is required")

            if self.cron_expression is not None:
                raise ValueError("cron_expression is not allowed for interval")

        if self.schedule_type == "cron":
            if self.interval_minutes is not None:
                raise ValueError("interval_minutes is not allowed for cron")

            if not self.cron_expression:
                raise ValueError("cron_expression is required")

            if not croniter.is_valid(self.cron_expression):
                raise ValueError("Invalid cron expression")

        return self
