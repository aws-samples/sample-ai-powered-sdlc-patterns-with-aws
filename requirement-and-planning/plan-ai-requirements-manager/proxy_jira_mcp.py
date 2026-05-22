#!/usr/bin/env python3
"""
JIRA MCP Proxy Server

A local MCP (Model Context Protocol) server that proxies requests to a remote
JIRA MCP backend server. It handles authentication and forwards tool calls
via JSON-RPC over stdio.

Configuration (via environment variables):
    MCP_BACKEND_URL: URL of the backend MCP server (e.g., API Gateway endpoint)
    MCP_ACCESS_TOKEN: Bearer token for authenticating with the backend server

See .env.example for configuration details.
"""

import asyncio
import json
import os
import sys
import urllib.request
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Load environment variables
load_dotenv()

# Configuration from environment variables
MCP_BACKEND_URL = os.getenv("MCP_BACKEND_URL")
MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN")

if not MCP_BACKEND_URL:
    print(
        "ERROR: MCP_BACKEND_URL environment variable is required. "
        "Set it to your backend MCP server URL (e.g., API Gateway endpoint).",
        file=sys.stderr,
    )
    sys.exit(1)

if not MCP_ACCESS_TOKEN:
    print(
        "ERROR: MCP_ACCESS_TOKEN environment variable is required. "
        "Set it to your bearer token for the backend MCP server.",
        file=sys.stderr,
    )
    sys.exit(1)


def make_mcp_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Make authenticated request to the backend MCP server."""
    data = json.dumps(request_data).encode("utf-8")
    req = urllib.request.Request(
        f"{MCP_BACKEND_URL.rstrip('/')}/", data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {MCP_ACCESS_TOKEN}")

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


# Create MCP server
server = Server("jira-mcp-proxy")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available JIRA tools from the backend server."""
    request_data = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

    try:
        response = make_mcp_request(request_data)
        if "result" in response and "tools" in response["result"]:
            return [
                Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool["inputSchema"],
                )
                for tool in response["result"]["tools"]
            ]
    except Exception as e:
        print(f"Error listing tools: {e}", file=sys.stderr)

    return []


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Call a JIRA tool on the backend server."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }

    try:
        response = make_mcp_request(request_data)
        if "result" in response and "content" in response["result"]:
            return [
                TextContent(type="text", text=content["text"])
                for content in response["result"]["content"]
                if content.get("type") == "text"
            ]
        elif "error" in response:
            return [
                TextContent(
                    type="text", text=f"Error: {response['error']['message']}"
                )
            ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling tool: {str(e)}")]

    return [TextContent(type="text", text="No response received")]


async def main():
    """Run the MCP proxy server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
