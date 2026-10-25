from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_identity
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
)
from app.schemas.search import SearchRequest, SearchResponse
from app.services.knowledge_base import KnowledgeBaseService
from app.services.retrieval import RetrievalService

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


@router.delete(
    "/{knowledge_base_id}/",
    status_code=204,
)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeBaseService(db)

    deleted = await service.delete(
        knowledge_base_id=knowledge_base_id,
        workspace_id=UUID(identity["workspace_id"]),
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    return None


@router.post(
    "/{knowledge_base_id}/search/",
    response_model=SearchResponse,
)
async def search_knowledge_base(
    knowledge_base_id: UUID,
    data: SearchRequest,
    identity: dict = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    service = RetrievalService(db)

    # Validate query before calling the embedding API
    query = data.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Search query cannot be empty",
        )

    # Verify knowledge base ownership
    knowledge_base = await service.knowledge_base_repository.get_by_id(
        knowledge_base_id=knowledge_base_id,
        workspace_id=UUID(identity["workspace_id"]),
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    results = await service.retrieve(
        workspace_id=UUID(identity["workspace_id"]),
        knowledge_base_id=knowledge_base_id,
        query=query,
        top_k=data.top_k,
    )

    return SearchResponse(
        knowledge_base_id=knowledge_base_id,
        query=query,
        results=results,
    )
