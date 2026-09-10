"""
Central LLM client for Applyr — Applyr 2.0 Backward Compatibility Wrapper.

All calls route through the centralized Applyr AI Gateway (core.ai.gateway).
"""

import json
import logging
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv

from core.ai.gateway import get_ai_gateway
from core.ai.schemas import AIRequest

load_dotenv()

logger = logging.getLogger(__name__)


class _AIGatewayLangChainAdapter:
    """Adapter making AIGateway act like a LangChain ChatModel object."""

    def __init__(self, temperature: float = 0.0, model: Optional[str] = None):
        self.temperature = temperature
        self.model = model

    def invoke(self, messages: Any, **kwargs) -> Any:
        gateway = get_ai_gateway()
        req = AIRequest(
            task="llm_client_adapter",
            messages=messages if isinstance(messages, list) else None,
            prompt=str(messages) if not isinstance(messages, list) else "",
            model_preference=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", self.temperature),
        )
        res = gateway.generate(req)
        
        # Return wrapper object with .content and provider_attempts for observability
        class _Resp:
            def __init__(self, text: str, provider_attempts=None):
                self.content = text
                self.provider_attempts = provider_attempts or []

        return _Resp(res.text, getattr(res, "provider_attempts", []))


def get_llm(temperature: float = 0.0, model: Optional[str] = None) -> Any:
    """Get AI Gateway wrapped client for LLM operations."""
    return _AIGatewayLangChainAdapter(temperature=temperature, model=model)


def get_fast_llm(temperature: float = 0.0) -> Any:
    """Get fast LLM model through AI Gateway."""
    return get_llm(temperature=temperature)


def chat(prompt: str, system_prompt: str = "", temperature: float = 0.0) -> str:
    """One-shot chat completion through Applyr AI Gateway."""
    gateway = get_ai_gateway()
    req = AIRequest(
        task="llm_client_chat",
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
    )
    res = gateway.generate(req)
    return res.text


def chat_json(prompt: str, system_prompt: str = "", temperature: float = 0.0) -> dict:
    """Chat completion through AI Gateway that parses JSON output."""
    response = chat(prompt, system_prompt, temperature)
    return parse_json_response(response)


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            return {"items": json.loads(match.group(0))}
        raise


if __name__ == "__main__":
    load_dotenv()
    print("Testing Applyr AI Gateway compatibility wrapper...")
    try:
        result = chat("Say 'LLM is working!' in exactly those words.")
        print(f"Response: {result}")
        print("[OK] AI Gateway connection successful!")
    except Exception as e:
        print(f"[FAIL] AI Gateway connection error (expected if offline/mocked): {e}")
