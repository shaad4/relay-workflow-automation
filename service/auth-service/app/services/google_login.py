import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_access_token, create_refresh_token
from app.models import User
from app.models.google_login_session import GoogleLoginSession


GOOGLE_LOGIN_SESSION_EXPIRE_MINUTES = 5


async def create_google_login_session(
    user_id: uuid.UUID,
    session: AsyncSession,
):
    login_session = GoogleLoginSession(
        id=uuid.uuid4(),
        user_id=user_id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(
                minutes=GOOGLE_LOGIN_SESSION_EXPIRE_MINUTES
            )
        ),
    )

    session.add(login_session)

    await session.commit()
    await session.refresh(login_session)

    return login_session


async def consume_google_login_session(
    login_session_id: uuid.UUID,
    session: AsyncSession,
):
    result = await session.execute(
        select(GoogleLoginSession)
        .where(GoogleLoginSession.id == login_session_id)
        .with_for_update()
    )

    login_session = result.scalar_one_or_none()

    if not login_session:
        raise ValueError(
            "Invalid Google login session"
        )

    if login_session.used_at is not None:
        raise ValueError(
            "Google login session has already been used"
        )

    if login_session.expires_at <= datetime.now(timezone.utc):
        raise ValueError(
            "Google login session has expired"
        )

    result = await session.execute(
        select(User).where(
            User.id == login_session.user_id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(
            "Relay user not found"
        )

    login_session.used_at = datetime.now(timezone.utc)

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "workspace_id": str(user.workspace_id),
        }
    )

    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
            "workspace_id": str(user.workspace_id),
        }
    )

    await session.commit()

    return access_token, refresh_token