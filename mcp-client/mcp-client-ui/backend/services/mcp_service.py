"""MCP (Model Context Protocol) service for tool integration."""

import asyncio
import logging
from typing import Dict, Any, Optional

from config.settings import settings
from mcp_client.core.models import MCPResponse


class MCPService:
    """Service for managing MCP client and tool integrations."""
    
    def __init__(self):
        """Initialize the MCP service."""
        self.logger = logging.getLogger(__name__)
        self._mcp_client = None
        self._available_tools = {}
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False
        self._initialization_error = None
        self._server_configs = {}
        self._registered_servers = set()
        self._cognito_jwt_token = None  # Store the current JWT token
        

    
    async def initialize(self) -> bool:
        """Initialize the MCP client and related services."""
        async with self._initialization_lock:
            if self._is_initialized:
                return self._initialization_error is None
            
            try:
                # Import required modules for MCP integration
                import sys
                import os
                
                # Add project root to path for imports
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                # Import MCP client and components
                from mcp_client.client import MCPClient
                from mcp_client.core.models import MCPClientConfig, DiscoveryMode
                from examples.config_loader import MCPConfigLoader
                
                # Load MCP servers from configuration
                config_loader = MCPConfigLoader()
                servers = config_loader.get_servers_for_environment(settings.MCP_ENVIRONMENT)
                
                # Initialize MCP client if servers are available
                if servers:
                    client_config = MCPClientConfig(
                        aws_region=settings.AWS_REGION,
                        enable_aws_auth=True,  # Enable AWS SigV4 authentication for Lambda URL
                        discovery_mode=DiscoveryMode.STATIC,
                        static_servers=servers,
                        timeout_seconds=300.0,  # Increased to 5 minutes for long-running operations
                        # Ensure we use the ECS task role credentials
                        aws_profile=None,  # Use default credential chain (ECS task role)
                        aws_role_arn=None,  # Not using role assumption, using ECS task role directly
                    )
                    
                    # Test AWS credentials before initializing MCP client
                    try:
                        import boto3
                        from botocore.exceptions import NoCredentialsError, ClientError
                        
                        # Try to get credentials using the default credential chain
                        session = boto3.Session(region_name=settings.AWS_REGION)
                        credentials = session.get_credentials()
                        
                        if not credentials:
                            self.logger.error("No AWS credentials found in the credential chain")
                            self.logger.error("Available credential sources: environment variables, IAM roles, credential files")
                            raise Exception("No AWS credentials available")
                        
                        # Test the credentials with STS
                        sts_client = session.client('sts')
                        identity = sts_client.get_caller_identity()
                        self.logger.info(f"AWS credentials verified - Account: {identity.get('Account')}, ARN: {identity.get('Arn')}")
                        self.logger.info(f"MCP client config - enable_aws_auth: {client_config.enable_aws_auth}, aws_region: {client_config.aws_region}")
                        
                        # Log credential source for debugging
                        if hasattr(credentials, 'method'):
                            self.logger.info(f"Credential source: {credentials.method}")
                        
                    except (NoCredentialsError, ClientError) as e:
                        self.logger.error(f"AWS credentials verification failed: {e}")
                        self.logger.error("Make sure your ECS task role has the necessary permissions")
                        # Don't fail initialization, but log the issue
                    except Exception as e:
                        self.logger.error(f"Unexpected error during AWS credential verification: {e}")
                    
                    self.logger.debug(f"Creating MCP client with AWS auth: {client_config.enable_aws_auth}")
                    self._mcp_client = MCPClient(client_config)
                    self.logger.info("MCP client created successfully")
                    
                    # Configure MCP logging to reduce verbosity
                    self._configure_mcp_logging()
                    
                    # Store server configs for on-demand loading instead of registering all
                    self._server_configs = {server.server_id: server for server in servers}
                    self._registered_servers = set()
                    
                    # Pre-populate available tools metadata without registering servers
                    self._available_tools = {}
                    for server in servers:
                        self._available_tools[server.server_id] = {
                            'capabilities': server.capabilities,
                            'description': server.metadata.get('description', f'{server.server_type} server'),
                            'server_type': server.server_type,
                            'registered': False
                        }
                    
                    self.logger.info(f"Stored {len(servers)} server configurations for on-demand loading")
                else:
                    self.logger.info("No MCP servers configured - running without tools")
                    self._mcp_client = None
                    self._available_tools = {}
                
                # Initialize related services
                await self._initialize_related_services()
                
                self._is_initialized = True
                self._initialization_error = None
                self.logger.debug("MCP service initialized successfully")
                return True
                
            except Exception as e:
                self._initialization_error = str(e)
                self._is_initialized = True
                self.logger.error(f"MCP service initialization failed: {e}")
                
                # Initialize fallback services
                await self._initialize_fallback_services()
                return False
    
    def _configure_mcp_logging(self):
        """Configure MCP logging to reduce verbosity."""
        mcp_loggers = [
            'mcp_client', 'mcp_client.transport', 'mcp_client.protocol',
            'mcp_client.discovery', 'mcp_client.security', 'mcp_client.client',
            'mcp_client.performance', 'mcp_client.aws.auth', 'services.mcp_discovery',
            'mcp_client.transport.http'  # This is the noisy one
        ]
        
        for logger_name in mcp_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)  # Changed from ERROR to WARNING
            # Remove any existing handlers to prevent duplicate logs
            logger.handlers.clear()
            logger.propagate = False
    
    async def ensure_server_registered(self, server_id: str) -> bool:
        """Ensure a specific server is registered when needed (on-demand)."""
        if server_id in self._registered_servers:
            return True
        
        if server_id not in self._server_configs:
            self.logger.warning(f"Server {server_id} not found in configurations")
            return False
        
        if not self._mcp_client:
            self.logger.error(f"Cannot register server {server_id}: MCP client not available")
            return False
        
        try:
            server = self._server_configs[server_id]
            self.logger.info(f"On-demand registration of MCP server: {server_id}")
            
            # Add additional logging for AWS authentication debugging
            if hasattr(server, 'auth') and server.auth:
                self.logger.info(f"Server {server_id} has authentication config: {type(server.auth)}")
            
            await self._mcp_client.register_server(server)
            self._registered_servers.add(server_id)
            
            # Update tool metadata
            if server_id in self._available_tools:
                self._available_tools[server_id]['registered'] = True
            
            self.logger.info(f"Successfully registered MCP server on-demand: {server_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register MCP server {server_id} on-demand: {e}")
            # Log more details for debugging
            if "credentials" in str(e).lower():
                self.logger.error("This appears to be an AWS credentials issue")
                self.logger.error("Check that your ECS task role has the necessary permissions")
            return False
    
    async def _register_servers(self, servers):
        """Legacy method - now handled by on-demand loading."""
        # This method is kept for backward compatibility but does nothing
        # All registration is now handled on-demand
        pass
    
    async def _initialize_related_services(self):
        """Initialize services that depend on MCP client."""
        try:
            # Initialize Design MCP Integration
            from services.design_mcp_integration import DesignMCPIntegration
            from services.mcp_discovery import MCPServerDiscovery
            
            mcp_discovery = MCPServerDiscovery(self._mcp_client)
            self._design_mcp_integration = DesignMCPIntegration(self._mcp_client, mcp_discovery)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize related services: {e}")
    
    async def _initialize_fallback_services(self):
        """Initialize fallback services when MCP client is not available."""
        try:
            from services.design_mcp_integration import DesignMCPIntegration
            self._design_mcp_integration = DesignMCPIntegration(None, None)
            
            # Fallback initialization complete
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize fallback services: {e}")
            self._design_mcp_integration = None
    
    def is_available(self) -> bool:
        """Check if MCP client is available and initialized."""
        return self._is_initialized and self._initialization_error is None and self._mcp_client is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get status information about MCP client initialization."""
        return {
            'is_initialized': self._is_initialized,
            'has_error': self._initialization_error is not None,
            'error_message': self._initialization_error,
            'mcp_client_available': self._mcp_client is not None,
            'available_tools_count': len(self._available_tools)
        }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get available MCP tools."""
        return self._available_tools.copy()
    
    def get_mcp_client(self):
        """Get the MCP client instance."""
        return self._mcp_client
    
    def get_registered_servers(self):
        """Get the set of currently registered servers."""
        return getattr(self, '_registered_servers', set())
    
    def get_server_configs(self):
        """Get the server configurations."""
        return getattr(self, '_server_configs', {})
    

    
    def get_design_integration(self):
        """Get the design MCP integration."""
        return self._design_mcp_integration
    
    def set_cognito_id_token(self, id_token: str):
        """
        Set the Cognito ID token for Amazon Q Business authentication.
        
        Args:
            id_token: The ID token from Cognito authentication (not access token)
        """
        self._cognito_jwt_token = id_token
        
        # Set it directly in the authenticator if available
        if self._mcp_client and hasattr(self._mcp_client, '_transport') and hasattr(self._mcp_client._transport, 'authenticator'):
            authenticator = self._mcp_client._transport.authenticator
            if hasattr(authenticator, '_jwt_token'):
                authenticator._jwt_token = id_token
            elif hasattr(authenticator, 'jwt_token'):
                authenticator.jwt_token = id_token
        
        self.logger.info("Cognito ID token updated for Amazon Q Business")
        self.logger.info(f"ID token length: {len(id_token)} chars, stored in MCP service instance")
    
    def get_cognito_id_token(self) -> Optional[str]:
        """
        Get the current Cognito ID token.
        
        Returns:
            Optional[str]: The current ID token or None if not set
        """
        return self._cognito_jwt_token
    
    def clear_cognito_id_token(self):
        """Clear the stored Cognito ID token."""
        self._cognito_jwt_token = None
        # Clear from authenticator if available
        if self._mcp_client and hasattr(self._mcp_client, '_transport') and hasattr(self._mcp_client._transport, 'authenticator'):
            authenticator = self._mcp_client._transport.authenticator
            if hasattr(authenticator, '_jwt_token'):
                authenticator._jwt_token = None
        self.logger.info("Cognito ID token cleared")
    
    async def send_request_with_jwt(self, request_data: Dict[str, Any], server_id: str = "amazon-q-business") -> MCPResponse:
        """
        Send a request to Amazon Q Business with simplified JWT authentication.
        
        Uses client's AWS credentials + includes JWT token in X-Cognito-JWT header.
        
        Args:
            request_data: The request data to send
            server_id: The server ID to send the request to (default: amazon-q-business)
            
        Returns:
            MCPResponse: The full MCP response object from the server
            
        Raises:
            Exception: If the request fails or JWT token is not available
        """
        if not self.is_available():
            raise Exception("MCP client is not available")
        
        try:
            # Ensure the server is registered
            await self.ensure_server_registered(server_id)
            
            # Create MCP request
            from mcp_client.core.models import MCPRequest
            
            # Prepare headers with JWT token for Amazon Q Business authentication
            headers = {"Content-Type": "application/json"}
            
            # Add JWT token directly to headers if available
            if self._cognito_jwt_token:
                headers["X-Cognito-JWT"] = self._cognito_jwt_token
                self.logger.info(f"Added JWT token to request headers for {server_id}")
            else:
                self.logger.info(f"No JWT token provided for {server_id} request (this is expected if not using Amazon Q Business features)")
            
            # Extract tool name and arguments from request_data
            if "name" in request_data:
                tool_name = request_data["name"]
                arguments = request_data.get("arguments", {})
            elif "params" in request_data and "name" in request_data["params"]:
                tool_name = request_data["params"]["name"]
                arguments = request_data["params"].get("arguments", {})
            else:
                tool_name = "mcp_amazon_q_business_retrieve"  # Default tool
                arguments = request_data
            
            # Format as proper MCP tool call
            tool_call_content = {
                "name": tool_name,
                "arguments": arguments
            }
            
            mcp_request = MCPRequest(
                request_type="tools/call",
                content=tool_call_content,
                required_capabilities=["mcp_amazon_q_business_retrieve", "mcp_amazon_q_business_create"],
                preferred_server_id=server_id,
                headers=headers
            )
            
            # Send the request (JWT will be added during SigV4 signing)
            response = await self._mcp_client.send_request(mcp_request)
            
            self.logger.info(f"Successfully sent request to {server_id}")
            return response  # Return the full MCPResponse object, not just content
            
        except Exception as e:
            self.logger.error(f"Failed to send request to {server_id}: {e}")
            if "credentials" in str(e).lower() or "authentication" in str(e).lower():
                self.logger.error("Authentication failed - check that:")
                self.logger.error("1. AWS credentials are available")
                self.logger.error("2. Cognito JWT token is set via set_cognito_jwt_token()")
            raise
    
    async def re_register_all_servers(self):
        """Re-register all MCP servers - useful after authentication changes."""
        try:
            self.logger.info("Re-registering all MCP servers...")
            
            # Clear registered servers to force re-registration
            self._registered_servers.clear()
            
            # Mark all tools as not registered
            for server_id in self._available_tools:
                self._available_tools[server_id]['registered'] = False
            
            # Re-register all servers that were previously configured
            for server_id in self._server_configs:
                try:
                    await self.ensure_server_registered(server_id)
                except Exception as e:
                    self.logger.warning(f"Failed to re-register server {server_id}: {e}")
            
            self.logger.info(f"Re-registration completed - {len(self._registered_servers)} servers registered")
            
        except Exception as e:
            self.logger.error(f"Failed to re-register MCP servers: {e}")
    
    def diagnose_aws_credentials(self) -> Dict[str, Any]:
        """
        Diagnose AWS credential configuration and availability.
        
        Returns:
            Dict[str, Any]: Diagnostic information about AWS credentials
        """
        diagnosis = {
            "credentials_available": False,
            "credential_source": None,
            "account_id": None,
            "arn": None,
            "region": None,
            "errors": []
        }
        
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            from config.settings import settings
            
            # Try to get credentials
            session = boto3.Session(region_name=settings.AWS_REGION)
            credentials = session.get_credentials()
            
            if credentials:
                diagnosis["credentials_available"] = True
                diagnosis["region"] = settings.AWS_REGION
                
                # Get credential source if available
                if hasattr(credentials, 'method'):
                    diagnosis["credential_source"] = credentials.method
                
                # Test credentials with STS
                try:
                    sts_client = session.client('sts')
                    identity = sts_client.get_caller_identity()
                    diagnosis["account_id"] = identity.get('Account')
                    diagnosis["arn"] = identity.get('Arn')
                except Exception as e:
                    diagnosis["errors"].append(f"STS call failed: {str(e)}")
            else:
                diagnosis["errors"].append("No credentials found in credential chain")
                
        except NoCredentialsError as e:
            diagnosis["errors"].append(f"No credentials error: {str(e)}")
        except Exception as e:
            diagnosis["errors"].append(f"Unexpected error: {str(e)}")
        
        return diagnosis
    
    async def test_amazon_q_business_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Amazon Q Business service.
        
        Returns:
            Dict[str, Any]: Test results
        """
        test_result = {
            "success": False,
            "server_registered": False,
            "authentication_working": False,
            "error_message": None,
            "aws_credentials": None
        }
        
        try:
            # First check AWS credentials
            test_result["aws_credentials"] = self.diagnose_aws_credentials()
            
            if not test_result["aws_credentials"]["credentials_available"]:
                test_result["error_message"] = "AWS credentials not available"
                return test_result
            
            # Try to register the Amazon Q Business server
            server_id = "amazon-q-business"
            test_result["server_registered"] = await self.ensure_server_registered(server_id)
            
            if not test_result["server_registered"]:
                test_result["error_message"] = "Failed to register Amazon Q Business server"
                return test_result
            
            # Try a simple test request
            test_request = {
                "tool_name": "mcp_amazon_q_business_retrieve",
                "message": "Test connection to Amazon Q Business"
            }
            
            response = await self.send_request_with_jwt(test_request, server_id)
            test_result["success"] = True
            test_result["authentication_working"] = True
            
        except Exception as e:
            test_result["error_message"] = str(e)
            self.logger.error(f"Amazon Q Business connection test failed: {e}")
        
        return test_result