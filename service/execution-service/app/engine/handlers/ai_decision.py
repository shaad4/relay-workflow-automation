from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import AIDecisionInput
from app.ai.structured_generation import StructuredAIGeneration
from app.services.ai_provider_connection import (
    AIProviderConnectionService,
)
from app.ai.input_validation import validate_resolved_ai_inputs


async def execute_ai_decision(
    configuration: dict,
    workspace_id: str,
    session: AsyncSession,
) -> dict:
    """Execute a generic AI Decision node."""

    if not isinstance(configuration, dict):
        raise ValueError("Invalid AI Decision configuration")

    try:
        connection_id = UUID(
            str(configuration["connection_id"])
        )

        workspace_uuid = UUID(workspace_id)

    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(
            "Invalid AI connection or workspace ID"
        ) from exc

    model = configuration.get("model")
    instructions = configuration.get("instructions")
    input_mappings = configuration.get(
        "input_mappings", {}
    )
    rag_context = configuration.get(
        "rag_context", ""
    )
    allowed_decisions = configuration.get(
        "allowed_decisions"
    )

    if not isinstance(model, str) or not model.strip():
        raise ValueError("AI model is required")

    if not isinstance(input_mappings, dict):
        raise ValueError("Invalid AI input mappings")

    if not isinstance(rag_context, str):
        raise ValueError("Invalid RAG context")

    validate_resolved_ai_inputs(
        input_mappings=input_mappings,
        rag_context=rag_context,
    )

    try:
        decision_input = AIDecisionInput(
            structured_data=input_mappings,
            rag_context=rag_context,
            instructions=instructions,
            allowed_decisions=allowed_decisions,
        )

    except ValidationError as exc:
        raise ValueError(
            "Invalid AI Decision input configuration"
        ) from exc

    connection_service = AIProviderConnectionService(
        session
    )

    provider, api_key = (
        await connection_service.get_execution_credentials(
            connection_id=connection_id,
            workspace_id=workspace_uuid,
        )
    )

    generator = StructuredAIGeneration()

    result = await generator.generate_decision(
        provider=provider,
        api_key=api_key,
        model=model.strip(),
        decision_input=decision_input,
    )

    return result
