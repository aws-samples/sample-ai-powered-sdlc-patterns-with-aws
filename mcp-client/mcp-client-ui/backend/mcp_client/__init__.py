"""
MCP Client - A Python client for the Model Context Protocol.
"""

from mcp_client.client import MCPClient
from mcp_client.core.models import MCPClientConfig, MCPError, MCPRequest, MCPResponse, MCPServerInfo

__version__ = "0.1.0"

__all__ = [
    "MCPClient",
    "MCPClientConfig",
    "MCPError",
    "MCPRequest",
    "MCPResponse",
    "MCPServerInfo",
]