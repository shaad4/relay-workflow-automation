import logging
import uuid

from app.db.database import AsyncSessionLocal
from app.services.ingestion import IngestionService


logger = logging.getLogger(__name__)


async def process_document_task(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """Process an uploaded document in the background."""

    try:
        async with AsyncSessionLocal() as db:
            service = IngestionService(db)

            chunk_count = await service.ingest_document(
                document_id=document_id,
                workspace_id=workspace_id,
            )

            logger.info(
                "Document ingestion completed: document_id=%s chunks=%s",
                document_id,
                chunk_count,
            )

    except Exception:
        logger.exception(
            "Document ingestion failed: document_id=%s",
            document_id,
        )
