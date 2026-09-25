from fastapi import Header, HTTPException

from app.core.security import verify_access_token


async def get_current_identity(
    authorization: str | None = Header(default=None),
) -> dict:
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

    try:
        payload = verify_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    return payload