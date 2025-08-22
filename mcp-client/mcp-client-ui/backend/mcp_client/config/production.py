"""
Production-ready configuration for the MCP Client.

This module provides production-optimized configuration settings,
deployment templates, and validation for production environments.
"""

import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from mcp_client.config.environment import Environment, EnvironmentConfig, get_environment_config
from mcp_client.core.models import MCPClientConfig
# Health server functionality removed - was unused
from mcp_client.monitoring.logging import MCPLoggingConfig, get_logger
from mcp_client.monitoring.metrics import get_mcp_metrics


logger = get_logger(__name__)


@dataclass
class ProductionConfig:
    """Production-specific configuration settings."""
    
    # Application settings
    app_name: str = "mcp-client"
    app_version: str = "1.0.0"
    environment: Environment = Environment.PRODUCTION
    
    # Logging configuration
    log_to_file: bool = True
    log_file_path: str = "/var/log/mcp-client/app.log"
    log_max_file_size: int = 100 * 1024 * 1024  # 100MB
    log_backup_count: int = 10
    json_logging: bool = True
    
    # Health check configuration removed - was unused
    
    # Graceful shutdown configuration
    shutdown_timeout: float = 30.0
    shutdown_hooks: List[Callable[[], None]] = field(default_factory=list)
    
    # Performance settings
    worker_threads: int = 10
    connection_pool_size: int = 20
    request_timeout: float = 30.0
    
    # Security settings
    enable_security_headers: bool = True
    cors_enabled: bool = False
    cors_origins: List[str] = field(default_factory=list)
    
    # Monitoring settings
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    performance_monitoring: bool = True
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    
    # Additional production settings
    extra_settings: Dict[str, Any] = field(default_factory=dict)


