import asyncio
import json

from mcp import Client
from server import mcp


EXECUTION_ID = "3fed9b4d-af7a-4db8-84c6-614a109a0ce7"


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_get_execution_steps",
            {"execution_id": EXECUTION_ID},
        )

        assert not result.is_error, result

        for block in result.content:
            if block.type != "text":
                continue

            data = json.loads(block.text)

            for step in data.get("items", []):
                print("\nNode:", step["node_id"])
                print("Status:", step["status"])

                if step["node_id"] == "generate_1":
                    print("\nAI-generated report:")
                    print(
                        json.dumps(
                            step.get("output"),
                            indent=2,
                            ensure_ascii=False,
                        )
                    )


if __name__ == "__main__":
    asyncio.run(main())