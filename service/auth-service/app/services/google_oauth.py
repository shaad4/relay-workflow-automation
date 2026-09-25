import os
import secrets
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

load_dotenv()

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def create_google_authorization_url():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    if not redirect_uri:
        raise RuntimeError("GOOGLE_REDIRECT_URI is not configured")

    state = secrets.token_urlsafe(32)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    authorization_url = (
        f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(params)}"
    )

    return authorization_url, state


async def exchange_google_code(code: str):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    if not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_SECRET is not configured")

    if not redirect_uri:
        raise RuntimeError("GOOGLE_REDIRECT_URI is not configured")

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=data,
        )

    if not response.is_success:
        raise RuntimeError(
            f"Google token exchange failed: {response.text}"
        )

    return response.json()


async def get_google_userinfo(access_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

    if not response.is_success:
        raise RuntimeError(
            f"Google userinfo request failed: {response.text}"
        )

    return response.json()

async def find_google_user(
    google_id: str,
    email: str,
    session: AsyncSession,
):
    result = await session.execute(
        select(User).where(User.google_id == google_id)
    )

    user = result.scalar_one_or_none()

    if user:
        return user

    result = await session.execute(
        select(User).where(User.email == email)
    )

    return result.scalar_one_or_none()