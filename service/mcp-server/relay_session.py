import os

import httpx


class RelaySession:
    def __init__(self):
        self.base_url = os.environ["RELAY_API_URL"].rstrip("/")
        self.email = os.environ["RELAY_EMAIL"]
        self.password = os.environ["RELAY_PASSWORD"]

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
        )

    async def login(self):
        response = await self.client.post(
            "/auth/login",
            json={
                "email": self.email,
                "password": self.password,
            },
        )
        response.raise_for_status()

        if not self.client.cookies.get("relay_access_token"):
            raise RuntimeError("Relay login failed: access cookie missing")

    async def refresh(self):
        refresh_token = self.client.cookies.get(
            "relay_refresh_token"
        )

        if not refresh_token:
            raise RuntimeError("Relay refresh token missing")

        response = await self.client.post(
            "/auth/refresh",
            cookies={
                "relay_refresh_token": refresh_token
            },
        )

        response.raise_for_status()

    async def request(self, method: str, path: str, **kwargs):
        access_token = self.client.cookies.get(
            "relay_access_token"
        )

        if not access_token:
            await self.login()
            access_token = self.client.cookies.get(
                "relay_access_token"
            )

        headers = {
            **kwargs.pop("headers", {}),
            "Authorization": f"Bearer {access_token}",
        }

        response = await self.client.request(
            method,
            path,
            headers=headers,
            **kwargs,
        )

        if response.status_code == 401:
            await self.refresh()

            access_token = self.client.cookies.get(
                "relay_access_token"
            )

            headers["Authorization"] = f"Bearer {access_token}"

            response = await self.client.request(
                method,
                path,
                headers=headers,
                **kwargs,
            )

        response.raise_for_status()
        return response

    async def get(self, path: str):
        return await self.request("GET", path)

    async def close(self):
        await self.client.aclose()
