"""
Central AI Gateway — Applyr 2.0
================================

Centralized AI Gateway orchestrating provider selection, fallback cascades,
bounded retries with exponential backoff, timeout handling, and safe audit logging.
"""

import logging
import os
import time
import uuid
from typing import Dict, List, Optional, Type

from core.ai.schemas import AIRequest, AIResponse
from core.ai.errors import (
    AIGatewayError,
    ProviderUnavailableError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    MalformedResponseError,
    sanitize_exception_message,
)
from core.ai.providers.base import BaseAIProvider
from core.ai.providers.groq import GroqProvider
from core.ai.providers.openrouter import OpenRouterProvider
from core.ai.providers.gemini import GeminiProvider

logger = logging.getLogger("applyr.ai.gateway")


class AIGateway:
    """Central AI Gateway for Applyr 2.0."""

    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {
            "groq": GroqProvider(),
            "openrouter": OpenRouterProvider(),
            "gemini": GeminiProvider(),
        }
        self.default_cascade = ["groq", "openrouter", "gemini"]

    def generate(self, request: AIRequest) -> AIResponse:
        """Process AIRequest through provider selection, bounded retries, and fallback cascade."""
        if not request.request_id:
            request.request_id = f"req_{uuid.uuid4().hex[:12]}"

        max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        # Determine provider trial sequence
        sequence = list(self.default_cascade)
        if request.provider_preference and request.provider_preference in self.providers:
            # Place preferred provider first
            sequence = [request.provider_preference] + [p for p in sequence if p != request.provider_preference]

        attempts_total = 0
        fallback_triggered = False

        for idx, provider_name in enumerate(sequence):
            provider = self.providers.get(provider_name)
            if not provider or not provider.health_check():
                logger.info(f"[gateway] Skipping unconfigured provider: {provider_name} (req_id={request.request_id})")
                if idx > 0:
                    fallback_triggered = True
                continue

            if idx > 0:
                fallback_triggered = True

            # Attempt bounded retries for current provider
            for attempt in range(1, max_retries + 1):
                attempts_total += 1
                try:
                    logger.info(
                        f"[gateway] Executing task='{request.task}' via provider='{provider_name}' "
                        f"attempt={attempt}/{max_retries} (req_id={request.request_id})"
                    )
                    
                    response = provider.generate(request)
                    response.attempts = attempts_total
                    response.fallback_used = fallback_triggered

                    logger.info(
                        f"[gateway] SUCCESS req_id={response.request_id} provider={response.provider} "
                        f"model={response.model} latency={response.latency_ms}ms fallback={response.fallback_used}"
                    )
                    return response

                except AuthenticationError as e:
                    logger.warning(f"[gateway] Auth error on provider='{provider_name}': {e}. Moving to fallback.")
                    # Do not retry auth errors repeatedly on same provider; break to next provider
                    break

                except (RateLimitError, TimeoutError, ProviderUnavailableError, MalformedResponseError) as e:
                    logger.warning(
                        f"[gateway] Transient error on provider='{provider_name}' "
                        f"attempt {attempt}/{max_retries}: {e}"
                    )
                    if attempt < max_retries:
                        sleep_time = min(8.0, 0.5 * (2 ** (attempt - 1)))
                        time.sleep(sleep_time)
                    else:
                        logger.warning(f"[gateway] Max retries exhausted for provider='{provider_name}'. Falling back.")

                except Exception as e:
                    # Sanitize exception message to remove API keys from URLs and headers
                    err_msg = sanitize_exception_message(str(e))
                    logger.error(f"[gateway] Unexpected exception on provider='{provider_name}': {err_msg}")
                    break

        # All providers failed or were unconfigured
        logger.error(f"[gateway] ALL PROVIDERS FAILED for req_id={request.request_id}")
        raise ProviderUnavailableError(f"All AI providers unavailable or failed for req_id={request.request_id}")

    def health_check(self) -> Dict[str, bool]:
        """Return status of all registered providers."""
        return {name: p.health_check() for name, p in self.providers.items()}


# Singleton instance
_gateway_instance: Optional[AIGateway] = None

def get_ai_gateway() -> AIGateway:
    """Get global AIGateway singleton instance."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = AIGateway()
    return _gateway_instance
