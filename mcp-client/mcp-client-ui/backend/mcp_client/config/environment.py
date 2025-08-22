"""
Environment-based configuration management for the MCP Client.

This module provides functionality to load configuration from environment variables,
validate environment settings, and manage different deployment environments.
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from mcp_client.core.models import DiscoveryMode, MCPClientConfig, MCPServerInfo, ServerType


class Environment(str, Enum):
    """Deployment environments."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration settings."""
    
    environment: Environment
    debug: bool = False
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = True
    # Health check configuration removed - was unused
    
    # AWS Configuration
    aws_region: str = "us-west-2"
    aws_profile: Optional[str] = None
    aws_role_arn: Optional[str] = None
    
    # Security Configuration
    use_tls: bool = True
    verify_ssl: bool = True
    min_tls_version: str = "TLSv1.2"
    
    # Performance Configuration
    timeout_seconds: float = 120.0  # Increased from 30 to 120 seconds for complex operations
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    
    # Discovery Configuration
    discovery_mode: DiscoveryMode = DiscoveryMode.DYNAMIC
    static_servers: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional settings
    extra_settings: Dict[str, Any] = field(default_factory=dict)


def get_environment() -> Environment:
    """Get the current environment from environment variables."""
    env_name = os.getenv("MCP_ENVIRONMENT", "development").lower()
    
    try:
        return Environment(env_name)
    except ValueError:
        # Default to development if invalid environment specified
        return Environment.DEVELOPMENT


def load_config_from_env() -> EnvironmentConfig:
    """Load configuration from environment variables."""
    env = get_environment()
    
    config = EnvironmentConfig(environment=env)
    
    # Basic settings
    config.debug = _get_bool_env("MCP_DEBUG", config.debug)
    config.log_level = os.getenv("MCP_LOG_LEVEL", config.log_level)
    config.enable_metrics = _get_bool_env("MCP_ENABLE_METRICS", config.enable_metrics)
    config.enable_tracing = _get_bool_env("MCP_ENABLE_TRACING", config.enable_tracing)
    
    # Health check settings removed - was unused
    
    # AWS settings
    config.aws_region = os.getenv("AWS_REGION", os.getenv("MCP_AWS_REGION", config.aws_region))
    config.aws_profile = os.getenv("AWS_PROFILE", os.getenv("MCP_AWS_PROFILE"))
    config.aws_role_arn = os.getenv("MCP_AWS_ROLE_ARN")
    
    # Security settings
    config.use_tls = _get_bool_env("MCP_USE_TLS", config.use_tls)
    config.verify_ssl = _get_bool_env("MCP_VERIFY_SSL", config.verify_ssl)
    config.min_tls_version = os.getenv("MCP_MIN_TLS_VERSION", config.min_tls_version)
    
    # Performance settings
    config.timeout_seconds = _get_float_env("MCP_TIMEOUT_SECONDS", config.timeout_seconds)
    config.max_retries = _get_int_env("MCP_MAX_RETRIES", config.max_retries)
    config.retry_backoff_factor = _get_float_env("MCP_RETRY_BACKOFF_FACTOR", config.retry_backoff_factor)
    
    # Discovery settings
    discovery_mode_str = os.getenv("MCP_DISCOVERY_MODE", config.discovery_mode.value)
    try:
        config.discovery_mode = DiscoveryMode(discovery_mode_str.lower())
    except ValueError:
        config.discovery_mode = DiscoveryMode.DYNAMIC
    
    # Static servers from environment (JSON format)
    static_servers_json = os.getenv("MCP_STATIC_SERVERS")
    if static_servers_json:
        try:
            import json
            config.static_servers = json.loads(static_servers_json)
        except (json.JSONDecodeError, ImportError):
            config.static_servers = []
    
    return config


def get_environment_config(environment: Optional[Environment] = None) -> EnvironmentConfig:
    """Get environment-specific configuration with defaults."""
    if environment is None:
        environment = get_environment()
    
    base_config = load_config_from_env()
    base_config.environment = environment
    
    # Apply environment-specific overrides
    if environment == Environment.PRODUCTION:
        base_config.debug = False
        base_config.log_level = "INFO"
        base_config.verify_ssl = True
        base_config.use_tls = True
        base_config.min_tls_version = "TLSv1.2"
    elif environment == Environment.STAGING:
        base_config.debug = False
        base_config.log_level = "INFO"
        base_config.verify_ssl = True
    elif environment == Environment.DEVELOPMENT:
        base_config.debug = _get_bool_env("MCP_DEBUG", True)
        base_config.log_level = os.getenv("MCP_LOG_LEVEL", "DEBUG")
        base_config.verify_ssl = _get_bool_env("MCP_VERIFY_SSL", False)
    elif environment == Environment.TESTING:
        base_config.debug = True
        base_config.log_level = "DEBUG"
        base_config.enable_metrics = False
        base_config.enable_tracing = False
        base_config.verify_ssl = False
    
    return base_config


