"""Shared input validation utilities for MCP server tools."""

import os
import re

# Validation patterns
LOG_GROUP_PATTERN = re.compile(r'^[a-zA-Z0-9._/\-]+$')
TIME_RANGE_PATTERN = re.compile(r'^(\d+)([mhd])$')
TRACE_ID_PATTERN = re.compile(r'^1-[0-9a-f]{8}-[0-9a-f]{24}$')
SERVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
ALLOWED_METRIC_TYPES = {'latency', 'error_rate', 'availability'}

MAX_LOG_GROUP_LENGTH = 512
MAX_LIMIT = 500

# Maximum time range caps (in the respective unit)
MAX_TIME_RANGE = {'m': 10080, 'h': 168, 'd': 7}  # 7 days max

# Configurable log group prefix allowlist via environment variable.
# Set LOG_GROUP_ALLOWLIST to a comma-separated list of allowed prefixes.
# Example: LOG_GROUP_ALLOWLIST="/aws/lambda/,/aws/apigateway/"
# If unset, all log groups are allowed (backward compatible).
_raw_allowlist = os.environ.get('LOG_GROUP_ALLOWLIST', '')
LOG_GROUP_ALLOWLIST: list[str] = [
    p.strip() for p in _raw_allowlist.split(',') if p.strip()
]


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_log_group(log_group: str) -> str:
    """Validate CloudWatch log group name.

    Checks format, length, and optionally restricts to allowed prefixes
    configured via the LOG_GROUP_ALLOWLIST environment variable.
    """
    if not log_group or not isinstance(log_group, str):
        raise ValidationError("log_group is required and must be a string")
    if len(log_group) > MAX_LOG_GROUP_LENGTH:
        raise ValidationError(f"log_group exceeds maximum length of {MAX_LOG_GROUP_LENGTH}")
    if not LOG_GROUP_PATTERN.match(log_group):
        raise ValidationError("log_group contains invalid characters. Allowed: alphanumeric, '.', '_', '/', '-'")

    # Enforce prefix allowlist when configured
    if LOG_GROUP_ALLOWLIST:
        if not any(log_group.startswith(prefix) for prefix in LOG_GROUP_ALLOWLIST):
            allowed = ', '.join(LOG_GROUP_ALLOWLIST)
            raise ValidationError(
                f"log_group must start with one of the allowed prefixes: {allowed}. "
                "Set LOG_GROUP_ALLOWLIST env var to configure allowed prefixes."
            )

    return log_group


def validate_limit(limit) -> int:
    """Validate and cap the limit parameter."""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValidationError("limit must be an integer")
    if limit < 1:
        raise ValidationError("limit must be at least 1")
    return min(limit, MAX_LIMIT)


def validate_time_range(time_range: str) -> str:
    """Validate time range format and enforce maximum cap.

    Accepts patterns like '1h', '30m', '7d'. Caps at 7 days maximum
    to prevent excessive API calls and cost.
    """
    if not time_range or not isinstance(time_range, str):
        raise ValidationError("time_range is required and must be a string")

    match = TIME_RANGE_PATTERN.match(time_range)
    if not match:
        raise ValidationError("time_range must match pattern: <number><m|h|d> (e.g., '1h', '30m', '7d')")

    value = int(match.group(1))
    unit = match.group(2)

    max_val = MAX_TIME_RANGE[unit]
    if value > max_val:
        raise ValidationError(
            f"time_range exceeds maximum of {max_val}{unit} (7 days). "
            f"Requested: {value}{unit}"
        )

    return time_range


def validate_trace_id(trace_id: str) -> str:
    """Validate X-Ray trace ID format."""
    if not trace_id or not isinstance(trace_id, str):
        raise ValidationError("trace_id is required and must be a string")
    if not TRACE_ID_PATTERN.match(trace_id):
        raise ValidationError("trace_id must match X-Ray format: 1-<8 hex>-<24 hex>")
    return trace_id


def validate_service_name(service_name: str) -> str:
    """Validate service/function name."""
    if not service_name or not isinstance(service_name, str):
        raise ValidationError("service_name is required and must be a string")
    if len(service_name) > 140:
        raise ValidationError("service_name exceeds maximum length of 140 characters")
    if not SERVICE_NAME_PATTERN.match(service_name):
        raise ValidationError("service_name must contain only alphanumeric characters, hyphens, and underscores")
    return service_name


def validate_metric_type(metric_type: str) -> str:
    """Validate metric type against allowed values."""
    if not metric_type or not isinstance(metric_type, str):
        raise ValidationError("metric_type is required and must be a string")
    if metric_type not in ALLOWED_METRIC_TYPES:
        raise ValidationError(f"metric_type must be one of: {', '.join(sorted(ALLOWED_METRIC_TYPES))}")
    return metric_type


def validate_filter_pattern(filter_pattern: str) -> str:
    """Validate CloudWatch filter pattern (basic length check)."""
    if not isinstance(filter_pattern, str):
        raise ValidationError("filter_pattern must be a string")
    if len(filter_pattern) > 1024:
        raise ValidationError("filter_pattern exceeds maximum length of 1024")
    return filter_pattern


def validate_threshold(threshold) -> float:
    """Validate threshold is a finite positive number."""
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        raise ValidationError("threshold must be a number")
    if threshold < 0:
        raise ValidationError("threshold must be non-negative")
    if not __import__('math').isfinite(threshold):
        raise ValidationError("threshold must be a finite number")
    return threshold


# Pattern for request IDs: alphanumeric, hyphens, underscores, dots, colons
# Rejects CloudWatch filter syntax characters like ?, {, }, [, ], (, ), =, !, <, >, &, |
REQUEST_ID_PATTERN = re.compile(r'^[a-zA-Z0-9._:\-]+$')
MAX_REQUEST_ID_LENGTH = 256

# Pattern for error type items: simple alphanumeric words with common separators
# Rejects CloudWatch filter syntax to prevent filter injection
ERROR_TYPE_PATTERN = re.compile(r'^[a-zA-Z0-9._:\-]+$')
MAX_ERROR_TYPE_LENGTH = 100


def validate_request_id(request_id: str) -> str:
    """Validate request ID format.

    Ensures the request_id contains only safe characters and cannot
    be used to inject CloudWatch filter pattern syntax.
    """
    if not request_id or not isinstance(request_id, str):
        raise ValidationError("request_id is required and must be a string")
    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise ValidationError(f"request_id exceeds maximum length of {MAX_REQUEST_ID_LENGTH}")
    if not REQUEST_ID_PATTERN.match(request_id):
        raise ValidationError(
            "request_id contains invalid characters. "
            "Allowed: alphanumeric, '.', '_', ':', '-'"
        )
    return request_id


def validate_error_type_item(error_type: str) -> str:
    """Validate a single error_type item for use in CloudWatch filter patterns.

    Prevents injection of arbitrary CloudWatch filter syntax via the
    error_types array in analyze_errors.
    """
    if not error_type or not isinstance(error_type, str):
        raise ValidationError("error_type item must be a non-empty string")
    if len(error_type) > MAX_ERROR_TYPE_LENGTH:
        raise ValidationError(f"error_type item exceeds maximum length of {MAX_ERROR_TYPE_LENGTH}")
    if not ERROR_TYPE_PATTERN.match(error_type):
        raise ValidationError(
            f"error_type item '{error_type}' contains invalid characters. "
            "Allowed: alphanumeric, '.', '_', ':', '-'"
        )
    return error_type
