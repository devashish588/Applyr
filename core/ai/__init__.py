"""
Applyr 2.0 AI Gateway Package
"""

from core.ai.schemas import AIRequest, AIResponse
from core.ai.errors import (
    AIGatewayError,
    ProviderUnavailableError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    MalformedResponseError,
)
from core.ai.gateway import AIGateway, get_ai_gateway

__all__ = [
    "AIRequest",
    "AIResponse",
    "AIGatewayError",
    "ProviderUnavailableError",
    "AuthenticationError",
    "RateLimitError",
    "TimeoutError",
    "MalformedResponseError",
    "AIGateway",
    "get_ai_gateway",
]
