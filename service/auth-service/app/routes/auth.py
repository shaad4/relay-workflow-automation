from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import login_user, refresh_access_token, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/register", response_model=RegisterResponse)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db)
):
    try:
        user = await register_user(data, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )
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

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    data: RefreshTokenRequest
):
    try:
        access_token = await refresh_access_token(data.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        )

    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer",
    )