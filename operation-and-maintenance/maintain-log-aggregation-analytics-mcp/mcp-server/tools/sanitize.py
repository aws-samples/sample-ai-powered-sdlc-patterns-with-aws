"""Sanitization utilities for text sent to Amazon Bedrock."""

import re

MAX_BEDROCK_TEXT_LENGTH = 10000

# Patterns for sensitive data that should be redacted
SENSITIVE_PATTERNS = [
    # AWS Access Keys
    (re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}'), '[REDACTED_AWS_ACCESS_KEY]'),
    # AWS Secret Keys (40-char base64 after common prefixes)
    (re.compile(r'(?:aws_secret_access_key|secret_key|SecretAccessKey)\s*[=:]\s*\S+', re.IGNORECASE), '[REDACTED_AWS_SECRET_KEY]'),
    # AWS Session Tokens
    (re.compile(r'(?:aws_session_token|SessionToken)\s*[=:]\s*\S+', re.IGNORECASE), '[REDACTED_AWS_SESSION_TOKEN]'),
    # Bearer tokens
    (re.compile(r'[Bb]earer\s+[A-Za-z0-9\-._~+/]+=*'), '[REDACTED_BEARER_TOKEN]'),
    # Generic API keys / tokens (key=value patterns)
    (re.compile(r'(?:api[_-]?key|api[_-]?secret|token|password|passwd|secret|credential|auth)\s*[=:]\s*\S+', re.IGNORECASE), '[REDACTED_CREDENTIAL]'),
    # Credit card numbers (13-19 digits, with optional separators)
    (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), '[REDACTED_CREDIT_CARD]'),
    # US Social Security Numbers
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[REDACTED_SSN]'),
    # Phone numbers (various formats)
    (re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), '[REDACTED_PHONE]'),
    # Email addresses
    (re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'), '[REDACTED_EMAIL]'),
    # IP addresses (IPv4)
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[REDACTED_IP]'),
    # AWS Account IDs (12-digit numbers in ARN-like contexts)
    (re.compile(r'(?<=arn:aws[a-z\-]*:[a-z0-9\-]+:[a-z0-9\-]*:)\d{12}(?=:)'), '[REDACTED_ACCOUNT_ID]'),
    # JWT tokens (three base64 segments separated by dots)
    (re.compile(r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'), '[REDACTED_JWT]'),
    # Private keys
    (re.compile(r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA )?PRIVATE KEY-----'), '[REDACTED_PRIVATE_KEY]'),
    # Connection strings with credentials
    (re.compile(r'(?:mongodb|postgres|mysql|redis|amqp)://[^\s]+@[^\s]+', re.IGNORECASE), '[REDACTED_CONNECTION_STRING]'),
]

# Prompt injection guard: patterns that attempt to manipulate AI behavior
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts|context)', re.IGNORECASE),
    re.compile(r'(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|new\s+instructions?)', re.IGNORECASE),
    re.compile(r'(?:system\s*:\s*|<\s*system\s*>|<<\s*SYS\s*>>)', re.IGNORECASE),
]


def sanitize_for_bedrock(text: str) -> str:
    """Sanitize text before sending to Amazon Bedrock.

    Strips sensitive patterns (credentials, PII, tokens), neutralizes
    prompt injection attempts, and enforces a maximum character limit.
    """
    if not text:
        return text

    # Redact sensitive data
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)

    # Neutralize prompt injection attempts
    for pattern in PROMPT_INJECTION_PATTERNS:
        text = pattern.sub('[FILTERED_CONTENT]', text)

    if len(text) > MAX_BEDROCK_TEXT_LENGTH:
        text = text[:MAX_BEDROCK_TEXT_LENGTH] + "\n... [TRUNCATED: exceeded maximum length]"

    return text


# AWS error message patterns to strip
_AWS_ACCOUNT_ID_PATTERN = re.compile(r'\b\d{12}\b')
_AWS_ARN_PATTERN = re.compile(r'arn:aws[a-z\-]*:[a-z0-9\-]+:[a-z0-9\-]*:\d{12}:[^\s,\'"]+')
_AWS_REGION_PATTERN = re.compile(r'(?:us|eu|ap|sa|ca|me|af)-(?:east|west|north|south|central|northeast|southeast)-\d')


def sanitize_aws_error(error_message: str) -> str:
    """Sanitize AWS error messages to strip account IDs, ARNs, and region details.

    Prevents information leakage about AWS infrastructure through error responses.
    """
    if not error_message:
        return error_message

    sanitized = _AWS_ARN_PATTERN.sub('[REDACTED_ARN]', error_message)
    sanitized = _AWS_ACCOUNT_ID_PATTERN.sub('[REDACTED_ACCOUNT]', sanitized)
    sanitized = _AWS_REGION_PATTERN.sub('[REDACTED_REGION]', sanitized)

    return sanitized
