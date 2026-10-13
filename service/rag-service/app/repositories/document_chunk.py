import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chunks(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> list[DocumentChunk]:

        if not chunks or len(chunks) != len(embeddings):
            raise ValueError(
                "Chunks and embeddings must be non-empty and match"
            )

        if any(not chunk.strip() for chunk in chunks):
            raise ValueError("Chunks cannot contain empty text")

        if any(len(vector) != 1536 for vector in embeddings):
            raise ValueError("Embedding dimension must be 1536")

        records = [
            DocumentChunk(
                document_id=document_id,
                workspace_id=workspace_id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
            )
            for index, (chunk, embedding) in enumerate(
                zip(chunks, embeddings)
            )
        ]

        self.db.add_all(records)
        await self.db.flush()

        return records

    async def search_similar(
        self,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:

        if len(query_embedding) != 1536:
            raise ValueError("Query embedding must have 1536 dimensions")

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        distance = DocumentChunk.embedding.cosine_distance(
            query_embedding
        )

        statement = (
            select(DocumentChunk, distance.label("distance"))
            .join(
                Document,
                DocumentChunk.document_id == Document.id,
            )
            .where(
                DocumentChunk.workspace_id == workspace_id,
                Document.workspace_id == workspace_id,
                Document.knowledge_base_id == knowledge_base_id,
                Document.status == "ready",
            )
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.db.execute(statement)

        return [
            (chunk, float(distance_value))
            for chunk, distance_value in result.all()
        ]