from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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


@router.get(
    "/",
    response_model=list[KnowledgeBaseResponse],
)
async def list_knowledge_bases(
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeBaseService(db)

    return await service.list_by_workspace(
        workspace_id=UUID(identity["workspace_id"]),
    )


@router.get(
    "/{knowledge_base_id}/",
    response_model=KnowledgeBaseResponse,
)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeBaseService(db)

    knowledge_base = await service.get_by_id(
        knowledge_base_id=knowledge_base_id,
        workspace_id=UUID(identity["workspace_id"]),
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    return knowledge_base