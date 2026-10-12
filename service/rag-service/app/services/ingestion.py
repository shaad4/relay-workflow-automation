import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.repositories.document import DocumentRepository
from app.parsers.document_processor import process_document
from app.storage.supabase_storage import SupabaseStorage
from app.embeddings.provider import EmbeddingProvider
from app.repositories.document_chunk import DocumentChunkRepository


class IngestionService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.storage = SupabaseStorage()
        self.embedding_provider = EmbeddingProvider()
        self.chunk_repository = DocumentChunkRepository(db)

    async def prepare_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[str]:

        # 1. Retrieve document metadata
        document = await self.document_repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if document is None:
            raise ValueError("Document not found")

        if document.status != "pending":
            raise ValueError(
                "Document is not ready for ingestion"
            )

        # 2. Download original document
        content = await run_in_threadpool(
            self.storage.download,
            document.storage_path,
        )

        # 3. Parse, clean, and chunk
        chunks = await run_in_threadpool(
            process_document,
            content,
            document.content_type,
        )

        if not chunks:
            raise ValueError(
                "Document produced no text chunks"
            )

        return chunks


    async def prepare_embeddings(
        self,
        chunks: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for document chunks."""

        if not chunks:
            raise ValueError("No chunks available for embedding")

        embeddings = await self.embedding_provider.generate_embeddings(
            chunks
        )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embedding count does not match chunk count"
            )

        return embeddings


    async def save_chunks(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> int:
        """Persist document chunks and embeddings."""

        if not chunks or len(chunks) != len(embeddings):
            raise ValueError("Invalid chunks or embeddings")

        document = await self.document_repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if document is None:
            raise ValueError("Document not found")

        if document.status != "pending":
            raise ValueError("Document is not ready for ingestion")

        try:
            records = await self.chunk_repository.create_chunks(
                document_id=document_id,
                workspace_id=workspace_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            await self.db.commit()

            return len(records)

        except Exception:
            await self.db.rollback()
            raise