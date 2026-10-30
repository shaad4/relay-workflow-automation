import httpx


class UserRelaySession:
    def __init__(
        self,
        base_url: str,
        access_token: str,
        refresh_token: str,
    ):
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=15.0,
            follow_redirects=False,
        )

        self.access_token = access_token
        self.refresh_token = refresh_token

    async def get_identity(self) -> dict:
        response = await self.client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {self.access_token}",
            },
        )

        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()