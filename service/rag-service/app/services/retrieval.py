import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.provider import EmbeddingProvider
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_provider = EmbeddingProvider()
        self.chunk_repository = DocumentChunkRepository(db)
        self.knowledge_base_repository = KnowledgeBaseRepository(db)

    async def retrieve(
        self,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:

        # 1. Validate query
        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        if len(query) > 2000:
            raise ValueError("Search query cannot exceed 2000 characters")

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        # 2. Verify knowledge base ownership
        knowledge_base = await self.knowledge_base_repository.get_by_id(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        if knowledge_base is None:
            raise ValueError("Knowledge base not found")

        # 3. Generate query embedding
        embeddings = await self.embedding_provider.generate_embeddings([query])

        query_embedding = embeddings[0]

        # 4. Search pgvector
        results = await self.chunk_repository.search_similar(
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # 5. Format retrieval results
        return [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": round(1.0 - distance, 4),
            }
            for chunk, distance in results
        ]
