import os

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import EmailVerificationRequired
from app.db.database import AsyncSessionLocal
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleLoginExchangeRequest,
    GoogleLoginExchangeResponse,
    GoogleSignupCompleteRequest,
    GoogleSignupCompleteResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.auth_service import login_user, refresh_access_token, register_user
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)
from app.services.email_verification_service import (
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
    resend_verification_email,
    verify_email_token,
)
from app.services.google_login import (
    consume_google_login_session,
    create_google_login_session,
)
from app.services.google_oauth import (
    create_google_authorization_url,
    exchange_google_code,
    find_google_user,
    get_google_userinfo,
)
from app.services.google_signup import (
    complete_google_signup,
    create_google_signup_session,
)
from app.services.password_reset_service import (
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    create_password_reset_token,
    reset_password,
)

load_dotenv()

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


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
)
async def resend_verification(
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    result = await resend_verification_email(
        data.email,
        session,
    )

    if result is not None:
        verification_token, user = result

        background_tasks.add_task(
            send_verification_email,
            user.email,
            user.name,
            verification_token.token,
            VERIFICATION_TOKEN_EXPIRE_MINUTES,
        )

    return ResendVerificationResponse(
        message=(
            "If an account with that email exists, "
            "a verification email has been sent."
        )
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    result = await create_password_reset_token(
        data.email,
        session,
    )

    if result is not None:
        token, user = result

        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.name,
            token.token,
            PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )


    return ForgotPasswordResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password_route(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        await reset_password(
            token=data.token,
            new_password=data.new_password,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return ResetPasswordResponse(
        message="Password reset successfully",
    )

@router.get("/google")
async def google_login():
    authorization_url, state = create_google_authorization_url()

    response = RedirectResponse(url=authorization_url)

    response.set_cookie(
        key="google_oauth_state",
        value=state,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,
        path="/auth/google",
    )

    return response

@router.get("/google/callback")
async def google_callback(
    state: str = Query(...),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    google_oauth_state: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_db),
):
    if not google_oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth state is missing",
        )

    if state != google_oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid Google OAuth state",
        )

    if error:
        frontend_url = os.getenv("FRONTEND_URL")

        if not frontend_url:
            raise RuntimeError(
                "FRONTEND_URL is not configured"
            )

        return RedirectResponse(
            url=f"{frontend_url}/login"
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Google authorization code is missing",
        )


    google_tokens = await exchange_google_code(code)

    google_user = await get_google_userinfo(
        google_tokens["access_token"]
    )

    google_id = google_user["sub"]
    email = google_user["email"]

    user = await find_google_user(
        google_id=google_id,
        email=email,
        session=session,
    )

    if user:
        login_session = await create_google_login_session(
            user_id=user.id,
            session=session,
        )

        frontend_url = os.getenv("FRONTEND_URL")

        if not frontend_url:
            raise RuntimeError(
                "FRONTEND_URL is not configured"
            )

        return RedirectResponse(
            url=(
                f"{frontend_url}"
                f"/auth/google/callback"
                f"?code={login_session.id}"
            )
        )

    signup_session = await create_google_signup_session(
        google_id=google_id,
        email=email,
        name=google_user.get("name") or "",
        session=session,
    )

    frontend_url = os.getenv("FRONTEND_URL")

    if not frontend_url:
        raise RuntimeError(
            "FRONTEND_URL is not configured"
        )

    return RedirectResponse(
        url=(
            f"{frontend_url}"
            f"/workspace-setup"
            f"?session={signup_session.id}"
        )
    )

@router.post(
    "/google/exchange",
    response_model=GoogleLoginExchangeResponse,
)
async def exchange_google_login_code(
    data: GoogleLoginExchangeRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        access_token, refresh_token = (
            await consume_google_login_session(
                login_session_id=data.code,
                session=session,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return GoogleLoginExchangeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/google/complete",
    response_model=GoogleSignupCompleteResponse,
)
async def complete_google_signup_route(
    data: GoogleSignupCompleteRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        user, access_token, refresh_token = (
            await complete_google_signup(
                signup_session_id=data.signup_session_id,
                workspace_name=data.workspace_name,
                session=session,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return GoogleSignupCompleteResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )