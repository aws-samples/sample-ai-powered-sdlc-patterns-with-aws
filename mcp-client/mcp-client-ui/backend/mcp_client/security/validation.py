"""
Input validation and sanitization for the MCP Client.
"""

import re
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from mcp_client.core.models import ErrorCode, MCPError, MCPRequest

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes input data for MCP Client."""
    
    # Security patterns
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>.*?</iframe>',  # Iframes
        r'<object[^>]*>.*?</object>',  # Objects
        r'<embed[^>]*>.*?</embed>',  # Embeds
        r'<link[^>]*>',  # Link tags
        r'<meta[^>]*>',  # Meta tags
        r'<style[^>]*>.*?</style>',  # Style tags
        r'data:text/html',  # Data URLs with HTML
        r'vbscript:',  # VBScript URLs
    ]
    
    # SQL injection patterns - more specific to avoid false positives
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|EXEC|UNION)\s+\w+\s+FROM\b)',  # More specific SQL patterns
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+[\'"][^\'"]*[\'"])',
        r'(--\s*[^\n]*(\n|$))',  # SQL comments with content
        r'(/\*.*?\*/)',  # SQL block comments
        r'(\bxp_cmdshell\b)',
        r'(\bsp_executesql\b)',
        r'(\bUNION\s+SELECT\b)',  # Union-based injection
        r'(\'\s*(OR|AND)\s+\'\w*\'\s*=\s*\'\w*)',  # Quote-based injection
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$(){}[\]<>]',  # Shell metacharacters
        r'\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ping|curl|wget|nc|ncat|telnet|ssh|ftp|scp|rsync)\b',
        r'(\.\.\/|\.\.\\)',  # Directory traversal
        r'(\$\{|\$\()',  # Variable expansion
    ]
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        'prompt': 10000,
        'message': 5000,
        'server_id': 100,
        'endpoint_url': 500,
        'capability': 50,
        'metadata_key': 100,
        'metadata_value': 1000,
        'session_name': 100,
        'role_arn': 200,
        'external_id': 100,
    }
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize the input validator.
        
        Args:
            strict_mode: Whether to use strict validation rules
        """
        self.strict_mode = strict_mode
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                               for pattern in self.DANGEROUS_PATTERNS]
        self.sql_injection_regex = [re.compile(pattern, re.IGNORECASE) 
                                   for pattern in self.SQL_INJECTION_PATTERNS]
        self.command_injection_regex = [re.compile(pattern, re.IGNORECASE) 
                                       for pattern in self.COMMAND_INJECTION_PATTERNS]
    
    def validate_string(self, value: str, field_name: str, max_length: Optional[int] = None) -> str:
        """
        Validate and sanitize a string input.
        
        Args:
            value: The string to validate
            field_name: Name of the field for error reporting
            max_length: Maximum allowed length
            
        Returns:
            str: Sanitized string
            
        Raises:
            MCPError: If validation fails
        """
        if not isinstance(value, str):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Field '{field_name}' must be a string",
                details={"field": field_name, "type": type(value).__name__}
            )
        
        # Check length
        max_len = max_length or self.MAX_LENGTHS.get(field_name, 1000000)
        if len(value) > max_len:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Field '{field_name}' exceeds maximum length of {max_len}",
                details={"field": field_name, "length": len(value), "max_length": max_len}
            )
        
        # Check for dangerous patterns
        self._check_dangerous_patterns(value, field_name)
        
        # Sanitize the string
        sanitized = self._sanitize_string(value)
        
        return sanitized
    
    def validate_url(self, url: str, field_name: str = "url") -> str:
        """
        Validate and sanitize a URL.
        
        Args:
            url: The URL to validate
            field_name: Name of the field for error reporting
            
        Returns:
            str: Validated URL
            
        Raises:
            MCPError: If validation fails
        """
        if not isinstance(url, str):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Field '{field_name}' must be a string",
                details={"field": field_name}
            )
        
        # Check length
        if len(url) > self.MAX_LENGTHS.get('endpoint_url', 500):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"URL '{field_name}' is too long",
                details={"field": field_name, "length": len(url)}
            )
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid URL format for '{field_name}': {str(e)}",
                details={"field": field_name, "url": url}
            )
        
        # Validate scheme
        if parsed.scheme not in ['http', 'https']:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"URL '{field_name}' must use HTTP or HTTPS scheme",
                details={"field": field_name, "scheme": parsed.scheme}
            )
        
        # Validate hostname
        if not parsed.hostname:
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"URL '{field_name}' must have a valid hostname",
                details={"field": field_name, "url": url}
            )
        
        # Check for dangerous patterns in URL
        self._check_dangerous_patterns(url, field_name)
        
        return url
    
    def validate_json(self, data: Union[str, Dict, List], field_name: str) -> Union[Dict, List]:
        """
        Validate and sanitize JSON data.
        
        Args:
            data: The JSON data to validate
            field_name: Name of the field for error reporting
            
        Returns:
            Union[Dict, List]: Validated JSON data
            
        Raises:
            MCPError: If validation fails
        """
        # If it's a string, try to parse it
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid JSON in field '{field_name}': {str(e)}",
                    details={"field": field_name, "error": str(e)}
                )
        
        # Validate the parsed data
        if not isinstance(data, (dict, list)):
            raise MCPError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Field '{field_name}' must be a JSON object or array",
                details={"field": field_name, "type": type(data).__name__}
            )
        
        # Recursively sanitize the data
        sanitized_data = self._sanitize_json_data(data, field_name)
        
        return sanitized_data
    
    def validate_mcp_request(self, request: MCPRequest) -> MCPRequest:
        """
        Validate and sanitize an MCP request.
        
        Args:
            request: The MCP request to validate
            
        Returns:
            MCPRequest: Validated and sanitized request
            
        Raises:
            MCPError: If validation fails
        """
        # Validate request type
        request.request_type = self.validate_string(
            request.request_type, 
            "request_type", 
            max_length=50
        )
        
        # Validate content
        if request.content:
            request.content = self.validate_json(request.content, "content")
        
        # Validate capabilities
        if request.required_capabilities:
            validated_capabilities = []
            for cap in request.required_capabilities:
                validated_cap = self.validate_string(cap, "capability", max_length=50)
                validated_capabilities.append(validated_cap)
            request.required_capabilities = validated_capabilities
        
        # Validate preferred server ID
        if request.preferred_server_id:
            request.preferred_server_id = self.validate_string(
                request.preferred_server_id,
                "preferred_server_id",
                max_length=100
            )
        
        # Validate timeout
        if request.timeout_seconds is not None:
            if not isinstance(request.timeout_seconds, (int, float)) or request.timeout_seconds <= 0:
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="timeout_seconds must be a positive number",
                    details={"timeout_seconds": request.timeout_seconds}
                )
        
        # Validate metadata
        if request.metadata:
            request.metadata = self.validate_json(request.metadata, "metadata")
        
        return request
    
    def _check_dangerous_patterns(self, value: str, field_name: str):
        """Check for dangerous patterns in input."""
        # Check for XSS patterns
        for pattern in self.dangerous_regex:
            if pattern.search(value):
                logger.warning(f"Dangerous pattern detected in field '{field_name}': {pattern.pattern}")
                if self.strict_mode:
                    raise MCPError(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message=f"Potentially dangerous content detected in field '{field_name}'",
                        details={"field": field_name, "pattern": "XSS"}
                    )
        
        # Check for SQL injection patterns (skip for architecture/design content)
        architecture_fields = [
            'prompt', 'message', 'content', 'description', 'requirements', 
            'architecture_description', 'details', 'query', 'arguments',
            'design', 'specification', 'features', 'functionality'
        ]
        
        # Only check SQL injection for non-architecture fields
        if not any(arch_field in field_name.lower() for arch_field in architecture_fields):
            for pattern in self.sql_injection_regex:
                if pattern.search(value):
                    logger.warning(f"SQL injection pattern detected in field '{field_name}': {pattern.pattern}")
                    if self.strict_mode:
                        raise MCPError(
                            error_code=ErrorCode.VALIDATION_ERROR,
                            message=f"Potentially dangerous SQL content detected in field '{field_name}'",
                            details={"field": field_name, "pattern": "SQL_INJECTION"}
                        )
        
        # Check for command injection patterns (less strict for architecture content)
        architecture_fields = [
            'prompt', 'message', 'content', 'description', 'requirements', 
            'architecture_description', 'details', 'query', 'arguments'
        ]
        
        # Skip command injection checks for architecture-related fields
        if not any(arch_field in field_name.lower() for arch_field in architecture_fields):
            for pattern in self.command_injection_regex:
                if pattern.search(value):
                    logger.warning(f"Command injection pattern detected in field '{field_name}': {pattern.pattern}")
                    if self.strict_mode:
                        raise MCPError(
                            error_code=ErrorCode.VALIDATION_ERROR,
                            message=f"Potentially dangerous command content detected in field '{field_name}'",
                            details={"field": field_name, "pattern": "COMMAND_INJECTION"}
                        )
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize a string by removing or escaping dangerous content."""
        # HTML escape
        sanitized = html.escape(value, quote=True)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def _sanitize_json_data(self, data: Union[Dict, List, Any], field_name: str) -> Union[Dict, List, Any]:
        """Recursively sanitize JSON data."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Validate and sanitize key
                if not isinstance(key, str):
                    key = str(key)
                
                sanitized_key = self.validate_string(key, f"{field_name}.key", max_length=100)
                
                # Recursively sanitize value
                sanitized_value = self._sanitize_json_data(value, f"{field_name}.{key}")
                sanitized[sanitized_key] = sanitized_value
            
            return sanitized
        
        elif isinstance(data, list):
            sanitized = []
            for i, item in enumerate(data):
                sanitized_item = self._sanitize_json_data(item, f"{field_name}[{i}]")
                sanitized.append(sanitized_item)
            
            return sanitized
        
        elif isinstance(data, str):
            # Special handling for image data fields - allow larger size
            if 'image_data' in field_name.lower():
                return self.validate_string(data, field_name, max_length=500000)  # 500KB for images
            return self.validate_string(data, field_name, max_length=100000)
        
        elif isinstance(data, (int, float, bool)) or data is None:
            return data
        
        else:
            # Convert unknown types to string and sanitize
            return self.validate_string(str(data), field_name, max_length=100000)


