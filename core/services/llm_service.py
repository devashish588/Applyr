"""
LLM Service — REST-based LLM clients.

Provides unified access to OpenRouter (primary) with Groq/Gemini fallback.
All calls go through REST API (no LangChain dependency) for reliability.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class _LLMResponse:
    """Thin wrapper so REST clients look like LangChain model responses (has .content)."""
    def __init__(self, content: str):
        self.content = content


class OpenRouterClient:
    """Lightweight REST client for OpenRouter API (OpenAI-compatible)."""

    # LangChain message types -> OpenAI/OpenRouter roles
    _ROLE_MAP = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    def invoke(self, prompt, **kwargs):
        """Send a prompt to OpenRouter.

        Accepts:
        - str: plain text prompt
        - list[dict]: messages array with {"role", "content"}
        - list[LangChain BaseMessage]: converted automatically

        Returns a response object with `.content` (LangChain-compatible).
        """
        if not self._available:
            raise RuntimeError("OpenRouter not configured — set OPENROUTER_API_KEY")
        messages = self._normalize_messages(prompt)
        text = self._chat_completion(messages, **kwargs)
        return _LLMResponse(text)

    def chat(self, messages, **kwargs):
        """Send a chat messages array. Returns a response object with `.content`."""
        return self.invoke(messages, **kwargs)

    @staticmethod
    def _normalize_messages(prompt) -> List[Dict[str, str]]:
        """Convert various input formats to OpenAI message dicts."""
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        if isinstance(prompt, list):
            result = []
            for m in prompt:
                if isinstance(m, dict):
                    # Normalize LangChain-style roles in raw dicts too
                    role = OpenRouterClient._ROLE_MAP.get(m.get("role"), m.get("role"))
                    result.append({**m, "role": role} if role else m)
                elif hasattr(m, "type") and hasattr(m, "content"):
                    # LangChain BaseMessage objects (SystemMessage, HumanMessage, etc.)
                    # m.type is "human"/"ai"/"system"/"tool" — map to OpenAI roles.
                    role = OpenRouterClient._ROLE_MAP.get(m.type, m.type)
                    result.append({"role": role, "content": m.content})
                else:
                    result.append({"role": "user", "content": str(m)})
            return result
        return [{"role": "user", "content": str(prompt)}]

    def _chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Add OpenRouter-specific headers (optional but recommended)
        site_url = os.getenv("SITE_URL", "http://localhost:5000")
        site_name = os.getenv("SITE_NAME", "Applyr")
        headers["HTTP-Referer"] = site_url
        headers["X-Title"] = site_name

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 60),
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content or ""
        except requests.exceptions.RequestException as e:
            logger.error(f"[llm] OpenRouter API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"[llm] Response: {e.response.text[:500]}")
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"[llm] OpenRouter parse error: {e}")
            raise RuntimeError(f"OpenRouter returned unexpected response: {e}")


def get_llm_client():
    """Get the best available LLM client (Groq primary, OpenRouter fallback)."""
    # Primary: Groq (fast, reliable)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and groq_key != "gsk_xxxxxxxxxxxxx":
        logger.info("[llm] Using Groq (model: %s)", os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"))
        return _GroqFallbackClient()

    # Fallback: OpenRouter
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key:
        logger.info("[llm] Using OpenRouter (model: %s)", os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"))
        return OpenRouterClient()

    # Last resort
    raise RuntimeError(
        "No LLM provider configured. Set GROQ_API_KEY or OPENROUTER_API_KEY in .env"
    )


class _GroqFallbackClient:
    """Thin REST client for Groq API (fallback when OpenRouter unavailable)."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        if base.endswith("/openai/v1"):
            base = base[:-len("/openai/v1")]
        self.base_url = base

    @property
    def available(self) -> bool:
        return bool(self.api_key) and self.api_key != "gsk_xxxxxxxxxxxxx"

    def invoke(self, prompt, **kwargs):
        messages = OpenRouterClient._normalize_messages(prompt)
        text = self._chat_completion(messages, **kwargs)
        return _LLMResponse(text)

    def chat(self, messages, **kwargs):
        return self.invoke(messages, **kwargs)

    def _chat_completion(self, messages, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        try:
            resp = requests.post(
                f"{self.base_url}/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 60),
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""
        except Exception as e:
            logger.error(f"[llm] Groq fallback error: {e}")
            raise
