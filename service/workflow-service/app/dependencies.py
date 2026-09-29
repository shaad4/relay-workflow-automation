from fastapi import Cookie, Header, HTTPException

from app.grpc.auth_client import AuthGrpcClient


async def get_current_identity(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias="relay_access_token"),
) -> dict:
    if not authorization and isinstance(access_cookie, str) and access_cookie:
        authorization = f"Bearer {access_cookie}"
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )

    client = AuthGrpcClient()

    try:
        response = await client.validate_token(token)
    finally:
        await client.close()

    if not response.valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    return {
        "user_id": response.user_id,
        "workspace_id": response.workspace_id,
    }
