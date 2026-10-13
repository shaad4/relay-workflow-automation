from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.encryption import CredentialEncryption
from app.repositories.ai_provider_connection import (
    AIProviderConnectionRepository,
)
from app.ai.connection_test import test_ai_provider_connection
from app.ai.model_catalog import list_provider_models

SUPPORTED_PROVIDERS = {
    "openai",
    "gemini",
    "anthropic",
}


class AIProviderConnectionService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIProviderConnectionRepository(db)
        self.encryption = CredentialEncryption()

    async def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        provider: str,
        api_key: str,
    ):
        name = name.strip()
        provider = provider.strip().lower()

        if not name or len(name) > 100:
            raise ValueError(
                "Connection name must be between 1 and 100 characters"
            )

        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported AI provider")

        if not api_key or not api_key.strip():
            raise ValueError("API key is required")

        encrypted_api_key = self.encryption.encrypt(api_key)

        try:
            connection = await self.repository.create(
                workspace_id=workspace_id,
                name=name,
                provider=provider,
                encrypted_api_key=encrypted_api_key,
            )

            await self.db.commit()
            await self.db.refresh(connection)

            return connection

        except Exception:
            await self.db.rollback()
            raise

    async def get(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ):
        return await self.repository.get_by_id(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

    async def list(
        self,
        workspace_id: uuid.UUID,
    ):
        return await self.repository.list_by_workspace(
            workspace_id=workspace_id,
        )

    async def update(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: str | None = None,
        api_key: str | None = None,
        status: str | None = None,
    ):
        connection = await self.repository.get_by_id(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

        if connection is None:
            return None

        if name is not None:
            name = name.strip()

            if not name or len(name) > 100:
                raise ValueError(
                    "Connection name must be between 1 and 100 characters"
                )

        if api_key is not None:
            if not api_key.strip():
                raise ValueError("API key cannot be empty")

            api_key = self.encryption.encrypt(api_key)

        if status is not None:
            status = status.strip().lower()

            if status not in {"active", "inactive"}:
                raise ValueError("Invalid connection status")

        try:
            await self.repository.update(
                connection=connection,
                name=name,
                encrypted_api_key=api_key,
                status=status,
            )

            await self.db.commit()
            await self.db.refresh(connection)

            return connection

        except Exception:
            await self.db.rollback()
            raise

    async def delete(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        connection = await self.repository.get_by_id(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

        if connection is None:
            return False

        try:
            await self.repository.delete(connection)
            await self.db.commit()
            return True

        except Exception:
            await self.db.rollback()
            raise

    async def get_execution_credentials(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> tuple[str, str]:
        """Resolve provider and API key for internal AI execution."""

        connection = await self.repository.get_by_id(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

        if connection is None:
            raise ValueError("AI connection not found")

        if connection.status != "active":
            raise ValueError("AI connection is inactive")

        api_key = self.encryption.decrypt(
            connection.encrypted_api_key
        )

        return connection.provider, api_key


    async def test_connection(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Test a workspace-owned AI provider connection."""

        provider, api_key = await self.get_execution_credentials(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

        return await test_ai_provider_connection(
            provider=provider,
            api_key=api_key,
        )

    
    async def list_models(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[dict]:
        """List models for an active workspace AI connection."""

        provider, api_key = await self.get_execution_credentials(
            connection_id=connection_id,
            workspace_id=workspace_id,
        )

        return await list_provider_models(
            provider=provider,
            api_key=api_key,
        )

