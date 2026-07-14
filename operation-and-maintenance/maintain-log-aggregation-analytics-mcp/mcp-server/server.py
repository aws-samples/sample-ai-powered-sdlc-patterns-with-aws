#!/usr/bin/env python3
"""Log Analysis MCP Server - AI-powered log aggregation and analysis for developers."""

import json
import asyncio
import logging
from datetime import datetime, timezone

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.fetch_logs import fetch_logs
from tools.analyze_errors import analyze_errors
from tools.trace_request import trace_request
from tools.check_sla import check_sla
from tools.sanitize import sanitize_aws_error
from tools.credentials import check_credentials

# Audit logger — writes structured records of every tool invocation
audit_logger = logging.getLogger("mcp.audit")
audit_logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(_handler)

# Security logger for credential warnings
security_logger = logging.getLogger("mcp.security")
security_logger.setLevel(logging.WARNING)
_sec_handler = logging.StreamHandler()
_sec_handler.setFormatter(logging.Formatter("[SECURITY] %(message)s"))
security_logger.addHandler(_sec_handler)

app = Server("log-analysis-mcp")

TOOLS = [
    Tool(
        name="fetch_logs",
        description="Fetch logs from CloudWatch for a specific log group and time range",
        inputSchema={
            "type": "object",
            "properties": {
                "log_group": {"type": "string", "description": "CloudWatch log group name"},
                "start_time": {"type": "string", "description": "Start time (ISO format or relative like '1h', '30m')"},
                "end_time": {"type": "string", "description": "End time (ISO format or 'now')"},
                "filter_pattern": {"type": "string", "description": "CloudWatch filter pattern (optional)"},
                "limit": {"type": "integer", "description": "Max log events to return", "default": 100}
            },
            "required": ["log_group"]
        }
    ),
    Tool(
        name="analyze_errors",
        description="Use AI to analyze log errors, detect patterns, and suggest fixes",
        inputSchema={
            "type": "object",
            "properties": {
                "log_group": {"type": "string", "description": "CloudWatch log group name"},
                "time_range": {"type": "string", "description": "Time range (e.g., '1h', '24h', '7d')", "default": "1h"},
                "error_types": {"type": "array", "items": {"type": "string"}, "description": "Specific error types to focus on"}
            },
            "required": ["log_group"]
        }
    ),
    Tool(
        name="trace_request",
        description="Trace a request across services using X-Ray traces and correlate logs",
        inputSchema={
            "type": "object",
            "properties": {
                "trace_id": {"type": "string", "description": "X-Ray trace ID"},
                "request_id": {"type": "string", "description": "Request ID to search for in logs"},
                "time_range": {"type": "string", "description": "Time range to search", "default": "1h"}
            }
        }
    ),
    Tool(
        name="check_sla",
        description="Check metrics against SLA thresholds and report compliance",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Service/Lambda function name"},
                "metric_type": {"type": "string", "enum": ["latency", "error_rate", "availability"], "description": "Metric to check"},
                "threshold": {"type": "number", "description": "SLA threshold value"},
                "time_range": {"type": "string", "description": "Time range to evaluate", "default": "24h"}
            },
            "required": ["service_name", "metric_type", "threshold"]
        }
    )
]


def _sanitize_args_for_audit(args: dict) -> dict:
    """Create a copy of arguments safe for audit logging (no sensitive values)."""
    safe = {}
    for key, value in args.items():
        if isinstance(value, str) and len(value) > 200:
            safe[key] = value[:200] + "...[truncated]"
        else:
            safe[key] = value
    return safe


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    handlers = {
        "fetch_logs": fetch_logs,
        "analyze_errors": analyze_errors,
        "trace_request": trace_request,
        "check_sla": check_sla
    }

    timestamp = datetime.now(timezone.utc).isoformat()

    if name not in handlers:
        audit_logger.info(json.dumps({
            "event": "tool_call",
            "timestamp": timestamp,
            "tool": name,
            "status": "rejected",
            "reason": "unknown_tool"
        }))
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # Audit log the invocation
    audit_logger.info(json.dumps({
        "event": "tool_call",
        "timestamp": timestamp,
        "tool": name,
        "arguments": _sanitize_args_for_audit(arguments),
        "status": "started"
    }))

    try:
        result = await handlers[name](arguments)
        audit_logger.info(json.dumps({
            "event": "tool_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": name,
            "status": "success"
        }))
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        # Sanitize error message to prevent information leakage
        safe_error = sanitize_aws_error(str(e))
        audit_logger.info(json.dumps({
            "event": "tool_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": name,
            "status": "error",
            "error": safe_error
        }))
        return [TextContent(type="text", text=f"Error: {safe_error}")]


async def main():
    # Run credential safety check at startup
    cred_report = check_credentials()
    audit_logger.info(json.dumps({
        "event": "startup_credential_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "credential_type": cred_report["credential_type"],
        "valid": cred_report["valid"],
        "warning_count": len(cred_report["warnings"]),
        "identity_type": cred_report["identity"].get("arn_type", "none"),
    }))
    for warning in cred_report["warnings"]:
        security_logger.warning(warning)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
