import asyncio

from relay_session import RelaySession


async def main():
    session = RelaySession()

    try:
        await session.login()
        print("Initial login: OK")

        # Simulate invalid access and refresh tokens.
        for cookie in session.client.cookies.jar:
            if cookie.name in {
                "relay_access_token",
                "relay_refresh_token",
            }:
                cookie.value = "invalid-token"

        response = await session.get("/workflows/")

        assert response.status_code == 200

        print("Automatic re-login: OK")
        print("Workflows found:", len(response.json()))

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())