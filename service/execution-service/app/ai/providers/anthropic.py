
from anthropic import AsyncAnthropic

from app.ai.base import AIProvider, AIResponse

from app.ai.config import AI_REQUEST_TIMEOUT_SECONDS


class AnthropicProvider(AIProvider):

    async def generate(
        self,
        api_key: str,
        model: str,
        instructions: str,
        prompt: str,
    ) -> AIResponse:
        """Generate text using Anthropic Claude."""

        if not api_key or not api_key.strip():
            raise ValueError(
                "Anthropic API key is required"
            )

        if not model or not model.strip():
            raise ValueError(
                "Anthropic model is required"
            )

        if not prompt or not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty"
            )

        client = AsyncAnthropic(
            api_key=api_key,
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                system=instructions or "You are a helpful assistant.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            if response.stop_reason not in {
                "end_turn",
                "stop_sequence",
            }:
                raise RuntimeError(
                    "Claude response did not complete normally"
                )

            content = "\n".join(
                block.text
                for block in response.content
                if block.type == "text"
            )

            if not content.strip():
                raise RuntimeError(
                    "Claude returned an empty response"
                )

            usage = response.usage

            return AIResponse(
                content=content,
                model=response.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )

        finally:
            await client.close()
