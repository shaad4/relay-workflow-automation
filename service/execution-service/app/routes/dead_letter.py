from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.repositories.dead_letter import DeadLetterRepository
from app.services.dead_letter import DeadLetterService
from app.schemas.dead_letter import DeadLetterListResponse, DeadLetterEventResponse

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



@router.get(
    "/{event_id}/",
    response_model=DeadLetterEventResponse,
)
async def get_dead_letter_event(
    event_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workspace_id = UUID(identity["workspace_id"])

    repository = DeadLetterRepository(session)
    service = DeadLetterService(repository)

    event = await service.get_event(
        event_id=event_id,
        workspace_id=workspace_id,
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Dead-letter event not found",
        )

    return event



@router.post("/{event_id}/resolve/")
async def resolve_dead_letter_event(
    event_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workspace_id = UUID(identity["workspace_id"])

    repository = DeadLetterRepository(session)
    service = DeadLetterService(repository)

    result = await service.resolve_event(
        event_id=event_id,
        workspace_id=workspace_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Pending dead-letter event not found",
        )

    return result




@router.post("/{event_id}/replay/", status_code=202)
async def replay_dead_letter_event(
    event_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workspace_id = UUID(identity["workspace_id"])

    repository = DeadLetterRepository(session)
    service = DeadLetterService(repository)

    try:
        return await service.replay_event(
            event_id=event_id,
            workspace_id=workspace_id,
        )

    except ValueError as exc:
        error = str(exc)

        if error == "not_found":
            raise HTTPException(
                status_code=404,
                detail="Dead-letter event not found",
            ) from exc

        if error == "already_handled":
            raise HTTPException(
                status_code=409,
                detail="Dead-letter event already handled",
            ) from exc

        raise HTTPException(
            status_code=422,
            detail="Execution is not eligible for safe replay",
        ) from exc
