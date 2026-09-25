import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailVerificationRequired
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security import hash_password, verify_password
from app.models import User, Workspace
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_verification_service import create_verification_token


async def register_user(
    data: RegisterRequest,
    session: AsyncSession,
):
    result = await session.execute(
        select(User).where(User.email == data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise ValueError("Email already registered")

    password_hash = hash_password(data.password)

    workspace = Workspace(
        name=data.workspace_name
    )

    session.add(workspace)
    await session.flush()

    user = User(
        workspace_id=workspace.id,
        name=data.name,
        email=data.email,
        password_hash=password_hash,
    )

    session.add(user)

    await session.flush()

    verification_token = await create_verification_token(
        user_id=user.id,
        session=session
    )

    await session.commit()
    await session.refresh(user)

    return user, verification_token


async def login_user(
    data: LoginRequest,
    session: AsyncSession,
):
    result = await session.execute(
        select(User).where(
            User.email == data.email
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(
            "Invalid email or password"
        )

    # Verify password before sending a new
    # verification email.
    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise ValueError(
            "Invalid email or password"
        )

    if user.email_verified_at is None:

        verification_token = (
            await create_verification_token(
                user_id=user.id,
                session=session,
            )
        )

        await session.commit()

        raise EmailVerificationRequired(
            token=verification_token.token,
            user_email=user.email,
            user_name=user.name,
        )

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "workspace_id": str(
                user.workspace_id
            ),
        }
    )

    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
            "workspace_id": str(
                user.workspace_id
            ),
        }
    )

    return access_token, refresh_token


async def refresh_access_token(
        refresh_token: str,
) -> str:
    
    try:
        payload = decode_token(refresh_token)
    except jwt.InvalidTokenError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")


    access_token = create_access_token(
        {
            "sub": payload["sub"],
            "workspace_id": payload["workspace_id"],
        }
    )

    return access_token
    
    