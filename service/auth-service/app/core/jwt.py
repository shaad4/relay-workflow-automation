import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

from app.config import integer

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = integer("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
REFRESH_TOKEN_EXPIRE_DAYS = integer("REFRESH_TOKEN_EXPIRE_DAYS", 7)


def create_token(
    data: dict,
    expires_minutes: int,
    token_type: str,
    expires_at: datetime | None = None,
) -> str:
    payload = data.copy()

    expire = expires_at or datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    payload["exp"] = expire
    payload["type"] = token_type

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_access_token(data: dict) -> str:
    return create_token(
        data=data,
        expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        token_type="access",
    )


def create_refresh_token(
    data: dict,
    expires_at: datetime | None = None,
) -> str:
    return create_token(
        data=data,
        expires_minutes=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60,
        token_type="refresh",
        expires_at=expires_at,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
