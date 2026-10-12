import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.tasks.ingestion import ingest_document_task
from starlette.concurrency import run_in_threadpool

from app.db.database import get_db
from app.dependencies import get_current_identity
from app.schemas.document import DocumentResponse
from app.services.document import DocumentService

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["Documents"],
)



@router.post(
    "/{knowledge_base_id}/documents/",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)

    workspace_id = UUID(identity["workspace_id"])

    # 1. Upload to Supabase and save document metadata
    document = await service.upload_document(
        file=file,
        workspace_id=workspace_id,
        knowledge_base_id=knowledge_base_id,
    )

    # 2. Queue ingestion after successful upload
    try:
        await run_in_threadpool(
            ingest_document_task.delay,
            str(document.id),
            str(workspace_id),
        )

    except Exception:
        logger.exception(
            "Failed to queue document ingestion: %s",
            document.id,
        )

        # The document remains pending for retry.
        # Never report that ingestion was queued successfully.
        raise HTTPException(
            status_code=503,
            detail=(
                "Document uploaded successfully, "
                "but ingestion could not be queued"
            ),
        )

    # 3. Return pending document
    return document

