import httpx
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.schemas.connection import ConnectionCreate, ConnectionUpdate, ConnectionTestResponse


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
        credential=data.credential,
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


async def update_connection(
    connection_id: UUID,
    workspace_id: UUID,
    data: ConnectionUpdate,
    session: AsyncSession,
) -> Connection | None:
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return None

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


async def delete_connection(
    connection_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
) -> bool:
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
        raise ValueError(
            f"Unsupported connection provider: {connection.provider}"
        )

    config = connection.config or {}

    test_url = config.get("test_url")

    if not test_url:
        raise ValueError(
            "config.test_url is required to test this connection"
        )

    headers: dict[str, str] = {}
    params: dict[str, str] = {}

    if connection.auth_type == "none":
        pass

    elif connection.auth_type == "bearer":
        if not connection.credential:
            raise ValueError(
                "Credential is required for bearer authentication"
            )

        headers["Authorization"] = (
            f"Bearer {connection.credential}"
        )

    elif connection.auth_type == "api_key_header":
        if not connection.credential:
            raise ValueError(
                "Credential is required for api_key_header authentication"
            )

        auth_header = config.get("auth_header")

        if not auth_header:
            raise ValueError(
                "config.auth_header is required for api_key_header"
            )

        headers[auth_header] = connection.credential

    elif connection.auth_type == "api_key_query":
        if not connection.credential:
            raise ValueError(
                "Credential is required for api_key_query authentication"
            )

        auth_param = config.get("auth_param")

        if not auth_param:
            raise ValueError(
                "config.auth_param is required for api_key_query"
            )

        params[auth_param] = connection.credential

    else:
        raise ValueError(
            f"Unsupported auth_type: {connection.auth_type}"
        )

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
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

    if 200 <= response.status_code < 300:
        return ConnectionTestResponse(
            success=True,
            status_code=response.status_code,
            message="Connection test successful",
            response=response_payload,
        )

    return ConnectionTestResponse(
        success=False,
        status_code=response.status_code,
        message=(
            f"Connection test failed with status code "
            f"{response.status_code}"
        ),
        response=response_payload,
    )