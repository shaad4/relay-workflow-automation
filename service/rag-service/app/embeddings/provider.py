import os

from openai import AsyncOpenAI


class EmbeddingProvider:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            timeout=30.0,
            max_retries=2,
        )

        self.model = os.getenv(
            "EMBEDDING_MODEL",
            "text-embedding-3-small",
        )