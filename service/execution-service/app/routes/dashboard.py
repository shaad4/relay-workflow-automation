from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity
from app.routes.executions import get_db
from app.schemas.dashboard import DashboardRange, DashboardSummary
from app.services.dashboard import get_dashboard_summary


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    range: DashboardRange = Query(default="7d"),
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await get_dashboard_summary(
            session,
            UUID(identity["workspace_id"]),
            UUID(identity["user_id"]),
            range,
        )

    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve dashboard summary",
        ) from exc
