"""
Server selection strategies for the MCP Client.
"""

import logging
import secrets
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set

from mcp_client.core.models import MCPRequest, MCPServerInfo, ServerStatus

logger = logging.getLogger(__name__)


class ServerSelectionStrategy(ABC):
    """Base class for server selection strategies."""

    @abstractmethod
    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select a server for a request.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        pass


class PreferredServerStrategy(ServerSelectionStrategy):
    """Strategy that selects the preferred server if available."""

    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select the preferred server if available.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        if not request.preferred_server_id:
            return None
            
        server_id = request.preferred_server_id
        if server_id in available_servers:
            server = available_servers[server_id]
            # Accept both ACTIVE and DEGRADED servers for preferred server selection
            if server.status in [ServerStatus.ACTIVE, ServerStatus.DEGRADED]:
                # Check if the server has all required capabilities
                if self._server_has_capabilities(server, request.required_capabilities):
                    logger.debug(f"Selected preferred server {server_id} for request (status: {server.status})")
                    return server
                else:
                    logger.warning(
                        f"Preferred server {server_id} does not have all required capabilities: "
                        f"{request.required_capabilities}"
                    )
            else:
                logger.warning(f"Preferred server {server_id} is not active (status: {server.status})")
        else:
            logger.warning(f"Preferred server {server_id} not found in registry")
            
        return None
        
    def _server_has_capabilities(self, server: MCPServerInfo, required_capabilities: List[str]) -> bool:
        """
        Check if a server has all the required capabilities.
        
        Args:
            server: The server to check
            required_capabilities: The capabilities to check for
            
        Returns:
            bool: True if the server has all required capabilities, False otherwise
        """
        if not required_capabilities:
            return True
            
        return all(capability in server.capabilities for capability in required_capabilities)


class RoundRobinStrategy(ServerSelectionStrategy):
    """Strategy that selects servers in a round-robin fashion."""

    def __init__(self):
        """Initialize the round-robin strategy."""
        self._last_server_index: Dict[str, int] = {}  # capability -> last server index
        
    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select a server in a round-robin fashion.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        # Find servers with all required capabilities
        candidate_servers = self._find_servers_with_capabilities(
            request.required_capabilities, available_servers
        )
        if not candidate_servers:
            logger.warning(
                f"No servers found with all required capabilities: {request.required_capabilities}"
            )
            return None
            
        # Get the capability key for the round-robin index
        capability_key = self._get_capability_key(request.required_capabilities)
        
        # Get the current index for this capability
        current_index = self._last_server_index.get(capability_key, -1)
        
        # Convert candidate servers to a list for indexing
        server_ids = list(candidate_servers)
        
        # Find the next active server, fallback to degraded servers
        selected_server = None
        selected_index = -1
        
        for _ in range(len(server_ids)):
            current_index = (current_index + 1) % len(server_ids)
            server_id = server_ids[current_index]
            server = available_servers[server_id]
            
            if server.status == ServerStatus.ACTIVE:
                # Update the last server index
                self._last_server_index[capability_key] = current_index
                logger.debug(f"Selected server {server_id} for request using round-robin strategy")
                return server
            elif server.status == ServerStatus.DEGRADED and selected_server is None:
                # Keep track of the first degraded server as fallback
                selected_server = server
                selected_index = current_index
                
        # If no active servers found, use degraded server as fallback
        if selected_server:
            self._last_server_index[capability_key] = selected_index
            logger.debug(f"Selected degraded server {selected_server.server_id} for request using round-robin strategy")
            return selected_server
                
        logger.warning("No active or degraded servers found with required capabilities")
        return None
        
    def _get_capability_key(self, capabilities: List[str]) -> str:
        """
        Get a key for the round-robin index based on capabilities.
        
        Args:
            capabilities: The capabilities to create a key for
            
        Returns:
            str: A key for the round-robin index
        """
        if not capabilities:
            return "default"
            
        return ",".join(sorted(capabilities))
        
    def _find_servers_with_capabilities(
        self, required_capabilities: List[str], available_servers: Dict[str, MCPServerInfo]
    ) -> Set[str]:
        """
        Find servers that have all the required capabilities.
        
        Args:
            required_capabilities: The capabilities to look for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Set[str]: A set of server IDs that have all the required capabilities
        """
        if not required_capabilities:
            # If no capabilities are required, return all server IDs
            return set(available_servers.keys())
            
        # Find servers with all required capabilities
        server_ids = set()
        for server_id, server in available_servers.items():
            if all(capability in server.capabilities for capability in required_capabilities):
                server_ids.add(server_id)
                
        return server_ids


