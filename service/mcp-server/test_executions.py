import asyncio
import json

from mcp import Client
from server import mcp


WORKFLOW_ID = "6d4c5e88-2ffa-4f7e-97f8-45a272f785a4"


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_list_executions",
            {"page": 1},
        )

        assert not result.is_error, result

        for block in result.content:
            if block.type != "text":
                continue

            data = json.loads(block.text)

            executions = [
                execution
                for execution in data.get("items", [])
                if execution["workflow_id"] == WORKFLOW_ID
            ]

            print("Matching executions:", len(executions))

            for execution in executions:
                print("Execution ID:", execution["id"])
                print("Status:", execution["status"])
                print("Workflow:", execution.get("workflow_name"))
                print("---")


if __name__ == "__main__":
    asyncio.run(main())