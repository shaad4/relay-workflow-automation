from fastapi import Cookie, Header, HTTPException
import grpc

from app.grpc.auth_client import AuthGrpcClient


async def get_current_identity(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(
        default=None,
        alias="relay_access_token",
    ),
) -> dict:

    if not authorization and access_cookie:
        authorization = f"Bearer {access_cookie}"

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )

    client = AuthGrpcClient()

    try:
        response = await client.validate_token(token.strip())

    except grpc.RpcError as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from exc

    finally:
        await client.close()

    if not response.valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    if not response.user_id or not response.workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication identity",
        )

    return {
        "user_id": response.user_id,
        "workspace_id": response.workspace_id,
    }