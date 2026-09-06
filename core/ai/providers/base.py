"""
Abstract AI Provider Interface — Applyr 2.0
===========================================

Base class for Groq, OpenRouter, and Gemini provider adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.ai.schemas import AIRequest, AIResponse


class BaseAIProvider(ABC):
    """Abstract provider adapter interface."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Send request to provider API and return normalized AIResponse."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Lightweight check verifying if provider API key & endpoint are configured."""
        pass

    @staticmethod
    def _normalize_messages(request: AIRequest) -> List[Dict[str, str]]:
        """Normalize prompt or message list into standard OpenAI-compatible role dicts."""
        if request.messages:
            result = []
            for m in request.messages:
                if isinstance(m, dict):
                    role = m.get("role", "user")
                    if role in ("human", "user"):
                        role = "user"
                    elif role in ("ai", "assistant"):
                        role = "assistant"
                    elif role in ("system",):
                        role = "system"
                    result.append({"role": role, "content": str(m.get("content", ""))})
                elif hasattr(m, "type") and hasattr(m, "content"):
                    role = getattr(m, "type", "user")
                    if role == "human":
                        role = "user"
                    elif role == "ai":
                        role = "assistant"
                    result.append({"role": role, "content": str(getattr(m, "content", ""))})
            return result

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        if request.prompt:
            messages.append({"role": "user", "content": request.prompt})
        if not messages:
            messages.append({"role": "user", "content": "Hello"})
        return messages
