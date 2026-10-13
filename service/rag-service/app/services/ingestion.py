
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.embeddings.provider import EmbeddingProvider
from app.parsers.document_processor import process_document
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.storage.supabase_storage import SupabaseStorage


logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        self.storage = SupabaseStorage()
        self.embedding_provider = EmbeddingProvider()

    async def prepare_embeddings(
        self,
        chunks: list[str],
    ) -> list[list[float]]:
        """Generate and validate embeddings for document chunks."""

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

    async def ingest_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> int:
        """Ingest a document with atomic status transitions."""

        # 1. Retrieve document within the workspace
        document = await self.document_repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if document is None:
            raise ValueError("Document not found")

        # 2. Skip already processed documents
        if document.status == "ready":
            logger.info(
                "Document already ingested: %s",
                document_id,
            )
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

            # Synchronize ORM state
            await self.db.refresh(document)

        except Exception:
            await self.db.rollback()
            raise

        # 4. Process the claimed document
        try:
            # Download original document from Supabase
            content = await run_in_threadpool(
                self.storage.download,
                document.storage_path,
            )

            # Parse, clean and chunk
            chunks = await run_in_threadpool(
                process_document,
                content,
                document.content_type,
            )

            if not chunks:
                raise ValueError(
                    "Document produced no text chunks"
                )

            # 5. Transition parsing -> chunking
            transitioned = await (
                self.document_repository.transition_ingestion_status(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    expected_status="parsing",
                    new_status="chunking",
                )
            )

            if not transitioned:
                raise RuntimeError(
                    "Document ingestion state changed during chunking"
                )

            await self.db.commit()

            # 6. Transition chunking -> embedding
            transitioned = await (
                self.document_repository.transition_ingestion_status(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    expected_status="chunking",
                    new_status="embedding",
                )
            )

            if not transitioned:
                raise RuntimeError(
                    "Document ingestion state changed during embedding"
                )

            await self.db.commit()

            # 7. Generate embeddings
            embeddings = await self.prepare_embeddings(chunks)

            # 8. Persist chunks and mark ready atomically
            await self.chunk_repository.create_chunks(
                document_id=document_id,
                workspace_id=workspace_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            completed = await self.document_repository.complete_ingestion(
                document_id=document_id,
                workspace_id=workspace_id,
            )

            if not completed:
                raise RuntimeError(
                    "Document ingestion state changed during completion"
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

            # Mark failed only if document is still processing
            try:
                failed = await self.document_repository.fail_ingestion(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    error_message="Document ingestion failed",
                )

                await self.db.commit()

                if not failed:
                    logger.warning(
                        "Document %s was not marked failed "
                        "because its status already changed",
                        document_id,
                    )

            except Exception:
                await self.db.rollback()

                logger.exception(
                    "Failed to persist ingestion failure: %s",
                    document_id,
                )

            raise
