"""
OpenRouter Provider Adapter — Applyr 2.0
=========================================

REST adapter for OpenRouter API (OpenAI-compatible endpoints).
"""

import logging
import os
import time
from typing import Any, Dict

import requests

from core.ai.providers.base import BaseAIProvider
from core.ai.schemas import AIRequest, AIResponse
from core.ai.errors import (
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ProviderUnavailableError,
    MalformedResponseError,
    sanitize_exception_message,
)

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseAIProvider):
    """Provider adapter for OpenRouter API."""

    def __init__(self):
        super().__init__(name="openrouter")
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        if not self.health_check():
            raise ProviderUnavailableError("OpenRouter API key not configured")

        model_name = request.model_preference or self.model
        messages = self._normalize_messages(request)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5173"),
            "X-Title": os.getenv("SITE_NAME", "Applyr"),
        }
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))
        start_time = time.time()

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            latency_ms = (time.time() - start_time) * 1000

            if resp.status_code == 401 or resp.status_code == 403:
                raise AuthenticationError(f"OpenRouter authentication failed (status {resp.status_code})")
            elif resp.status_code == 429:
                raise RateLimitError("OpenRouter rate limit exceeded (HTTP 429)")
            elif resp.status_code >= 500:
                raise ProviderUnavailableError(f"OpenRouter server error (status {resp.status_code})")

            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage", {})

            return AIResponse(
                text=content,
                provider="openrouter",
                model=model_name,
                request_id=request.request_id or "req_openrouter",
                latency_ms=round(latency_ms, 2),
                usage={"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0)},
            )

        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"OpenRouter request timed out: {sanitize_exception_message(str(e))}")
        except requests.exceptions.ConnectionError as e:
            raise ProviderUnavailableError(f"OpenRouter connection error: {sanitize_exception_message(str(e))}")
        except (KeyError, IndexError, ValueError) as e:
            raise MalformedResponseError(f"OpenRouter response parsing error: {e}")
