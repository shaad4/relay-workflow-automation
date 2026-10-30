"""Subprocess regression of the unchanged stdio entry point, without live API access."""

import asyncio
import json
import secrets
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class StdioTests(unittest.TestCase):
    def test_stdio_initialization_tools_and_hello(self):
        # Bound the subprocess test so a transport failure cannot hang the suite.
        try:
            result = subprocess.run(
                [sys.executable, __file__, "--probe"], capture_output=True, text=True, timeout=20
            )
        except subprocess.TimeoutExpired:
            self.fail("Local stdio probe timed out (check subprocess sandbox restrictions)")
        self.assertEqual(result.returncode, 0, "Local stdio probe failed; no upstream API was used")
        report = json.loads(result.stdout)
        self.assertEqual(report["tools"], 16)
        self.assertTrue(report["hello"])
        self.assertTrue(report["contracts_match"])


async def probe():
    from contextlib import asynccontextmanager

    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.server import MCPServer
    from tools import register_tools

    @asynccontextmanager
    async def unused_context(name):
        raise AssertionError("Discovery must not create a Relay client")
        yield

    shared = MCPServer("contract comparison", log_level="ERROR")
    register_tools(shared, unused_context)
    expected = await shared.list_tools()
    env = {
        "RELAY_API_URL": "https://relay.invalid",
        "RELAY_EMAIL": "demo@example.invalid",
        "RELAY_PASSWORD": secrets.token_urlsafe(32),
    }
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            hello = await session.call_tool("relay_hello", {"name": "smoke"})

            def contracts(items):
                return {t.name: t.model_dump(by_alias=True) for t in items}

            print(
                json.dumps(
                    {
                        "tools": len(tools),
                        "hello": not hello.is_error,
                        "contracts_match": contracts(tools) == contracts(expected),
                    }
                )
            )


if __name__ == "__main__":
    if "--probe" in sys.argv:
        asyncio.run(probe())
    else:
        unittest.main()
