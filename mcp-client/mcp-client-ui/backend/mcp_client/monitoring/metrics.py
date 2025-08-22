"""
Metrics collection infrastructure for the MCP Client.

This module provides comprehensive metrics collection capabilities with:
- Counter, Gauge, Histogram, and Timer metrics
- Health check endpoints
- Performance monitoring
- Operational metrics
- Export capabilities for monitoring systems
"""

import asyncio
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from mcp_client.core.models import ErrorCode, MCPError, MCPServerInfo


class MetricType(str, Enum):
    """Types of metrics supported."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class HealthStatus(str, Enum):
    """Health check status values."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class MetricValue:
    """A single metric value with metadata."""
    
    name: str
    value: Union[int, float]
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    help_text: Optional[str] = None


@dataclass
class HealthCheck:
    """A health check result."""
    
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class Counter:
    """A counter metric that only increases."""
    
    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the counter by the given amount."""
        if amount < 0:
            raise ValueError("Counter can only be incremented by positive values")
        
        with self._lock:
            self._value += amount
    
    def get_value(self) -> MetricValue:
        """Get the current counter value."""
        with self._lock:
            return MetricValue(
                name=self.name,
                value=self._value,
                metric_type=MetricType.COUNTER,
                labels=self.labels,
                help_text=self.help_text
            )
    
    def reset(self) -> None:
        """Reset the counter to zero."""
        with self._lock:
            self._value = 0


class Gauge:
    """A gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._value = 0
        self._lock = threading.Lock()
    
    def set(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Set the gauge to a specific value."""
        with self._lock:
            self._value = value
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the gauge by the given amount."""
        with self._lock:
            self._value += amount
    
    def decrement(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement the gauge by the given amount."""
        with self._lock:
            self._value -= amount
    
    def get_value(self) -> MetricValue:
        """Get the current gauge value."""
        with self._lock:
            return MetricValue(
                name=self.name,
                value=self._value,
                metric_type=MetricType.GAUGE,
                labels=self.labels,
                help_text=self.help_text
            )


class Histogram:
    """A histogram metric for tracking distributions."""
    
    def __init__(self, name: str, help_text: str = "", buckets: Optional[List[float]] = None, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._bucket_counts[float('inf')] = 0  # +Inf bucket
        self._count = 0
        self._sum = 0.0
        self._lock = threading.Lock()
    
    def observe(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value and update the histogram."""
        with self._lock:
            self._count += 1
            self._sum += value
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
            self._bucket_counts[float('inf')] += 1
    
    def get_value(self) -> MetricValue:
        """Get the current histogram value."""
        with self._lock:
            return MetricValue(
                name=self.name,
                value={
                    'count': self._count,
                    'sum': self._sum,
                    'buckets': dict(self._bucket_counts)
                },
                metric_type=MetricType.HISTOGRAM,
                labels=self.labels,
                help_text=self.help_text
            )
    
    def get_percentile(self, percentile: float) -> float:
        """Calculate an approximate percentile value."""
        if not (0 <= percentile <= 100):
            raise ValueError("Percentile must be between 0 and 100")
        
        with self._lock:
            if self._count == 0:
                return 0.0
            
            target_count = (percentile / 100) * self._count
            cumulative_count = 0
            
            for bucket in sorted(self.buckets):
                cumulative_count += self._bucket_counts[bucket]
                if cumulative_count >= target_count:
                    return bucket
            
            return float('inf')


class Timer:
    """A timer metric for measuring durations."""
    
    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}
        self._histogram = Histogram(f"{name}_duration_seconds", help_text, labels=labels)
        self._active_timers: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start(self, timer_id: Optional[str] = None) -> str:
        """Start a timer and return its ID."""
        if timer_id is None:
            timer_id = uuid4().hex
        
        with self._lock:
            self._active_timers[timer_id] = time.time()
        
        return timer_id
    
    def stop(self, timer_id: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Stop a timer and record the duration."""
        with self._lock:
            start_time = self._active_timers.pop(timer_id, None)
        
        if start_time is None:
            raise ValueError(f"Timer {timer_id} not found")
        
        duration = time.time() - start_time
        self._histogram.observe(duration, labels)
        return duration
    
    def time_context(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimerContext(self, labels)
    
    def get_value(self) -> MetricValue:
        """Get the current timer value."""
        return self._histogram.get_value()


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.timer_id: Optional[str] = None
    
    def __enter__(self) -> 'TimerContext':
        self.timer_id = self.timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.timer_id:
            self.timer.stop(self.timer_id, self.labels)


class MetricsRegistry:
    """Registry for managing metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, Union[Counter, Gauge, Histogram, Timer]] = {}
        self._health_checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._lock = threading.Lock()
    
    def register_counter(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Counter:
        """Register a new counter metric."""
        with self._lock:
            if name in self._metrics:
                existing = self._metrics[name]
                if not isinstance(existing, Counter):
                    raise ValueError(f"Metric {name} already exists with different type")
                return existing
            
            counter = Counter(name, help_text, labels)
            self._metrics[name] = counter
            return counter
    
    def register_gauge(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Register a new gauge metric."""
        with self._lock:
            if name in self._metrics:
                existing = self._metrics[name]
                if not isinstance(existing, Gauge):
                    raise ValueError(f"Metric {name} already exists with different type")
                return existing
            
            gauge = Gauge(name, help_text, labels)
            self._metrics[name] = gauge
            return gauge
    
    def register_histogram(self, name: str, help_text: str = "", buckets: Optional[List[float]] = None, labels: Optional[Dict[str, str]] = None) -> Histogram:
        """Register a new histogram metric."""
        with self._lock:
            if name in self._metrics:
                existing = self._metrics[name]
                if not isinstance(existing, Histogram):
                    raise ValueError(f"Metric {name} already exists with different type")
                return existing
            
            histogram = Histogram(name, help_text, buckets, labels)
            self._metrics[name] = histogram
            return histogram
    
    def register_timer(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Timer:
        """Register a new timer metric."""
        with self._lock:
            if name in self._metrics:
                existing = self._metrics[name]
                if not isinstance(existing, Timer):
                    raise ValueError(f"Metric {name} already exists with different type")
                return existing
            
            timer = Timer(name, help_text, labels)
            self._metrics[name] = timer
            return timer
    
    def register_health_check(self, name: str, check_func: Callable[[], HealthCheck]) -> None:
        """Register a health check function."""
        with self._lock:
            self._health_checks[name] = check_func
    
    def get_metric(self, name: str) -> Optional[Union[Counter, Gauge, Histogram, Timer]]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def get_all_metrics(self) -> List[MetricValue]:
        """Get all metric values."""
        with self._lock:
            return [metric.get_value() for metric in self._metrics.values()]
    
    def get_health_checks(self) -> List[HealthCheck]:
        """Run all health checks and return results."""
        results = []
        with self._lock:
            health_checks = dict(self._health_checks)
        
        for name, check_func in health_checks.items():
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                results.append(HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    details={"exception": str(e)}
                ))
        
        return results
    
    def clear(self) -> None:
        """Clear all metrics and health checks."""
        with self._lock:
            self._metrics.clear()
            self._health_checks.clear()


class MCPMetrics:
    """MCP-specific metrics collector."""
    
    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or MetricsRegistry()
        self._setup_default_metrics()
        self._setup_health_checks()
    
    def _setup_default_metrics(self) -> None:
        """Set up default MCP metrics."""
        # Request metrics
        self.requests_total = self.registry.register_counter(
            "mcp_requests_total",
            "Total number of MCP requests"
        )
        
        self.request_duration = self.registry.register_histogram(
            "mcp_request_duration_seconds",
            "Duration of MCP requests in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.request_errors_total = self.registry.register_counter(
            "mcp_request_errors_total",
            "Total number of MCP request errors"
        )
        
        # Server metrics
        self.servers_discovered = self.registry.register_gauge(
            "mcp_servers_discovered",
            "Number of discovered MCP servers"
        )
        
        self.servers_healthy = self.registry.register_gauge(
            "mcp_servers_healthy",
            "Number of healthy MCP servers"
        )
        
        self.server_discovery_duration = self.registry.register_histogram(
            "mcp_server_discovery_duration_seconds",
            "Duration of server discovery operations in seconds"
        )
        
        # Transport metrics
        self.transport_connections_active = self.registry.register_gauge(
            "mcp_transport_connections_active",
            "Number of active transport connections"
        )
        
        self.transport_requests_total = self.registry.register_counter(
            "mcp_transport_requests_total",
            "Total number of transport requests"
        )
        
        self.transport_errors_total = self.registry.register_counter(
            "mcp_transport_errors_total",
            "Total number of transport errors"
        )
        
        # Protocol metrics
        self.protocol_validation_errors = self.registry.register_counter(
            "mcp_protocol_validation_errors_total",
            "Total number of protocol validation errors"
        )
        
        self.protocol_version_compatibility = self.registry.register_gauge(
            "mcp_protocol_version_compatibility",
            "Protocol version compatibility score"
        )
        
        # Performance metrics
        self.memory_usage_bytes = self.registry.register_gauge(
            "mcp_memory_usage_bytes",
            "Memory usage in bytes"
        )
        
        self.cpu_usage_percent = self.registry.register_gauge(
            "mcp_cpu_usage_percent",
            "CPU usage percentage"
        )
    
    def _setup_health_checks(self) -> None:
        """Set up default health checks."""
        self.registry.register_health_check("mcp_client", self._check_client_health)
        self.registry.register_health_check("server_discovery", self._check_server_discovery_health)
        self.registry.register_health_check("transport", self._check_transport_health)
    
    def _check_client_health(self) -> HealthCheck:
        """Check overall client health."""
        # This is a basic implementation - in practice, you'd check various client components
        return HealthCheck(
            name="mcp_client",
            status=HealthStatus.HEALTHY,
            message="MCP client is operational"
        )
    
    def _check_server_discovery_health(self) -> HealthCheck:
        """Check server discovery health."""
        servers_count = self.servers_discovered.get_value().value
        healthy_servers = self.servers_healthy.get_value().value
        
        if servers_count == 0:
            return HealthCheck(
                name="server_discovery",
                status=HealthStatus.DEGRADED,
                message="No servers discovered",
                details={"servers_count": servers_count}
            )
        elif healthy_servers / servers_count < 0.5:
            return HealthCheck(
                name="server_discovery",
                status=HealthStatus.DEGRADED,
                message="Less than 50% of servers are healthy",
                details={"servers_count": servers_count, "healthy_servers": healthy_servers}
            )
        else:
            return HealthCheck(
                name="server_discovery",
                status=HealthStatus.HEALTHY,
                message="Server discovery is operational",
                details={"servers_count": servers_count, "healthy_servers": healthy_servers}
            )
    
    def _check_transport_health(self) -> HealthCheck:
        """Check transport layer health."""
        active_connections = self.transport_connections_active.get_value().value
        
        return HealthCheck(
            name="transport",
            status=HealthStatus.HEALTHY,
            message="Transport layer is operational",
            details={"active_connections": active_connections}
        )
    
    def record_request(self, request_type: str, server_id: str, duration: float, success: bool, error_code: Optional[ErrorCode] = None) -> None:
        """Record a request metric."""
        labels = {"request_type": request_type, "server_id": server_id}
        
        self.requests_total.increment(labels=labels)
        self.request_duration.observe(duration, labels=labels)
        
        if not success:
            error_labels = {**labels, "error_code": error_code.value if error_code else "unknown"}
            self.request_errors_total.increment(labels=error_labels)
    
    def record_server_discovery(self, servers_found: int, healthy_servers: int, duration: float) -> None:
        """Record server discovery metrics."""
        self.servers_discovered.set(servers_found)
        self.servers_healthy.set(healthy_servers)
        self.server_discovery_duration.observe(duration)
    
    def record_transport_activity(self, connections_active: int, request_success: bool) -> None:
        """Record transport activity metrics."""
        self.transport_connections_active.set(connections_active)
        self.transport_requests_total.increment()
        
        if not request_success:
            self.transport_errors_total.increment()
    
    def record_protocol_validation_error(self, error_type: str) -> None:
        """Record a protocol validation error."""
        self.protocol_validation_errors.increment(labels={"error_type": error_type})
    
    def update_system_metrics(self, memory_bytes: int, cpu_percent: float) -> None:
        """Update system resource metrics."""
        self.memory_usage_bytes.set(memory_bytes)
        self.cpu_usage_percent.set(cpu_percent)


# Global metrics registry
_default_registry = MetricsRegistry()
_default_mcp_metrics = MCPMetrics(_default_registry)


def get_metrics_registry() -> MetricsRegistry:
    """Get the default metrics registry."""
    return _default_registry


def get_mcp_metrics() -> MCPMetrics:
    """Get the default MCP metrics collector."""
    return _default_mcp_metrics


def create_counter(name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Counter:
    """Create a counter metric using the default registry."""
    return _default_registry.register_counter(name, help_text, labels)


def create_gauge(name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Gauge:
    """Create a gauge metric using the default registry."""
    return _default_registry.register_gauge(name, help_text, labels)


def create_histogram(name: str, help_text: str = "", buckets: Optional[List[float]] = None, labels: Optional[Dict[str, str]] = None) -> Histogram:
    """Create a histogram metric using the default registry."""
    return _default_registry.register_histogram(name, help_text, buckets, labels)


def create_timer(name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> Timer:
    """Create a timer metric using the default registry."""
    return _default_registry.register_timer(name, help_text, labels)