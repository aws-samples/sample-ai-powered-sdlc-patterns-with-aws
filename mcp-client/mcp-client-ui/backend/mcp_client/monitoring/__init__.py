"""
Monitoring and observability components for the MCP Client.
"""

# Health server functionality removed - was unused and contained security findings
from mcp_client.monitoring.logging import (
    MCPLoggingConfig,
    MCPLoggerAdapter,
    PerformanceLogger,
    SensitiveDataFilter,
    clear_request_context,
    get_logger,
    get_performance_logger,
    log_error,
    log_request,
    log_response,
    log_server_discovery,
    set_request_context,
)
from mcp_client.monitoring.metrics import (
    Counter,
    Gauge,
    HealthCheck,
    HealthStatus,
    Histogram,
    MCPMetrics,
    MetricType,
    MetricValue,
    MetricsRegistry,
    Timer,
    create_counter,
    create_gauge,
    create_histogram,
    create_timer,
    get_mcp_metrics,
    get_metrics_registry,
)

__all__ = [
    # Logging
    "MCPLoggingConfig",
    "MCPLoggerAdapter", 
    "PerformanceLogger",
    "SensitiveDataFilter",
    "clear_request_context",
    "get_logger",
    "get_performance_logger",
    "log_error",
    "log_request", 
    "log_response",
    "log_server_discovery",
    "set_request_context",
    # Metrics
    "Counter",
    "Gauge",
    "HealthCheck",
    "HealthStatus",
    "Histogram",
    "MCPMetrics",
    "MetricType",
    "MetricValue",
    "MetricsRegistry",
    "Timer",
    "create_counter",
    "create_gauge",
    "create_histogram",
    "create_timer",
    "get_mcp_metrics",
    "get_metrics_registry",
    # Health server functionality removed
]