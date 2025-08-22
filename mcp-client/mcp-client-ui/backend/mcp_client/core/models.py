"""
Core data models for the MCP Client.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ServerStatus(str, Enum):
    """Status of an MCP server."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"


class ServerType(str, Enum):
    """Type of an MCP server."""

    IMAGE_CREATION = "image_creation"
    DATA_RETRIEVAL = "data_retrieval"
    CONVERSATIONAL = "conversational"
    ACTION = "action"
    TOOL = "tool"  # Added for tool-based servers
    ARCHITECTURE = "architecture"  # Added for architecture design servers
    GENERAL = "general"


class DiscoveryMode(str, Enum):
    """Mode for server discovery."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    HYBRID = "hybrid"


class MCPClientConfig(BaseModel):
    """Configuration for the MCP Client."""

    # AWS configuration
    aws_region: str
    aws_profile: Optional[str] = None
    aws_role_arn: Optional[str] = None
    aws_session_name: Optional[str] = None
    aws_external_id: Optional[str] = None
    enable_aws_auth: bool = False

    # Server discovery configuration
    discovery_mode: DiscoveryMode = DiscoveryMode.DYNAMIC
    static_servers: List["MCPServerInfo"] = Field(default_factory=list)
    registry_table_name: Optional[str] = None

    # Transport configuration
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.5

    # Security configuration
    use_tls: bool = True
    verify_ssl: bool = True
    cert_path: Optional[str] = None  # Deprecated, use client_cert_path
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    client_key_password: Optional[str] = None
    min_tls_version: Optional[str] = None
    cert_fingerprints: Dict[str, str] = Field(default_factory=dict)
    cipher_suites: Optional[str] = None

    # Monitoring configuration
    enable_metrics: bool = True
    enable_tracing: bool = True
    log_level: str = "INFO"

    @field_validator("aws_region")
    def validate_aws_region(cls, v: str) -> str:
        """Validate that the AWS region is valid."""
        # This is a simplified validation, in a real implementation we would check against
        # a list of valid AWS regions or use boto3 to validate
        if not v.startswith("us-") and not v.startswith("eu-") and not v.startswith("ap-"):
            raise ValueError(f"Invalid AWS region: {v}")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate that the log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v
        
    @field_validator("timeout_seconds", "max_retries", "retry_backoff_factor")
    def validate_positive_values(cls, v: float) -> float:
        """Validate that the value is positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
        
    @model_validator(mode="after")
    def validate_static_servers(self) -> "MCPClientConfig":
        """Validate that static servers are provided when using static discovery mode."""
        if self.discovery_mode == DiscoveryMode.STATIC and not self.static_servers:
            raise ValueError("Static servers must be provided when using static discovery mode")
        return self


class AuthConfig(BaseModel):
    """Authentication configuration for MCP servers."""
    
    type: str  # "aws_sigv4", "bearer_token", "api_key", etc.
    region: Optional[str] = None  # For AWS SigV4
    service: Optional[str] = None  # For AWS SigV4
    role_arn: Optional[str] = None  # For cross-account AWS access
    token: Optional[str] = None  # For bearer token auth
    api_key: Optional[str] = None  # For API key auth
    headers: Dict[str, str] = Field(default_factory=dict)  # Custom headers


class HealthCheckMethod(str, Enum):
    """HTTP method to use for health checks."""
    
    GET = "GET"
    POST = "POST"
    AUTO = "AUTO"  # Try GET first, fallback to POST if 405


class MCPServerInfo(BaseModel):
    """Information about an MCP server."""

    server_id: str
    endpoint_url: Optional[str] = None  # Made optional to support stdio transport
    capabilities: List[str]
    server_type: ServerType
    health_check_url: Optional[str] = None
    health_check_method: HealthCheckMethod = HealthCheckMethod.AUTO
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_seen: Optional[datetime] = None
    status: ServerStatus = ServerStatus.ACTIVE
    auth_config: Optional[AuthConfig] = None  # Authentication configuration
    auth: Optional[Dict[str, Any]] = None  # Alternative auth format (for backward compatibility)
    
    # Additional fields for stdio transport
    transport: Optional[str] = None  # "stdio", "http", etc.
    command: Optional[str] = None  # Command to run for stdio transport
    args: Optional[List[str]] = None  # Arguments for stdio transport


class MCPRequest(BaseModel):
    """A request to an MCP server."""

    request_type: str
    content: Dict[str, Any]
    required_capabilities: List[str] = Field(default_factory=list)
    preferred_server_id: Optional[str] = None
    timeout_seconds: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)  # Custom headers for authentication


class ResponseStatus(str, Enum):
    """Status of an MCP response."""

    SUCCESS = "success"
    ERROR = "error"


class MCPResponse(BaseModel):
    """A response from an MCP server."""

    status: ResponseStatus
    content: Dict[str, Any]
    server_id: str
    request_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorCode(str, Enum):
    """Error codes for MCP errors."""

    PROTOCOL_ERROR = "protocol_error"
    TRANSPORT_ERROR = "transport_error"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    DISCOVERY_ERROR = "discovery_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class MCPError(Exception):
    """An error from the MCP client."""

    def __init__(self, error_code: ErrorCode, message: str, details: Dict[str, Any] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(message)


# Update forward references
MCPClientConfig.model_rebuild()