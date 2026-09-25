import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_access_token, create_refresh_token
from app.core.security import hash_password
from app.models import User, Workspace
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
            + timedelta(
                minutes=GOOGLE_SIGNUP_SESSION_EXPIRE_MINUTES
            )
        ),
    )

    session.add(signup_session)

    await session.commit()
    await session.refresh(signup_session)

    return signup_session


async def complete_google_signup(
    signup_session_id: uuid.UUID,
    workspace_name: str,
    session: AsyncSession,
):
    # 1. Find and lock the signup session
    result = await session.execute(
        select(GoogleSignupSession)
        .where(GoogleSignupSession.id == signup_session_id)
        .with_for_update()
    )

    signup_session = result.scalar_one_or_none()

    if not signup_session:
        raise ValueError(
            "Invalid Google signup session"
        )

    # 2. Check whether the session was already used
    if signup_session.used_at is not None:
        raise ValueError(
            "Google signup session has already been used"
        )

    # 3. Check whether the session has expired
    if signup_session.expires_at <= datetime.now(timezone.utc):
        raise ValueError(
            "Google signup session has expired"
        )

    # 4. Validate workspace name
    workspace_name = workspace_name.strip()

    if not workspace_name:
        raise ValueError(
            "Workspace name is required"
        )

    if len(workspace_name) < 2:
        raise ValueError(
            "Workspace name must be at least 2 characters"
        )

    if len(workspace_name) > 100:
        raise ValueError(
            "Workspace name must be 100 characters or fewer"
        )

    # 5. Make sure the Google account wasn't created
    # between the callback and this request.
    result = await session.execute(
        select(User).where(
            User.google_id == signup_session.google_id
        )
    )

    existing_google_user = result.scalar_one_or_none()

    if existing_google_user:
        raise ValueError(
            "Google account is already registered"
        )

    # 6. Check email again before creating the user
    result = await session.execute(
        select(User).where(
            User.email == signup_session.email
        )
    )

    existing_email_user = result.scalar_one_or_none()

    if existing_email_user:
        raise ValueError(
            "An account with this email already exists"
        )

    # 7. Create workspace
    workspace = Workspace(
        name=workspace_name
    )

    session.add(workspace)

    # Make sure workspace.id is available
    await session.flush()

    # 8. Google users don't set a password.
    # Generate a random password hash so the existing
    # non-null password_hash column remains satisfied.
    random_password = secrets.token_urlsafe(32)
    password_hash = hash_password(random_password)

    # 9. Create Relay user
    user = User(
        workspace_id=workspace.id,
        name=signup_session.name,
        email=signup_session.email,
        password_hash=password_hash,
        google_id=signup_session.google_id,
        email_verified_at=datetime.now(timezone.utc),
    )

    session.add(user)

    await session.flush()

    # 10. Consume the signup session
    signup_session.used_at = datetime.now(timezone.utc)

    # 11. Create Relay tokens
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

    # 12. Commit everything together
    await session.commit()

    await session.refresh(user)

    return user, access_token, refresh_token