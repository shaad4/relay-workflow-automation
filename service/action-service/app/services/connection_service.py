from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.schemas.connection import ConnectionCreate


async def create_connection(
    data: ConnectionCreate,
    workspace_id: UUID,
    session: AsyncSession,
) -> Connection:
    connection = Connection(
        workspace_id=workspace_id,
        name=data.name,
        provider=data.provider,
        auth_type=data.auth_type,
        credential_ref=data.credential_ref,
        config=data.config,
    )

    session.add(connection)

    try:
        await session.commit()
        await session.refresh(connection)

        return connection

    except SQLAlchemyError:
        await session.rollback()
        raise


async def get_connections(
    workspace_id: UUID,
    session: AsyncSession,
) -> list[Connection]:
    result = await session.execute(
        select(Connection)
        .where(Connection.workspace_id == workspace_id)
        .order_by(Connection.created_at.desc())
    )

    return list(result.scalars().all())


async def get_connection(
    connection_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
) -> Connection | None:
    result = await session.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        )
    )

    return result.scalar_one_or_none()