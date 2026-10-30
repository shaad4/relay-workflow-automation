import asyncio
import os

from relay_client import RelayClient


async def main():
    client = RelayClient(
        base_url=os.environ["RELAY_API_URL"],
        access_token=os.environ["RELAY_ACCESS_TOKEN"],
    )

    workflows = await client.list_workflows()

    print("Relay API connection: OK")
    print("Workflows found:", len(workflows))

    for workflow in workflows:
        print("-", workflow["name"])


if __name__ == "__main__":
    asyncio.run(main())