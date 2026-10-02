import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.dependencies import get_current_identity


router = APIRouter(
    prefix="/connections/gmail/oauth",
    tags=["gmail-oauth"],
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


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