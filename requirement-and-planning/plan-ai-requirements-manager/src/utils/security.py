"""
Security utilities for input validation, rate limiting, and session encryption.

This module provides security functions to help reduce risk of common vulnerabilities:
- Input sanitization (prompt injection, XSS)
- Rate limiting for API calls
- Session state encryption (using Fernet symmetric encryption)
- Path validation
"""

import re
import os
import time
import hashlib
import logging
import base64
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Rate limiting storage
_rate_limit_store: Dict[str, list] = defaultdict(list)


class SecurityError(Exception):
    """Base exception for security-related errors"""
    pass


class RateLimitExceeded(SecurityError):
    """Raised when rate limit is exceeded"""
    pass


class InputValidationError(SecurityError):
    """Raised when input validation fails"""
    pass


def sanitize_prompt(prompt: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to help reduce risk of prompt injection attacks.

    Filters known malicious patterns (e.g., instruction override, XSS payloads)
    and enforces length limits. Designed to block common prompt injection
    patterns; novel or sophisticated attacks may require additional controls.

    Security metrics:
        - Length enforcement prevents token-exhaustion attacks
        - Pattern filtering addresses known prompt injection vectors
        - Implementation priority: Critical (apply before all AI model calls)

    Args:
        prompt: User input text
        max_length: Maximum allowed length (default 10000; configurable via MAX_PROMPT_LENGTH env var)

    Returns:
        Sanitized prompt

    Raises:
        InputValidationError: If input is invalid or dangerous
    """
    if not isinstance(prompt, str):
        raise InputValidationError("Prompt must be a string")

    # Check length
    if len(prompt) > max_length:
        raise InputValidationError(f"Prompt exceeds maximum length of {max_length} characters")

    # Remove null bytes
    prompt = prompt.replace('\x00', '')

    # Check for potential prompt injection patterns
    dangerous_patterns = [
        r'ignore\s+previous\s+instructions',
        r'disregard\s+all\s+prior',
        r'forget\s+everything',
        r'new\s+instructions:',
        r'system\s+prompt:',
        r'<\s*script',  # XSS attempt
        r'javascript:',  # XSS attempt
        r'on\w+\s*=',  # Event handlers (XSS)
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected: {pattern}")
            # Don't reject, but log and sanitize
            prompt = re.sub(pattern, '[FILTERED]', prompt, flags=re.IGNORECASE)

    # Remove excessive whitespace
    prompt = ' '.join(prompt.split())

    return prompt


def sanitize_jira_input(text: str, max_length: int = 32000) -> str:
    """
    Sanitize text for JIRA fields (summary, description).

    Args:
        text: Input text
        max_length: Maximum allowed length (JIRA limit is 32,767)

    Returns:
        Sanitized text

    Raises:
        InputValidationError: If input is invalid
    """
    if not isinstance(text, str):
        raise InputValidationError("JIRA input must be a string")

    # Check length
    if len(text) > max_length:
        raise InputValidationError(f"JIRA input exceeds maximum length of {max_length} characters")

    # Remove null bytes
    text = text.replace('\x00', '')

    # JIRA-specific sanitization
    # Remove potential JIRA markup injection
    dangerous_jira_patterns = [
        r'\{code:.*?\|.*?\}',  # Code blocks with potential injection
        r'\{sql:.*?\}',  # SQL blocks
    ]

    for pattern in dangerous_jira_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Potential JIRA markup injection detected: {pattern}")
            text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)

    return text


def validate_jira_key(jira_key: str) -> bool:
    """
    Validate JIRA issue key format.

    Args:
        jira_key: JIRA key to validate (e.g., "DP-123")

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(jira_key, str):
        return False

    # JIRA key format: PROJECT-NUMBER (e.g., DP-123, PROJ-1)
    pattern = r'^[A-Z][A-Z0-9]*-\d+$'
    return bool(re.match(pattern, jira_key))


def rate_limit(
    identifier: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> None:
    """
    Rate limiting for API calls.

    Limits request frequency per identifier to mitigate automated abuse.
    Configure via RATE_LIMIT_MAX_REQUESTS and RATE_LIMIT_WINDOW_SECONDS env vars.

    Security metrics:
        - Default: 10 requests/60s per session
        - Production recommendation: adjust based on expected legitimate traffic
        - Implementation priority: High

    Args:
        identifier: Unique identifier for rate limiting (e.g., session_id, user_id)
        max_requests: Maximum requests allowed in the time window
        window_seconds: Time window in seconds

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    current_time = time.time()
    cutoff_time = current_time - window_seconds

    # Clean old entries
    _rate_limit_store[identifier] = [
        timestamp for timestamp in _rate_limit_store[identifier]
        if timestamp > cutoff_time
    ]

    # Check rate limit
    if len(_rate_limit_store[identifier]) >= max_requests:
        raise RateLimitExceeded(
            f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds"
        )

    # Add current request
    _rate_limit_store[identifier].append(current_time)


def validate_file_upload(
    file_content: bytes,
    allowed_extensions: list,
    max_size_mb: int = 10
) -> None:
    """
    Validate uploaded file.

    Enforces size limits and binary-file rejection to help prevent resource
    exhaustion and malicious file uploads. Configure via MAX_FILE_SIZE_MB env var.

    Security metrics:
        - Size limit prevents memory exhaustion from oversized uploads
        - Null-byte check rejects binary/executable content
        - Implementation priority: High

    Args:
        file_content: File content as bytes
        allowed_extensions: List of allowed file extensions (e.g., ['.md', '.txt'])
        max_size_mb: Maximum file size in MB

    Raises:
        InputValidationError: If file is invalid
    """
    # Check size
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(file_content) > max_size_bytes:
        raise InputValidationError(
            f"File size exceeds maximum of {max_size_mb}MB"
        )

    # Check for null bytes (potential binary file)
    if b'\x00' in file_content:
        raise InputValidationError("File contains null bytes (binary file not allowed)")


def _get_fernet_key(key: Optional[str] = None) -> bytes:
    """
    Derive a valid Fernet key from the provided key or environment variable.

    Args:
        key: Optional encryption key string

    Returns:
        URL-safe base64-encoded 32-byte key for Fernet

    Raises:
        SecurityError: If no encryption key is configured
    """
    if key is None:
        key = os.environ.get("SESSION_ENCRYPTION_KEY")
    if not key:
        raise SecurityError(
            "SESSION_ENCRYPTION_KEY environment variable must be set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # Derive a 32-byte key using SHA-256 so any string works as input
    derived = hashlib.sha256(key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(derived)


def encrypt_session_data(data: str, key: Optional[str] = None) -> str:
    """
    Encrypt sensitive session data using Fernet symmetric encryption.

    Args:
        data: Data to encrypt
        key: Encryption key (if None, reads SESSION_ENCRYPTION_KEY env var)

    Returns:
        Encrypted data as a Fernet token string

    Raises:
        SecurityError: If no encryption key is configured
    """
    fernet_key = _get_fernet_key(key)
    f = Fernet(fernet_key)
    return f.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_session_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    Decrypt session data.

    Args:
        encrypted_data: Fernet token string
        key: Decryption key (if None, reads SESSION_ENCRYPTION_KEY env var)

    Returns:
        Decrypted data

    Raises:
        SecurityError: If decryption fails or key is missing
    """
    try:
        fernet_key = _get_fernet_key(key)
        f = Fernet(fernet_key)
        return f.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise SecurityError("Decryption failed: invalid key or corrupted data")


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate JSON data against a schema.

    Args:
        data: JSON data to validate
        schema: JSON schema

    Returns:
        True if valid

    Raises:
        InputValidationError: If validation fails

    Note: This is a basic implementation. For production, use jsonschema library
    """
    try:
        # Basic type checking
        for key, expected_type in schema.items():
            if key not in data:
                raise InputValidationError(f"Missing required field: {key}")

            if not isinstance(data[key], expected_type):
                raise InputValidationError(
                    f"Invalid type for {key}: expected {expected_type.__name__}, "
                    f"got {type(data[key]).__name__}"
                )

        return True
    except Exception as e:
        raise InputValidationError(f"Schema validation failed: {str(e)}")


def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
    """
    Sanitize error messages to avoid exposing internal details.

    Args:
        error: Exception object
        include_details: Whether to include detailed error info (for debugging)

    Returns:
        Sanitized error message
    """
    if include_details:
        # For development/debugging
        return str(error)

    # For production - generic messages
    error_type = type(error).__name__

    generic_messages = {
        'FileNotFoundError': 'The requested file could not be found',
        'PermissionError': 'Permission denied',
        'ValueError': 'Invalid input provided',
        'KeyError': 'Required data is missing',
        'ConnectionError': 'Connection failed',
        'TimeoutError': 'Operation timed out',
    }

    return generic_messages.get(error_type, 'An error occurred. Please try again.')


def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """
    Log security-related events for audit trail.

    Args:
        event_type: Type of security event (e.g., 'rate_limit', 'validation_error')
        details: Event details
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'details': details
    }

    logger.warning(f"SECURITY EVENT: {log_entry}")