class RandomStrategy(ServerSelectionStrategy):
    """Strategy that selects servers randomly."""

    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select a server randomly.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        # Find servers with all required capabilities
        candidate_servers = self._find_servers_with_capabilities(
            request.required_capabilities, available_servers
        )
        if not candidate_servers:
            logger.warning(
                f"No servers found with all required capabilities: {request.required_capabilities}"
            )
            return None
            
        # Filter for active servers
        active_servers = [
            available_servers[server_id]
            for server_id in candidate_servers
            if available_servers[server_id].status == ServerStatus.ACTIVE
        ]
        
        if not active_servers:
            logger.warning("No active servers found with required capabilities")
            return None
            
        # Select a random server using cryptographically secure randomness
        server_index = secrets.randbelow(len(active_servers))
        server = active_servers[server_index]
        logger.debug(f"Selected server {server.server_id} for request using secure random strategy")
        return server
        
    def _find_servers_with_capabilities(
        self, required_capabilities: List[str], available_servers: Dict[str, MCPServerInfo]
    ) -> Set[str]:
        """
        Find servers that have all the required capabilities.
        
        Args:
            required_capabilities: The capabilities to look for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Set[str]: A set of server IDs that have all the required capabilities
        """
        if not required_capabilities:
            # If no capabilities are required, return all server IDs
            return set(available_servers.keys())
            
        # Find servers with all required capabilities
        server_ids = set()
        for server_id, server in available_servers.items():
            if all(capability in server.capabilities for capability in required_capabilities):
                server_ids.add(server_id)
                
        return server_ids


class LoadBalancedStrategy(ServerSelectionStrategy):
    """Strategy that selects servers based on load balancing."""

    def __init__(self):
        """Initialize the load-balanced strategy."""
        self._server_loads: Dict[str, int] = {}  # server_id -> current load
        
    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select a server based on load balancing.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        # Find servers with all required capabilities
        candidate_servers = self._find_servers_with_capabilities(
            request.required_capabilities, available_servers
        )
        if not candidate_servers:
            logger.warning(
                f"No servers found with all required capabilities: {request.required_capabilities}"
            )
            return None
            
        # Filter for active servers
        active_server_ids = [
            server_id
            for server_id in candidate_servers
            if available_servers[server_id].status == ServerStatus.ACTIVE
        ]
        
        if not active_server_ids:
            logger.warning("No active servers found with required capabilities")
            return None
            
        # Initialize load for new servers
        for server_id in active_server_ids:
            if server_id not in self._server_loads:
                self._server_loads[server_id] = 0
                
        # Find the server with the lowest load
        min_load = float("inf")
        min_load_server_id = None
        
        for server_id in active_server_ids:
            load = self._server_loads.get(server_id, 0)
            if load < min_load:
                min_load = load
                min_load_server_id = server_id
                
        if min_load_server_id:
            # Increment the load for the selected server
            self._server_loads[min_load_server_id] += 1
            logger.debug(
                f"Selected server {min_load_server_id} for request using load-balanced strategy "
                f"(load: {self._server_loads[min_load_server_id]})"
            )
            return available_servers[min_load_server_id]
            
        return None
        
    def request_completed(self, server_id: str) -> None:
        """
        Notify the strategy that a request has completed.
        
        Args:
            server_id: The ID of the server that completed the request
        """
        if server_id in self._server_loads:
            self._server_loads[server_id] = max(0, self._server_loads[server_id] - 1)
            logger.debug(f"Decreased load for server {server_id} to {self._server_loads[server_id]}")
            
    def _find_servers_with_capabilities(
        self, required_capabilities: List[str], available_servers: Dict[str, MCPServerInfo]
    ) -> Set[str]:
        """
        Find servers that have all the required capabilities.
        
        Args:
            required_capabilities: The capabilities to look for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Set[str]: A set of server IDs that have all the required capabilities
        """
        if not required_capabilities:
            # If no capabilities are required, return all server IDs
            return set(available_servers.keys())
            
        # Find servers with all required capabilities
        server_ids = set()
        for server_id, server in available_servers.items():
            if all(capability in server.capabilities for capability in required_capabilities):
                server_ids.add(server_id)
                
        return server_ids


class CompositeStrategy(ServerSelectionStrategy):
    """Strategy that combines multiple strategies."""

    def __init__(self, strategies: List[ServerSelectionStrategy]):
        """
        Initialize the composite strategy.
        
        Args:
            strategies: List of strategies to try in order
        """
        self.strategies = strategies
        
    def select_server(
        self, request: MCPRequest, available_servers: Dict[str, MCPServerInfo]
    ) -> Optional[MCPServerInfo]:
        """
        Select a server using multiple strategies.
        
        Args:
            request: The request to select a server for
            available_servers: Dictionary of available servers (server_id -> MCPServerInfo)
            
        Returns:
            Optional[MCPServerInfo]: The selected server, or None if no suitable server was found
        """
        for strategy in self.strategies:
            server = strategy.select_server(request, available_servers)
            if server:
                return server
                
        return None