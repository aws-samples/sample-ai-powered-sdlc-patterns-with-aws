"""
Stdio transport implementation for the MCP Client.
Supports subprocess-based MCP servers that communicate via stdin/stdout.
"""

import asyncio
import json
import logging
import os
import signal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp_client.core.interfaces import Transport
from mcp_client.core.models import ErrorCode, MCPError, MCPServerInfo

logger = logging.getLogger(__name__)


class StdioTransport(Transport):
    """Stdio transport implementation for subprocess-based MCP servers."""

    def __init__(
        self,
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        retry_backoff_factor: float = 1.5,
    ):
        """
        Initialize the stdio transport.

        Args:
            timeout_seconds: Timeout for requests in seconds
            max_retries: Maximum number of retries for failed requests
            retry_backoff_factor: Factor to increase backoff time between retries
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        
        # Track active processes
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._process_locks: Dict[str, asyncio.Lock] = {}
        self._communication_locks: Dict[str, asyncio.Lock] = {}  # Locks for process communication
        self._initialized_processes: set = set()  # Track which processes have been initialized
        self._request_counter = 0  # Counter for unique request IDs
        
        logger.info(
            f"Initialized stdio transport with timeout={timeout_seconds}s, "
            f"max_retries={max_retries}"
        )

    async def _get_or_create_process(self, server_info: MCPServerInfo) -> asyncio.subprocess.Process:
        """
        Get or create a subprocess for the given server.
        
        Args:
            server_info: Information about the server
            
        Returns:
            asyncio.subprocess.Process: The subprocess
            
        Raises:
            MCPError: If the process cannot be created
        """
        server_id = server_info.server_id
        
        # Get or create a lock for this server
        if server_id not in self._process_locks:
            self._process_locks[server_id] = asyncio.Lock()
        
        async with self._process_locks[server_id]:
            # Check if we already have a running process
            if server_id in self._processes:
                process = self._processes[server_id]
                if process.returncode is None:  # Process is still running
                    return process
                else:
                    # Process has died, remove it
                    del self._processes[server_id]
                    self._initialized_processes.discard(server_id)
            
            # Extract command and args from server info
            # We expect the server_info to have command and args in metadata
            metadata = server_info.metadata or {}
            command = metadata.get('command')
            args = metadata.get('args', [])
            
            if not command:
                raise MCPError(
                    error_code=ErrorCode.INVALID_REQUEST,
                    message=f"No command specified for stdio server {server_id}",
                    details={"server_id": server_id}
                )
            
            # Build the full command
            full_command = [command] + args
            
            try:
                # Create the subprocess
                process = await asyncio.create_subprocess_exec(
                    *full_command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
                
                self._processes[server_id] = process
                logger.info(f"Created subprocess for server {server_id}: {' '.join(full_command)}")
                
                # Initialize the MCP connection if not already done
                if server_id not in self._initialized_processes:
                    await self._initialize_mcp_connection(process, server_id)
                    self._initialized_processes.add(server_id)
                
                return process
                
            except Exception as e:
                raise MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message=f"Failed to create subprocess for server {server_id}: {str(e)}",
                    details={
                        "server_id": server_id,
                        "command": full_command,
                        "error": str(e)
                    }
                )

    async def _initialize_mcp_connection(self, process: asyncio.subprocess.Process, server_id: str):
        """
        Initialize the MCP connection with the subprocess and discover available tools.
        
        Args:
            process: The subprocess
            server_id: The server ID for logging
        """
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send the initialize request
            init_response = await self._send_to_process(process, init_request)
            logger.debug(f"MCP initialize response for {server_id}: {init_response}")
            
            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            # Send initialized notification (no response expected)
            init_json = json.dumps(initialized_notification) + '\n'
            init_bytes = init_json.encode('utf-8')
            process.stdin.write(init_bytes)
            await process.stdin.drain()
            
            # Discover available tools
            await self._discover_tools(process, server_id)
            
            logger.info(f"Successfully initialized MCP connection for {server_id}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize MCP connection for {server_id}: {e}")
            # Don't raise here, let the connection attempt proceed

    async def _discover_tools(self, process: asyncio.subprocess.Process, server_id: str):
        """
        Discover available tools from the MCP server.
        
        Args:
            process: The subprocess
            server_id: The server ID for logging
        """
        try:
            # Send tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            # Send the tools/list request
            tools_response = await self._send_to_process(process, tools_request)
            
            if tools_response.get("result") and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                tool_names = [tool.get("name") for tool in tools if tool.get("name")]
                logger.info(f"Discovered tools for {server_id}: {tool_names}")
                
                # Log tool details for debugging
                for tool in tools:
                    logger.debug(f"Tool {tool.get('name')}: {tool.get('description', 'No description')}")
            else:
                logger.warning(f"No tools found in response for {server_id}: {tools_response}")
                
        except Exception as e:
            logger.warning(f"Failed to discover tools for {server_id}: {e}")

    async def _send_to_process(
        self, 
        process: asyncio.subprocess.Process, 
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a request to a subprocess and get the response.
        
        Args:
            process: The subprocess to send to
            request_data: The request data to send
            
        Returns:
            Dict[str, Any]: The response data
            
        Raises:
            MCPError: If the communication fails
        """
        try:
            # Ensure request has a unique ID
            if "id" not in request_data:
                self._request_counter += 1
                request_data["id"] = self._request_counter
            
            # Convert request to JSON and send
            request_json = json.dumps(request_data) + '\n'
            request_bytes = request_json.encode('utf-8')
            
            logger.debug(f"Sending request: {request_json.strip()}")
            
            # Send the request
            process.stdin.write(request_bytes)
            await process.stdin.drain()
            
            # Read the response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                raise MCPError(
                    error_code=ErrorCode.TIMEOUT,
                    message=f"Request timed out after {self.timeout_seconds} seconds",
                    details={"timeout_seconds": self.timeout_seconds}
                )
            
            if not response_line:
                # Process has closed stdout, check if it's still running
                if process.returncode is not None:
                    raise MCPError(
                        error_code=ErrorCode.SERVER_ERROR,
                        message=f"Process terminated with code {process.returncode}",
                        details={"return_code": process.returncode}
                    )
                else:
                    raise MCPError(
                        error_code=ErrorCode.SERVER_ERROR,
                        message="No response received from process",
                        details={}
                    )
            
            response_str = response_line.decode('utf-8').strip()
            logger.debug(f"Received response: {response_str}")
            
            # Parse the JSON response
            try:
                response_data = json.loads(response_str)
                return response_data
            except json.JSONDecodeError as e:
                raise MCPError(
                    error_code=ErrorCode.INVALID_RESPONSE,
                    message=f"Invalid JSON response: {str(e)}",
                    details={
                        "response": response_str,
                        "json_error": str(e)
                    }
                )
                
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                error_code=ErrorCode.SERVER_ERROR,
                message=f"Communication error: {str(e)}",
                details={"error": str(e)}
            )

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
            
        Raises:
            MCPError: If the request fails
        """
        server_id = server_info.server_id
        
        # Get or create communication lock for this server
        if server_id not in self._communication_locks:
            self._communication_locks[server_id] = asyncio.Lock()
        
        # Use the communication lock to ensure only one request at a time
        async with self._communication_locks[server_id]:
            for attempt in range(self.max_retries + 1):
                try:
                    # Get or create the process
                    process = await self._get_or_create_process(server_info)
                    
                    # Send the request and get response
                    response = await self._send_to_process(process, formatted_request)
                    
                    logger.debug(f"Successfully sent request to {server_id} on attempt {attempt + 1}")
                    return response
                    
                except MCPError as e:
                    if attempt == self.max_retries:
                        logger.error(f"Request to {server_id} failed after {self.max_retries + 1} attempts: {e}")
                        raise
                    
                    # Clean up the failed process
                    if server_id in self._processes:
                        try:
                            process = self._processes[server_id]
                            if process.returncode is None:
                                process.terminate()
                                try:
                                    await asyncio.wait_for(process.wait(), timeout=5.0)
                                except asyncio.TimeoutError:
                                    process.kill()
                                    await process.wait()
                        except (ProcessLookupError, OSError):
                            # Process already terminated or cleanup failed - safe to ignore
                            pass
                        finally:
                            if server_id in self._processes:
                                del self._processes[server_id]
                            self._initialized_processes.discard(server_id)
                    
                    # Wait before retrying
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(f"Request to {server_id} failed on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)

    async def check_server_health(self, server_info: MCPServerInfo) -> bool:
        """
        Check if a server is healthy by attempting to create/verify the process.
        
        Args:
            server_info: Information about the server to check
            
        Returns:
            bool: True if the server is healthy, False otherwise
        """
        try:
            # Try to get or create the process
            process = await self._get_or_create_process(server_info)
            
            # Check if the process is still running
            if process.returncode is None:
                return True
            else:
                # Process has died, clean it up
                server_id = server_info.server_id
                if server_id in self._processes:
                    del self._processes[server_id]
                    self._initialized_processes.discard(server_id)
                return False
                
        except Exception as e:
            logger.warning(f"Health check failed for server {server_info.server_id}: {e}")
            return False

    async def cleanup(self):
        """Clean up all active processes."""
        for server_id, process in list(self._processes.items()):
            try:
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
            except Exception as e:
                logger.warning(f"Error cleaning up process for {server_id}: {e}")
        
        self._processes.clear()
        self._process_locks.clear()
        self._communication_locks.clear()
        self._initialized_processes.clear()

    def __del__(self):
        """Cleanup when the transport is destroyed."""
        # Note: This is not ideal for async cleanup, but provides a fallback
        for process in self._processes.values():
            try:
                if process.returncode is None:
                    process.terminate()
            except (ProcessLookupError, OSError):
                # Process already terminated or not accessible - safe to ignore
                pass