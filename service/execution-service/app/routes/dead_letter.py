from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.repositories.dead_letter import DeadLetterRepository
from app.services.dead_letter import DeadLetterService
from app.schemas.dead_letter import DeadLetterListResponse

router = APIRouter(
    prefix="/dead-letter-events",
    tags=["Dead Letter Events"],
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/", response_model=DeadLetterListResponse)
async def list_dead_letter_events(
    status: str | None = Query(
        default=None,
        pattern="^(pending|replayed|resolved)$",
    ),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workspace_id = UUID(identity["workspace_id"])

    repository = DeadLetterRepository(session)
    service = DeadLetterService(repository)

    return await service.list_events(
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
        status=status,
    )
