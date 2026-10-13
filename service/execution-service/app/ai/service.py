
from app.ai.base import AIResponse
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.anthropic import AnthropicProvider


class AIService:

    def __init__(self):
        self.providers = {
            "openai": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "anthropic": AnthropicProvider(),
        }

    async def generate(
        self,
        provider: str,
        api_key: str,
        model: str,
        instructions: str,
        prompt: str,
    ) -> AIResponse:
        """Generate text using the selected LLM provider."""

        if not isinstance(provider, str):
            raise ValueError("AI provider is required")

        provider = provider.strip().lower()

        selected_provider = self.providers.get(provider)

        if selected_provider is None:
            raise ValueError(
                f"Unsupported AI provider: {provider}"
            )

        return await selected_provider.generate(
            api_key=api_key,
            model=model,
            instructions=instructions,
            prompt=prompt,
        )