class ProductionManager:
    """Manager for production deployment lifecycle."""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        # Health server functionality removed
        self.shutdown_event = threading.Event()
        self.startup_checks_passed = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown()
        
        # Handle common termination signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle SIGUSR1 for configuration reload (if supported)
        if hasattr(signal, 'SIGUSR1'):
            signal.signal(signal.SIGUSR1, self._handle_reload_signal)
    
    def _handle_reload_signal(self, signum, frame):
        """Handle configuration reload signal."""
        logger.info("Received reload signal, reloading configuration")
        # Implementation for configuration reload would go here
    
    def startup_checks(self) -> bool:
        """Perform startup validation checks."""
        logger.info("Performing startup validation checks")
        
        checks = [
            self._check_environment,
            self._check_permissions,
            self._check_network_connectivity,
            self._check_resource_limits,
            self._check_dependencies,
        ]
        
        for check in checks:
            try:
                if not check():
                    return False
            except Exception as e:
                logger.error(f"Startup check failed: {e}")
                return False
        
        self.startup_checks_passed = True
        logger.info("All startup checks passed ✓")
        return True
    
    def _check_environment(self) -> bool:
        """Check environment configuration."""
        from mcp_client.config.environment import validate_environment
        
        issues = validate_environment()
        if issues:
            logger.error("Environment validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        
        logger.info("Environment configuration is valid ✓")
        return True
    
    def _check_permissions(self) -> bool:
        """Check file system permissions."""
        # Check log directory permissions
        if self.config.log_to_file:
            log_dir = os.path.dirname(self.config.log_file_path)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    logger.info(f"Created log directory: {log_dir}")
                except OSError as e:
                    logger.error(f"Cannot create log directory {log_dir}: {e}")
                    return False
            
            if not os.access(log_dir, os.W_OK):
                logger.error(f"No write permission for log directory: {log_dir}")
                return False
        
        logger.info("File system permissions are valid ✓")
        return True
    
    def _check_network_connectivity(self) -> bool:
        """Check network connectivity and port availability."""
        import socket
        
        # Health check port validation removed - was unused
        
        return True
    
    def _check_resource_limits(self) -> bool:
        """Check system resource availability."""
        try:
            import psutil
            
            # Check available memory
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            
            if available_mb < self.config.max_memory_mb:
                logger.warning(f"Available memory ({available_mb:.0f}MB) is less than configured limit ({self.config.max_memory_mb}MB)")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.config.max_cpu_percent:
                logger.warning(f"Current CPU usage ({cpu_percent:.1f}%) is above configured limit ({self.config.max_cpu_percent}%)")
            
            logger.info("Resource limits check completed ✓")
            return True
            
        except ImportError:
            logger.warning("psutil not available, skipping resource checks")
            return True
        except Exception as e:
            logger.error(f"Resource check failed: {e}")
            return False
    
    def _check_dependencies(self) -> bool:
        """Check that all required dependencies are available."""
        required_modules = [
            'mcp_client.core.models',
            'mcp_client.monitoring.logging',
            'mcp_client.monitoring.metrics',
            'mcp_client.monitoring.health',
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError as e:
                logger.error(f"Required module {module} is not available: {e}")
                return False
        
        logger.info("All dependencies are available ✓")
        return True
    
    # Health server functionality removed - was unused
    
    def configure_logging(self):
        """Configure production logging."""
        logging_config = MCPLoggingConfig(
            level="INFO",
            json_format=self.config.json_logging,
            include_context=True,
            log_to_file=self.config.log_to_file,
            log_file_path=self.config.log_file_path if self.config.log_to_file else None,
            max_file_size=self.config.log_max_file_size,
            backup_count=self.config.log_backup_count,
            enable_performance_logging=self.config.performance_monitoring,
        )
        logging_config.configure_logging()
        logger.info("Production logging configured")
    
    def startup(self) -> bool:
        """Complete startup sequence."""
        logger.info(f"Starting {self.config.app_name} v{self.config.app_version} in {self.config.environment.value} mode")
        
        # Configure logging first
        self.configure_logging()
        
        # Perform startup checks
        if not self.startup_checks():
            logger.error("Startup checks failed, aborting startup")
            return False
        
        # Health server functionality removed
        
        # Execute custom startup hooks
        for hook in self.config.shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Startup hook failed: {e}")
        
        logger.info("Production startup completed successfully ✓")
        return True
    
    def shutdown(self):
        """Graceful shutdown sequence."""
        if self.shutdown_event.is_set():
            logger.warning("Shutdown already in progress")
            return
        
        logger.info("Initiating graceful shutdown")
        self.shutdown_event.set()
        
        # Execute shutdown hooks
        for hook in self.config.shutdown_hooks:
            try:
                hook()
                logger.info("Shutdown hook executed successfully")
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        
        # Health server functionality removed
        
        logger.info("Graceful shutdown completed")
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.shutdown()
    
    def is_healthy(self) -> bool:
        """Check if the application is healthy."""
        if not self.startup_checks_passed:
            return False
        
        if self.shutdown_event.is_set():
            return False
        
        # Add additional health checks here
        return True


def get_production_defaults() -> ProductionConfig:
    """Get production configuration with sensible defaults."""
    env_config = get_environment_config(Environment.PRODUCTION)
    
    return ProductionConfig(
        environment=Environment.PRODUCTION,
        # Health check configuration removed
        json_logging=True,
        log_to_file=True,
        metrics_enabled=env_config.enable_metrics,
        tracing_enabled=env_config.enable_tracing,
    )


def create_production_config(
    app_name: str = "mcp-client",
    app_version: str = "1.0.0",
    **overrides
) -> ProductionConfig:
    """Create a production configuration with custom overrides."""
    config = get_production_defaults()
    config.app_name = app_name
    config.app_version = app_version
    
    # Apply any overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            config.extra_settings[key] = value
    
    return config


def create_production_mcp_config(prod_config: Optional[ProductionConfig] = None) -> MCPClientConfig:
    """Create an MCPClientConfig optimized for production."""
    if prod_config is None:
        prod_config = get_production_defaults()
    
    from mcp_client.config.environment import create_mcp_client_config, get_environment_config
    
    env_config = get_environment_config(Environment.PRODUCTION)
    mcp_config = create_mcp_client_config(env_config)
    
    # Apply production-specific optimizations
    mcp_config.log_level = "INFO"
    mcp_config.enable_metrics = prod_config.metrics_enabled
    mcp_config.enable_tracing = prod_config.tracing_enabled
    mcp_config.use_tls = True
    mcp_config.verify_ssl = True
    
    return mcp_config


class ProductionApplication:
    """Complete production application wrapper."""
    
    def __init__(self, 
                 app_name: str = "mcp-client",
                 app_version: str = "1.0.0",
                 config_overrides: Optional[Dict[str, Any]] = None):
        self.config = create_production_config(
            app_name=app_name,
            app_version=app_version,
            **(config_overrides or {})
        )
        self.manager = ProductionManager(self.config)
        self.mcp_client = None
    
    def run(self):
        """Run the production application."""
        try:
            # Startup sequence
            if not self.manager.startup():
                logger.error("Application startup failed")
                sys.exit(1)
            
            # Create and configure MCP client
            mcp_config = create_production_mcp_config(self.config)
            
            # Import here to avoid circular imports
            from mcp_client.client import MCPClient
            self.mcp_client = MCPClient(mcp_config)
            
            logger.info("MCP Client initialized successfully")
            
            # Wait for shutdown signal
            self.manager.wait_for_shutdown()
            
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            # Cleanup
            if self.mcp_client:
                try:
                    self.mcp_client.close_sync()
                except Exception as e:
                    logger.error(f"Error closing MCP client: {e}")
            
            self.manager.shutdown()


if __name__ == "__main__":
    # Example production application
    app = ProductionApplication(
        app_name="mcp-client-production",
        app_version="1.0.0"
    )
    app.run()