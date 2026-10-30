import asyncio

from relay_session import RelaySession


async def main():
    session = RelaySession()

    try:
        response = await session.get("/auth/me")
        user = response.json()

        assert user.get("id")
        assert user.get("workspace_id")

        print("Relay identity verification: OK")
        print("User ID:", user["id"])
        print("Workspace ID:", user["workspace_id"])

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())