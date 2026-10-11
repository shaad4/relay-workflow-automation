from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_identity
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
)
from app.services.knowledge_base import KnowledgeBaseService


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["Knowledge Bases"],
)


@router.post(
    "/",
    response_model=KnowledgeBaseResponse,
    status_code=201,
)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeBaseService(db)

    return await service.create(
        workspace_id=UUID(identity["workspace_id"]),
        data=data,
    )