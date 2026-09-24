from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.services.auth_service import register_user

router = APIRouter(prefix="/auth", tags=["Auth"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/register", response_model=RegisterResponse)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db)
):
    user = await register_user(data, session)
    return user