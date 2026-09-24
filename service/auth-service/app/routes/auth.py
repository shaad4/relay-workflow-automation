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
from app.services.email_verification_service import verify_email_token
from app.core.dependencies import get_current_user
from app.models import User

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
    try:
        access_token, refresh_token = await login_user(data, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        )

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

@router.get("/me", response_model=RegisterResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
):
    return {
        "message": "Logged out successfully"
    }

@router.get("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_db)
):
    try:
        await verify_email_token(token, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {
        "message": "Email verified successfully",
    }