import asyncio
import json

from mcp import Client
from server import mcp


WORKFLOW_ID = "6d4c5e88-2ffa-4f7e-97f8-45a272f785a4"


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_run_workflow",
            {
                "workflow_id": WORKFLOW_ID,
                "input_data": {
                    "student_name": "Rahul",
                    "maths": 85,
                    "science": 90,
                    "english": 78,
                },
            },
        )

        assert not result.is_error, result

        for block in result.content:
            if block.type == "text":
                data = json.loads(block.text)
                print(json.dumps(data, indent=2))

                assert data["status"] == "accepted"

        print("Workflow execution request accepted!")


if __name__ == "__main__":
    asyncio.run(main())