import os

import httpx


async def authenticate_relay_user(
    email: str,
    password: str,
) -> dict:
    base_url = os.environ["RELAY_API_URL"].rstrip("/")

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=15.0,
        follow_redirects=False,
        headers={
            "Origin": "https://relay.shaad.site",
        },
    ) as client:

        login_response = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        login_response.raise_for_status()

        access_token = client.cookies.get(
            "relay_access_token"
        )
        refresh_token = client.cookies.get(
            "relay_refresh_token"
        )

        if not access_token or not refresh_token:
            raise RuntimeError(
                "Relay login did not return authentication tokens"
            )

        identity_response = await client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        identity_response.raise_for_status()
        user = identity_response.json()

        if not user.get("id") or not user.get("workspace_id"):
            raise RuntimeError(
                "Relay identity response is incomplete"
            )

        return {
            "user_id": user["id"],
            "workspace_id": user["workspace_id"],
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
