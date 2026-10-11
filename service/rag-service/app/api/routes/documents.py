from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_identity
from app.schemas.document import DocumentResponse
from app.services.document import DocumentService


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

    return await service.upload_document(
        file=file,
        workspace_id=UUID(identity["workspace_id"]),
        knowledge_base_id=knowledge_base_id,
    )