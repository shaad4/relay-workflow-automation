import asyncio

from relay_client import RelayClient
from relay_session import RelaySession


async def main():
    session = RelaySession()

    try:
        client = RelayClient(session)

        workflows = await client.list_workflows()

        print("Automatic authentication: OK")
        print("Workflows found:", len(workflows))

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())