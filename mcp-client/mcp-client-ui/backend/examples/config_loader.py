#!/usr/bin/env python3
"""
Configuration Loader - Load MCP servers from various sources.
"""

import json
import os
import sys
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client.core.models import MCPServerInfo, ServerType, AuthConfig

class MCPConfigLoader:
    """Load MCP server configurations from various sources."""
    
    def __init__(self, config_file: str = "../mcp_servers.json"):
        self.config_file = config_file
        self._config_cache = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self._config_cache is None:
            try:
                with open(self.config_file, 'r') as f:
                    self._config_cache = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Config file {self.config_file} not found")
                self._config_cache = {"environments": {}, "server_templates": {}}
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in {self.config_file}: {e}")
                self._config_cache = {"environments": {}, "server_templates": {}}
        
        return self._config_cache
    
    def get_servers_for_environment(self, environment: str = "development") -> List[MCPServerInfo]:
        """Get servers for a specific environment."""
        config = self.load_config()
        env_config = config.get("environments", {}).get(environment, {})
        server_configs = env_config.get("servers", [])
        
        servers = []
        for server_config in server_configs:
            try:
                # Convert string server_type to enum
                if isinstance(server_config.get("server_type"), str):
                    server_config["server_type"] = ServerType(server_config["server_type"])
                
                # Handle timeout_config - extract and store for later use
                timeout_config = server_config.pop("timeout_config", None)
                
                # Handle stdio transport fields - extract and store in metadata
                command = server_config.pop("command", None)
                args = server_config.pop("args", None)
                transport = server_config.pop("transport", None)
                
                # Handle auth_config if present
                if "auth_config" in server_config and isinstance(server_config["auth_config"], dict):
                    server_config["auth_config"] = AuthConfig(**server_config["auth_config"])
                
                # Handle auth format (alternative to auth_config)
                if "auth" in server_config and isinstance(server_config["auth"], dict):
                    # Keep auth as dict for now, we'll handle it in the transport layer
                    pass
                
                # Create the server info
                server_info = MCPServerInfo(**server_config)
                
                # Initialize metadata if needed
                if not hasattr(server_info, 'metadata') or server_info.metadata is None:
                    server_info.metadata = {}
                
                # Add timeout config as metadata if present
                if timeout_config:
                    server_info.metadata["timeout_config"] = timeout_config
                
                # Add stdio transport config as metadata if present
                if command:
                    server_info.metadata["command"] = command
                if args:
                    server_info.metadata["args"] = args
                if transport:
                    server_info.metadata["transport"] = transport
                
                servers.append(server_info)
            except Exception as e:
                print(f"Warning: Invalid server config: {e}")
                continue
        
        return servers
    
    def get_timeout_config(self, server_info: MCPServerInfo, operation: str = None) -> Dict[str, Any]:
        """Get timeout configuration for a server and optional operation."""
        timeout_config = {}
        
        # Get timeout config from metadata
        if hasattr(server_info, 'metadata') and server_info.metadata:
            stored_config = server_info.metadata.get("timeout_config", {})
            
            # Set default timeout
            timeout_config["timeout_seconds"] = stored_config.get("default_timeout_seconds", 60.0)
            timeout_config["max_retries"] = stored_config.get("max_retries", 3)
            timeout_config["retry_backoff_factor"] = stored_config.get("retry_backoff_factor", 1.5)
            timeout_config["health_check_timeout_seconds"] = stored_config.get("health_check_timeout_seconds", 5.0)
            
            # Override with operation-specific timeout if available
            if operation and "operation_timeouts" in stored_config:
                operation_timeout = stored_config["operation_timeouts"].get(operation)
                if operation_timeout:
                    timeout_config["timeout_seconds"] = operation_timeout
        else:
            # Default values
            timeout_config = {
                "timeout_seconds": 60.0,
                "max_retries": 3,
                "retry_backoff_factor": 1.5,
                "health_check_timeout_seconds": 5.0
            }
        
        return timeout_config
    
    def get_auth_config(self, server_info: MCPServerInfo) -> Dict[str, Any]:
        """Get authentication configuration for a server."""
        auth_config = {}
        
        # Check for auth in the server info
        if hasattr(server_info, 'auth') and server_info.auth:
            if isinstance(server_info.auth, dict):
                auth_config = server_info.auth.copy()
            else:
                # Convert AuthConfig object to dict
                auth_config = server_info.auth.model_dump()
        
        # Also check auth_config field
        if hasattr(server_info, 'auth_config') and server_info.auth_config:
            if isinstance(server_info.auth_config, dict):
                auth_config.update(server_info.auth_config)
            else:
                auth_config.update(server_info.auth_config.model_dump())
        
        return auth_config
    
    def get_resource_names(self, server_info: MCPServerInfo) -> Dict[str, str]:
        """Get resource names for a server."""
        resource_names = {}
        
        if hasattr(server_info, 'metadata') and server_info.metadata:
            resource_names = server_info.metadata.get("resource_names", {})
        
        return resource_names
    
    def get_server_by_id(self, server_id: str, environment: str = "development") -> MCPServerInfo:
        """Get a specific server by ID."""
        servers = self.get_servers_for_environment(environment)
        for server in servers:
            if server.server_id == server_id:
                return server
        raise ValueError(f"Server {server_id} not found in environment {environment}")
    
    def list_environments(self) -> List[str]:
        """List available environments."""
        config = self.load_config()
        return list(config.get("environments", {}).keys())
    
    def list_servers(self, environment: str = None) -> Dict[str, List[str]]:
        """List all servers by environment."""
        config = self.load_config()
        result = {}
        
        environments = [environment] if environment else self.list_environments()
        
        for env in environments:
            servers = self.get_servers_for_environment(env)
            result[env] = [server.server_id for server in servers]
        
        return result
    
    def add_server(self, server: MCPServerInfo, environment: str = "development"):
        """Add a server to the configuration."""
        config = self.load_config()
        
        if "environments" not in config:
            config["environments"] = {}
        if environment not in config["environments"]:
            config["environments"][environment] = {"servers": []}
        
        # Convert to dict for JSON serialization
        server_dict = server.model_dump()
        server_dict["server_type"] = server_dict["server_type"].value
        
        config["environments"][environment]["servers"].append(server_dict)
        
        # Save back to file
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        # Clear cache
        self._config_cache = None

def example_usage():
    """Example of how to use the config loader."""
    print("🔧 MCP Configuration Loader Example")
    print("=" * 40)
    
    loader = MCPConfigLoader()
    
    # List environments
    environments = loader.list_environments()
    print(f"📋 Available environments: {environments}")
    
    # List servers by environment
    servers_by_env = loader.list_servers()
    for env, servers in servers_by_env.items():
        print(f"\n🌍 {env.title()} Environment:")
        for server_id in servers:
            try:
                server = loader.get_server_by_id(server_id, env)
                print(f"  • {server_id}: {', '.join(server.capabilities)}")
            except Exception as e:
                print(f"  • {server_id}: Error loading - {e}")
    
    # Get servers for development
    dev_servers = loader.get_servers_for_environment("development")
    print(f"\n🛠️  Development servers loaded: {len(dev_servers)}")

if __name__ == "__main__":
    example_usage()