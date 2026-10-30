
import asyncio

from relay_session import RelaySession


async def main():
    session = RelaySession()

    try:
        await session.login()
        print("Initial login: OK")

        # Find and replace the existing access cookie
        # without creating a duplicate.
        access_cookie = next(
            cookie
            for cookie in session.client.cookies.jar
            if cookie.name == "relay_access_token"
        )

        access_cookie.value = "expired-token"

        # The session should detect the invalid token,
        # refresh authentication, and retry the GET.
        response = await session.get("/workflows/")

        print("Automatic recovery:", response.status_code)
        print("Workflows found:", len(response.json()))

        assert response.status_code == 200

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
