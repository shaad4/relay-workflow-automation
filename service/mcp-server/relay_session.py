import asyncio
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
import jwt


class RelaySession:
    def __init__(self):
        self.base_url = os.environ["RELAY_API_URL"].rstrip("/")
        self.email = os.environ["RELAY_EMAIL"]
        self.password = os.environ["RELAY_PASSWORD"]

        parsed_url = urlsplit(self.base_url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
            follow_redirects=False,
            headers={
                "Origin": origin,
            },
        )

        self._auth_lock = asyncio.Lock()

    def _get_cookie(self, name: str) -> str | None:
        return self.client.cookies.get(name)

    def _access_token_valid(self) -> bool:
        token = self._get_cookie("relay_access_token")

        if not token:
            return False

        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"],
            )

            expires_at = payload.get("exp", 0)

            # Refresh 60 seconds before expiry.
            return expires_at > (datetime.now(timezone.utc).timestamp() + 60)

        except (jwt.PyJWTError, ValueError, TypeError):
            return False

    async def login(self):
        response = await self.client.post(
            "/auth/login",
            json={
                "email": self.email,
                "password": self.password,
            },
        )

        response.raise_for_status()

        if not self._get_cookie("relay_access_token"):
            raise RuntimeError("Relay login failed: access cookie missing")

    async def refresh(self):
        refresh_token = self._get_cookie("relay_refresh_token")

        if not refresh_token:
            raise RuntimeError("Refresh token missing")

        response = await self.client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"relay_refresh_token={refresh_token}",
            },
        )

        response.raise_for_status()

        if not self._get_cookie("relay_access_token"):
            raise RuntimeError("Access token missing after refresh")

    async def _ensure_authenticated(self):
        if self._access_token_valid():
            return

        async with self._auth_lock:
            if self._access_token_valid():
                return

            try:
                await self.refresh()
            except (httpx.HTTPError, RuntimeError):
                await self.login()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ):
        await self._ensure_authenticated()

        token = self._get_cookie("relay_access_token")

        headers = {
            **kwargs.pop("headers", {}),
            "Authorization": f"Bearer {token}",
        }

        response = await self.client.request(
            method,
            path,
            headers=headers,
            **kwargs,
        )

        if response.status_code == 401:
            # Never automatically retry mutations.
            if method.upper() not in {"GET", "HEAD"}:
                response.raise_for_status()

            async with self._auth_lock:
                try:
                    await self.refresh()
                except (httpx.HTTPError, RuntimeError):
                    await self.login()

            headers["Authorization"] = f"Bearer {self._get_cookie('relay_access_token')}"

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
