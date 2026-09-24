from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import login_user, register_user

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


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    access_token, refresh_token = await login_user(data, session)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )