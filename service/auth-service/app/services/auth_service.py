from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailVerificationRequired
from app.core.security import hash_password, verify_password
from app.models import User, Workspace
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_verification_service import create_verification_token
from app.services.token_sessions import create_refresh_session, rotate_refresh_token


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

    access_token, refresh_token = await create_refresh_session(
        user_id=user.id,
        workspace_id=user.workspace_id,
        session=session,
    )
    await session.commit()

    return access_token, refresh_token


async def refresh_access_token(
    refresh_token: str,
    session: AsyncSession,
) -> tuple[str, str]:
    return await rotate_refresh_token(refresh_token, session)
    
    
