import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import PasswordResetToken, User

load_dotenv()

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)

def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)

async def create_password_reset_token(
    email: str,
    session: AsyncSession,
) -> tuple[PasswordResetToken, User] | None:

    result = await session.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        return None

    now = datetime.now(timezone.utc)

    # Expire existing unused tokens
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(expires_at=now)
    )

    token = PasswordResetToken(
        user_id=user.id,
        token=generate_password_reset_token(),
        expires_at=(
            now
            + timedelta(
                minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            )
        ),
    )

    session.add(token)

    await session.commit()
    await session.refresh(token)

    return token, user


async def reset_password(
    token: str,
    new_password: str,
    session: AsyncSession,
) -> None:
    
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token
        )
    )

    reset_token = result.scalar_one_or_none()

    if reset_token is None:
        raise ValueError(
            "Invalid password reset token"
        )

    if reset_token.used_at is not None:
        raise ValueError(
            "Password reset token has already been used"
        )

    now = datetime.now(timezone.utc)

    if reset_token.expires_at <= now:
        raise ValueError(
            "Password reset token has expired"
        )

    result = await session.execute(
        select(User).where(
            User.id == reset_token.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    user.password_hash = hash_password(
        new_password
    )

    reset_token.used_at = now

    await session.commit()

