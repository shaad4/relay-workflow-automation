import asyncio

from relay_session import RelaySession


async def main():
    session = RelaySession()

    try:
        await session.login()
        print("Relay login: OK")

        response = await session.get("/workflows/")
        print("Authenticated API request:", response.status_code)
        print("Workflows found:", len(response.json()))

        await session.refresh()
        print("Session refresh: OK")

        response = await session.get("/workflows/")
        print("Request after refresh:", response.status_code)

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())