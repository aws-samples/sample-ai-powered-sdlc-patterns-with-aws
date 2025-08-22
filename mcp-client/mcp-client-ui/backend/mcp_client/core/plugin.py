"""
Plugin architecture for the MCP Client.
"""

import abc
import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union

from mcp_client.core.models import MCPRequest, MCPResponse, MCPServerInfo

logger = logging.getLogger(__name__)


class PluginHook(Enum):
    """Enum defining the available hook points for plugins."""
    
    # Request lifecycle hooks
    PRE_REQUEST = "pre_request"  # Before a request is sent to a server
    POST_REQUEST = "post_request"  # After a response is received from a server
    
    # Server discovery hooks
    PRE_SERVER_SELECTION = "pre_server_selection"  # Before a server is selected for a request
    POST_SERVER_SELECTION = "post_server_selection"  # After a server is selected for a request
    SERVER_REGISTERED = "server_registered"  # When a new server is registered
    SERVER_UNREGISTERED = "server_unregistered"  # When a server is unregistered
    
    # Client lifecycle hooks
    CLIENT_INIT = "client_init"  # When the client is initialized
    CLIENT_CLOSE = "client_close"  # When the client is closed
    
    # Error handling hooks
    ERROR_OCCURRED = "error_occurred"  # When an error occurs


class MCPPlugin(abc.ABC):
    """Base class for MCP Client plugins."""
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Get the name of the plugin.
        
        Returns:
            str: The name of the plugin
        """
        pass
        
    @property
    @abc.abstractmethod
    def version(self) -> str:
        """
        Get the version of the plugin.
        
        Returns:
            str: The version of the plugin
        """
        pass
        
    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        Get the description of the plugin.
        
        Returns:
            str: The description of the plugin
        """
        pass
        
    @property
    def hooks(self) -> Dict[PluginHook, Set[str]]:
        """
        Get the hooks that this plugin implements.
        
        Returns:
            Dict[PluginHook, Set[str]]: A dictionary mapping hook points to method names
        """
        hooks = {}
        
        # Find all methods that are hook handlers
        for attr_name in dir(self):
            if attr_name == "hooks" or attr_name.startswith("_"):
                continue
                
            try:
                attr = getattr(self, attr_name)
                if not callable(attr):
                    continue
                    
                # Check if the method has a _hook_point attribute
                hook_point = getattr(attr, "_hook_point", None)
                if hook_point is not None:
                    if hook_point not in hooks:
                        hooks[hook_point] = set()
                    hooks[hook_point].add(attr_name)
            except RecursionError:
                # Skip attributes that cause recursion
                continue
                
        return hooks
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Configuration for the plugin
        """
        pass
        
    async def shutdown(self) -> None:
        """
        Shut down the plugin and release resources.
        """
        pass


def hook(hook_point: PluginHook):
    """
    Decorator to mark a method as a hook handler.
    
    Args:
        hook_point: The hook point that this method handles
        
    Returns:
        The decorated method
    """
    def decorator(func):
        func._hook_point = hook_point
        return func
    return decorator


class PluginManager:
    """Manager for MCP Client plugins."""
    
    def __init__(self):
        """Initialize the plugin manager."""
        self._plugins: Dict[str, MCPPlugin] = {}
        self._hook_handlers: Dict[PluginHook, List[Dict[str, Any]]] = {}
        
    def register_plugin(self, plugin: MCPPlugin, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a plugin with the manager.
        
        Args:
            plugin: The plugin to register
            config: Optional configuration for the plugin
        """
        plugin_name = plugin.name
        
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} is already registered, replacing")
            
        # Initialize the plugin
        plugin.initialize(config or {})
        
        # Register the plugin
        self._plugins[plugin_name] = plugin
        
        # Register hook handlers
        for hook_point, method_names in plugin.hooks.items():
            if hook_point not in self._hook_handlers:
                self._hook_handlers[hook_point] = []
                
            for method_name in method_names:
                handler = getattr(plugin, method_name)
                self._hook_handlers[hook_point].append({
                    "plugin": plugin_name,
                    "method": method_name,
                    "handler": handler,
                })
                
        logger.info(f"Registered plugin {plugin_name} v{plugin.version}")
        
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin from the manager.
        
        Args:
            plugin_name: The name of the plugin to unregister
            
        Returns:
            bool: True if the plugin was unregistered, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin {plugin_name} is not registered")
            return False
            
        # Remove hook handlers
        for hook_point in list(self._hook_handlers.keys()):
            self._hook_handlers[hook_point] = [
                handler for handler in self._hook_handlers[hook_point]
                if handler["plugin"] != plugin_name
            ]
            
            # Remove empty hook points
            if not self._hook_handlers[hook_point]:
                del self._hook_handlers[hook_point]
                
        # Remove the plugin
        plugin = self._plugins.pop(plugin_name)
        
        logger.info(f"Unregistered plugin {plugin_name}")
        return True
        
    def get_plugin(self, plugin_name: str) -> Optional[MCPPlugin]:
        """
        Get a plugin by name.
        
        Args:
            plugin_name: The name of the plugin to get
            
        Returns:
            Optional[MCPPlugin]: The plugin, or None if not found
        """
        return self._plugins.get(plugin_name)
        
    def get_plugins(self) -> List[MCPPlugin]:
        """
        Get all registered plugins.
        
        Returns:
            List[MCPPlugin]: A list of all registered plugins
        """
        return list(self._plugins.values())
        
    async def execute_hook(
        self, hook_point: PluginHook, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute all handlers for a hook point.
        
        Args:
            hook_point: The hook point to execute
            *args: Positional arguments to pass to the handlers
            **kwargs: Keyword arguments to pass to the handlers
            
        Returns:
            Dict[str, Any]: A dictionary mapping plugin names to handler results
        """
        results = {}
        
        if hook_point not in self._hook_handlers:
            return results
            
        for handler_info in self._hook_handlers[hook_point]:
            plugin_name = handler_info["plugin"]
            method_name = handler_info["method"]
            handler = handler_info["handler"]
            
            try:
                # Check if the handler is a coroutine function
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                    
                results[plugin_name] = result
                
            except Exception as e:
                logger.error(
                    f"Error executing hook {hook_point.value} in plugin {plugin_name}.{method_name}: {e}"
                )
                
        return results
        
    async def shutdown(self) -> None:
        """
        Shut down all plugins and release resources.
        """
        for plugin_name, plugin in list(self._plugins.items()):
            try:
                await plugin.shutdown()
                logger.debug(f"Shut down plugin {plugin_name}")
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_name}: {e}")
                
        self._plugins.clear()
        self._hook_handlers.clear()