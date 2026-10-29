from uuid import UUID

from app.dependencies import get_current_identity
from app.models.workflow import Workflow
from app.routes.workflows import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class WorkflowSummary(BaseModel):
    total_workflows: int
    active_workflows: int


@router.get("/summary", response_model=WorkflowSummary)
async def summary(
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        row = (
            await session.execute(
                select(
                    func.count(Workflow.id),
                    func.count(Workflow.id).filter(Workflow.status == "active"),
                ).where(Workflow.workspace_id == UUID(identity["workspace_id"]))
            )
        ).one()

        return {
            "total_workflows": row[0],
            "active_workflows": row[1],
        }

    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve workflow summary",
        ) from exc
