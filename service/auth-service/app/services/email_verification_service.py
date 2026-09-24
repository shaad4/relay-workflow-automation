import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailVerificationToken, User


load_dotenv()


VERIFICATION_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("VERIFICATION_TOKEN_EXPIRE_MINUTES", "30")
)


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


async def create_verification_token(
    user_id,
    session: AsyncSession,
) -> EmailVerificationToken:

    now = datetime.now(timezone.utc)

    # Expire all currently active tokens for this user.
    await session.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > now,
        )
        .values(expires_at=now)
    )

    # Create the new token.
    token = generate_verification_token()

    verification_token = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=(
            now
            + timedelta(
                minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES
            )
        ),
    )

    session.add(verification_token)

    return verification_token


async def resend_verification_email(
    email: str,
    session: AsyncSession,
):
    result = await session.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        return None

    if user.email_verified_at is not None:
        return None

    verification_token = await create_verification_token(
        user.id,
        session,
    )

    await session.commit()

    return verification_token, user


async def verify_email_token(
    token: str,
    session: AsyncSession,
) -> None:

    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token
        )
    )

    verification_token = result.scalar_one_or_none()

    if verification_token is None:
        raise ValueError("Invalid verification token")

    if verification_token.used_at is not None:
        raise ValueError(
            "Verification token has already been used"
        )

    if verification_token.expires_at <= now:
        raise ValueError(
            "Verification token has expired"
        )

    result = await session.execute(
        select(User).where(
            User.id == verification_token.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    user.email_verified_at = now
    verification_token.used_at = now

    await session.commit()
    