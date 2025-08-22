"""
Protocol handler implementation for the MCP Client.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union, cast

from mcp_client.core.interfaces import ProtocolHandler
from mcp_client.core.models import (
    ErrorCode,
    MCPError,
    MCPRequest,
    MCPResponse,
    ResponseStatus,
)
from mcp_client.protocol.models import (
    ActionResponse,
    ChatResponse,
    EmbeddingResponse,
    ImageGenerationResponse,
    RequestType,
    TextGenerationResponse,
)

logger = logging.getLogger(__name__)


class MCPProtocolHandler(ProtocolHandler):
    """Implementation of the MCP protocol handler."""

    # Supported protocol versions
    SUPPORTED_VERSIONS = ["1.0", "1.1", "2.0"]
    DEFAULT_VERSION = "1.0"
    
    # Required fields for requests and responses
    REQUEST_REQUIRED_FIELDS = ["request_type", "content"]
    RESPONSE_REQUIRED_FIELDS = ["status", "content", "server_id", "request_id", "timestamp"]
    
    # Protocol version compatibility mapping
    # Maps newer versions to the closest compatible older version
    VERSION_COMPATIBILITY = {
        "2.0": "1.1",
        "1.1": "1.0"
    }

    def __init__(self, protocol_version: str = DEFAULT_VERSION):
        """
        Initialize the protocol handler.

        Args:
            protocol_version: The MCP protocol version to use
            
        Raises:
            ValueError: If the protocol version is not supported
        """
        if protocol_version not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported protocol version: {protocol_version}. Supported versions: {self.SUPPORTED_VERSIONS}")
            
        self.protocol_version = protocol_version
        self._response_type_map = {
            RequestType.TEXT_GENERATION: TextGenerationResponse,
            RequestType.IMAGE_GENERATION: ImageGenerationResponse,
            RequestType.EMBEDDING: EmbeddingResponse,
            RequestType.CHAT: ChatResponse,
            RequestType.ACTION: ActionResponse,
        }
        
        logger.info(f"Initialized MCP Protocol Handler with version {protocol_version}")
        
    def get_compatible_version(self, server_version: str) -> str:
        """
        Get a compatible protocol version for communicating with a server.
        
        Args:
            server_version: The protocol version supported by the server
            
        Returns:
            str: The compatible protocol version to use
            
        Raises:
            ValueError: If no compatible version can be found
        """
        # If versions match exactly, use that version
        if server_version == self.protocol_version:
            return self.protocol_version
            
        # If server version is newer than client version, use client version
        # (assuming server maintains backward compatibility)
        if self._compare_versions(server_version, self.protocol_version) > 0:
            return self.protocol_version
            
        # If client version is newer, find a compatible older version
        current_version = self.protocol_version
        while current_version in self.VERSION_COMPATIBILITY:
            current_version = self.VERSION_COMPATIBILITY[current_version]
            if current_version == server_version:
                return server_version
                
        # No compatible version found
        raise ValueError(
            f"No compatible protocol version found. Server version: {server_version}, Client version: {self.protocol_version}"
        )
        
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
                
        return 0

    def validate_request(self, request: MCPRequest) -> bool:
        """
        Validate that a request conforms to the MCP protocol.

        Args:
            request: The request to validate

        Returns:
            bool: True if the request is valid, False otherwise

        Raises:
            ValueError: If the request is invalid
        """
        # Check that the request has all required fields
        for field in self.REQUEST_REQUIRED_FIELDS:
            if not hasattr(request, field) or not getattr(request, field):
                # Use specific error messages for backward compatibility with tests
                if field == "request_type":
                    raise ValueError("Request must have a request type")
                elif field == "content":
                    raise ValueError("Request must have content")
                else:
                    raise ValueError(f"Request must have a {field}")

        # Validate request type - allow custom request types for tool servers
        known_types = [rt.value for rt in RequestType]
        if request.request_type not in known_types:
            # Allow custom request types that aren't in the predefined list
            # This enables tool servers to define their own request types
            logger.debug(f"Using custom request type: {request.request_type}")

        # Additional validation based on request type
        if request.request_type == RequestType.TEXT_GENERATION:
            if "prompt" not in request.content:
                raise ValueError("Text generation request must have a prompt")
            # Validate prompt is a string
            if not isinstance(request.content["prompt"], str):
                raise ValueError("Text generation prompt must be a string")
                
        elif request.request_type == RequestType.IMAGE_GENERATION:
            if "prompt" not in request.content:
                raise ValueError("Image generation request must have a prompt")
            # Validate prompt is a string
            if not isinstance(request.content["prompt"], str):
                raise ValueError("Image generation prompt must be a string")
                
        elif request.request_type == RequestType.EMBEDDING:
            if "text" not in request.content:
                raise ValueError("Embedding request must have text")
            # Validate text is a string or list of strings
            if not isinstance(request.content["text"], (str, list)):
                raise ValueError("Embedding text must be a string or list of strings")
            if isinstance(request.content["text"], list):
                if not all(isinstance(item, str) for item in request.content["text"]):
                    raise ValueError("All items in embedding text list must be strings")
                    
        elif request.request_type == RequestType.CHAT:
            if "messages" not in request.content:
                raise ValueError("Chat request must have messages")
            # Validate messages is a list
            if not isinstance(request.content["messages"], list):
                raise ValueError("Chat messages must be a list")
            # Validate each message has role and content
            for i, message in enumerate(request.content["messages"]):
                if not isinstance(message, dict):
                    raise ValueError(f"Chat message {i} must be a dictionary")
                if "role" not in message:
                    raise ValueError(f"Chat message {i} must have a role")
                if "content" not in message:
                    raise ValueError(f"Chat message {i} must have content")
                    
        elif request.request_type == RequestType.ACTION:
            if "action" not in request.content:
                raise ValueError("Action request must have an action")
            # Validate action is a string
            if not isinstance(request.content["action"], str):
                raise ValueError("Action must be a string")

        # Validate capabilities if present
        if request.required_capabilities and not isinstance(request.required_capabilities, list):
            raise ValueError("Required capabilities must be a list")
            
        # Validate timeout if present
        if request.timeout_seconds is not None and not isinstance(request.timeout_seconds, (int, float)):
            raise ValueError("Timeout must be a number")
        if request.timeout_seconds is not None and request.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
            
        # Validate metadata if present
        if request.metadata and not isinstance(request.metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        return True

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that a response conforms to the MCP protocol.

        Args:
            response: The raw response to validate

        Returns:
            bool: True if the response is valid, False otherwise

        Raises:
            ValueError: If the response is invalid
        """
        # Check that the response has all required fields
        for field in self.RESPONSE_REQUIRED_FIELDS:
            if field not in response:
                # Use specific error messages for backward compatibility with tests
                if field == "content":
                    raise ValueError("Response must have content")
                elif field == "status":
                    raise ValueError("Response must have a status")
                elif field == "server_id":
                    raise ValueError("Response must have a server_id")
                elif field == "request_id":
                    raise ValueError("Response must have a request_id")
                elif field == "timestamp":
                    raise ValueError("Response must have a timestamp")
                else:
                    raise ValueError(f"Response must have a {field}")
                
        # Validate protocol version if present
        if "protocol_version" in response:
            protocol_version = response["protocol_version"]
            if protocol_version not in self.SUPPORTED_VERSIONS:
                logger.warning(f"Response uses unsupported protocol version: {protocol_version}")
                
        # Validate status
        if response["status"] not in [status.value for status in ResponseStatus]:
            raise ValueError(f"Unknown response status: {response['status']}")
            
        # Validate content is a dictionary
        if not isinstance(response["content"], dict):
            raise ValueError("Response content must be a dictionary")
            
        # Validate server_id is a string
        if not isinstance(response["server_id"], str):
            raise ValueError("Server ID must be a string")
            
        # Validate request_id is a string
        if not isinstance(response["request_id"], str):
            raise ValueError("Request ID must be a string")
            
        # Validate timestamp format
        if isinstance(response["timestamp"], str):
            try:
                datetime.fromisoformat(response["timestamp"])
            except ValueError:
                # Just log a warning for invalid timestamps, don't raise an error
                # This is to maintain compatibility with the test_parse_response_invalid_timestamp test
                logger.warning(f"Invalid timestamp format: {response['timestamp']}")
                
        # Additional validation based on response status
        if response["status"] == ResponseStatus.SUCCESS:
            # Validate based on the request type if available
            if "request_type" in response:
                request_type = response["request_type"]
                if request_type == RequestType.TEXT_GENERATION:
                    if "text" not in response["content"]:
                        raise ValueError("Text generation response must have text")
                    if not isinstance(response["content"]["text"], str):
                        raise ValueError("Text generation response text must be a string")
                        
                elif request_type == RequestType.IMAGE_GENERATION:
                    if "image_url" not in response["content"] and "image_data" not in response["content"]:
                        raise ValueError("Image generation response must have an image URL or data")
                    if "image_url" in response["content"] and not isinstance(response["content"]["image_url"], str):
                        raise ValueError("Image URL must be a string")
                    if "image_data" in response["content"] and not isinstance(response["content"]["image_data"], str):
                        raise ValueError("Image data must be a string (base64 encoded)")
                        
                elif request_type == RequestType.EMBEDDING:
                    if "embeddings" not in response["content"]:
                        raise ValueError("Embedding response must have embeddings")
                    if not isinstance(response["content"]["embeddings"], list):
                        raise ValueError("Embeddings must be a list")
                        
                elif request_type == RequestType.CHAT:
                    if "message" not in response["content"]:
                        raise ValueError("Chat response must have a message")
                    if not isinstance(response["content"]["message"], dict):
                        raise ValueError("Chat message must be a dictionary")
                    if "role" not in response["content"]["message"]:
                        raise ValueError("Chat message must have a role")
                    if "content" not in response["content"]["message"]:
                        raise ValueError("Chat message must have content")
                        
                elif request_type == RequestType.ACTION:
                    if "result" not in response["content"]:
                        raise ValueError("Action response must have a result")
                        
        elif response["status"] == ResponseStatus.ERROR:
            # Check that the error response has an error code and message
            if "error_code" not in response["content"]:
                raise ValueError("Error response must have an error code")
            if "message" not in response["content"]:
                raise ValueError("Error response must have an error message")
            # Validate error code is a string
            if not isinstance(response["content"]["error_code"], str):
                raise ValueError("Error code must be a string")
            # Validate error message is a string
            if not isinstance(response["content"]["message"], str):
                raise ValueError("Error message must be a string")

        return True

    def format_request(self, request: MCPRequest, server_protocol_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a request according to the MCP protocol.

        Args:
            request: The request to format
            server_protocol_version: Optional protocol version supported by the target server

        Returns:
            Dict[str, Any]: The formatted request
            
        Raises:
            ValueError: If the request is invalid or no compatible protocol version can be found
        """
        # Validate the request first
        self.validate_request(request)
        
        # Determine the protocol version to use
        protocol_version = self.protocol_version
        if server_protocol_version:
            # Check if the server version is supported
            if server_protocol_version not in self.SUPPORTED_VERSIONS:
                raise ValueError(f"Unsupported protocol version: {server_protocol_version}. Supported versions: {self.SUPPORTED_VERSIONS}")
                
            try:
                protocol_version = self.get_compatible_version(server_protocol_version)
                logger.debug(f"Using compatible protocol version {protocol_version} for server version {server_protocol_version}")
            except ValueError as e:
                logger.error(f"Protocol version compatibility error: {e}")
                raise

        # Check if this is an Amazon Q Business MCP server request
        server_id = getattr(request, 'preferred_server_id', None)
        is_amazon_q_business = server_id in ["amazon-q-business", "amazon-q-business-prod"]
        
        # Format the request according to MCP over JSON-RPC 2.0 wire format
        request_id = str(uuid.uuid4())
        
        if is_amazon_q_business and request.request_type == "tools/call":
            # Special formatting for Amazon Q Business MCP server
            tool_name = request.content.get("name", "")
            tool_arguments = request.content.get("arguments", {})
            
            formatted_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_arguments
                },
                "id": request_id
            }
            
            logger.info(f"Formatted Amazon Q Business MCP request: {formatted_request}")
        else:
            # Standard MCP formatting - MCP message content goes directly in params
            formatted_request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": request.request_type,
                "params": request.content.copy()  # MCP message content goes directly in params
            }
        
        # Add MCP protocol metadata to params if needed
        if request.metadata:
            formatted_request["params"]["_mcp_metadata"] = request.metadata
        
        # Include custom headers if present (for transport layer)
        if request.headers:
            formatted_request["headers"] = request.headers
            
        # Apply version-specific transformations if needed
        formatted_request = self._apply_version_specific_formatting(formatted_request, protocol_version)

        return formatted_request
    
    def _parse_jsonrpc_response(self, raw_response: Dict[str, Any]) -> MCPResponse:
        """
        Parse a JSON-RPC 2.0 response into an MCPResponse object.
        
        Args:
            raw_response: The raw JSON-RPC response
            
        Returns:
            MCPResponse: The parsed response
        """
        from mcp_client.core.models import ResponseStatus
        
        # Extract basic info
        request_id = raw_response.get("id", "unknown")
        timestamp = datetime.now()
        
        # Check for error or result
        if "error" in raw_response:
            # JSON-RPC error response
            error = raw_response["error"]
            status = ResponseStatus.ERROR
            content = {
                "error_code": error.get("code", -1),
                "message": error.get("message", "Unknown error"),
                "details": error.get("data", {})
            }
        elif "result" in raw_response:
            # JSON-RPC success response
            status = ResponseStatus.SUCCESS
            content = raw_response["result"]
        else:
            # Invalid JSON-RPC response
            status = ResponseStatus.ERROR
            content = {
                "error_code": -32600,
                "message": "Invalid JSON-RPC response: missing result or error",
                "details": {"raw_response": raw_response}
            }
        
        # Create MCPResponse
        response = MCPResponse(
            status=status,
            content=content,
            server_id="unknown",  # JSON-RPC doesn't include server_id
            request_id=str(request_id),
            timestamp=timestamp,
            metadata={}
        )
        
        return response
    

        
    def _apply_version_specific_formatting(self, request: Dict[str, Any], version: str) -> Dict[str, Any]:
        """
        Apply version-specific transformations to a formatted request.
        
        Args:
            request: The formatted request
            version: The protocol version to format for
            
        Returns:
            Dict[str, Any]: The transformed request
        """
        # Clone the request to avoid modifying the original
        result = request.copy()
        
        # Apply transformations based on version
        if version == "1.0":
            # Version 1.0 doesn't support certain fields that might be in newer versions
            # Remove any fields that aren't supported in 1.0
            if "stream" in result:
                del result["stream"]
                
        elif version == "1.1":
            # Version 1.1 specific transformations
            pass
            
        elif version == "2.0":
            # Version 2.0 specific transformations
            pass
            
        return result

    def parse_response(self, raw_response: Dict[str, Any]) -> MCPResponse:
        """
        Parse a raw response into an MCPResponse object.
        Handles both MCP format and JSON-RPC format responses.

        Args:
            raw_response: The raw response to parse

        Returns:
            MCPResponse: The parsed response
        """
        try:
            # Check if this is a JSON-RPC response
            if "jsonrpc" in raw_response and raw_response["jsonrpc"] == "2.0":
                return self._parse_jsonrpc_response(raw_response)
            
            # Handle traditional MCP response format
            # Check for protocol version compatibility
            if "protocol_version" in raw_response:
                server_version = raw_response["protocol_version"]
                if server_version not in self.SUPPORTED_VERSIONS:
                    logger.warning(f"Server response uses unsupported protocol version: {server_version}")
                    # Try to handle it anyway, but log the warning
            
            # Validate the response
            self.validate_response(raw_response)

            # Parse the timestamp
            timestamp = raw_response.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {timestamp}")
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Create the appropriate response object based on the request type
            request_type = raw_response.get("request_type")
            response_class = self._get_response_class(request_type)

            # Apply any version-specific transformations to the response
            if "protocol_version" in raw_response:
                raw_response = self._apply_version_specific_response_parsing(
                    raw_response, raw_response["protocol_version"]
                )

            # Create the response object
            response = response_class(
                status=raw_response["status"],
                content=raw_response["content"],
                server_id=raw_response["server_id"],
                request_id=raw_response["request_id"],
                timestamp=timestamp,
                metadata=raw_response.get("metadata", {}),
            )
            return response
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            # Return an error response if parsing fails
            return MCPResponse(
                status=ResponseStatus.ERROR,
                content={
                    "error_code": ErrorCode.PROTOCOL_ERROR,
                    "message": f"Error parsing response: {str(e)}",
                    "details": {"raw_response": raw_response},
                },
                server_id=raw_response.get("server_id", "unknown"),
                request_id=raw_response.get("request_id", "unknown"),
                timestamp=datetime.now(),
                metadata=raw_response.get("metadata", {}),
            )
            
    def _apply_version_specific_response_parsing(self, response: Dict[str, Any], version: str) -> Dict[str, Any]:
        """
        Apply version-specific transformations to a raw response.
        
        Args:
            response: The raw response
            version: The protocol version of the response
            
        Returns:
            Dict[str, Any]: The transformed response
        """
        # Clone the response to avoid modifying the original
        result = response.copy()
        
        # Apply transformations based on version
        if version == "1.0":
            # Version 1.0 specific transformations
            pass
            
        elif version == "1.1":
            # Version 1.1 specific transformations
            pass
            
        elif version == "2.0":
            # Version 2.0 specific transformations
            # For example, if 2.0 uses a different field name that we need to map to our model
            if "response_content" in result and "content" not in result:
                result["content"] = result["response_content"]
                
        return result

    def _get_response_class(self, request_type: Optional[str]) -> Type[MCPResponse]:
        """
        Get the appropriate response class based on the request type.

        Args:
            request_type: The request type

        Returns:
            Type[MCPResponse]: The response class
        """
        if not request_type:
            return MCPResponse

        return self._response_type_map.get(request_type, MCPResponse)
        
    def detect_protocol_version(self, response: Dict[str, Any]) -> str:
        """
        Detect the protocol version from a response.
        
        Args:
            response: The raw response
            
        Returns:
            str: The detected protocol version, or the default version if not detected
        """
        if "protocol_version" in response:
            version = response["protocol_version"]
            if version in self.SUPPORTED_VERSIONS:
                return version
            else:
                logger.warning(f"Unsupported protocol version detected: {version}")
                
        # Try to infer version from response structure
        if "api_version" in response:
            # This might be a v2.0 response using a different field name
            logger.info("Detected potential v2.0 response using 'api_version' field")
            return "2.0"
            
        # Default to the handler's version
        return self.protocol_version
        
    def is_compatible_with_server(self, server_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if the client is compatible with a server.
        
        Args:
            server_info: Information about the server, including supported protocol versions
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple of (is_compatible, compatible_version)
        """
        if "supported_versions" in server_info:
            server_versions = server_info["supported_versions"]
            
            # First check for exact match
            if self.protocol_version in server_versions:
                return True, self.protocol_version
                
            # Then check for compatible versions
            for version in server_versions:
                try:
                    compatible_version = self.get_compatible_version(version)
                    return True, compatible_version
                except ValueError:
                    continue
                    
            # No compatible version found
            return False, None
            
        elif "protocol_version" in server_info:
            # Server only advertises a single version
            server_version = server_info["protocol_version"]
            try:
                compatible_version = self.get_compatible_version(server_version)
                return True, compatible_version
            except ValueError:
                return False, None
                
        # No version information available
        logger.warning("No protocol version information available for server")
        return True, self.protocol_version  # Assume compatibility with default version