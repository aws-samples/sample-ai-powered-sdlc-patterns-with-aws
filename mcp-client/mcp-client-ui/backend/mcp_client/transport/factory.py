"""
Transport factory for creating appropriate transports based on server configuration.
"""

import logging
from typing import Any, Dict, Optional

from mcp_client.core.interfaces import Transport
from mcp_client.core.models import MCPServerInfo
from mcp_client.transport.http import HTTPTransport
from mcp_client.transport.stdio import StdioTransport

logger = logging.getLogger(__name__)


class TransportFactory:
    """Factory for creating appropriate transports based on server configuration."""
    
    def __init__(
        self,
        default_timeout_seconds: float = 120.0,
        default_max_retries: int = 3,
        default_retry_backoff_factor: float = 1.5,
        **http_transport_kwargs
    ):
        """
        Initialize the transport factory.
        
        Args:
            default_timeout_seconds: Default timeout for requests
            default_max_retries: Default max retries
            default_retry_backoff_factor: Default retry backoff factor
            **http_transport_kwargs: Additional kwargs for HTTP transport
        """
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_retries = default_max_retries
        self.default_retry_backoff_factor = default_retry_backoff_factor
        self.http_transport_kwargs = http_transport_kwargs
        
        # Cache transports to reuse them
        self._http_transport: Optional[HTTPTransport] = None
        self._stdio_transport: Optional[StdioTransport] = None
    
    def get_transport_for_server(self, server_info: MCPServerInfo) -> Transport:
        """
        Get the appropriate transport for a server.
        
        Args:
            server_info: Information about the server
            
        Returns:
            Transport: The appropriate transport for the server
        """
        # Check if this is a stdio-based server
        if self._is_stdio_server(server_info):
            return self._get_stdio_transport()
        else:
            return self._get_http_transport()
    
    def _is_stdio_server(self, server_info: MCPServerInfo) -> bool:
        """
        Determine if a server uses stdio transport.
        
        Args:
            server_info: Information about the server
            
        Returns:
            bool: True if the server uses stdio transport
        """
        # Check for transport field in metadata
        metadata = server_info.metadata or {}
        transport_type = metadata.get('transport')
        
        if transport_type in ['stdio', 'subprocess']:
            return True
        
        # Check if command and args are present (indicates subprocess)
        if metadata.get('command') and metadata.get('args'):
            return True
        
        # Check endpoint URL for stdio protocol
        if server_info.endpoint_url and server_info.endpoint_url.startswith('stdio://'):
            return True
        
        return False
    
    def _get_http_transport(self) -> HTTPTransport:
        """Get or create the HTTP transport."""
        if self._http_transport is None:
            self._http_transport = HTTPTransport(
                timeout_seconds=self.default_timeout_seconds,
                max_retries=self.default_max_retries,
                retry_backoff_factor=self.default_retry_backoff_factor,
                **self.http_transport_kwargs
            )
        return self._http_transport
    
    def _get_stdio_transport(self) -> StdioTransport:
        """Get or create the stdio transport."""
        if self._stdio_transport is None:
            self._stdio_transport = StdioTransport(
                timeout_seconds=self.default_timeout_seconds,
                max_retries=self.default_max_retries,
                retry_backoff_factor=self.default_retry_backoff_factor
            )
        return self._stdio_transport
    
    async def cleanup(self):
        """Clean up all transports."""
        if self._stdio_transport:
            await self._stdio_transport.cleanup()


class MultiTransport(Transport):
    """
    A transport that delegates to different transports based on server configuration.
    """
    
    def __init__(self, transport_factory: TransportFactory):
        """
        Initialize the multi-transport.
        
        Args:
            transport_factory: Factory for creating transports
        """
        self.transport_factory = transport_factory
    
    async def send_request(
        self, server_info: MCPServerInfo, formatted_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a formatted request to a server using the appropriate transport.
        
        Args:
            server_info: Information about the server to send the request to
            formatted_request: The formatted request to send
            
        Returns:
            Dict[str, Any]: The raw response from the server
        """
        # Get the appropriate transport for this server
        transport = self.transport_factory.get_transport_for_server(server_info)
        
        # For stdio servers, we need to add command/args to the server info
        if isinstance(transport, StdioTransport):
            server_info = self._prepare_stdio_server_info(server_info)
        
        # Delegate to the appropriate transport
        return await transport.send_request(server_info, formatted_request)
    
    async def check_server_health(self, server_info: MCPServerInfo) -> bool:
        """
        Check if a server is healthy using the appropriate transport.
        
        Args:
            server_info: Information about the server to check
            
        Returns:
            bool: True if the server is healthy, False otherwise
        """
        # Get the appropriate transport for this server
        transport = self.transport_factory.get_transport_for_server(server_info)
        
        # For stdio servers, we need to add command/args to the server info
        if isinstance(transport, StdioTransport):
            server_info = self._prepare_stdio_server_info(server_info)
        
        # Delegate to the appropriate transport
        return await transport.check_server_health(server_info)
    
    def _prepare_stdio_server_info(self, server_info: MCPServerInfo) -> MCPServerInfo:
        """
        Prepare server info for stdio transport by ensuring command/args are in metadata.
        
        Args:
            server_info: Original server info
            
        Returns:
            MCPServerInfo: Server info with command/args in metadata
        """
        # Create a copy of the server info
        metadata = dict(server_info.metadata or {})
        
        # If command/args are not in metadata, try to extract from other fields
        if 'command' not in metadata:
            # Check if they're stored as top-level fields (from JSON config)
            # This would require modifying the config loader, but for now we'll assume
            # they're already in metadata
            pass
        
        # Create new server info with updated metadata
        new_server_info = MCPServerInfo(
            server_id=server_info.server_id,
            endpoint_url=server_info.endpoint_url,
            capabilities=server_info.capabilities,
            server_type=server_info.server_type,
            health_check_url=server_info.health_check_url,
            health_check_method=server_info.health_check_method,
            metadata=metadata,
            last_seen=server_info.last_seen,
            status=server_info.status,
            auth_config=server_info.auth_config,
            auth=server_info.auth
        )
        
        return new_server_info