import os

import httpx

from app.connectors.base import Connector


async def refresh_access_token(refresh_token: str) -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Google OAuth credentials are not configured")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data=data,
        )

    if response.status_code != 200:
        raise ValueError(
            f"Failed to refresh Google access token: {response.text}"
        )

    token_data = response.json()

    access_token = token_data.get("access_token")

    if not access_token:
        raise ValueError("Google did not return an access token")

    return access_token


class GmailConnector(Connector):

    async def execute(
        self,
        action: str,
        config: dict,
        input_data: dict,
    ) -> dict:

        if action != "send_email":
            raise ValueError(f"Unsupported Gmail action: {action}")

        # Gmail API implementation will be added next.
        raise NotImplementedError("Gmail connector is not implemented yet")