def validate_environment() -> List[str]:
    """Validate the current environment configuration and return any issues."""
    issues = []
    config = load_config_from_env()
    
    # Check required AWS settings for production
    if config.environment == Environment.PRODUCTION:
        if not config.aws_region:
            issues.append("AWS_REGION is required for production environment")
        
        if config.discovery_mode == DiscoveryMode.STATIC and not config.static_servers:
            issues.append("Static servers must be configured when using static discovery mode")
        
        if not config.use_tls:
            issues.append("TLS should be enabled in production environment")
        
        if not config.verify_ssl:
            issues.append("SSL verification should be enabled in production environment")
    
    # Check log level validity
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_log_levels:
        issues.append(f"Invalid log level: {config.log_level}. Must be one of {valid_log_levels}")
    
    # Check timeout values
    if config.timeout_seconds <= 0:
        issues.append("Timeout seconds must be positive")
    
    if config.max_retries < 0:
        issues.append("Max retries must be non-negative")
    
    if config.retry_backoff_factor <= 0:
        issues.append("Retry backoff factor must be positive")
    
    # Health check port validation removed - was unused
    
    return issues


def create_mcp_client_config(env_config: Optional[EnvironmentConfig] = None) -> MCPClientConfig:
    """Create an MCPClientConfig from environment configuration."""
    if env_config is None:
        env_config = get_environment_config()
    
    # Convert static servers from dict format to MCPServerInfo
    static_servers = []
    for server_dict in env_config.static_servers:
        try:
            server_info = MCPServerInfo(
                server_id=server_dict["server_id"],
                endpoint_url=server_dict["endpoint_url"],
                capabilities=server_dict.get("capabilities", []),
                server_type=ServerType(server_dict.get("server_type", "general")),
                health_check_url=server_dict.get("health_check_url"),
                metadata=server_dict.get("metadata", {}),
            )
            static_servers.append(server_info)
        except (KeyError, ValueError) as e:
            # Skip invalid server configurations
            continue
    
    return MCPClientConfig(
        aws_region=env_config.aws_region,
        aws_profile=env_config.aws_profile,
        aws_role_arn=env_config.aws_role_arn,
        enable_aws_auth=True,  # Always enable AWS auth when AWS region is configured
        discovery_mode=env_config.discovery_mode,
        static_servers=static_servers,
        timeout_seconds=env_config.timeout_seconds,
        max_retries=env_config.max_retries,
        retry_backoff_factor=env_config.retry_backoff_factor,
        use_tls=env_config.use_tls,
        verify_ssl=env_config.verify_ssl,
        min_tls_version=env_config.min_tls_version,
        enable_metrics=env_config.enable_metrics,
        enable_tracing=env_config.enable_tracing,
        log_level=env_config.log_level,
    )


def _get_bool_env(key: str, default: bool = False) -> bool:
    """Get a boolean value from environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default


def _get_int_env(key: str, default: int = 0) -> int:
    """Get an integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_float_env(key: str, default: float = 0.0) -> float:
    """Get a float value from environment variable."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def print_environment_info():
    """Print current environment information for debugging."""
    config = load_config_from_env()
    issues = validate_environment()
    
    print(f"MCP Client Environment Information")
    print(f"=" * 40)
    print(f"Environment: {config.environment.value}")
    print(f"Debug Mode: {config.debug}")
    print(f"Log Level: {config.log_level}")
    print(f"AWS Region: {config.aws_region}")
    print(f"Discovery Mode: {config.discovery_mode.value}")
    print(f"Use TLS: {config.use_tls}")
    print(f"Verify SSL: {config.verify_ssl}")
    # Health check configuration removed
    print(f"Metrics Enabled: {config.enable_metrics}")
    print(f"Tracing Enabled: {config.enable_tracing}")
    
    if issues:
        print(f"\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\nConfiguration is valid ✓")


if __name__ == "__main__":
    print_environment_info()