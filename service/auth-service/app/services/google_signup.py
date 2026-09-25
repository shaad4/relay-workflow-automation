import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.google_signup_session import GoogleSignupSession


GOOGLE_SIGNUP_SESSION_EXPIRE_MINUTES = 10


async def create_google_signup_session(
    google_id: str,
    email: str,
    name: str,
    session: AsyncSession,
):
    signup_session = GoogleSignupSession(
        id=uuid.uuid4(),
        google_id=google_id,
        email=email,
        name=name,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=GOOGLE_SIGNUP_SESSION_EXPIRE_MINUTES)
        ),
    )

    session.add(signup_session)

    await session.commit()
    await session.refresh(signup_session)

    return signup_session