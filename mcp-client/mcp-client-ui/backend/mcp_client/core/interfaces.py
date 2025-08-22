"""
Core interfaces for the MCP Client.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from mcp_client.core.models import MCPRequest, MCPResponse, MCPServerInfo


@runtime_checkable
class ProtocolHandler(Protocol):
    """Interface for handling MCP protocol operations."""

    @abstractmethod
    def validate_request(self, request: MCPRequest) -> bool:
        """
        Validate that a request conforms to the MCP protocol.
        
        Args:
            request: The request to validate
            
        Returns:
            bool: True if the request is valid, False otherwise
        """
        ...

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that a response conforms to the MCP protocol.
        
        Args:
            response: The raw response to validate
            
        Returns:
            bool: True if the response is valid, False otherwise
        """
        ...

    @abstractmethod
    def format_request(self, request: MCPRequest) -> Dict[str, Any]:
        """
        Format a request according to the MCP protocol.
        
        Args:
            request: The request to format
            
        Returns:
            Dict[str, Any]: The formatted request
        """
        ...

    @abstractmethod
    def parse_response(self, raw_response: Dict[str, Any]) -> MCPResponse:
        """
        Parse a raw response into an MCPResponse object.
        
        Args:
            raw_response: The raw response to parse
            
        Returns:
            MCPResponse: The parsed response
        """
        ...


@runtime_checkable
class Transport(Protocol):
    """Interface for handling transport operations."""

    @abstractmethod
    async def send_request(
        self, server_info: MCPServerInfo, formatted_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a formatted request to a server and return the raw response.
        
        Args:
            server_info: Information about the server to send the request to
            formatted_request: The formatted request to send
            
        Returns:
            Dict[str, Any]: The raw response from the server
        """
        ...

    @abstractmethod
    async def check_server_health(self, server_info: MCPServerInfo) -> bool:
        """
        Check if a server is healthy.
        
        Args:
            server_info: Information about the server to check
            
        Returns:
            bool: True if the server is healthy, False otherwise
        """
        ...


@runtime_checkable
class ServerDiscovery(Protocol):
    """Interface for server discovery operations."""

    @abstractmethod
    async def discover_servers(self) -> List[MCPServerInfo]:
        """
        Discover available MCP servers.
        
        Returns:
            List[MCPServerInfo]: A list of available servers
        """
        ...

    @abstractmethod
    async def register_server(self, server_info: MCPServerInfo) -> bool:
        """
        Register a new server.
        
        Args:
            server_info: Information about the server to register
            
        Returns:
            bool: True if the server was registered successfully, False otherwise
        """
        ...

    @abstractmethod
    async def unregister_server(self, server_id: str) -> bool:
        """
        Unregister a server.
        
        Args:
            server_id: The ID of the server to unregister
            
        Returns:
            bool: True if the server was unregistered successfully, False otherwise
        """
        ...

    @abstractmethod
    async def select_server(self, request: MCPRequest) -> Optional[MCPServerInfo]:
        """
        Select an appropriate server for a request.
        
        Args:
            request: The request to select a server for
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        ...


class MCPClient(ABC):
    """Interface for the MCP Client."""

    @abstractmethod
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send a request to an appropriate MCP server.
        
        Args:
            request: The request to send
            
        Returns:
            MCPResponse: The response from the server
        """
        ...

    @abstractmethod
    def send_request_sync(self, request: MCPRequest) -> MCPResponse:
        """
        Synchronous version of send_request.
        
        Args:
            request: The request to send
            
        Returns:
            MCPResponse: The response from the server
        """
        ...

    @abstractmethod
    async def register_server(self, server_info: MCPServerInfo) -> bool:
        """
        Register a new MCP server.
        
        Args:
            server_info: Information about the server to register
            
        Returns:
            bool: True if the server was registered successfully, False otherwise
        """
        ...

    @abstractmethod
    async def get_servers(self, capabilities: Optional[List[str]] = None) -> List[MCPServerInfo]:
        """
        Get available servers, optionally filtered by capabilities.
        
        Args:
            capabilities: Optional list of capabilities to filter servers by
            
        Returns:
            List[MCPServerInfo]: A list of available servers
        """
        ...