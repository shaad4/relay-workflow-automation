import asyncio

from mcp import Client
from server import mcp


WORKFLOW_ID = "6d4c5e88-2ffa-4f7e-97f8-45a272f785a4"


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_add_node",
            {
                "workflow_id": WORKFLOW_ID,
                "version": 1,
                "node_id": "trigger_1",
                "node_type": "trigger.manual",
                "configuration": {
                    "description": "Start student grade report generation",
                    "input_schema": {"type": "object"},
                },
            },
        )

        assert not result.is_error, result

        print("Manual Trigger created successfully!")

        for block in result.content:
            if block.type == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
    