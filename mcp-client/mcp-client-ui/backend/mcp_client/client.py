"""
MCP Client implementation.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from mcp_client.core.interfaces import MCPClient as MCPClientInterface
from mcp_client.core.interfaces import ProtocolHandler, ServerDiscovery, Transport
from mcp_client.core.models import (
    ErrorCode,
    MCPClientConfig,
    MCPError,
    MCPRequest,
    MCPResponse,
    MCPServerInfo,
    ResponseStatus,
)
from mcp_client.core.plugin import MCPPlugin, PluginHook, PluginManager
from mcp_client.discovery.registry import InMemoryServerRegistry
from mcp_client.monitoring.logging import (
    MCPLoggingConfig,
    clear_request_context,
    get_logger,
    get_performance_logger,
    log_error,
    log_request,
    log_response,
    set_request_context,
)
from mcp_client.monitoring.metrics import get_mcp_metrics
from mcp_client.protocol.handler import MCPProtocolHandler
from mcp_client.security.validation import SecurityMiddleware
from mcp_client.transport.http import HTTPTransport
from mcp_client.transport.factory import TransportFactory, MultiTransport

logger = get_logger(__name__)


class MCPClient(MCPClientInterface):
    """Implementation of the MCP Client."""

    def __init__(
        self,
        config: MCPClientConfig,
        protocol_handler: Optional[ProtocolHandler] = None,
        server_discovery: Optional[ServerDiscovery] = None,
        transport: Optional[Transport] = None,
        plugins: Optional[List[MCPPlugin]] = None,
    ):
        """
        Initialize the MCP Client.

        Args:
            config: Configuration for the client
            protocol_handler: Protocol handler to use, or None to create a new one
            server_discovery: Server discovery to use, or None to create a new one
            transport: Transport to use, or None to create a new one
            plugins: List of plugins to register, or None for no plugins
        """
        self.config = config
        
        # Initialize logging configuration
        logging_config = MCPLoggingConfig(
            level=config.log_level,
            json_format=False,  # Default to human-readable for now
            include_context=True,
            enable_performance_logging=config.enable_metrics,
        )
        logging_config.configure_logging()
        
        # Get performance logger and metrics collector
        self._performance_logger = get_performance_logger()
        self._metrics = get_mcp_metrics() if config.enable_metrics else None
        
        logger.info("Initializing MCP Client", extra={
            "discovery_mode": config.discovery_mode,
            "aws_region": config.aws_region,
            "enable_metrics": config.enable_metrics,
            "enable_tracing": config.enable_tracing,
        })
        
        # Set up AWS authentication if enabled
        self._aws_authenticator: Optional[Any] = None
        if config.enable_aws_auth:
            try:
                from mcp_client.aws.auth import AWSAuthenticator, AWSCredentialProvider
                credential_provider = AWSCredentialProvider(
                    region=config.aws_region,
                    profile=config.aws_profile,
                    role_arn=config.aws_role_arn,
                    session_name=config.aws_session_name,
                    external_id=config.aws_external_id,
                )
                self._aws_authenticator = AWSAuthenticator(credential_provider)
                logger.info(f"AWS authentication enabled for region: {config.aws_region}")
                logger.debug(f"AWS authenticator initialized with profile: {config.aws_profile}, role_arn: {config.aws_role_arn}")
            except ImportError as e:
                logger.error(f"AWS authentication requested but dependencies not available: {e}")
                logger.error("Install AWS dependencies with: pip install boto3")
                raise
        
        # Set up security middleware
        self._security_middleware = SecurityMiddleware()
        logger.info("Security middleware initialized")
        
        self._protocol_handler = protocol_handler or MCPProtocolHandler()
        
        # Create transport factory and multi-transport
        if transport:
            self._transport = transport
        else:
            transport_factory = TransportFactory(
                default_timeout_seconds=config.timeout_seconds,
                default_max_retries=config.max_retries,
                default_retry_backoff_factor=config.retry_backoff_factor,
                # HTTP transport specific kwargs
                use_tls=config.use_tls,
                verify_ssl=config.verify_ssl,
                cert_path=config.cert_path,
                ca_cert_path=config.ca_cert_path,
                client_cert_path=config.client_cert_path,
                client_key_path=config.client_key_path,
                client_key_password=config.client_key_password,
                min_tls_version=config.min_tls_version,
                cert_fingerprints=config.cert_fingerprints,
                cipher_suites=config.cipher_suites,
                authenticator=self._aws_authenticator,
            )
            self._transport = MultiTransport(transport_factory)
            self._transport_factory = transport_factory
        
        # Set up server discovery based on the configuration
        if server_discovery:
            self._server_discovery = server_discovery
            # Start the health check background task if using dynamic discovery
            if config.discovery_mode != "static":
                self._start_server_discovery()
        elif config.discovery_mode == "static":
            # Use static servers from the configuration
            self._server_discovery = InMemoryServerRegistry(transport=self._transport)
            # Register the static servers
            self._register_static_servers(config.static_servers)
        else:
            # Use dynamic server discovery
            self._server_discovery = InMemoryServerRegistry(transport=self._transport)
            # Start the health check background task
            self._start_server_discovery()
            
        # Set up a thread pool for synchronous operations
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # Set up a lock for thread safety
        self._lock = threading.RLock()
        
        # Set up the plugin manager
        self._plugin_manager = PluginManager()
        
        # Register plugins
        if plugins:
            for plugin in plugins:
                self._plugin_manager.register_plugin(plugin)
                
        # Execute the CLIENT_INIT hook
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, we can create a task
            asyncio.create_task(self._plugin_manager.execute_hook(PluginHook.CLIENT_INIT, self))
        except RuntimeError:
            # No running event loop, create a new one
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._plugin_manager.execute_hook(PluginHook.CLIENT_INIT, self))
        
        logger.info(f"Initialized MCP Client with discovery mode: {config.discovery_mode}")
        
    def __del__(self):
        """Clean up resources when the client is deleted."""
        # Shut down the thread pool
        self._thread_pool.shutdown(wait=False)
        
        # Note: We don't stop the server discovery here because it might cause issues
        # with the event loop. The server discovery should be stopped explicitly by the user
        # or it will be cleaned up when the process exits.
        
    async def __aenter__(self) -> "MCPClient":
        """Enter the async context manager."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        await self.close()
        
    async def close(self) -> None:
        """Close the client and release resources."""
        # Execute the CLIENT_CLOSE hook
        try:
            await self._plugin_manager.execute_hook(PluginHook.CLIENT_CLOSE, self)
        except Exception as e:
            logger.warning(f"Error executing CLIENT_CLOSE hook: {e}")
            
        # Shut down plugins
        try:
            await self._plugin_manager.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down plugins: {e}")
            
        # Stop the server discovery
        if hasattr(self._server_discovery, "stop"):
            try:
                await self._server_discovery.stop()
            except Exception as e:
                logger.warning(f"Error stopping server discovery: {e}")
                
        # Close the transport
        if hasattr(self._transport, "close"):
            try:
                await self._transport.close()
            except Exception as e:
                logger.warning(f"Error closing transport: {e}")
        
        # Cleanup transport factory if we have one
        if hasattr(self, '_transport_factory'):
            try:
                await self._transport_factory.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up transport factory: {e}")
                
        # Shut down the thread pool
        self._thread_pool.shutdown(wait=False)
        
        logger.info("Closed MCP client and released resources")
        
    def close_sync(self) -> None:
        """Synchronous version of close."""
        with self._lock:
            try:
                # Try to get the running loop - this will raise RuntimeError if there's no running loop
                loop = asyncio.get_running_loop()
                # We're in an async context, we can't block with run_until_complete
                raise RuntimeError("Cannot call close_sync from an async context")
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                
            try:
                loop.run_until_complete(self.close())
            except Exception as e:
                logger.error(f"Error closing client: {e}")
                raise
        
    def _start_server_discovery(self):
        """Start the server discovery background task."""
        try:
            # Try to get the running loop - this will raise RuntimeError if there's no running loop
            loop = asyncio.get_running_loop()
            # We're in an async context, we can just create a task
            asyncio.create_task(self._server_discovery.start())
        except RuntimeError:
            # No running event loop, create a new one
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._server_discovery.start())
            
    def _register_static_servers(self, servers):
        """Register static servers from the configuration."""
        try:
            # Try to get the running loop - this will raise RuntimeError if there's no running loop
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task to register servers
            logger.info("Registering static servers in async context")
            self._registration_task = asyncio.create_task(self._register_static_servers_async(servers))
            return
        except RuntimeError:
            # No running event loop, create a new one
            loop = asyncio.new_event_loop()
            for server in servers:
                loop.run_until_complete(self._server_discovery.register_server(server, skip_health_check=True))
            self._registration_task = None  # Already completed synchronously
                
    async def _register_static_servers_async(self, servers):
        """Async version of static server registration."""
        for server in servers:
            try:
                # Skip health checks for static servers since they may not have health endpoints
                await self._server_discovery.register_server(server, skip_health_check=True)
                logger.info(f"Registered static server: {server.server_id}")
            except Exception as e:
                logger.error(f"Failed to register static server {server.server_id}: {e}")
    
    async def wait_for_server_registration(self, timeout_seconds: float = 10.0) -> bool:
        """
        Wait for static server registration to complete.
        
        Args:
            timeout_seconds: Maximum time to wait for registration
            
        Returns:
            bool: True if registration completed successfully, False if timeout
        """
        if not hasattr(self, '_registration_task') or self._registration_task is None:
            # Registration was completed synchronously or no registration needed
            return True
        
        try:
            await asyncio.wait_for(self._registration_task, timeout=timeout_seconds)
            logger.info("Static server registration completed successfully")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Server registration timed out after {timeout_seconds} seconds")
            return False
        except Exception as e:
            logger.error(f"Error waiting for server registration: {e}")
            return False
        
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send a request to an appropriate MCP server.
        
        Args:
            request: The request to send
            
        Returns:
            MCPResponse: The response from the server
            
        Raises:
            MCPError: If the request fails
        """
        # Generate request ID for correlation
        request_id = uuid4().hex
        start_time = time.time()
        
        # Set logging context
        set_request_context(request_id=request_id)
        
        # Start performance timer
        timer_id = self._performance_logger.start_timer("send_request")
        
        try:
            logger.info("Starting request processing", extra={
                "request_type": request.request_type,
                "required_capabilities": request.required_capabilities,
                "preferred_server_id": request.preferred_server_id,
            })
            
            # Validate the request
            validation_timer = self._performance_logger.start_timer("request_validation")
            self._protocol_handler.validate_request(request)
            self._performance_logger.end_timer(validation_timer, "request_validation")
            
            # Security validation and sanitization
            security_timer = self._performance_logger.start_timer("security_validation")
            request = self._security_middleware.validate_request(request)
            self._performance_logger.end_timer(security_timer, "security_validation")
            
            # Execute the PRE_SERVER_SELECTION hook
            await self._plugin_manager.execute_hook(PluginHook.PRE_SERVER_SELECTION, self, request)
            
            # Select a server
            selection_timer = self._performance_logger.start_timer("server_selection")
            server = await self._server_discovery.select_server(request)
            self._performance_logger.end_timer(selection_timer, "server_selection")
            
            if not server:
                error = MCPError(
                    error_code=ErrorCode.DISCOVERY_ERROR,
                    message="No suitable server found for the request",
                    details={"required_capabilities": request.required_capabilities},
                )
                log_error(logger.logger, error, {"request_id": request_id})
                raise error
            
            # Update context with server ID
            set_request_context(request_id=request_id, server_id=server.server_id)
            
            logger.info(f"Selected server {server.server_id} for request")
            
            # Execute the POST_SERVER_SELECTION hook
            await self._plugin_manager.execute_hook(PluginHook.POST_SERVER_SELECTION, self, request, server)
            
            # Format the request
            format_timer = self._performance_logger.start_timer("request_formatting")
            formatted_request = self._protocol_handler.format_request(request)
            self._performance_logger.end_timer(format_timer, "request_formatting")
            
            # Execute the PRE_REQUEST hook
            await self._plugin_manager.execute_hook(PluginHook.PRE_REQUEST, self, request, server, formatted_request)
            
            # Log the outgoing request
            log_request(logger.logger, request, server)
            
            # Send the request
            transport_timer = self._performance_logger.start_timer("transport_request")
            raw_response = await self._transport.send_request(server, formatted_request)
            transport_duration = self._performance_logger.end_timer(transport_timer, "transport_request")
            
            # Parse the response
            parse_timer = self._performance_logger.start_timer("response_parsing")
            response = self._protocol_handler.parse_response(raw_response)
            self._performance_logger.end_timer(parse_timer, "response_parsing")
            
            # Set response metadata
            response.request_id = request_id
            
            # Log the response
            total_duration = time.time() - start_time
            log_response(logger.logger, response, duration=total_duration)
            
            # Execute the POST_REQUEST hook
            await self._plugin_manager.execute_hook(PluginHook.POST_REQUEST, self, request, server, response)
            
            # Check for errors
            if response.status == ResponseStatus.ERROR:
                error = MCPError(
                    error_code=ErrorCode.SERVER_ERROR,
                    message=response.content.get("message", "Unknown server error"),
                    details=response.content,
                )
                
                log_error(logger.logger, error, {
                    "request_id": request_id,
                    "server_id": server.server_id,
                    "transport_duration": transport_duration,
                    "total_duration": total_duration,
                })
                
                # Execute the ERROR_OCCURRED hook
                await self._plugin_manager.execute_hook(PluginHook.ERROR_OCCURRED, self, error)
                
                raise error
            
            # Log successful completion
            self._performance_logger.end_timer(timer_id, "send_request", 
                                             server_id=server.server_id,
                                             request_type=request.request_type,
                                             response_status=response.status)
            
            logger.info("Request completed successfully", extra={
                "total_duration": total_duration,
                "transport_duration": transport_duration,
                "response_status": response.status,
            })
            
            # Record metrics
            if self._metrics:
                self._metrics.record_request(
                    request_type=request.request_type,
                    server_id=server.server_id,
                    duration=total_duration,
                    success=True
                )
            
            return response
            
        except MCPError as e:
            # Log the error
            log_error(logger.logger, e, {"request_id": request_id})
            
            # Execute the ERROR_OCCURRED hook
            await self._plugin_manager.execute_hook(PluginHook.ERROR_OCCURRED, self, e)
            
            # End performance timer with error
            self._performance_logger.end_timer(timer_id, "send_request", 
                                             error=str(e),
                                             error_code=e.error_code)
            
            # Record error metrics
            if self._metrics:
                server_id = getattr(server, 'server_id', 'unknown') if 'server' in locals() else 'unknown'
                self._metrics.record_request(
                    request_type=request.request_type,
                    server_id=server_id,
                    duration=time.time() - start_time,
                    success=False,
                    error_code=e.error_code
                )
            
            # Re-raise MCPError exceptions
            raise
        except Exception as e:
            # Wrap other exceptions in MCPError
            error = MCPError(
                error_code=ErrorCode.CLIENT_ERROR,
                message=f"Client error: {str(e)}",
                details={"exception_type": type(e).__name__},
            )
            
            # Log the error
            log_error(logger.logger, error, {"request_id": request_id})
            
            # Execute the ERROR_OCCURRED hook
            await self._plugin_manager.execute_hook(PluginHook.ERROR_OCCURRED, self, error)
            
            # End performance timer with error
            self._performance_logger.end_timer(timer_id, "send_request", 
                                             error=str(error),
                                             error_code=error.error_code)
            
            # Record error metrics
            if self._metrics:
                server_id = getattr(server, 'server_id', 'unknown') if 'server' in locals() else 'unknown'
                self._metrics.record_request(
                    request_type=request.request_type,
                    server_id=server_id,
                    duration=time.time() - start_time,
                    success=False,
                    error_code=error.error_code
                )
            
            raise error from e
        finally:
            # Clear the request context
            clear_request_context()
            
    def wait_for_server_registration_sync(self, timeout_seconds: float = 10.0) -> bool:
        """
        Synchronous version of wait_for_server_registration.
        
        Args:
            timeout_seconds: Maximum time to wait for registration
            
        Returns:
            bool: True if registration completed successfully, False if timeout
        """
        with self._lock:
            try:
                # Try to get the running loop - this will raise RuntimeError if there's no running loop
                loop = asyncio.get_running_loop()
                # We're in an async context, we can't block with run_until_complete
                raise RuntimeError("Cannot call wait_for_server_registration_sync from an async context")
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                
            try:
                return loop.run_until_complete(self.wait_for_server_registration(timeout_seconds))
            except Exception as e:
                logger.error(f"Error in synchronous server registration wait: {e}")
                return False

    def send_request_sync(self, request: MCPRequest) -> MCPResponse:
        """
        Synchronous version of send_request.
        
        Args:
            request: The request to send
            
        Returns:
            MCPResponse: The response from the server
            
        Raises:
            MCPError: If the request fails
        """
        # Use the thread pool to run the async method
        with self._lock:
            try:
                # Try to get the running loop - this will raise RuntimeError if there's no running loop
                loop = asyncio.get_running_loop()
                # We're in an async context, we can't block with run_until_complete
                raise RuntimeError("Cannot call send_request_sync from an async context")
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                
            try:
                return loop.run_until_complete(self.send_request(request))
            except Exception as e:
                # Ensure any asyncio exceptions are properly converted to MCPError
                if isinstance(e, MCPError):
                    raise
                else:
                    raise MCPError(
                        error_code=ErrorCode.CLIENT_ERROR,
                        message=f"Client error in synchronous request: {str(e)}",
                        details={"exception_type": type(e).__name__},
                    ) from e
                    
    async def register_server(self, server_info: MCPServerInfo) -> bool:
        """
        Register a new MCP server.
        
        Args:
            server_info: Information about the server to register
            
        Returns:
            bool: True if the server was registered successfully, False otherwise
        """
        return await self._server_discovery.register_server(server_info)
        
    def register_server_sync(self, server_info: MCPServerInfo) -> bool:
        """
        Synchronous version of register_server.
        
        Args:
            server_info: Information about the server to register
            
        Returns:
            bool: True if the server was registered successfully, False otherwise
        """
        # Use the thread pool to run the async method
        with self._lock:
            try:
                # Try to get the running loop - this will raise RuntimeError if there's no running loop
                loop = asyncio.get_running_loop()
                # We're in an async context, we can't block with run_until_complete
                raise RuntimeError("Cannot call register_server_sync from an async context")
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                
            return loop.run_until_complete(self.register_server(server_info))
            
    async def get_servers(self, capabilities: Optional[List[str]] = None) -> List[MCPServerInfo]:
        """
        Get available servers, optionally filtered by capabilities.
        
        Args:
            capabilities: Optional list of capabilities to filter servers by
            
        Returns:
            List[MCPServerInfo]: A list of available servers
        """
        servers = await self._server_discovery.discover_servers()
        
        if capabilities:
            # Filter servers by capabilities
            filtered_servers = []
            for server in servers:
                if all(capability in server.capabilities for capability in capabilities):
                    filtered_servers.append(server)
            return filtered_servers
        else:
            return servers
            
    def get_servers_sync(self, capabilities: Optional[List[str]] = None) -> List[MCPServerInfo]:
        """
        Synchronous version of get_servers.
        
        Args:
            capabilities: Optional list of capabilities to filter servers by
            
        Returns:
            List[MCPServerInfo]: A list of available servers
        """
        # Use the thread pool to run the async method
        with self._lock:
            try:
                # Try to get the running loop - this will raise RuntimeError if there's no running loop
                loop = asyncio.get_running_loop()
                # We're in an async context, we can't block with run_until_complete
                raise RuntimeError("Cannot call get_servers_sync from an async context")
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                
            return loop.run_until_complete(self.get_servers(capabilities))
            
    def create_text_generation_request(
        self, prompt: str, **kwargs: Any
    ) -> MCPRequest:
        """
        Create a text generation request.
        
        Args:
            prompt: The prompt to generate text from
            **kwargs: Additional parameters for the request
            
        Returns:
            MCPRequest: The created request
        """
        content = {"prompt": prompt}
        content.update(kwargs)
        
        return MCPRequest(
            request_type="text_generation",
            content=content,
            required_capabilities=["text-generation"],
        )
        
    def create_image_generation_request(
        self, prompt: str, **kwargs: Any
    ) -> MCPRequest:
        """
        Create an image generation request.
        
        Args:
            prompt: The prompt to generate an image from
            **kwargs: Additional parameters for the request
            
        Returns:
            MCPRequest: The created request
        """
        content = {"prompt": prompt}
        content.update(kwargs)
        
        return MCPRequest(
            request_type="image_generation",
            content=content,
            required_capabilities=["image-generation"],
        )
        
    def create_embedding_request(
        self, text: Union[str, List[str]], **kwargs: Any
    ) -> MCPRequest:
        """
        Create an embedding request.
        
        Args:
            text: The text to create embeddings for
            **kwargs: Additional parameters for the request
            
        Returns:
            MCPRequest: The created request
        """
        content = {"text": text}
        content.update(kwargs)
        
        return MCPRequest(
            request_type="embedding",
            content=content,
            required_capabilities=["embedding"],
        )
        
    def create_chat_request(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> MCPRequest:
        """
        Create a chat request.
        
        Args:
            messages: The chat messages
            **kwargs: Additional parameters for the request
            
        Returns:
            MCPRequest: The created request
        """
        content = {"messages": messages}
        content.update(kwargs)
        
        return MCPRequest(
            request_type="chat",
            content=content,
            required_capabilities=["chat"],
        )
        
    def create_action_request(
        self, action: str, **kwargs: Any
    ) -> MCPRequest:
        """
        Create an action request.
        
        Args:
            action: The action to perform
            **kwargs: Additional parameters for the request
            
        Returns:
            MCPRequest: The created request
        """
        content = {"action": action}
        content.update(kwargs)
        
        return MCPRequest(
            request_type="action",
            content=content,
            required_capabilities=["action"],
        )
        
    def generate_text(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The prompt to generate text from
            **kwargs: Additional parameters for the request
            
        Returns:
            str: The generated text
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_text_generation_request(prompt, **kwargs)
        response = self.send_request_sync(request)
        
        if "text" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain generated text",
                details={"response_content": response.content},
            )
            
        return response.content["text"]
        
    def generate_image(self, prompt: str, **kwargs: Any) -> Dict[str, str]:
        """
        Generate an image from a prompt.
        
        Args:
            prompt: The prompt to generate an image from
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict[str, str]: The generated image data
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_image_generation_request(prompt, **kwargs)
        response = self.send_request_sync(request)
        
        if "image_url" not in response.content and "image_data" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain image URL or data",
                details={"response_content": response.content},
            )
            
        result = {}
        if "image_url" in response.content:
            result["image_url"] = response.content["image_url"]
        if "image_data" in response.content:
            result["image_data"] = response.content["image_data"]
            
        return result
        
    def create_embedding(self, text: Union[str, List[str]], **kwargs: Any) -> List[List[float]]:
        """
        Create embeddings for text.
        
        Args:
            text: The text to create embeddings for
            **kwargs: Additional parameters for the request
            
        Returns:
            List[List[float]]: The embeddings
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_embedding_request(text, **kwargs)
        response = self.send_request_sync(request)
        
        if "embeddings" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain embeddings",
                details={"response_content": response.content},
            )
            
        return response.content["embeddings"]
        
    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, str]:
        """
        Send a chat request.
        
        Args:
            messages: The chat messages
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict[str, str]: The chat response message
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_chat_request(messages, **kwargs)
        response = self.send_request_sync(request)
        
        if "message" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain a message",
                details={"response_content": response.content},
            )
            
        return response.content["message"]
        
    def perform_action(self, action: str, **kwargs: Any) -> Any:
        """
        Perform an action.
        
        Args:
            action: The action to perform
            **kwargs: Additional parameters for the request
            
        Returns:
            Any: The action result
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_action_request(action, **kwargs)
        response = self.send_request_sync(request)
        
        if "result" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain a result",
                details={"response_content": response.content},
            )
            
        return response.content["result"]
        
    async def generate_text_async(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate text from a prompt asynchronously.
        
        Args:
            prompt: The prompt to generate text from
            **kwargs: Additional parameters for the request
            
        Returns:
            str: The generated text
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_text_generation_request(prompt, **kwargs)
        response = await self.send_request(request)
        
        if "text" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain generated text",
                details={"response_content": response.content},
            )
            
        return response.content["text"]
        
    async def generate_image_async(self, prompt: str, **kwargs: Any) -> Dict[str, str]:
        """
        Generate an image from a prompt asynchronously.
        
        Args:
            prompt: The prompt to generate an image from
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict[str, str]: The generated image data
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_image_generation_request(prompt, **kwargs)
        response = await self.send_request(request)
        
        if "image_url" not in response.content and "image_data" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain image URL or data",
                details={"response_content": response.content},
            )
            
        result = {}
        if "image_url" in response.content:
            result["image_url"] = response.content["image_url"]
        if "image_data" in response.content:
            result["image_data"] = response.content["image_data"]
            
        return result
        
    async def create_embedding_async(self, text: Union[str, List[str]], **kwargs: Any) -> List[List[float]]:
        """
        Create embeddings for text asynchronously.
        
        Args:
            text: The text to create embeddings for
            **kwargs: Additional parameters for the request
            
        Returns:
            List[List[float]]: The embeddings
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_embedding_request(text, **kwargs)
        response = await self.send_request(request)
        
        if "embeddings" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain embeddings",
                details={"response_content": response.content},
            )
            
        return response.content["embeddings"]
        
    async def chat_async(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, str]:
        """
        Send a chat request asynchronously.
        
        Args:
            messages: The chat messages
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict[str, str]: The chat response message
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_chat_request(messages, **kwargs)
        response = await self.send_request(request)
        
        if "message" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain a message",
                details={"response_content": response.content},
            )
            
        return response.content["message"]
        
    async def perform_action_async(self, action: str, **kwargs: Any) -> Any:
        """
        Perform an action asynchronously.
        
        Args:
            action: The action to perform
            **kwargs: Additional parameters for the request
            
        Returns:
            Any: The action result
            
        Raises:
            MCPError: If the request fails
        """
        request = self.create_action_request(action, **kwargs)
        response = await self.send_request(request)
        
        if "result" not in response.content:
            raise MCPError(
                error_code=ErrorCode.PROTOCOL_ERROR,
                message="Response does not contain a result",
                details={"response_content": response.content},
            )
            
        return response.content["result"]