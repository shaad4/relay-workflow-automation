from contextlib import asynccontextmanager

from mcp.server import MCPServer
from relay_client import RelayClient
from relay_session import RelaySession
from tools import register_tools

mcp = MCPServer("Relay MCP Server")
relay_session = RelaySession()
relay_client = RelayClient(relay_session)


@asynccontextmanager
async def local_client_context(tool_name):
    yield relay_client


register_tools(mcp, local_client_context)


# Start MCP Server

if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        # RelaySession owns an async HTTP client.
        # Its cleanup will be handled through the MCP lifecycle
        # in a later improvement.
        pass
