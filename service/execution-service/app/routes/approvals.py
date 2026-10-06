from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity
from app.db.database import AsyncSessionLocal
from app.schemas.approvals import ApprovalListResponse, ApprovalResponse
from app.services.approval_service import (
    list_pending_approvals,
    get_approval,
)


router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"],
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/", response_model=ApprovalListResponse)
async def get_approvals(
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    approvals = await list_pending_approvals(
        workspace_id=identity["workspace_id"],
        approver_user_id=identity["user_id"],
        session=session,
    )

    return ApprovalListResponse(
        approvals=[
            ApprovalResponse.model_validate(approval)
            for approval in approvals
        ]
    )


@router.get("/{approval_id}/", response_model=ApprovalResponse)
async def get_approval_details(
    approval_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    approval = await get_approval(
        approval_id=approval_id,
        workspace_id=identity["workspace_id"],
        approver_user_id=identity["user_id"],
        session=session,
    )

    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Approval not found",
        )

    return ApprovalResponse.model_validate(approval)