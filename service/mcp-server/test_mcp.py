import asyncio

from mcp import Client
from server import mcp


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()

        print("Available MCP tools:")
        for tool in tools.tools:
            print("-", tool.name)

        result = await client.call_tool(
            "relay_list_workflows",
            {},
        )

        assert not result.is_error, result

        print("\nRelay workflows:")
        print(result.structured_content)


if __name__ == "__main__":
    asyncio.run(main())