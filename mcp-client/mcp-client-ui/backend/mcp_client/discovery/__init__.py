"""
Server discovery module for the MCP Client.
"""

from mcp_client.discovery.registry import InMemoryServerRegistry
from mcp_client.discovery.selection import (
    CompositeStrategy,
    LoadBalancedStrategy,
    PreferredServerStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    ServerSelectionStrategy,
)

__all__ = [
    "InMemoryServerRegistry",
    "ServerSelectionStrategy",
    "PreferredServerStrategy",
    "RoundRobinStrategy",
    "RandomStrategy",
    "LoadBalancedStrategy",
    "CompositeStrategy",
]