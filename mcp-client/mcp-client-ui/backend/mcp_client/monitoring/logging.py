"""
Structured logging infrastructure for the MCP Client.

This module provides comprehensive logging capabilities with:
- Structured logging with JSON formatting
- Context-aware log formatting
- Sensitive data filtering
- Performance logging
- Request/response correlation
"""

import json
import logging
import logging.config
import sys
import threading
import time
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from mcp_client.core.models import ErrorCode, MCPError, MCPRequest, MCPResponse, MCPServerInfo


# Context variables for request correlation
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
server_id_context: ContextVar[Optional[str]] = ContextVar('server_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class SensitiveDataFilter:
    """Filter to remove sensitive data from log records."""
    
    # Fields that should be redacted in logs
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'auth', 'credential',
        'authorization', 'x-api-key', 'x-auth-token', 'bearer',
        'aws_access_key_id', 'aws_secret_access_key', 'aws_session_token'
    }
    
    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = [
        'password', 'secret', 'token', 'key', 'auth', 'credential'
    ]
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize a dictionary by redacting sensitive fields."""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if the key itself is sensitive (but not container keys like "auth")
            if any(pattern in key_lower for pattern in cls.SENSITIVE_PATTERNS) and not isinstance(value, dict):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized
    
    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Sanitize a string by looking for patterns that might contain sensitive data."""
        # This is a basic implementation - in production you might want more sophisticated
        # pattern matching for things like API keys, tokens, etc.
        if any(pattern in text.lower() for pattern in cls.SENSITIVE_PATTERNS):
            # If the string contains sensitive patterns, we could do more sophisticated
            # redaction here. For now, we'll just note that it might contain sensitive data
            return f"[STRING_MAY_CONTAIN_SENSITIVE_DATA: {len(text)} chars]"
        return text


class ContextualFormatter(logging.Formatter):
    """Custom formatter that includes context information and structured data."""
    
    def __init__(self, include_context: bool = True, json_format: bool = False):
        self.include_context = include_context
        self.json_format = json_format
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with context and structured data."""
        # Get context information
        request_id = request_id_context.get()
        server_id = server_id_context.get()
        user_id = user_id_context.get()
        
        # Create the base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context information if available
        if self.include_context:
            context = {}
            if request_id:
                context['request_id'] = request_id
            if server_id:
                context['server_id'] = server_id
            if user_id:
                context['user_id'] = user_id
            if context:
                log_data['context'] = context
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add any extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                # Sanitize the extra field
                if isinstance(value, dict):
                    extra_fields[key] = SensitiveDataFilter.sanitize_dict(value)
                elif isinstance(value, str):
                    extra_fields[key] = SensitiveDataFilter.sanitize_string(value)
                else:
                    extra_fields[key] = value
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        # Format as JSON or human-readable
        if self.json_format:
            return json.dumps(log_data, default=str)
        else:
            # Human-readable format
            parts = [f"{log_data['timestamp']} [{log_data['level']}] {log_data['logger']}: {log_data['message']}"]
            
            if self.include_context and 'context' in log_data:
                context_str = ', '.join(f"{k}={v}" for k, v in log_data['context'].items())
                parts.append(f"[{context_str}]")
            
            if 'extra' in log_data:
                extra_str = ', '.join(f"{k}={v}" for k, v in log_data['extra'].items())
                parts.append(f"({extra_str})")
            
            if 'exception' in log_data:
                parts.append(f"\nException: {log_data['exception']['traceback']}")
            
            return ' '.join(parts)


class MCPLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes MCP-specific context."""
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the log message and add context."""
        # Add context from ContextVars
        extra = kwargs.get('extra', {})
        
        request_id = request_id_context.get()
        if request_id:
            extra['request_id'] = request_id
            
        server_id = server_id_context.get()
        if server_id:
            extra['server_id'] = server_id
            
        user_id = user_id_context.get()
        if user_id:
            extra['user_id'] = user_id
        
        # Add any adapter-specific extra data
        extra.update(self.extra)
        
        kwargs['extra'] = extra
        return msg, kwargs


class PerformanceLogger:
    """Logger for tracking performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_timer(self, operation: str) -> str:
        """Start a timer for an operation."""
        timer_id = f"{operation}_{uuid4().hex[:8]}"
        with self._lock:
            self._timers[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str, operation: str, **extra_data: Any) -> float:
        """End a timer and log the duration."""
        with self._lock:
            start_time = self._timers.pop(timer_id, None)
        
        if start_time is None:
            self.logger.warning(f"Timer {timer_id} not found for operation {operation}")
            return 0.0
        
        duration = time.time() - start_time
        
        self.logger.info(
            f"Performance: {operation} completed",
            extra={
                'operation': operation,
                'duration_seconds': duration,
                'timer_id': timer_id,
                **extra_data
            }
        )
        
        return duration
    
    def log_performance(self, operation: str, duration: float, **extra_data: Any):
        """Log performance data directly."""
        self.logger.info(
            f"Performance: {operation}",
            extra={
                'operation': operation,
                'duration_seconds': duration,
                **extra_data
            }
        )


