import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import select
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

    token = generate_verification_token()

    verification_token = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
        ),
    )

    session.add(verification_token)

    return verification_token

async def verify_email_token(
    token: str,
    session: AsyncSession
) -> None:

    result = await session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token
        )
    )

    verification_token = result.scalar_one_or_none()

    if verification_token is None:
        raise ValueError("Invalid verification token")

    if verification_token.used_at is not None:
        raise ValueError("Verification token has already been used")

    if verification_token.expires_at <= datetime.now(timezone.utc):
        raise ValueError("Verification token has expired")

    result = await session.execute(
        select(User).where(
            User.id == verification_token.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    user.email_verified_at = datetime.now(timezone.utc)

    verification_token.used_at = datetime.now(timezone.utc)

    await session.commit()




