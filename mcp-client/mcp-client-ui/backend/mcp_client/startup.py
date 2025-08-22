"""
Startup validation and initialization for the MCP Client.

This module provides comprehensive startup checks, graceful shutdown handling,
and production-ready initialization sequences.
"""

import atexit
import os
import signal
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from mcp_client.config.environment import get_environment_config, validate_environment
from mcp_client.config.production import ProductionApplication, ProductionManager
from mcp_client.core.models import MCPClientConfig
# Health server functionality removed - was unused
from mcp_client.monitoring.logging import get_logger
from mcp_client.monitoring.metrics import get_mcp_metrics


logger = get_logger(__name__)


class StartupValidator:
    """Validates system requirements and configuration before startup."""
    
    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []
    
    def add_check(self, name: str, check_func: Callable[[], bool], required: bool = True):
        """Add a startup check."""
        self.checks.append({
            'name': name,
            'func': check_func,
            'required': required
        })
    
    def run_all_checks(self) -> bool:
        """Run all startup checks and return success status."""
        logger.info("Running startup validation checks")
        
        success = True
        for check in self.checks:
            try:
                logger.info(f"Running check: {check['name']}")
                result = check['func']()
                
                if result:
                    logger.info(f"✓ {check['name']} passed")
                else:
                    if check['required']:
                        logger.error(f"✗ {check['name']} failed (required)")
                        self.errors.append(check['name'])
                        success = False
                    else:
                        logger.warning(f"⚠ {check['name']} failed (optional)")
                        self.warnings.append(check['name'])
                        
            except Exception as e:
                logger.error(f"✗ {check['name']} failed with exception: {e}")
                if check['required']:
                    self.errors.append(check['name'])
                    success = False
                else:
                    self.warnings.append(check['name'])
        
        if success:
            logger.info("All required startup checks passed ✓")
        else:
            logger.error(f"Startup validation failed. Errors: {self.errors}")
        
        if self.warnings:
            logger.warning(f"Startup warnings: {self.warnings}")
        
        return success
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of check results."""
        return {
            'total_checks': len(self.checks),
            'errors': self.errors,
            'warnings': self.warnings,
            'success': len(self.errors) == 0
        }


def check_python_version() -> bool:
    """Check if Python version is supported."""
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version >= min_version:
        logger.info(f"Python version {'.'.join(map(str, current_version))} is supported")
        return True
    else:
        logger.error(f"Python version {'.'.join(map(str, current_version))} is not supported. Minimum required: {'.'.join(map(str, min_version))}")
        return False


def check_required_modules() -> bool:
    """Check if all required modules are available."""
    required_modules = [
        'asyncio',
        'threading',
        'json',
        'logging',
        'dataclasses',
        'typing',
        'uuid',
        'time',
        'os',
        'sys',
    ]
    
    optional_modules = [
        'psutil',
        'boto3',
        'httpx',
    ]
    
    missing_required = []
    missing_optional = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)
    
    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)
            logger.warning(f"Optional module '{module}' not available")
    
    if missing_required:
        logger.error(f"Required modules missing: {missing_required}")
        return False
    
    logger.info("All required modules are available")
    return True


def check_environment_configuration() -> bool:
    """Check environment configuration validity."""
    try:
        issues = validate_environment()
        if issues:
            logger.error("Environment configuration issues:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        
        logger.info("Environment configuration is valid")
        return True
    except Exception as e:
        logger.error(f"Environment configuration check failed: {e}")
        return False


def check_file_permissions() -> bool:
    """Check file system permissions."""
    try:
        # Check if we can write to the current directory
        test_file = ".mcp_client_permission_test"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info("File system permissions are adequate")
            return True
        except (OSError, IOError) as e:
            logger.error(f"Insufficient file system permissions: {e}")
            return False
    except Exception as e:
        logger.error(f"File permission check failed: {e}")
        return False


def check_network_connectivity() -> bool:
    """Check basic network connectivity."""
    try:
        import socket
        
        # Try to create a socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            # Try to connect to a well-known service
            result = s.connect_ex(('8.8.8.8', 53))  # Google DNS
            if result == 0:
                logger.info("Network connectivity is available")
                return True
            else:
                logger.warning("Network connectivity test failed")
                return False
    except Exception as e:
        logger.warning(f"Network connectivity check failed: {e}")
        return False


def check_memory_availability() -> bool:
    """Check available system memory."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024 * 1024)
        
        # Require at least 256MB available
        min_memory_mb = 256
        
        if available_mb >= min_memory_mb:
            logger.info(f"Available memory: {available_mb:.0f}MB (sufficient)")
            return True
        else:
            logger.warning(f"Available memory: {available_mb:.0f}MB (may be insufficient)")
            return False
    except ImportError:
        logger.info("psutil not available, skipping memory check")
        return True
    except Exception as e:
        logger.warning(f"Memory check failed: {e}")
        return False


