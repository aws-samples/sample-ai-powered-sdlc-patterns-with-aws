"""
HTTP transport implementation for the MCP Client.
"""

import asyncio
import json
import logging
import secrets
import ssl
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout
from pydantic import ValidationError

from mcp_client.core.interfaces import Transport
from mcp_client.core.models import ErrorCode, MCPError, MCPServerInfo
from mcp_client.security.tls import (
    CertificateVerificationMode,
    CertificateVerifier,
    TLSConfig,
    TLSVersion,
    create_ssl_context,
)
from mcp_client.transport.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class HTTPTransport(Transport):
    """HTTP transport implementation for the MCP Client."""

    def __init__(
        self,
        timeout_seconds: float = 120.0,  # Increased from 30 to 120 seconds
        max_retries: int = 3,
        retry_backoff_factor: float = 1.5,
        use_tls: bool = True,
        verify_ssl: bool = True,
        cert_path: Optional[str] = None,
        ca_cert_path: Optional[str] = None,
        client_cert_path: Optional[str] = None,
        client_key_path: Optional[str] = None,
        client_key_password: Optional[str] = None,
        min_tls_version: Optional[TLSVersion] = None,
        cert_fingerprints: Optional[Dict[str, str]] = None,
        cipher_suites: Optional[str] = None,
        connection_pool_size: int = 100,
        connection_keepalive: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_reset_timeout_seconds: float = 60.0,
        authenticator: Optional[Any] = None,
    ):
        """
        Initialize the HTTP transport.

        Args:
            timeout_seconds: Timeout for requests in seconds
            max_retries: Maximum number of retries for failed requests
            retry_backoff_factor: Factor to increase backoff time between retries
            use_tls: Whether to use TLS/SSL for connections
            verify_ssl: Whether to verify SSL certificates
            cert_path: Path to a custom SSL certificate (deprecated, use client_cert_path)
            ca_cert_path: Path to CA certificate file or directory
            client_cert_path: Path to client certificate file
            client_key_path: Path to client private key file
            client_key_password: Password for client private key file
            min_tls_version: Minimum TLS version to use
            cert_fingerprints: Dictionary mapping hostnames to expected certificate fingerprints
            cipher_suites: Cipher suites to use
            connection_pool_size: Maximum number of connections in the pool
            connection_keepalive: Whether to keep connections alive
            circuit_breaker_failure_threshold: Number of failures before opening the circuit
            circuit_breaker_reset_timeout_seconds: Time to wait before transitioning from open to half-open
            authenticator: Optional authenticator for request signing
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.use_tls = use_tls
        self.verify_ssl = verify_ssl
        self.cert_path = cert_path  # Deprecated, use client_cert_path
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path or cert_path
        self.client_key_path = client_key_path
        self.client_key_password = client_key_password
        self.min_tls_version = min_tls_version or TLSVersion.get_default()
        self.cert_fingerprints = cert_fingerprints or {}
        self.cipher_suites = cipher_suites
        self.connection_pool_size = connection_pool_size
        self.connection_keepalive = connection_keepalive
        self.authenticator = authenticator
        
        self._session: Optional[ClientSession] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._cert_verifier: Optional[CertificateVerifier] = None
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Circuit breaker configuration
        self.circuit_breaker_failure_threshold = circuit_breaker_failure_threshold
        self.circuit_breaker_reset_timeout_seconds = circuit_breaker_reset_timeout_seconds
        
        # Set up TLS configuration
        if self.use_tls:
            self._setup_tls_config()
            
        logger.info(
            f"Initialized HTTP transport with timeout={timeout_seconds}s, "
            f"max_retries={max_retries}, use_tls={use_tls}"
        )
        
    def _setup_tls_config(self) -> None:
        """Set up the TLS configuration for secure connections."""
        # Determine the verification mode
        if not self.verify_ssl:
            verification_mode = CertificateVerificationMode.NONE
        elif self.cert_fingerprints:
            verification_mode = CertificateVerificationMode.FINGERPRINT
        else:
            verification_mode = CertificateVerificationMode.HOSTNAME
            
        # Create the TLS configuration
        tls_config = TLSConfig(
            enabled=self.use_tls,
            min_version=self.min_tls_version,
            verification_mode=verification_mode,
            ca_cert_path=self.ca_cert_path,
            client_cert_path=self.client_cert_path,
            client_key_path=self.client_key_path,
            client_key_password=self.client_key_password,
            cert_fingerprints=self.cert_fingerprints,
            cipher_suites=self.cipher_suites,
        )
        
        # Create the SSL context
        try:
            self._ssl_context = create_ssl_context(tls_config)
            self._cert_verifier = CertificateVerifier(tls_config)
        except ValueError as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
                
    async def _get_session(self) -> ClientSession:
        """
        Get or create an aiohttp ClientSession.
        
        Returns:
            ClientSession: The session to use for requests
        """
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.timeout_seconds)
            connector = aiohttp.TCPConnector(
                ssl=self._ssl_context if self.use_tls else None,
                limit=self.connection_pool_size,
                keepalive_timeout=300.0 if self.connection_keepalive else 0.0,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                json_serialize=json.dumps,
                raise_for_status=False,
            )
            
        return self._session
        
    async def close(self) -> None:
        """Close the transport and release resources."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("Closed HTTP transport session")
            
    async def __aenter__(self) -> "HTTPTransport":
        """Enter the async context manager."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        await self.close()

    def _get_circuit_breaker(self, server_id: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a server.
        
        Args:
            server_id: The ID of the server
            
        Returns:
            CircuitBreaker: The circuit breaker for the server
        """
        if server_id not in self._circuit_breakers:
            self._circuit_breakers[server_id] = CircuitBreaker(
                failure_threshold=self.circuit_breaker_failure_threshold,
                reset_timeout_seconds=self.circuit_breaker_reset_timeout_seconds,
            )
            
        return self._circuit_breakers[server_id]

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
        endpoint_url = server_info.endpoint_url
        server_id = server_info.server_id
        circuit_breaker = self._get_circuit_breaker(server_id)
        
        # Use the circuit breaker to protect the request
        try:
            return await circuit_breaker.execute(self._do_send_request, server_info, formatted_request)
        except CircuitBreakerError as e:
            # Circuit is open, server is considered unavailable
            raise MCPError(
                error_code=ErrorCode.SERVER_ERROR,
                message=f"Server {server_id} is unavailable: {str(e)}",
                details={
                    "server_id": server_id,
                    "endpoint_url": endpoint_url,
                    "circuit_state": circuit_breaker.state,
                },
            )
            
    async def _do_send_request(
        self, server_info: MCPServerInfo, formatted_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method to send a request with retries.
        
        Args:
            server_info: Information about the server to send the request to
            formatted_request: The formatted request to send
            
        Returns:
            Dict[str, Any]: The raw response from the server
            
        Raises:
            MCPError: If the request fails
        """
        endpoint_url = server_info.endpoint_url
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    # Calculate backoff time with exponential backoff and jitter
                    backoff_time = self.retry_backoff_factor * (2 ** (retry_count - 1))
                    jitter = backoff_time * 0.1  # 10% jitter
                    # Use cryptographically secure random for jitter
                    random_factor = (secrets.randbelow(1000) / 1000.0) - 0.5  # -0.5 to 0.5
                    backoff_time = backoff_time + (jitter * random_factor)
                    logger.info(f"Retrying request to {endpoint_url} after {backoff_time:.2f}s (attempt {retry_count}/{self.max_retries})")
                    await asyncio.sleep(backoff_time)
                
                session = await self._get_session()
                
                # Add request metadata for monitoring
                request_metadata = {
                    "server_id": server_info.server_id,
                    "endpoint_url": endpoint_url,
                    "retry_count": retry_count,
                }
                
                logger.debug(f"Sending request to {endpoint_url}: {json.dumps(formatted_request)}")
                
                # Prepare headers
                headers = {"Content-Type": "application/json"}
                
                # Add custom headers from the request if available
                # The formatted_request is a dict that may contain headers from MCPRequest.headers
                if isinstance(formatted_request, dict) and 'headers' in formatted_request:
                    headers.update(formatted_request['headers'])
                    # Remove headers from the request body to avoid sending them twice
                    formatted_request = formatted_request.copy()
                    del formatted_request['headers']
                    logger.debug(f"Added custom headers from formatted request: {list(headers.keys())}")
                elif hasattr(formatted_request, 'headers') and formatted_request.headers:
                    headers.update(formatted_request.headers)
                    logger.debug(f"Added custom headers from request object: {list(headers.keys())}")
                
                logger.debug(f"Request headers: {headers}")
                
                # Handle authentication
                auth_config = server_info.auth or server_info.auth_config
                logger.error(f"DEBUG: Authentication check - server_id: {server_info.server_id}, auth: {server_info.auth}, auth_config: {server_info.auth_config}, authenticator: {self.authenticator is not None}")
                if auth_config or self.authenticator:
                    try:
                        # Check for server-specific AWS SigV4 authentication
                        is_sigv4 = False
                        auth_type = None
                        
                        if auth_config:
                            if isinstance(auth_config, dict):
                                auth_type = auth_config.get("type")
                                is_sigv4 = auth_type == "aws_sigv4"
                            elif hasattr(auth_config, "type"):
                                auth_type = auth_config.type
                                is_sigv4 = auth_type == "aws_sigv4"
                        
                        logger.error(f"DEBUG: SigV4 check - is_sigv4: {is_sigv4}, auth_type: {auth_type}, auth_config: {type(auth_config)}, auth_config_value: {auth_config}")
                        if is_sigv4:
                            # Handle AWS SigV4 authentication with server-specific config
                            logger.debug(f"About to sign request - authenticator: {self.authenticator is not None}, has_sign_request: {hasattr(self.authenticator, 'sign_request') if self.authenticator else False}")
                            if self.authenticator and hasattr(self.authenticator, 'sign_request'):
                                request_body = json.dumps(formatted_request)
                                
                                # Get service from auth config
                                service = "lambda"  # default
                                if isinstance(auth_config, dict):
                                    service = auth_config.get("service", "lambda")
                                elif hasattr(auth_config, "service"):
                                    service = auth_config.service
                                
                                logger.info(f"Signing request for service: {service} to {endpoint_url}")
                                
                                # Handle cross-account role if specified
                                if isinstance(auth_config, dict) and auth_config.get("role_arn"):
                                    # Create a temporary credential provider for this specific role
                                    from mcp_client.aws.auth import AWSCredentialProvider, AWSAuthenticator
                                    logger.info(f"Using cross-account role: {auth_config.get('role_arn')}")
                                    temp_provider = AWSCredentialProvider(
                                        region=auth_config.get("region", "us-east-1"),
                                        role_arn=auth_config.get("role_arn"),
                                        external_id=auth_config.get("external_id")
                                    )
                                    temp_authenticator = AWSAuthenticator(temp_provider)
                                    signed_headers = temp_authenticator.sign_request(
                                        method="POST",
                                        url=endpoint_url,
                                        headers=headers,
                                        body=request_body,
                                        service=service,
                                        server_id=server_info.server_id
                                    )
                                else:
                                    # Use default authenticator
                                    logger.info(f"Signing request with default authenticator for {endpoint_url}")
                                    signed_headers = self.authenticator.sign_request(
                                        method="POST",
                                        url=endpoint_url,
                                        headers=headers,
                                        body=request_body,
                                        service=service,
                                        server_id=server_info.server_id
                                    )
                                headers.update(signed_headers)
                                logger.info(f"Successfully added AWS SigV4 authentication for service: {service}")
                                logger.debug(f"Signed headers: {list(signed_headers.keys())}")
                            else:
                                logger.error("AWS SigV4 requested but no compatible authenticator available")
                                raise MCPError(
                                    error_code=ErrorCode.AUTHENTICATION_ERROR,
                                    message="AWS SigV4 authentication required but authenticator not available",
                                    details={
                                        "server_id": server_info.server_id,
                                        "endpoint_url": endpoint_url,
                                        "auth_config": auth_config
                                    }
                                )
                        elif self.authenticator:
                            # Fallback to basic header authentication
                            if hasattr(self.authenticator, 'sign_request'):
                                request_body = json.dumps(formatted_request)
                                signed_headers = self.authenticator.sign_request(
                                    method="POST",
                                    url=endpoint_url,
                                    headers=headers,
                                    body=request_body,
                                    server_id=server_info.server_id
                                )
                                headers.update(signed_headers)
                                logger.debug("Added AWS SigV4 authentication to request")
                            else:
                                auth_headers = self.authenticator.get_auth_headers()
                                headers.update(auth_headers)
                                logger.debug("Added authentication headers to request")
                    except Exception as e:
                        logger.error(f"Failed to authenticate request to {endpoint_url}: {e}")
                        logger.debug(f"Authentication error details", exc_info=True)
                        
                        # If this is a credentials error, raise it instead of continuing
                        if "credentials" in str(e).lower() or "authentication" in str(e).lower():
                            raise MCPError(
                                error_code=ErrorCode.AUTHENTICATION_ERROR,
                                message=f"Authentication failed for {endpoint_url}: {str(e)}",
                                details={
                                    "server_id": server_info.server_id,
                                    "endpoint_url": endpoint_url,
                                    "auth_config": str(auth_config),
                                    "error": str(e)
                                }
                            )
                        # For other errors, continue without authentication headers
                        logger.warning("Continuing request without authentication headers due to auth error")
                
                # Send the request
                logger.info(f"Final request headers being sent to {endpoint_url}: {headers}")
                logger.info(f"Request body: {json.dumps(formatted_request)}")
                async with session.post(
                    endpoint_url,
                    json=formatted_request,
                    headers=headers,
                    raise_for_status=False,
                ) as response:
                    # Check for HTTP errors
                    if response.status >= 400:
                        error_message = await self._handle_http_error(response)
                        if self._should_retry(response.status, retry_count):
                            retry_count += 1
                            last_exception = MCPError(
                                error_code=ErrorCode.TRANSPORT_ERROR,
                                message=f"HTTP error {response.status}: {error_message}",
                                details={"status_code": response.status, **request_metadata},
                            )
                            continue
                        else:
                            raise MCPError(
                                error_code=ErrorCode.TRANSPORT_ERROR,
                                message=f"HTTP error {response.status}: {error_message}",
                                details={"status_code": response.status, **request_metadata},
                            )
                    
                    # Parse the response
                    try:
                        raw_response = await response.json()
                        logger.debug(f"Received response from {endpoint_url}: {json.dumps(raw_response)}")
                        return raw_response
                    except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                        if self._should_retry(response.status, retry_count):
                            retry_count += 1
                            last_exception = MCPError(
                                error_code=ErrorCode.PROTOCOL_ERROR,
                                message=f"Failed to parse response as JSON: {str(e)}",
                                details={"response_text": await response.text(), **request_metadata},
                            )
                            continue
                        else:
                            raise MCPError(
                                error_code=ErrorCode.PROTOCOL_ERROR,
                                message=f"Failed to parse response as JSON: {str(e)}",
                                details={"response_text": await response.text(), **request_metadata},
                            )
                            
            except (ClientError, asyncio.TimeoutError) as e:
                if self._should_retry(None, retry_count):
                    retry_count += 1
                    last_exception = MCPError(
                        error_code=ErrorCode.TRANSPORT_ERROR,
                        message=f"Request failed: {str(e)}",
                        details={"server_id": server_info.server_id, "endpoint_url": endpoint_url},
                    )
                    continue
                else:
                    raise MCPError(
                        error_code=ErrorCode.TRANSPORT_ERROR,
                        message=f"Request failed after {retry_count} retries: {str(e)}",
                        details={"server_id": server_info.server_id, "endpoint_url": endpoint_url},
                    )
                    
        # If we've exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception
            
        # This should never happen, but just in case
        raise MCPError(
            error_code=ErrorCode.TRANSPORT_ERROR,
            message=f"Request failed after {self.max_retries} retries",
            details={"server_id": server_info.server_id, "endpoint_url": endpoint_url},
        )
        
    async def _handle_http_error(self, response: ClientResponse) -> str:
        """
        Handle an HTTP error response.
        
        Args:
            response: The HTTP response
            
        Returns:
            str: The error message
        """
        try:
            error_data = await response.json()
            if isinstance(error_data, dict) and "message" in error_data:
                return error_data["message"]
            else:
                return f"Unexpected error response: {json.dumps(error_data)}"
        except (json.JSONDecodeError, aiohttp.ContentTypeError):
            return await response.text() or f"HTTP {response.status}"
            
    def _should_retry(self, status_code: Optional[int], retry_count: int) -> bool:
        """
        Determine if a request should be retried.
        
        Args:
            status_code: The HTTP status code, or None if the request failed before getting a response
            retry_count: The current retry count
            
        Returns:
            bool: True if the request should be retried, False otherwise
        """
        # Don't retry if we've reached the maximum number of retries
        if retry_count >= self.max_retries:
            return False
            
        # Retry on connection errors (no status code)
        if status_code is None:
            return True
            
        # Retry on 5xx server errors
        if 500 <= status_code < 600:
            return True
            
        # Retry on specific 4xx errors that might be temporary
        if status_code in (408, 429):  # Request Timeout, Too Many Requests
            return True
            
        # Don't retry on other 4xx client errors
        return False

    async def check_server_health(self, server_info: MCPServerInfo) -> bool:
        """
        Check if a server is healthy using MCP-compliant health check patterns.
        
        This method implements a robust health check strategy that:
        1. First attempts a GET request (standard HTTP health check)
        2. Falls back to POST with MCP ping request if GET fails with 405 (Method Not Allowed)
        3. Handles AWS Lambda Function URLs which only accept POST by default
        4. Follows MCP protocol patterns for server communication
        
        Args:
            server_info: Information about the server to check
            
        Returns:
            bool: True if the server is healthy, False otherwise
        """
        server_id = server_info.server_id
        circuit_breaker = self._get_circuit_breaker(server_id)
        
        # If the circuit is open, the server is considered unhealthy
        if circuit_breaker.is_open:
            logger.warning(f"Health check for {server_id} skipped: circuit is open")
            return False
            
        # Use dedicated health check URL if provided, otherwise use main endpoint
        health_check_url = server_info.health_check_url or server_info.endpoint_url
        
        try:
            session = await self._get_session()
            
            # Determine health check strategy based on configuration
            health_check_method = getattr(server_info, 'health_check_method', 'AUTO')
            if hasattr(health_check_method, 'value'):
                health_check_method = health_check_method.value
            
            health_result = False
            
            if health_check_method == 'GET':
                # Only try GET method
                health_result = await self._try_get_health_check(session, server_info, health_check_url)
                if health_result is None:
                    health_result = False  # Convert None to False for GET-only mode
            elif health_check_method == 'POST':
                # Only try POST method with MCP ping
                health_result = await self._try_mcp_ping_health_check(session, server_info, health_check_url)
            else:  # AUTO mode (default)
                # First, try a standard GET health check
                health_result = await self._try_get_health_check(session, server_info, health_check_url)
                
                # If GET failed with 405 (Method Not Allowed), try POST with MCP ping
                if health_result is None:
                    logger.debug(f"GET health check failed for {server_id}, trying MCP ping via POST")
                    health_result = await self._try_mcp_ping_health_check(session, server_info, health_check_url)
            
            if health_result:
                logger.debug(f"Health check for {server_id} succeeded using {health_check_method} method")
                # Reset the circuit breaker if it was in half-open state
                if circuit_breaker.is_half_open:
                    circuit_breaker.reset()
                return True
            else:
                logger.warning(f"Health check for {server_id} failed using {health_check_method} method")
                return False
                    
        except Exception as e:
            logger.warning(f"Health check for {server_id} failed: {str(e)}")
            return False
    
    async def _try_get_health_check(
        self, 
        session: ClientSession, 
        server_info: MCPServerInfo, 
        health_check_url: str
    ) -> Optional[bool]:
        """
        Try a standard GET health check.
        
        Args:
            session: The HTTP session to use
            server_info: Server information
            health_check_url: URL to check
            
        Returns:
            Optional[bool]: True if healthy, False if unhealthy, None if method not supported
        """
        try:
            # Prepare headers for GET health check
            headers = {}
            
            # Handle authentication for GET health check
            auth_config = server_info.auth or server_info.auth_config
            if auth_config and self._is_aws_sigv4_auth(auth_config):
                headers = await self._add_aws_auth_headers(auth_config, "GET", health_check_url, "")
            
            async with session.get(
                health_check_url,
                headers=headers,
                timeout=ClientTimeout(total=5.0),
                raise_for_status=False,
            ) as response:
                if response.status == 405:  # Method Not Allowed
                    logger.debug(f"GET method not allowed for {server_info.server_id}, will try POST")
                    return None
                elif response.status < 400:
                    return True
                else:
                    logger.debug(f"GET health check failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.debug(f"GET health check failed: {str(e)}")
            return False
    
    async def _try_mcp_ping_health_check(
        self, 
        session: ClientSession, 
        server_info: MCPServerInfo, 
        health_check_url: str
    ) -> bool:
        """
        Try an MCP-compliant ping health check using POST.
        
        This follows MCP protocol patterns by sending a minimal ping request
        to verify the server is responsive and can handle MCP protocol messages.
        
        Args:
            session: The HTTP session to use
            server_info: Server information
            health_check_url: URL to check
            
        Returns:
            bool: True if healthy, False if unhealthy
        """
        try:
            # Create a minimal MCP ping request following protocol patterns
            ping_request = {
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": "ping",
                "params": {}
            }
            
            # Prepare headers for POST health check
            headers = {"Content-Type": "application/json"}
            
            # Handle authentication for POST health check
            auth_config = server_info.auth or server_info.auth_config
            if auth_config and self._is_aws_sigv4_auth(auth_config):
                request_body = json.dumps(ping_request)
                headers = await self._add_aws_auth_headers(auth_config, "POST", health_check_url, request_body)
                headers["Content-Type"] = "application/json"  # Ensure content-type is preserved
            
            async with session.post(
                health_check_url,
                json=ping_request,
                headers=headers,
                timeout=ClientTimeout(total=5.0),
                raise_for_status=False,
            ) as response:
                if response.status < 400:
                    # For MCP ping, we accept any successful response
                    # The server might not implement ping specifically, but if it responds
                    # successfully to a POST request, it's likely healthy
                    return True
                else:
                    logger.debug(f"POST health check failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.debug(f"POST health check failed: {str(e)}")
            return False
    
    def _is_aws_sigv4_auth(self, auth_config: Union[Dict[str, Any], Any]) -> bool:
        """Check if the auth config is for AWS SigV4."""
        if isinstance(auth_config, dict):
            return auth_config.get("type") == "aws_sigv4"
        elif hasattr(auth_config, "type"):
            return auth_config.type == "aws_sigv4"
        return False
    
    async def _add_aws_auth_headers(
        self, 
        auth_config: Union[Dict[str, Any], Any], 
        method: str, 
        url: str, 
        body: str
    ) -> Dict[str, str]:
        """Add AWS SigV4 authentication headers."""
        headers = {}
        
        try:
            # Handle AWS SigV4 authentication
            if isinstance(auth_config, dict) and auth_config.get("role_arn"):
                # Create a temporary credential provider for this specific role
                from mcp_client.aws.auth import AWSCredentialProvider, AWSAuthenticator
                logger.debug(f"Creating temporary credential provider for role: {auth_config.get('role_arn')}")
                temp_provider = AWSCredentialProvider(
                    region=auth_config.get("region", "us-east-1"),
                    role_arn=auth_config.get("role_arn"),
                    external_id=auth_config.get("external_id")
                )
                temp_authenticator = AWSAuthenticator(temp_provider)
                service = auth_config.get("service", "lambda")
                signed_headers = temp_authenticator.sign_request(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    service=service,
                    server_id="health-check"
                )
                headers.update(signed_headers)
                logger.debug(f"Added AWS SigV4 authentication for {method} request to service: {service}")
            elif self.authenticator and hasattr(self.authenticator, 'sign_request'):
                service = "lambda"
                if hasattr(auth_config, "service"):
                    service = auth_config.service
                elif isinstance(auth_config, dict):
                    service = auth_config.get("service", "lambda")
                signed_headers = self.authenticator.sign_request(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    service=service,
                    server_id="health-check"
                )
                headers.update(signed_headers)
                logger.debug(f"Added AWS SigV4 authentication for {method} request")
        except Exception as e:
            logger.warning(f"Failed to authenticate {method} health check: {e}")
        
        return headers