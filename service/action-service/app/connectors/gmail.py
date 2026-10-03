import base64
import os
from email.message import EmailMessage

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

        refresh_token = config.get("refresh_token")

        if not refresh_token:
            raise ValueError("Gmail refresh token is required")

        to = input_data.get("to")
        subject = input_data.get("subject")
        body = input_data.get("body")

        if not to:
            raise ValueError("Recipient email is required")

        if not subject:
            raise ValueError("Email subject is required")

        if not body:
            raise ValueError("Email body is required")

        access_token = await refresh_access_token(refresh_token)

        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        payload = {
            "raw": raw_message,
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers=headers,
                json=payload,
            )

        if response.status_code not in (200, 202):
            raise ValueError(
                f"Failed to send Gmail message: {response.text}"
            )

        response_data = response.json()

        return {
            "success": True,
            "message_id": response_data.get("id"),
            "thread_id": response_data.get("threadId"),
            "label_ids": response_data.get("labelIds", []),
        }