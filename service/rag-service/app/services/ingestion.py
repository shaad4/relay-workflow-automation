import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.parsers.document_processor import process_document
from app.storage.supabase_storage import SupabaseStorage
from app.embeddings.provider import EmbeddingProvider


logger = logging.getLogger(__name__)


class IngestionService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        self.storage = SupabaseStorage()
        self.embedding_provider = EmbeddingProvider()

    async def prepare_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[str]:
        """Download, parse, clean, and chunk a pending document."""

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

        content = await run_in_threadpool(
            self.storage.download,
            document.storage_path,
        )

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
            raise ValueError(
                "No chunks available for embedding"
            )

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
        """Save chunks for a pending document."""

        if not chunks or len(chunks) != len(embeddings):
            raise ValueError("Invalid chunks or embeddings")

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

    async def ingest_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> int:
        """Process a document with atomic ingestion claiming."""

        # 1. Find document within the workspace
        document = await self.document_repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if document is None:
            raise ValueError("Document not found")

        # 2. Skip already completed documents
        if document.status == "ready":
            return 0

        # 3. Atomically claim pending document
        try:
            claimed = await self.document_repository.claim_for_ingestion(
                document_id=document_id,
                workspace_id=workspace_id,
            )

            if not claimed:
                await self.db.rollback()
                logger.info(
                    "Skipping ingestion: document %s is not pending",
                    document_id,
                )
                return 0

            # Persist pending -> parsing
            await self.db.commit()

            # Refresh the ORM object after the SQL UPDATE
            await self.db.refresh(document)

        except Exception:
            await self.db.rollback()
            raise

        # 4. Process claimed document
        try:
            # Download original document from Supabase
            content = await run_in_threadpool(
                self.storage.download,
                document.storage_path,
            )

            # Parse, clean, and chunk
            chunks = await run_in_threadpool(
                process_document,
                content,
                document.content_type,
            )

            if not chunks:
                raise ValueError(
                    "Document produced no text chunks"
                )

            # 5. Update processing status
            await self.document_repository.update_status(
                document,
                "chunking",
            )
            await self.db.commit()

            # 6. Generate embeddings
            await self.document_repository.update_status(
                document,
                "embedding",
            )
            await self.db.commit()

            embeddings = await self.prepare_embeddings(chunks)

            # 7. Save chunks and mark ready in one transaction
            await self.chunk_repository.create_chunks(
                document_id=document_id,
                workspace_id=workspace_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            await self.document_repository.update_status(
                document,
                "ready",
                error_message=None,
            )

            await self.db.commit()

            logger.info(
                "Ingestion completed: document_id=%s chunks=%s",
                document_id,
                len(chunks),
            )

            return len(chunks)

        except Exception:
            await self.db.rollback()

            logger.exception(
                "Document ingestion failed: document_id=%s",
                document_id,
            )

            try:
                # Reload after rollback
                document = await self.document_repository.get_by_id(
                    document_id=document_id,
                    workspace_id=workspace_id,
                )

                if document is not None:
                    await self.document_repository.update_status(
                        document,
                        "failed",
                        error_message="Document ingestion failed",
                    )

                    await self.db.commit()

            except Exception:
                await self.db.rollback()

                logger.exception(
                    "Failed to update ingestion status: %s",
                    document_id,
                )

            raise
