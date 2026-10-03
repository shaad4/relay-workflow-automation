import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.models.oauth_state import OAuthState

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select



router = APIRouter(
    prefix="/connections/gmail/oauth",
    tags=["gmail-oauth"],
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


async def exchange_google_code(code: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_GMAIL_REDIRECT_URI")

    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    if not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_SECRET is not configured")

    if not redirect_uri:
        raise RuntimeError(
            "GOOGLE_GMAIL_REDIRECT_URI is not configured"
        )

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=data,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Google token exchange failed: {response.text}"
        )

    return response.json()


@router.get("/start")
async def start_gmail_oauth(
    identity: dict = Depends(get_current_identity),
):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_GMAIL_REDIRECT_URI")

    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    if not redirect_uri:
        raise RuntimeError(
            "GOOGLE_GMAIL_REDIRECT_URI is not configured"
        )

    state = secrets.token_urlsafe(32)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    async with AsyncSessionLocal() as session:
        oauth_state = OAuthState(
            state=state,
            workspace_id=identity["workspace_id"],
            provider="gmail",
            expires_at=expires_at,
        )

        session.add(oauth_state)
        await session.commit()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": (
            "openid "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/gmail.send"
        ),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }

    authorization_url = (
        f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    )

    return RedirectResponse(
        url=authorization_url,
        status_code=302,
    )


@router.get("/callback")
async def gmail_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Google OAuth authorization failed: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code is missing",
        )

    if not state:
        raise HTTPException(
            status_code=400,
            detail="OAuth state is missing",
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.provider == "gmail",
            )
        )

        oauth_state = result.scalar_one_or_none()

        if oauth_state is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state",
            )

        if oauth_state.expires_at <= datetime.now(timezone.utc):
            await session.delete(oauth_state)
            await session.commit()

            raise HTTPException(
                status_code=400,
                detail="OAuth state has expired",
            )

        workspace_id = oauth_state.workspace_id

    tokens = await exchange_google_code(code)

    return {
        "message": "Google OAuth callback successful",
        "workspace_id": str(workspace_id),
        "token_received": bool(tokens.get("access_token")),
    }