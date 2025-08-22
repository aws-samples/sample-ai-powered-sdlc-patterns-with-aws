"""
Configuration management for the MCP Client.
"""

from mcp_client.config.environment import (
    Environment,
    EnvironmentConfig,
    get_environment_config,
    load_config_from_env,
    validate_environment,
)
from mcp_client.config.production import (
    ProductionConfig,
    create_production_config,
    get_production_defaults,
)
# Templates module removed - was unused and contained security findings

__all__ = [
    # Environment
    "Environment",
    "EnvironmentConfig",
    "get_environment_config",
    "load_config_from_env",
    "validate_environment",
    # Production
    "ProductionConfig",
    "create_production_config",
    "get_production_defaults",
    # Templates module removed - was unused
]