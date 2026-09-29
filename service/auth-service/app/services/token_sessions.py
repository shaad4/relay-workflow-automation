import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models import RefreshSession


async def create_refresh_session(
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    session_id = uuid.uuid4()
    token_id = str(uuid.uuid4())
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    row = RefreshSession(
        id=session_id,
        user_id=user_id,
        current_token_id=token_id,
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()

    access_token = create_access_token(
        {"sub": str(user_id), "workspace_id": str(workspace_id), "sid": str(session_id)}
    )
    refresh_token = create_refresh_token(
        {
            "sub": str(user_id),
            "workspace_id": str(workspace_id),
            "sid": str(session_id),
            "jti": token_id,
        },
        expires_at=expires_at,
    )
    return access_token, refresh_token


async def rotate_refresh_token(
    refresh_token: str,
    session: AsyncSession,
) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired refresh token") from exc

    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")

    try:
        session_id = uuid.UUID(payload["sid"])
        token_id = str(uuid.UUID(payload["jti"]))
        user_id = uuid.UUID(payload["sub"])
        workspace_id = uuid.UUID(payload["workspace_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid refresh token") from exc

    result = await session.execute(
        select(RefreshSession)
        .where(RefreshSession.id == session_id)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if row is None or row.user_id != user_id:
        raise ValueError("Refresh session is no longer valid")
    if row.revoked_at is not None or row.expires_at <= now:
        raise ValueError("Refresh session has expired or was revoked")

    if row.current_token_id != token_id:
        # Reuse of a rotated token indicates theft; revoke the whole session.
        row.revoked_at = now
        await session.commit()
        raise ValueError("Refresh token reuse detected; session revoked")

    next_token_id = str(uuid.uuid4())
    row.current_token_id = next_token_id
    access_token = create_access_token(
        {"sub": str(user_id), "workspace_id": str(workspace_id), "sid": str(session_id)}
    )
    next_refresh_token = create_refresh_token(
        {
            "sub": str(user_id),
            "workspace_id": str(workspace_id),
            "sid": str(session_id),
            "jti": next_token_id,
        },
        expires_at=row.expires_at,
    )
    await session.commit()
    return access_token, next_refresh_token


async def revoke_refresh_session(
    session_id: str | uuid.UUID | None,
    session: AsyncSession,
) -> bool:
    if not session_id:
        return False
    try:
        parsed_id = uuid.UUID(str(session_id))
    except ValueError:
        return False

    result = await session.execute(
        select(RefreshSession)
        .where(RefreshSession.id == parsed_id)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()
    return True
