from anthropic import AsyncAnthropic
from google import genai
from google.genai import types
from openai import AsyncOpenAI


async def test_ai_provider_connection(
    provider: str,
    api_key: str,
) -> bool:
    """Verify AI provider credentials without generating text."""

    if not api_key or not api_key.strip():
        raise ValueError("API key is required")

    if provider == "openai":
        client = AsyncOpenAI(
            api_key=api_key,
            timeout=10.0,
            max_retries=0,
        )

        try:
            await client.models.list()
            return True
        finally:
            await client.close()

    if provider == "gemini":
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=10000,
            ),
        )

        try:
            async for _ in await client.aio.models.list(config={"page_size": 1}):
                break

            return True
        finally:
            await client.aio.aclose()

    if provider == "anthropic":
        client = AsyncAnthropic(
            api_key=api_key,
            timeout=10.0,
            max_retries=0,
        )

        try:
            await client.models.list(limit=1)
            return True
        finally:
            await client.close()

    raise ValueError("Unsupported AI provider")
