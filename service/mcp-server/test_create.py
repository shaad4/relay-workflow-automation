import asyncio

from mcp import Client
from server import mcp


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "relay_create_workflow",
            {
                "name": "MCP Student Grade Report",
                "description": "Workflow created through Relay MCP Server",
            },
        )

        assert not result.is_error, result

        print("Workflow created successfully!")
        print("Structured content:", result.structured_content)

        print("Content blocks:")
        for block in result.content:
            if block.type == "text":
                print(block.text)

if __name__ == "__main__":
    asyncio.run(main())