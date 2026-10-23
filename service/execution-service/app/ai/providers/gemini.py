
from google import genai
from google.genai import types

from app.ai.base import AIProvider, AIResponse

from app.ai.config import AI_REQUEST_TIMEOUT_SECONDS


class GeminiProvider(AIProvider):

    async def generate(
        self,
        api_key: str,
        model: str,
        instructions: str,
        prompt: str,
    ) -> AIResponse:
        """Generate text using Google Gemini."""

        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key is required")

        if not model or not model.strip():
            raise ValueError("Gemini model is required")

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=AI_REQUEST_TIMEOUT_SECONDS * 1000,
            ),
        )

        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instructions or None,
                    temperature=0.2,
                ),
            )

            content = response.text

            if not content or not content.strip():
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            usage = response.usage_metadata

            return AIResponse(
                content=content,
                model=model,
                input_tokens=(
                    usage.prompt_token_count or 0
                    if usage else 0
                ),
                output_tokens=(
                    usage.candidates_token_count or 0
                    if usage else 0
                ),
            )

        finally:
            await client.aio.aclose()
