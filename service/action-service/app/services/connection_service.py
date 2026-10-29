from uuid import UUID

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import CredentialEncryption
from app.models.connection import Connection
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionTestResponse,
    ConnectionUpdate,
)

SENSITIVE_FIELDS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "api_key",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "credential",
    "credentials",
    "private_key",
    "cookie",
    "set-cookie",
}


def redact_response(
    value,
    credential: str | None = None,
):
    """Remove sensitive information from connection test responses."""

    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if str(key).lower().replace("-", "_") in SENSITIVE_FIELDS
                else redact_response(item, credential)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact_response(item, credential) for item in value]

    if isinstance(value, str):
        if credential:
            return value.replace(
                credential,
                "[REDACTED]",
            )

        return value

    return value


async def create_connection(
    data: ConnectionCreate,
    workspace_id: UUID,
    session: AsyncSession,
) -> Connection:
    credential = None

    if data.credential:
        encryption = CredentialEncryption()
        credential = encryption.encrypt(data.credential)

    connection = Connection(
        workspace_id=workspace_id,
        name=data.name,
        provider=data.provider,
        auth_type=data.auth_type,
        credential=credential,
        config=data.config,
    )

    try:
        session.add(connection)
        await session.commit()
        await session.refresh(connection)

        return connection

    except Exception:
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


async def update_connection(
    connection_id: UUID,
    workspace_id: UUID,
    data: ConnectionUpdate,
    session: AsyncSession,
) -> Connection | None:
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return None

    if "credential" in update_data:
        credential = update_data["credential"]

        if credential is not None:
            encryption = CredentialEncryption()
            update_data["credential"] = encryption.encrypt(credential)

    try:
        result = await session.execute(
            update(Connection)
            .where(
                Connection.id == connection_id,
                Connection.workspace_id == workspace_id,
            )
            .values(**update_data)
            .returning(Connection)
        )

        connection = result.scalar_one_or_none()

        if connection is None:
            await session.rollback()
            return None

        await session.commit()

        return connection

    except Exception:
        await session.rollback()
        raise


async def delete_connection(
    connection_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
) -> bool:
    try:
        result = await session.execute(
            delete(Connection).where(
                Connection.id == connection_id,
                Connection.workspace_id == workspace_id,
            )
        )

        if result.rowcount == 0:
            await session.rollback()
            return False

        await session.commit()

        return True

    except Exception:
        await session.rollback()
        raise


async def test_connection(
    connection_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
) -> ConnectionTestResponse:
    connection = await get_connection(
        connection_id=connection_id,
        workspace_id=workspace_id,
        session=session,
    )

    if connection is None:
        raise ValueError("Connection not found")

    if connection.provider != "http":
        raise ValueError(f"Unsupported connection provider: {connection.provider}")

    config = connection.config or {}

    test_url = config.get("test_url")

    if not test_url:
        raise ValueError("config.test_url is required to test this connection")

    # Decrypt credentials only when needed.
    credential = None

    if connection.auth_type != "none":
        if not connection.credential:
            raise ValueError("Credential is required for authentication")

        encryption = CredentialEncryption()
        credential = encryption.decrypt(connection.credential)

    headers: dict[str, str] = {}
    params: dict[str, str] = {}

    if connection.auth_type == "none":
        pass

    elif connection.auth_type == "bearer":
        headers["Authorization"] = f"Bearer {credential}"

    elif connection.auth_type == "api_key_header":
        auth_header = config.get("auth_header")

        if not auth_header:
            raise ValueError("config.auth_header is required for api_key_header")

        headers[auth_header] = credential

    elif connection.auth_type == "api_key_query":
        auth_param = config.get("auth_param")

        if not auth_param:
            raise ValueError("config.auth_param is required for api_key_query")

        params[auth_param] = credential

    else:
        raise ValueError(f"Unsupported auth_type: {connection.auth_type}")

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                test_url,
                headers=headers,
                params=params,
            )

    except httpx.RequestError:
        return ConnectionTestResponse(
            success=False,
            message="Failed to connect to the test endpoint",
        )

    try:
        response_payload = response.json()
    except ValueError:
        response_payload = response.text

    # Sanitize before returning to the frontend.
    safe_response = redact_response(
        response_payload,
        credential,
    )

    if 200 <= response.status_code < 300:
        return ConnectionTestResponse(
            success=True,
            status_code=response.status_code,
            message="Connection test successful",
            response=safe_response,
        )

    return ConnectionTestResponse(
        success=False,
        status_code=response.status_code,
        message=(f"Connection test failed with status code {response.status_code}"),
        response=safe_response,
    )
