
from anthropic import AsyncAnthropic
from google import genai
from google.genai import types
from openai import AsyncOpenAI


async def list_provider_models(
    provider: str,
    api_key: str,
) -> list[dict]:
    """List models accessible through a provider connection."""

    if not api_key or not api_key.strip():
        raise ValueError("API key is required")

    models = []

    if provider == "openai":
        client = AsyncOpenAI(
            api_key=api_key,
            timeout=15.0,
            max_retries=0,
        )

        try:
            response = await client.models.list()

            models = [
                {
                    "id": model.id,
                    "name": model.id,
                }
                for model in response.data
            ]

        finally:
            await client.close()

    elif provider == "gemini":
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=15000,
            ),
        )

        try:
            async for model in await client.aio.models.list():
                model_id = model.name or ""

                if model_id.startswith("models/"):
                    model_id = model_id.removeprefix("models/")

                models.append({
                    "id": model_id,
                    "name": model.display_name or model_id,
                })

        finally:
            await client.aio.aclose()

    elif provider == "anthropic":
        client = AsyncAnthropic(
            api_key=api_key,
            timeout=15.0,
            max_retries=0,
        )

        try:
            response = await client.models.list()

            models = [
                {
                    "id": model.id,
                    "name": model.display_name or model.id,
                }
                for model in response.data
            ]

        finally:
            await client.close()

    else:
        raise ValueError("Unsupported AI provider")

    return sorted(
        models,
        key=lambda model: model["name"].lower(),
    )