class MCPLoggingConfig:
    """Configuration for MCP logging."""
    
    def __init__(
        self,
        level: str = "INFO",
        json_format: bool = False,
        include_context: bool = True,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_performance_logging: bool = True,
    ):
        self.level = level
        self.json_format = json_format
        self.include_context = include_context
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_performance_logging = enable_performance_logging
    
    def configure_logging(self) -> None:
        """Configure the logging system."""
        # Create formatters
        formatter = ContextualFormatter(
            include_context=self.include_context,
            json_format=self.json_format
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, self.level.upper()))
        root_logger.addHandler(console_handler)
        
        # File handler if enabled
        if self.log_to_file and self.log_file_path:
            from logging.handlers import RotatingFileHandler
            
            file_handler = RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, self.level.upper()))
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        self._configure_mcp_loggers()
    
    def _configure_mcp_loggers(self) -> None:
        """Configure MCP-specific loggers."""
        # Set appropriate levels for different components
        logging.getLogger('mcp_client').setLevel(getattr(logging, self.level.upper()))
        logging.getLogger('mcp_client.transport').setLevel(getattr(logging, self.level.upper()))
        logging.getLogger('mcp_client.protocol').setLevel(getattr(logging, self.level.upper()))
        logging.getLogger('mcp_client.discovery').setLevel(getattr(logging, self.level.upper()))
        logging.getLogger('mcp_client.security').setLevel(getattr(logging, self.level.upper()))
        
        # Set external libraries to WARNING to reduce noise
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)


def get_logger(name: str) -> MCPLoggerAdapter:
    """Get a logger with MCP-specific context."""
    base_logger = logging.getLogger(name)
    return MCPLoggerAdapter(base_logger)


def set_request_context(request_id: Optional[str] = None, server_id: Optional[str] = None, user_id: Optional[str] = None):
    """Set the request context for logging."""
    if request_id:
        request_id_context.set(request_id)
    if server_id:
        server_id_context.set(server_id)
    if user_id:
        user_id_context.set(user_id)


def clear_request_context():
    """Clear the request context."""
    request_id_context.set(None)
    server_id_context.set(None)
    user_id_context.set(None)


def _sanitize_keys(keys: List[str]) -> List[str]:
    """Sanitize a list of keys by redacting sensitive ones."""
    sanitized_keys = []
    for key in keys:
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SensitiveDataFilter.SENSITIVE_PATTERNS):
            sanitized_keys.append("[REDACTED_KEY]")
        else:
            sanitized_keys.append(key)
    return sanitized_keys


def log_request(logger: logging.Logger, request: MCPRequest, server_info: MCPServerInfo):
    """Log an outgoing request with sanitized data."""
    sanitized_content = SensitiveDataFilter.sanitize_dict(request.content)
    sanitized_metadata = SensitiveDataFilter.sanitize_dict(request.metadata)
    
    logger.info(
        f"Sending request to server {server_info.server_id}",
        extra={
            'event_type': 'request_sent',
            'request_type': request.request_type,
            'server_id': server_info.server_id,
            'server_endpoint': server_info.endpoint_url,
            'required_capabilities': request.required_capabilities,
            'content_keys': _sanitize_keys(list(request.content.keys())),
            'metadata': sanitized_metadata,
            'timeout_seconds': request.timeout_seconds,
        }
    )


def log_response(logger: logging.Logger, response: MCPResponse, duration: Optional[float] = None):
    """Log an incoming response with sanitized data."""
    sanitized_content = SensitiveDataFilter.sanitize_dict(response.content)
    sanitized_metadata = SensitiveDataFilter.sanitize_dict(response.metadata)
    
    extra_data = {
        'event_type': 'response_received',
        'response_status': response.status,
        'server_id': response.server_id,
        'request_id': response.request_id,
        'content_keys': _sanitize_keys(list(response.content.keys())),
        'metadata': sanitized_metadata,
    }
    
    if duration is not None:
        extra_data['duration_seconds'] = duration
    
    logger.info(
        f"Received response from server {response.server_id}",
        extra=extra_data
    )


def log_error(logger: logging.Logger, error: MCPError, context: Optional[Dict[str, Any]] = None):
    """Log an error with sanitized details."""
    sanitized_details = SensitiveDataFilter.sanitize_dict(error.details)
    
    extra_data = {
        'event_type': 'error_occurred',
        'error_code': error.error_code,
        'error_message': error.message,
        'error_details': sanitized_details,
        'error_timestamp': error.timestamp.isoformat(),
    }
    
    if context:
        extra_data['error_context'] = SensitiveDataFilter.sanitize_dict(context)
    
    logger.error(
        f"MCP Error: {error.message}",
        extra=extra_data,
        exc_info=True
    )


def log_server_discovery(logger: logging.Logger, event: str, server_info: MCPServerInfo, **extra_data: Any):
    """Log server discovery events."""
    logger.info(
        f"Server discovery: {event}",
        extra={
            'event_type': 'server_discovery',
            'discovery_event': event,
            'server_id': server_info.server_id,
            'server_endpoint': server_info.endpoint_url,
            'server_type': server_info.server_type,
            'server_capabilities': server_info.capabilities,
            'server_status': server_info.status,
            **extra_data
        }
    )


# Create a default performance logger
_default_performance_logger = None


def get_performance_logger() -> PerformanceLogger:
    """Get the default performance logger."""
    global _default_performance_logger
    if _default_performance_logger is None:
        logger = get_logger('mcp_client.performance')
        _default_performance_logger = PerformanceLogger(logger.logger)
    return _default_performance_logger