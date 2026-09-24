from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
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
from app.core.exceptions import EmailVerificationRequired
from app.services.email_service import send_verification_email
from app.core.dependencies import get_current_user
from app.models import User
from app.services.email_verification_service import (
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/register", response_model=RegisterResponse)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    try:
        user, verification_token = await register_user(data, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.name,
        verification_token.token,
        VERIFICATION_TOKEN_EXPIRE_MINUTES,
    )

    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    try:
        access_token, refresh_token = await login_user(
            data,
            session,
        )

    except EmailVerificationRequired as exc:

        background_tasks.add_task(
            send_verification_email,
            exc.user_email,
            exc.user_name,
            exc.token,
            VERIFICATION_TOKEN_EXPIRE_MINUTES,
        )

        print("Background task added")

        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            background=background_tasks,
        )

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