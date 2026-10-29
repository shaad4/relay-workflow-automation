import asyncio
import logging
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.celery_app import celery_app
from app.services.ingestion import IngestionService

logger = logging.getLogger(__name__)


async def run_ingestion(
    document_id: UUID,
    workspace_id: UUID,
) -> int:
    """Run ingestion with an isolated async database engine."""

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as db:
            service = IngestionService(db)

            return await service.ingest_document(
                document_id=document_id,
                workspace_id=workspace_id,
            )

    finally:
        await engine.dispose()


@celery_app.task(
    name="rag.ingest_document",
    soft_time_limit=600,
    time_limit=660,
)
def ingest_document_task(
    document_id: str,
    workspace_id: str,
) -> int:
    """Celery entry point for document ingestion."""

    logger.info(
        "Starting document ingestion: %s",
        document_id,
    )

    chunk_count = asyncio.run(
        run_ingestion(
            document_id=UUID(document_id),
            workspace_id=UUID(workspace_id),
        )
    )

    logger.info(
        "Document ingestion completed: %s, chunks=%s",
        document_id,
        chunk_count,
    )

    return chunk_count
