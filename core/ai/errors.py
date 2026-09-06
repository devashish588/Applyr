"""
AI Gateway Exception Hierarchy — Applyr 2.0
===========================================

Normalized exceptions raised by AI Gateway and providers.
"""

import re

# Patterns that may contain secrets in error messages / URLs
_SECRET_PATTERNS = [
    # URL query parameter keys: ?key=..., &key=...
    (re.compile(r'([?&]key=)[^&\s]+', re.IGNORECASE), r'\1REDACTED'),
    # Bearer tokens in headers or error text
    (re.compile(r'(Bearer\s+)[A-Za-z0-9_\-\.]+', re.IGNORECASE), r'\1REDACTED'),
    # Authorization header values
    (re.compile(r'(Authorization["\s:=]+)[A-Za-z0-9_\-\.]+', re.IGNORECASE), r'\1REDACTED'),
]


def sanitize_exception_message(msg: str) -> str:
    """Remove API keys and secrets from exception/log strings.

    Handles URL query params (?key=...), Bearer tokens, and Authorization headers.
    Safe to call on any string; returns the string with secrets redacted.
    """
    if not msg:
        return msg
    sanitized = msg
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class AIGatewayError(Exception):
    """Base exception for all AI Gateway failures."""
    pass


class ProviderUnavailableError(AIGatewayError):
    """Raised when an AI provider is unconfigured, down, or returning 5xx errors."""
    pass


class AuthenticationError(AIGatewayError):
    """Raised on invalid or missing API key (HTTP 401/403)."""
    pass


class RateLimitError(AIGatewayError):
    """Raised when provider rate limits or quotas are exceeded (HTTP 429)."""
    pass


class TimeoutError(AIGatewayError):
    """Raised when an AI request exceeds timeout thresholds."""
    pass


class MalformedResponseError(AIGatewayError):
    """Raised when provider returns unparseable JSON or empty content."""
    pass
