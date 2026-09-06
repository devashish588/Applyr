"""
LLM Service — Applyr 2.0 Backward Compatibility Delegate
=========================================================

Provides backward-compatible wrappers (OpenRouterClient, get_llm_client)
that route all requests directly through the centralized Applyr AI Gateway.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from core.ai.gateway import get_ai_gateway
from core.ai.schemas import AIRequest

logger = logging.getLogger(__name__)


class _LLMResponse:
    """Thin wrapper so REST clients look like LangChain model responses (has .content)."""
    def __init__(self, content: str):
        self.content = content


class OpenRouterClient:
    """Backward-compatible client delegating to AIGateway."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    def invoke(self, prompt: Any, **kwargs) -> _LLMResponse:
        messages = self._normalize_messages(prompt)
        gateway = get_ai_gateway()
        req = AIRequest(
            task="llm_service_invoke",
            messages=messages,
            provider_preference="openrouter",
            model_preference=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        res = gateway.generate(req)
        return _LLMResponse(res.text)

    def chat(self, messages: Any, **kwargs) -> _LLMResponse:
        return self.invoke(messages, **kwargs)

    @staticmethod
    def _normalize_messages(prompt: Any) -> List[Dict[str, str]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        if isinstance(prompt, list):
            result = []
            for m in prompt:
                if isinstance(m, dict):
                    role = m.get("role", "user")
                    if role in ("human", "user"):
                        role = "user"
                    elif role in ("ai", "assistant"):
                        role = "assistant"
                    result.append({"role": role, "content": str(m.get("content", ""))})
                elif hasattr(m, "type") and hasattr(m, "content"):
                    role = getattr(m, "type", "user")
                    if role == "human":
                        role = "user"
                    elif role == "ai":
                        role = "assistant"
                    result.append({"role": role, "content": str(getattr(m, "content", ""))})
                else:
                    result.append({"role": "user", "content": str(m)})
            return result
        return [{"role": "user", "content": str(prompt)}]


class _GroqFallbackClient(OpenRouterClient):
    """Backward-compatible Groq delegate pointing to AIGateway."""

    def __init__(self):
        super().__init__(
            api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        )

    def invoke(self, prompt: Any, **kwargs) -> _LLMResponse:
        messages = self._normalize_messages(prompt)
        gateway = get_ai_gateway()
        req = AIRequest(
            task="llm_service_groq",
            messages=messages,
            provider_preference="groq",
            model_preference=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        res = gateway.generate(req)
        return _LLMResponse(res.text)


class _AIGatewayWrapper:
    """Generic client wrapping AIGateway with default cascade."""

    def invoke(self, prompt: Any, **kwargs) -> _LLMResponse:
        messages = OpenRouterClient._normalize_messages(prompt)
        gateway = get_ai_gateway()
        req = AIRequest(
            task="gateway_wrapper",
            messages=messages,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        res = gateway.generate(req)
        return _LLMResponse(res.text)

    def chat(self, messages: Any, **kwargs) -> _LLMResponse:
        return self.invoke(messages, **kwargs)


def get_llm_client():
    """Get AI Gateway wrapper client."""
    return _AIGatewayWrapper()
