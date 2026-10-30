import asyncio
import json

from mcp import Client
from server import mcp


WORKFLOW_ID = "6d4c5e88-2ffa-4f7e-97f8-45a272f785a4"


async def main():
    async with Client(mcp) as client:
        # Deactivate workflow
        result = await client.call_tool(
            "relay_deactivate_workflow",
            {"workflow_id": WORKFLOW_ID},
        )

        assert not result.is_error, result
        print("Workflow deactivated.")

        # Delete workflow
        result = await client.call_tool(
            "relay_delete_workflow",
            {"workflow_id": WORKFLOW_ID},
        )

        assert not result.is_error, result

        print("Workflow deleted successfully!")

        for block in result.content:
            if block.type == "text":
                print(json.dumps(json.loads(block.text), indent=2))


if __name__ == "__main__":
    asyncio.run(main())