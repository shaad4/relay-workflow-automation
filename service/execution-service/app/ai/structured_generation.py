
import json

from app.ai.service import AIService
from app.ai.schemas import (
    AIDecisionInput,
    AIDecisionOutput,
    validate_ai_decision,
)


class StructuredAIGeneration:

    def __init__(self):
        self.ai_service = AIService()

    async def generate_decision(
        self,
        provider: str,
        api_key: str,
        model: str,
        decision_input: AIDecisionInput,
    ) -> dict:
        """Generate and validate a generic AI decision."""

        instructions = (
            f"{decision_input.instructions}\n\n"
            "Return only a valid JSON object containing:\n"
            "- decision: one of the allowed decisions\n"
            "- reason: a clear explanation\n"
            "- data: an optional JSON object\n"
            "Do not include Markdown or code fences."
        )

        prompt = json.dumps(
            {
                "structured_data": decision_input.structured_data,
                "rag_context": decision_input.rag_context,
                "allowed_decisions": decision_input.allowed_decisions,
            },
            ensure_ascii=False,
        )

        response = await self.ai_service.generate(
            provider=provider,
            api_key=api_key,
            model=model,
            instructions=instructions,
            prompt=prompt,
        )

        try:
            output_data = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "AI provider returned invalid JSON"
            ) from exc

        output = AIDecisionOutput.model_validate(
            output_data
        )

        output = validate_ai_decision(
            output=output,
            allowed_decisions=decision_input.allowed_decisions,
        )

        return {
            "decision": output.decision,
            "reason": output.reason,
            "data": output.data,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        }
