"""
MCP Server Discovery and Fallback Service

Provides MCP server availability checking, discovery, and graceful fallback functionality.
Includes logging for server availability status and handles both MCP-enabled and fallback scenarios.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from mcp_client.client import MCPClient
from mcp_client.core.models import MCPServerInfo, MCPRequest, MCPResponse, ErrorCode, MCPError


class ServerAvailabilityStatus(Enum):
    """Server availability status enumeration"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class MCPServerDiscovery:
    """
    MCP Server Discovery and Fallback Service
    
    Provides functionality to:
    - Check MCP server availability before attempting to use design tools
    - Implement fallback to generic AI responses when MCP servers are not found
    - Create graceful degradation logic that searches for available MCP servers
    - Add logging for MCP server availability status
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None, check_interval: int = 60):
        """
        Initialize the MCP server discovery service
        
        Args:
            mcp_client: Optional MCP client instance
            check_interval: Interval in seconds between server availability checks
        """
        self.mcp_client = mcp_client
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        
        # Server availability tracking
        self._server_status: Dict[str, ServerAvailabilityStatus] = {}
        self._server_last_checked: Dict[str, datetime] = {}
        self._server_capabilities: Dict[str, List[str]] = {}
        self._server_errors: Dict[str, List[str]] = {}
        
        # Background task for periodic health checks
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Fallback configuration
        self.fallback_enabled = True
        self.max_fallback_attempts = 3
        
        self.logger.debug("Initialized MCP Server Discovery service")
    
    async def start(self) -> None:
        """Start the server discovery service with periodic health checks"""
        if self._running:
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(self._periodic_health_check())
        self.logger.info("Started MCP Server Discovery service")
    
    async def stop(self) -> None:
        """Stop the server discovery service"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        
        self.logger.info("Stopped MCP Server Discovery service")
    
    async def _periodic_health_check(self) -> None:
        """Background task for periodic server health checks"""
        while self._running:
            try:
                await self.check_all_servers_availability()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic health check: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def check_server_availability(self, server_id: Optional[str] = None) -> Dict[str, ServerAvailabilityStatus]:
        """
        Check availability of MCP servers
        
        Args:
            server_id: Optional specific server ID to check, if None checks all servers
            
        Returns:
            Dict mapping server IDs to their availability status
        """
        if not self.mcp_client:
            self.logger.warning("No MCP client available for server availability check")
            return {}
        
        try:
            # Get available servers from MCP client
            servers = await self.mcp_client.get_servers()
            
            if not servers:
                self.logger.info("No MCP servers discovered")
                return {}
            
            # Filter to specific server if requested
            if server_id:
                servers = [s for s in servers if s.server_id == server_id]
                if not servers:
                    self.logger.warning(f"Server {server_id} not found in discovered servers")
                    return {server_id: ServerAvailabilityStatus.UNAVAILABLE}
            
            # Check each server's availability
            availability_results = {}
            
            for server in servers:
                status = await self._check_individual_server(server)
                availability_results[server.server_id] = status
                
                # Update internal tracking
                self._server_status[server.server_id] = status
                self._server_last_checked[server.server_id] = datetime.now()
                self._server_capabilities[server.server_id] = server.capabilities
                
                # Log status change
                self.logger.info(
                    f"Server {server.server_id} status: {status.value}",
                    extra={
                        "server_id": server.server_id,
                        "status": status.value,
                        "capabilities": server.capabilities,
                        "endpoint": server.endpoint_url
                    }
                )
            
            return availability_results
            
        except Exception as e:
            self.logger.error(f"Error checking server availability: {e}")
            return {}
    
    async def _check_individual_server(self, server: MCPServerInfo) -> ServerAvailabilityStatus:
        """
        Check availability of an individual MCP server
        
        Args:
            server: Server information
            
        Returns:
            ServerAvailabilityStatus: The server's availability status
        """
        try:
            # Create a simple tools list request to test server responsiveness
            health_check_request = MCPRequest(
                request_type="tools/list",
                content={"query": ""},
                required_capabilities=[],
                preferred_server_id=server.server_id
            )
            
            # Set a shorter timeout for health checks
            start_time = time.time()
            
            try:
                response = await asyncio.wait_for(
                    self.mcp_client.send_request(health_check_request),
                    timeout=10.0  # 10 second timeout for health checks
                )
                
                response_time = time.time() - start_time
                
                if response and hasattr(response, 'status'):
                    if response_time > 5.0:
                        # Server is responding but slowly
                        self.logger.warning(f"Server {server.server_id} responding slowly: {response_time:.2f}s")
                        return ServerAvailabilityStatus.DEGRADED
                    else:
                        return ServerAvailabilityStatus.AVAILABLE
                else:
                    return ServerAvailabilityStatus.DEGRADED
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Server {server.server_id} health check timed out")
                return ServerAvailabilityStatus.UNAVAILABLE
            except MCPError as e:
                if e.error_code == ErrorCode.SERVER_ERROR:
                    self.logger.warning(f"Server {server.server_id} returned error: {e.message}")
                    return ServerAvailabilityStatus.DEGRADED
                else:
                    return ServerAvailabilityStatus.UNAVAILABLE
                    
        except Exception as e:
            self.logger.error(f"Error checking server {server.server_id}: {e}")
            self._server_errors.setdefault(server.server_id, []).append(str(e))
            return ServerAvailabilityStatus.UNAVAILABLE
    
    async def check_all_servers_availability(self) -> Dict[str, ServerAvailabilityStatus]:
        """
        Check availability of all discovered MCP servers
        
        Returns:
            Dict mapping server IDs to their availability status
        """
        return await self.check_server_availability()
    
    async def find_available_servers_for_capabilities(self, required_capabilities: List[str]) -> List[MCPServerInfo]:
        """
        Find available MCP servers that support the required capabilities
        
        Args:
            required_capabilities: List of required capabilities
            
        Returns:
            List of available servers that support the capabilities
        """
        if not self.mcp_client:
            self.logger.warning("No MCP client available for server search")
            return []
        
        try:
            # Get all servers with required capabilities
            servers = await self.mcp_client.get_servers(capabilities=required_capabilities)
            
            if not servers:
                self.logger.info(f"No servers found with capabilities: {required_capabilities}")
                return []
            
            # Filter to only available servers
            available_servers = []
            
            for server in servers:
                # Store server capabilities for later use
                self._server_capabilities[server.server_id] = server.capabilities
                
                # Check if we have recent status information
                if server.server_id in self._server_status:
                    last_checked = self._server_last_checked.get(server.server_id)
                    if last_checked and (datetime.now() - last_checked).seconds < self.check_interval:
                        # Use cached status if recent
                        status = self._server_status[server.server_id]
                    else:
                        # Re-check if status is stale
                        status = await self._check_individual_server(server)
                        self._server_status[server.server_id] = status
                        self._server_last_checked[server.server_id] = datetime.now()
                else:
                    # First time checking this server
                    status = await self._check_individual_server(server)
                    self._server_status[server.server_id] = status
                    self._server_last_checked[server.server_id] = datetime.now()
                
                # Include available and degraded servers
                if status in [ServerAvailabilityStatus.AVAILABLE, ServerAvailabilityStatus.DEGRADED]:
                    available_servers.append(server)
                    self.logger.debug(f"Found available server {server.server_id} for capabilities {required_capabilities}")
            
            self.logger.info(f"Found {len(available_servers)} available servers for capabilities: {required_capabilities}")
            return available_servers
            
        except Exception as e:
            self.logger.error(f"Error finding available servers: {e}")
            return []
    
    async def send_request_with_fallback(
        self, 
        request: MCPRequest, 
        fallback_handler: Optional[callable] = None
    ) -> Tuple[Optional[MCPResponse], bool]:
        """
        Send request to MCP servers with automatic fallback to generic AI
        
        Args:
            request: The MCP request to send
            fallback_handler: Optional fallback function to call if MCP fails
            
        Returns:
            Tuple of (response, used_mcp) where used_mcp indicates if MCP was used
        """
        if not self.mcp_client:
            self.logger.info("No MCP client available, using fallback immediately")
            if fallback_handler:
                fallback_response = await fallback_handler(request)
                return fallback_response, False
            return None, False
        
        # First, try to find available servers for the request
        available_servers = await self.find_available_servers_for_capabilities(
            request.required_capabilities
        )
        
        if not available_servers:
            self.logger.warning(
                f"No available MCP servers found for capabilities: {request.required_capabilities}, using fallback"
            )
            if fallback_handler and self.fallback_enabled:
                fallback_response = await fallback_handler(request)
                return fallback_response, False
            return None, False
        
        # Try to send the request to available servers
        last_error = None
        
        for attempt in range(self.max_fallback_attempts):
            try:
                self.logger.debug(f"Attempting MCP request (attempt {attempt + 1}/{self.max_fallback_attempts})")
                response = await self.mcp_client.send_request(request)
                
                if response:
                    self.logger.info("Successfully sent request via MCP")
                    return response, True
                    
            except MCPError as e:
                last_error = e
                self.logger.warning(f"MCP request failed (attempt {attempt + 1}): {e.message}")
                
                # If it's a server error, mark the server as degraded
                if e.error_code == ErrorCode.SERVER_ERROR and hasattr(request, 'preferred_server_id'):
                    server_id = request.preferred_server_id
                    if server_id:
                        self._server_status[server_id] = ServerAvailabilityStatus.DEGRADED
                        self.logger.warning(f"Marked server {server_id} as degraded due to error")
                
                # Wait before retry
                if attempt < self.max_fallback_attempts - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
            
            except Exception as e:
                last_error = e
                self.logger.error(f"Unexpected error in MCP request (attempt {attempt + 1}): {e}")
                break
        
        # All MCP attempts failed, use fallback if available
        self.logger.warning(f"All MCP attempts failed, using fallback. Last error: {last_error}")
        
        if fallback_handler and self.fallback_enabled:
            try:
                fallback_response = await fallback_handler(request)
                return fallback_response, False
            except Exception as e:
                self.logger.error(f"Fallback handler also failed: {e}")
                return None, False
        
        return None, False
    
    def get_server_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all server statuses
        
        Returns:
            Dictionary containing server status summary
        """
        summary = {
            "total_servers": len(self._server_status),
            "available_servers": len([s for s in self._server_status.values() if s == ServerAvailabilityStatus.AVAILABLE]),
            "degraded_servers": len([s for s in self._server_status.values() if s == ServerAvailabilityStatus.DEGRADED]),
            "unavailable_servers": len([s for s in self._server_status.values() if s == ServerAvailabilityStatus.UNAVAILABLE]),
            "last_check": max(self._server_last_checked.values()) if self._server_last_checked else None,
            "servers": {}
        }
        
        for server_id, status in self._server_status.items():
            summary["servers"][server_id] = {
                "status": status.value,
                "last_checked": self._server_last_checked.get(server_id),
                "capabilities": self._server_capabilities.get(server_id, []),
                "recent_errors": self._server_errors.get(server_id, [])[-3:]  # Last 3 errors
            }
        
        return summary
    
    async def is_mcp_available_for_capabilities_async(self, capabilities: List[str]) -> bool:
        """
        Async check if MCP is available for given capabilities
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            bool: True if at least one server with some of the capabilities is available
        """
        # If no server status is available, check server availability first
        if not self._server_status:
            self.logger.debug("No server status available, checking server availability first")
            await self.check_all_servers_availability()
        
        for server_id, status in self._server_status.items():
            if status in [ServerAvailabilityStatus.AVAILABLE, ServerAvailabilityStatus.DEGRADED]:
                server_capabilities = self._server_capabilities.get(server_id, [])
                # Check if server has at least one of the required capabilities
                if any(cap in server_capabilities for cap in capabilities):
                    self.logger.debug(f"Found available server {server_id} with some capabilities from {capabilities}")
                    return True
        
        self.logger.debug(f"No available servers found for capabilities {capabilities}")
        return False
    
    def is_mcp_available_for_capabilities(self, capabilities: List[str]) -> bool:
        """
        Quick check if MCP is available for given capabilities (synchronous version)
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            bool: True if at least one server with some of the capabilities is available
        """
        if not self._server_status:
            self.logger.debug("No server status available for capability check")
            return False
        
        for server_id, status in self._server_status.items():
            if status in [ServerAvailabilityStatus.AVAILABLE, ServerAvailabilityStatus.DEGRADED]:
                server_capabilities = self._server_capabilities.get(server_id, [])
                # Check if server has at least one of the required capabilities
                if any(cap in server_capabilities for cap in capabilities):
                    self.logger.debug(f"Found available server {server_id} with some capabilities from {capabilities}")
                    return True
        
        self.logger.debug(f"No available servers found for capabilities {capabilities}")
        return False
    
    def enable_fallback(self, enabled: bool = True) -> None:
        """
        Enable or disable fallback functionality
        
        Args:
            enabled: Whether to enable fallback
        """
        self.fallback_enabled = enabled
        self.logger.info(f"Fallback functionality {'enabled' if enabled else 'disabled'}")
    
    def set_max_fallback_attempts(self, attempts: int) -> None:
        """
        Set maximum number of fallback attempts
        
        Args:
            attempts: Maximum number of attempts
        """
        self.max_fallback_attempts = max(1, attempts)
        self.logger.info(f"Set maximum fallback attempts to {self.max_fallback_attempts}")