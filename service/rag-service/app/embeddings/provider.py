import os

from openai import AsyncOpenAI


class EmbeddingProvider:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            timeout=8.0,
            max_retries=1,
        )

        self.model = os.getenv(
            "EMBEDDING_MODEL",
            "text-embedding-3-small",
        )

    async def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            raise ValueError("No texts provided for embedding")

        if any(not text or not text.strip() for text in texts):
            raise ValueError("Embedding input contains empty text")

        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )

        embeddings = [
            item.embedding
            for item in sorted(
                response.data,
                key=lambda item: item.index,
            )
        ]

        if len(embeddings) != len(texts):
            raise ValueError("Embedding response count mismatch")

        if any(len(vector) != 1536 for vector in embeddings):
            raise ValueError("Invalid embedding dimensions")

        return embeddings