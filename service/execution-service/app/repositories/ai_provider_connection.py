import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider_connection import AIProviderConnection


class AIProviderConnectionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        provider: str,
        encrypted_api_key: str,
    ) -> AIProviderConnection:
        connection = AIProviderConnection(
            workspace_id=workspace_id,
            name=name,
            provider=provider,
            encrypted_api_key=encrypted_api_key,
            status="active",
        )

        self.db.add(connection)
        await self.db.flush()

        return connection

    async def get_by_id(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> AIProviderConnection | None:
        statement = select(AIProviderConnection).where(
            AIProviderConnection.id == connection_id,
            AIProviderConnection.workspace_id == workspace_id,
        )

        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[AIProviderConnection]:
        statement = (
            select(AIProviderConnection)
            .where(
                AIProviderConnection.workspace_id == workspace_id,
            )
            .order_by(AIProviderConnection.created_at.desc())
        )

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def update(
        self,
        connection: AIProviderConnection,
        name: str | None = None,
        encrypted_api_key: str | None = None,
        status: str | None = None,
    ) -> AIProviderConnection:
        if name is not None:
            connection.name = name

        if encrypted_api_key is not None:
            connection.encrypted_api_key = encrypted_api_key

        if status is not None:
            connection.status = status

        await self.db.flush()
        return connection

    async def delete(
        self,
        connection: AIProviderConnection,
    ) -> None:
        await self.db.delete(connection)
        await self.db.flush()
