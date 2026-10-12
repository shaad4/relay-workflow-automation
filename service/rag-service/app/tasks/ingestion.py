import asyncio
import logging
from uuid import UUID

from app.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.services.ingestion import IngestionService


logger = logging.getLogger(__name__)


async def run_ingestion(
    document_id: UUID,
    workspace_id: UUID,
) -> int:
    """Run document ingestion using a fresh DB session."""

    async with AsyncSessionLocal() as db:
        service = IngestionService(db)

        return await service.ingest_document(
            document_id=document_id,
            workspace_id=workspace_id,
        )


@celery_app.task(
    name="rag.ingest_document",
)
def ingest_document_task(
    document_id: str,
    workspace_id: str,
) -> int:
    """Celery entry point for document ingestion."""

    document_uuid = UUID(document_id)
    workspace_uuid = UUID(workspace_id)

    logger.info(
        "Starting document ingestion: %s",
        document_id,
    )

    chunk_count = asyncio.run(
        run_ingestion(
            document_id=document_uuid,
            workspace_id=workspace_uuid,
        )
    )

    logger.info(
        "Document ingestion completed: %s, chunks=%s",
        document_id,
        chunk_count,
    )

    return chunk_count
