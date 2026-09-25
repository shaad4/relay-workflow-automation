import os

import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def verify_access_token(token: str) -> dict:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )

    if payload.get("type") != "access":
        raise ValueError("Invalid access token")

    if not payload.get("sub"):
        raise ValueError("Token is missing user identity")

    if not payload.get("workspace_id"):
        raise ValueError("Token is missing workspace identity")

    return payload