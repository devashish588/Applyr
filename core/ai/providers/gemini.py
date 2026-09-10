"""
Gemini Provider Adapter — Applyr 2.0
====================================

REST adapter for Google Gemini REST API.
"""

import logging
import os
import time
from typing import Any, Dict, List

import requests

from core.ai.providers.base import BaseAIProvider
from core.ai.schemas import AIRequest, AIResponse
from core.ai.errors import (
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ProviderUnavailableError,
    PaymentRequiredError,
    MalformedResponseError,
    sanitize_exception_message,
)

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Provider adapter for Google Gemini API."""

    def __init__(self):
        super().__init__(name="gemini")
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        if not self.health_check():
            raise ProviderUnavailableError("Gemini API key not configured")

        model_name = request.model_preference or self.model
        messages = self._normalize_messages(request)
        
        # Build Gemini REST contents payload
        contents: List[Dict[str, Any]] = []
        system_instruction = None

        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))
        start_time = time.time()
        url = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"

        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            latency_ms = (time.time() - start_time) * 1000

            if resp.status_code == 401 or resp.status_code == 403:
                raise AuthenticationError(f"Gemini authentication failed (status {resp.status_code})")
            elif resp.status_code == 402:
                raise PaymentRequiredError(f"Gemini payment required (status 402)")
            elif resp.status_code == 429:
                raise RateLimitError("Gemini rate limit exceeded (HTTP 429)")
            elif resp.status_code >= 500:
                raise ProviderUnavailableError(f"Gemini server error (status {resp.status_code})")

            resp.raise_for_status()
            data = resp.json()

            # Parse Gemini response structure
            candidates = data.get("candidates", [])
            if not candidates:
                raise MalformedResponseError("Gemini returned empty candidates list")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

            return AIResponse(
                text=text,
                provider="gemini",
                model=model_name,
                request_id=request.request_id or "req_gemini",
                latency_ms=round(latency_ms, 2),
                usage={"prompt_tokens": 0, "completion_tokens": 0},
            )

        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Gemini request timed out: {sanitize_exception_message(str(e))}")
        except requests.exceptions.ConnectionError as e:
            raise ProviderUnavailableError(f"Gemini connection error: {sanitize_exception_message(str(e))}")
        except (KeyError, IndexError, ValueError) as e:
            raise MalformedResponseError(f"Gemini response parsing error: {e}")
