import asyncio
import os

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
                "node_id": "generate_1",
                "node_type": "ai.generate",
                "configuration": {
                    "connection_id": os.environ["RELAY_AI_CONNECTION_ID"],
                    "model": os.environ["RELAY_AI_MODEL"],
                    "instructions": (
                        "You are an academic report assistant. "
                        "Generate accurate, professional student grade reports. "
                        "Use only the provided student data. "
                        "Do not invent marks or grades."
                    ),
                    "prompt": (
                        "Generate a student grade report using this data: "
                        "{{trigger_1.input}}. "
                        "Include student name, subject marks, total, "
                        "percentage, grade, and a short performance summary."
                    ),
                },
            },
        )

        assert not result.is_error, result

        print("AI Generate node created successfully!")

        for block in result.content:
            if block.type == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())