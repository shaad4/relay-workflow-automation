from pydantic import BaseModel

from app.schemas.node_configuration import (
    AIDecisionConfig,
    AIGenerateConfig,
    ConditionConfig,
    EmailConfig,
    HttpRequestConfig,
    HumanApprovalConfig,
    ManualTriggerConfig,
    RagSearchConfig,
    RefundConfig,
    ScheduledTriggerConfig,
    WebhookTriggerConfig,
)

# Keep schema, public error code, and display name together for each node type.
NODE_VALIDATORS: dict[str, tuple[type[BaseModel], str, str]] = {
    "trigger.webhook": (
        WebhookTriggerConfig,
        "INVALID_WEBHOOK_CONFIGURATION",
        "Webhook Trigger",
    ),
    "trigger.manual": (
        ManualTriggerConfig,
        "INVALID_MANUAL_TRIGGER_CONFIGURATION",
        "Manual Trigger",
    ),
    "trigger.schedule": (
        ScheduledTriggerConfig,
        "INVALID_SCHEDULE_CONFIGURATION",
        "Scheduled Trigger",
    ),
    "action.http_request": (
        HttpRequestConfig,
        "INVALID_HTTP_CONFIGURATION",
        "HTTP Request",
    ),
    "action.email": (
        EmailConfig,
        "INVALID_EMAIL_CONFIGURATION",
        "Send Email",
    ),
    "action.refund": (
        RefundConfig,
        "INVALID_REFUND_CONFIGURATION",
        "Refund Payment",
    ),
    "human.approval": (
        HumanApprovalConfig,
        "INVALID_APPROVAL_CONFIGURATION",
        "Human Approval",
    ),
    "ai.rag_search": (
        RagSearchConfig,
        "INVALID_RAG_CONFIGURATION",
        "RAG Search",
    ),
    "ai.decision": (
        AIDecisionConfig,
        "INVALID_AI_DECISION_CONFIGURATION",
        "AI Decision",
    ),
    "ai.generate": (
        AIGenerateConfig,
        "INVALID_AI_GENERATE_CONFIGURATION",
        "AI Generate",
    ),
    "logic.condition": (
        ConditionConfig,
        "INVALID_CONDITION_CONFIGURATION",
        "Condition",
    ),
}
TRIGGER_TYPES = {"trigger.webhook", "trigger.manual", "trigger.schedule"}