class SecurityMiddleware:
    """Security middleware for MCP Client operations."""
    
    def __init__(self, validator: Optional[InputValidator] = None):
        """
        Initialize the security middleware.
        
        Args:
            validator: Input validator to use
        """
        self.validator = validator or InputValidator()
    
    def validate_request(self, request: MCPRequest) -> MCPRequest:
        """
        Validate an MCP request before processing.
        
        Args:
            request: The request to validate
            
        Returns:
            MCPRequest: Validated request
        """
        try:
            return self.validator.validate_mcp_request(request)
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            raise
    
    def validate_server_info(self, server_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate server information.
        
        Args:
            server_info: Server information to validate
            
        Returns:
            Dict[str, Any]: Validated server information
        """
        validated = {}
        
        # Validate server ID
        if 'server_id' in server_info:
            validated['server_id'] = self.validator.validate_string(
                server_info['server_id'], 
                'server_id'
            )
        
        # Validate endpoint URL
        if 'endpoint_url' in server_info:
            validated['endpoint_url'] = self.validator.validate_url(
                server_info['endpoint_url'], 
                'endpoint_url'
            )
        
        # Validate capabilities
        if 'capabilities' in server_info:
            if not isinstance(server_info['capabilities'], list):
                raise MCPError(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="capabilities must be a list",
                    details={"capabilities": server_info['capabilities']}
                )
            
            validated_capabilities = []
            for cap in server_info['capabilities']:
                validated_cap = self.validator.validate_string(cap, 'capability')
                validated_capabilities.append(validated_cap)
            validated['capabilities'] = validated_capabilities
        
        # Validate metadata
        if 'metadata' in server_info and server_info['metadata']:
            validated['metadata'] = self.validator.validate_json(
                server_info['metadata'], 
                'metadata'
            )
        
        # Copy other fields as-is (they should be validated by Pydantic)
        for key, value in server_info.items():
            if key not in validated:
                validated[key] = value
        
        return validated
    
    def sanitize_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize response data before returning to client.
        
        Args:
            response_data: Response data to sanitize
            
        Returns:
            Dict[str, Any]: Sanitized response data
        """
        # For responses, we're less strict but still sanitize strings
        return self.validator._sanitize_json_data(response_data, "response")


# Global validator instance
_default_validator = None


def get_validator(strict_mode: bool = True) -> InputValidator:
    """Get the default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = InputValidator(strict_mode=strict_mode)
    return _default_validator


def get_design_validator() -> InputValidator:
    """Get a relaxed validator for design/architecture content."""
    return InputValidator(strict_mode=False)


def validate_input(data: Any, field_name: str, data_type: str = "string") -> Any:
    """
    Convenience function to validate input data.
    
    Args:
        data: Data to validate
        field_name: Name of the field
        data_type: Type of data (string, url, json)
        
    Returns:
        Any: Validated data
    """
    validator = get_validator()
    
    if data_type == "string":
        return validator.validate_string(data, field_name)
    elif data_type == "url":
        return validator.validate_url(data, field_name)
    elif data_type == "json":
        return validator.validate_json(data, field_name)
    else:
        raise ValueError(f"Unknown data type: {data_type}")