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


class PaymentRequiredError(AIGatewayError):
    """Raised when provider requires payment/quota (HTTP 402)."""
    pass


# Provider error taxonomy — single source for retry/fallback decisions
ERROR_TAXONOMY = {
    RateLimitError: {"category": "RATE_LIMITED", "retryable": True, "fallback_allowed": True, "user_action_required": False},
    AuthenticationError: {"category": "AUTH_FAILED", "retryable": False, "fallback_allowed": True, "user_action_required": False},
    TimeoutError: {"category": "TIMEOUT", "retryable": True, "fallback_allowed": True, "user_action_required": False},
    PaymentRequiredError: {"category": "PAYMENT_REQUIRED", "retryable": False, "fallback_allowed": True, "user_action_required": True},
    ProviderUnavailableError: {"category": "PROVIDER_UNAVAILABLE", "retryable": True, "fallback_allowed": True, "user_action_required": False},
    MalformedResponseError: {"category": "INVALID_RESPONSE", "retryable": True, "fallback_allowed": True, "user_action_required": False},
    AIGatewayError: {"category": "UNKNOWN", "retryable": False, "fallback_allowed": False, "user_action_required": False},
}

def classify_error(exc: Exception) -> dict:
    for cls, meta in ERROR_TAXONOMY.items():
        if isinstance(exc, cls):
            return meta
    # Fallback for generic Exception containing config hints
    msg = str(exc)
    if "TAVILY_API_KEY" in msg or "All AI providers unavailable" in msg:
        return {"category": "CONFIGURATION_MISSING", "retryable": False, "fallback_allowed": False, "user_action_required": True}
    return {"category": "UNKNOWN", "retryable": False, "fallback_allowed": False, "user_action_required": False}
