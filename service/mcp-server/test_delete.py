import asyncio
import json
import os

from mcp import Client
from server import mcp


WORKFLOW_ID = os.environ["RELAY_DELETE_TEST_WORKFLOW_ID"]
EDGE_ID = os.environ["RELAY_DELETE_TEST_EDGE_ID"]


async def call(client, tool, arguments):
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, result

    for block in result.content:
        if block.type == "text":
            print(json.dumps(json.loads(block.text), indent=2))


async def main():
    async with Client(mcp) as client:
        # Delete the edge first.
        await call(
            client,
            "relay_delete_edge",
            {
                "workflow_id": WORKFLOW_ID,
                "version": 1,
                "edge_id": EDGE_ID,
            },
        )

        # Then delete the AI node.
        await call(
            client,
            "relay_delete_node",
            {
                "workflow_id": WORKFLOW_ID,
                "version": 1,
                "node_id": "generate_test",
            },
        )

    print("Node and edge deletion tests passed!")


if __name__ == "__main__":
    asyncio.run(main())