import asyncio

from anthropic import (
    AuthenticationError as AnthropicAuthenticationError,
    RateLimitError as AnthropicRateLimitError,
    APITimeoutError as AnthropicTimeoutError,
    APIConnectionError as AnthropicConnectionError,
    APIStatusError as AnthropicStatusError,
)
from openai import (
    AuthenticationError as OpenAIAuthenticationError,
    RateLimitError as OpenAIRateLimitError,
    APITimeoutError as OpenAITimeoutError,
    APIConnectionError as OpenAIConnectionError,
    APIStatusError as OpenAIStatusError,
)
from google.genai import errors as gemini_errors

from app.ai.base import AIResponse
from app.ai.exceptions import (
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIResponseError,
)
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
        if not isinstance(provider, str):
            raise ValueError("AI provider is required")

        provider = provider.strip().lower()
        selected_provider = self.providers.get(provider)

        if selected_provider is None:
            raise ValueError("Unsupported AI provider")

        try:
            return await selected_provider.generate(
                api_key=api_key,
                model=model,
                instructions=instructions,
                prompt=prompt,
            )

        except (
            OpenAIAuthenticationError,
            AnthropicAuthenticationError,
        ) as exc:
            raise AIAuthenticationError(
                "AI provider authentication failed"
            ) from exc

        except (
            OpenAIRateLimitError,
            AnthropicRateLimitError,
        ) as exc:
            raise AIRateLimitError(
                "AI provider rate limit or quota exceeded"
            ) from exc

        except (
            OpenAITimeoutError,
            AnthropicTimeoutError,
            asyncio.TimeoutError,
        ) as exc:
            raise AITimeoutError(
                "AI provider request timed out"
            ) from exc

        except (
            OpenAIConnectionError,
            AnthropicConnectionError,
        ) as exc:
            raise AIServiceUnavailableError(
                "AI provider connection failed"
            ) from exc

        except (
            OpenAIStatusError,
            AnthropicStatusError,
        ) as exc:
            if exc.status_code in {401, 403}:
                raise AIAuthenticationError(
                    "AI provider access denied"
                ) from exc

            if exc.status_code == 429:
                raise AIRateLimitError(
                    "AI provider rate limit exceeded"
                ) from exc

            if exc.status_code in {408, 504}:
                raise AITimeoutError(
                    "AI provider request timed out"
                ) from exc

            raise AIServiceUnavailableError(
                "AI provider request failed"
            ) from exc

        except (
            gemini_errors.ClientError,
            gemini_errors.ServerError,
        ) as exc:
            status_code = getattr(exc, "code", None)

            if status_code in {401, 403}:
                raise AIAuthenticationError(
                    "Gemini authentication failed"
                ) from exc

            if status_code == 429:
                raise AIRateLimitError(
                    "Gemini rate limit exceeded"
                ) from exc

            if status_code in {408, 504}:
                raise AITimeoutError(
                    "Gemini request timed out"
                ) from exc

            raise AIServiceUnavailableError(
                "Gemini request failed"
            ) from exc

        except RuntimeError as exc:
            raise AIResponseError(
                "AI provider returned an invalid response"
            ) from exc
