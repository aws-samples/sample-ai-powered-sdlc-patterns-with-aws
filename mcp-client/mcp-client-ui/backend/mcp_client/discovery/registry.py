"""
Server registry implementation for the MCP Client.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Type, Union

from mcp_client.core.interfaces import ServerDiscovery
from mcp_client.core.models import ErrorCode, MCPError, MCPRequest, MCPServerInfo, ServerStatus
from mcp_client.discovery.selection import (
    CompositeStrategy,
    PreferredServerStrategy,
    RoundRobinStrategy,
    ServerSelectionStrategy,
)
from mcp_client.transport.http import HTTPTransport

logger = logging.getLogger(__name__)


class InMemoryServerRegistry(ServerDiscovery):
    """In-memory implementation of the server registry."""

    def __init__(
        self,
        health_check_interval_seconds: float = 60.0,
        server_ttl_seconds: float = 300.0,
        transport: Optional[HTTPTransport] = None,
        selection_strategy: Optional[ServerSelectionStrategy] = None,
    ):
        """
        Initialize the in-memory server registry.

        Args:
            health_check_interval_seconds: Interval between health checks in seconds
            server_ttl_seconds: Time-to-live for server entries in seconds
            transport: Transport to use for health checks, or None to create a new one
        """
        self.health_check_interval_seconds = health_check_interval_seconds
        self.server_ttl_seconds = server_ttl_seconds
        self._servers: Dict[str, MCPServerInfo] = {}
        self._capabilities_index: Dict[str, Set[str]] = {}  # capability -> set of server_ids
        self._transport = transport or HTTPTransport()
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Set up the selection strategy
        if selection_strategy is None:
            # Default to a composite strategy that tries preferred server first, then round-robin
            self._selection_strategy = CompositeStrategy([
                PreferredServerStrategy(),
                RoundRobinStrategy(),
            ])
        else:
            self._selection_strategy = selection_strategy
        
        logger.info(
            f"Initialized in-memory server registry with health_check_interval={health_check_interval_seconds}s, "
            f"server_ttl={server_ttl_seconds}s"
        )
        
    async def start(self) -> None:
        """Start the health check background task."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started server health check background task")
            
    async def stop(self) -> None:
        """Stop the health check background task."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped server health check background task")
            
    async def _health_check_loop(self) -> None:
        """Background task to periodically check server health and remove expired servers."""
        try:
            while True:
                await self._check_all_servers_health()
                await self._remove_expired_servers()
                await asyncio.sleep(self.health_check_interval_seconds)
        except asyncio.CancelledError:
            logger.debug("Health check loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
            
    async def _check_all_servers_health(self) -> None:
        """Check the health of all registered servers."""
        logger.debug("Starting health check for all servers")
        
        async with self._lock:
            server_ids = list(self._servers.keys())
            
        for server_id in server_ids:
            try:
                await self._check_server_health(server_id)
            except Exception as e:
                logger.error(f"Error checking health of server {server_id}: {e}")
                
        logger.debug("Completed health check for all servers")
        
    async def _check_server_health(self, server_id: str) -> None:
        """
        Check the health of a specific server.
        
        Args:
            server_id: The ID of the server to check
        """
        async with self._lock:
            if server_id not in self._servers:
                return
                
            server_info = self._servers[server_id]
            
        # Check server health using the transport
        is_healthy = await self._transport.check_server_health(server_info)
        
        async with self._lock:
            if server_id not in self._servers:
                return
                
            if is_healthy:
                # Update the server status and last_seen timestamp
                server_info.status = ServerStatus.ACTIVE
                server_info.last_seen = datetime.now()
                self._servers[server_id] = server_info
                logger.debug(f"Server {server_id} is healthy")
            else:
                # Mark the server as degraded or inactive
                if server_info.status == ServerStatus.ACTIVE:
                    server_info.status = ServerStatus.DEGRADED
                    logger.warning(f"Server {server_id} is degraded")
                else:
                    server_info.status = ServerStatus.INACTIVE
                    logger.warning(f"Server {server_id} is inactive")
                    
                self._servers[server_id] = server_info
                
    async def _remove_expired_servers(self) -> None:
        """Remove servers that haven't been seen for longer than the TTL."""
        logger.debug("Checking for expired servers")
        now = datetime.now()
        expired_server_ids = []
        
        async with self._lock:
            for server_id, server_info in self._servers.items():
                if server_info.last_seen is None:
                    continue
                    
                age = now - server_info.last_seen
                if age > timedelta(seconds=self.server_ttl_seconds):
                    expired_server_ids.append(server_id)
                    
            for server_id in expired_server_ids:
                await self._remove_server(server_id)
                
        if expired_server_ids:
            logger.info(f"Removed {len(expired_server_ids)} expired servers: {expired_server_ids}")
            
    async def _remove_server(self, server_id: str) -> None:
        """
        Remove a server from the registry.
        
        Args:
            server_id: The ID of the server to remove
        """
        if server_id not in self._servers:
            return
            
        server_info = self._servers.pop(server_id)
        
        # Remove from capabilities index
        for capability in server_info.capabilities:
            if capability in self._capabilities_index:
                self._capabilities_index[capability].discard(server_id)
                if not self._capabilities_index[capability]:
                    del self._capabilities_index[capability]
                    
        logger.debug(f"Removed server {server_id} from registry")
        
    async def _add_server(self, server_info: MCPServerInfo) -> None:
        """
        Add a server to the registry.
        
        Args:
            server_info: The server information to add
        """
        server_id = server_info.server_id
        
        # Set last_seen to now if not provided
        if server_info.last_seen is None:
            server_info.last_seen = datetime.now()
            
        self._servers[server_id] = server_info
        
        # Update capabilities index
        for capability in server_info.capabilities:
            if capability not in self._capabilities_index:
                self._capabilities_index[capability] = set()
            self._capabilities_index[capability].add(server_id)
            
        logger.debug(f"Added server {server_id} to registry with capabilities {server_info.capabilities}")

    async def discover_servers(self) -> List[MCPServerInfo]:
        """
        Discover available MCP servers.
        
        Returns:
            List[MCPServerInfo]: A list of available servers
        """
        async with self._lock:
            # Return a copy of the server list to avoid modification during iteration
            return list(self._servers.values())
            
    async def register_server(self, server_info: MCPServerInfo, skip_health_check: bool = False) -> bool:
        """
        Register a new server.
        
        Args:
            server_info: Information about the server to register
            skip_health_check: Whether to skip the health check during registration
            
        Returns:
            bool: True if the server was registered successfully, False otherwise
        """
        try:
            # Validate server info
            if not server_info.server_id:
                raise ValueError("Server ID is required")
            # Endpoint URL is only required for non-stdio servers
            # Check both the transport field and metadata for transport type
            transport_type = getattr(server_info, 'transport', None) or server_info.metadata.get('transport')
            if not server_info.endpoint_url and transport_type != "stdio":
                raise ValueError("Endpoint URL is required")
            if not server_info.capabilities:
                raise ValueError("At least one capability is required")
                
            # Check if the server is healthy before registering (unless skipped)
            if not skip_health_check:
                is_healthy = await self._transport.check_server_health(server_info)
                if not is_healthy:
                    logger.warning(f"Server {server_info.server_id} failed health check during registration")
                    # Still register the server but mark it as degraded
                    server_info.status = ServerStatus.DEGRADED
            else:
                logger.info(f"Skipping health check for server {server_info.server_id} during registration")
                
            async with self._lock:
                await self._add_server(server_info)
                
            logger.info(f"Registered server {server_info.server_id} with capabilities {server_info.capabilities}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering server {server_info.server_id}: {e}")
            return False
            
    async def unregister_server(self, server_id: str) -> bool:
        """
        Unregister a server.
        
        Args:
            server_id: The ID of the server to unregister
            
        Returns:
            bool: True if the server was unregistered successfully, False otherwise
        """
        try:
            async with self._lock:
                if server_id not in self._servers:
                    logger.warning(f"Attempted to unregister unknown server {server_id}")
                    return False
                    
                await self._remove_server(server_id)
                
            logger.info(f"Unregistered server {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering server {server_id}: {e}")
            return False
            
    async def select_server(self, request: MCPRequest) -> Optional[MCPServerInfo]:
        """
        Select an appropriate server for a request.
        
        Args:
            request: The request to select a server for
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        async with self._lock:
            # Use the selection strategy to select a server
            server = self._selection_strategy.select_server(request, self._servers)
            
            if server:
                logger.debug(f"Selected server {server.server_id} for request")
            else:
                logger.warning("No suitable server found for request")
                
            return server
            
    def get_selection_strategy(self) -> ServerSelectionStrategy:
        """
        Get the current selection strategy.
        
        Returns:
            ServerSelectionStrategy: The current selection strategy
        """
        return self._selection_strategy
        
    def set_selection_strategy(self, strategy: ServerSelectionStrategy) -> None:
        """
        Set the selection strategy.
        
        Args:
            strategy: The selection strategy to use
        """
        self._selection_strategy = strategy
        logger.info(f"Set selection strategy to {strategy.__class__.__name__}")