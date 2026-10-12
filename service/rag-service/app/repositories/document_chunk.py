import uuid

from sqlalchemy.ext.asyncio import AsyncSession

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