class GracefulShutdownHandler:
    """Handles graceful shutdown of the application."""
    
    def __init__(self, shutdown_timeout: float = 30.0):
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_event = threading.Event()
        self.shutdown_hooks: List[Callable[[], None]] = []
        self.cleanup_hooks: List[Callable[[], None]] = []
        self._setup_signal_handlers()
        self._setup_atexit_handler()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown()
        
        # Handle termination signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle SIGUSR1 for graceful restart (if supported)
        if hasattr(signal, 'SIGUSR1'):
            signal.signal(signal.SIGUSR1, self._handle_restart_signal)
    
    def _handle_restart_signal(self, signum, frame):
        """Handle restart signal."""
        logger.info("Received restart signal")
        # Implementation for graceful restart would go here
    
    def _setup_atexit_handler(self):
        """Set up exit handler for cleanup."""
        atexit.register(self._cleanup)
    
    def add_shutdown_hook(self, hook: Callable[[], None]):
        """Add a function to be called during shutdown."""
        self.shutdown_hooks.append(hook)
    
    def add_cleanup_hook(self, hook: Callable[[], None]):
        """Add a function to be called during cleanup."""
        self.cleanup_hooks.append(hook)
    
    def shutdown(self):
        """Initiate graceful shutdown."""
        if self.shutdown_event.is_set():
            logger.warning("Shutdown already in progress")
            return
        
        logger.info("Initiating graceful shutdown")
        self.shutdown_event.set()
        
        # Execute shutdown hooks
        for hook in self.shutdown_hooks:
            try:
                hook()
                logger.debug("Shutdown hook executed successfully")
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        
        logger.info("Graceful shutdown completed")
    
    def _cleanup(self):
        """Cleanup function called on exit."""
        if not self.shutdown_event.is_set():
            logger.info("Performing cleanup on exit")
        
        # Execute cleanup hooks
        for hook in self.cleanup_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Cleanup hook failed: {e}")
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.shutdown()
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_event.is_set()


class MCPClientApplication:
    """Complete MCP Client application with startup validation and graceful shutdown."""
    
    def __init__(self, config: Optional[MCPClientConfig] = None):
        self.config = config
        self.client = None
        # Health server functionality removed
        self.validator = StartupValidator()
        self.shutdown_handler = GracefulShutdownHandler()
        self._setup_startup_checks()
    
    def _setup_startup_checks(self):
        """Set up all startup validation checks."""
        self.validator.add_check("Python Version", check_python_version, required=True)
        self.validator.add_check("Required Modules", check_required_modules, required=True)
        self.validator.add_check("Environment Configuration", check_environment_configuration, required=True)
        self.validator.add_check("File Permissions", check_file_permissions, required=True)
        self.validator.add_check("Network Connectivity", check_network_connectivity, required=False)
        self.validator.add_check("Memory Availability", check_memory_availability, required=False)
    
    def startup(self) -> bool:
        """Perform complete startup sequence."""
        logger.info("Starting MCP Client application")
        
        # Run startup validation
        if not self.validator.run_all_checks():
            logger.error("Startup validation failed")
            return False
        
        try:
            # Load configuration if not provided
            if self.config is None:
                from mcp_client.config.environment import create_mcp_client_config
                self.config = create_mcp_client_config()
            
            # Start health check server
            # Health server functionality removed - was unused
            if self.config.enable_metrics:
                logger.info("Metrics enabled (health server functionality removed)")
            
            # Initialize MCP client
            from mcp_client.client import MCPClient
            self.client = MCPClient(self.config)
            logger.info("MCP Client initialized successfully")
            
            # Add shutdown hook for client
            self.shutdown_handler.add_shutdown_hook(self._stop_client)
            
            logger.info("MCP Client application startup completed ✓")
            return True
            
        except Exception as e:
            logger.error(f"Startup failed: {e}", exc_info=True)
            return False
    
    # Health server functionality removed - was unused
    
    def _stop_client(self):
        """Stop the MCP client."""
        if self.client:
            try:
                self.client.close_sync()
                logger.info("MCP Client stopped")
            except Exception as e:
                logger.error(f"Error stopping MCP client: {e}")
    
    def run(self):
        """Run the application with startup and shutdown handling."""
        try:
            if not self.startup():
                logger.error("Application startup failed")
                sys.exit(1)
            
            # Wait for shutdown signal
            logger.info("Application is running. Press Ctrl+C to stop.")
            self.shutdown_handler.wait_for_shutdown()
            
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            logger.info("Application shutdown complete")
    
    def get_client(self):
        """Get the MCP client instance."""
        return self.client
    
    def is_healthy(self) -> bool:
        """Check if the application is healthy."""
        if self.shutdown_handler.is_shutdown_requested():
            return False
        
        if not self.client:
            return False
        
        # Add additional health checks here
        return True


def main():
    """Main entry point for the MCP Client application."""
    app = MCPClientApplication()
    app.run()


if __name__ == "__main__":
    main()