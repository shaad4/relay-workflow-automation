from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User, Workspace
from app.schemas.auth import RegisterRequest


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

    await session.commit()
    await session.refresh(user)

    return user