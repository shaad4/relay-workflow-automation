from openai import AsyncOpenAI

from app.ai.base import AIProvider, AIResponse

from app.ai.config import AI_REQUEST_TIMEOUT_SECONDS

class OpenAIProvider(AIProvider):

    async def generate(
        self,
        api_key: str,
        model: str,
        instructions: str,
        prompt: str,
    ) -> AIResponse:
        """Generate text using OpenAI."""

        if not api_key or not api_key.strip():
            raise ValueError("OpenAI API key is required")

        if not model or not model.strip():
            raise ValueError("OpenAI model is required")

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        client = AsyncOpenAI(
            api_key=api_key,
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

        try:
            response = await client.responses.create(
                model=model,
                instructions=instructions,
                input=prompt,
            )

            if response.status != "completed":
                raise RuntimeError(
                    "OpenAI response was not completed"
                )

            content = response.output_text

            if not content or not content.strip():
                raise RuntimeError(
                    "OpenAI returned an empty response"
                )

            usage = response.usage

            return AIResponse(
                content=content,
                model=response.model,
                input_tokens=(
                    usage.input_tokens if usage else 0
                ),
                output_tokens=(
                    usage.output_tokens if usage else 0
                ),
            )

        finally:
            await client.close()
