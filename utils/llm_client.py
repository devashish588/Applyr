"""
Central LLM client for Applyr - all agents use this.
OpenRouter primary (REST), Groq fallback (LangChain).
"""
import json
import logging
import os
import re
import time
from typing import Any, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

logger = logging.getLogger(__name__)

# Groq fallback config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None


def get_llm(temperature: float = 0, model: Optional[str] = None) -> Any:
    """Get the best available LLM (Groq > OpenRouter).

    Groq (llama-4-scout) is preferred because it produces reliable structured
    JSON; the free OpenRouter models tend to return truncated/empty JSON for
    extraction tasks. This also matches core.services.llm_service's ordering.
    """
    # Primary: Groq via LangChain (reliable structured output)
    if GROQ_API_KEY and GROQ_API_KEY != "gsk_xxxxxxxxxxxxx":
        if ChatGroq is None:
            raise ImportError("langchain-groq is not installed. Install it with: pip install langchain-groq")
        base_url = GROQ_BASE_URL.rstrip("/")
        if base_url.endswith("/openai/v1"):
            base_url = base_url[: -len("/openai/v1")]
        return ChatGroq(
            model=model or GROQ_MODEL,
            api_key=GROQ_API_KEY,
            base_url=base_url,
            temperature=temperature,
            max_retries=3,
            timeout=60,
        )

    # Fallback: OpenRouter via REST
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key:
        from core.services.llm_service import OpenRouterClient
        return OpenRouterClient(
            model=model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
        )

    raise EnvironmentError("No LLM provider configured. Set GROQ_API_KEY or OPENROUTER_API_KEY in .env")


def get_fast_llm(temperature: float = 0) -> Any:
    """Get a fast/cheap LLM for simple tasks."""
    return get_llm(temperature=temperature, model=GROQ_FAST_MODEL)


def chat(prompt: str, system_prompt: str = "", temperature: float = 0) -> str:
    """Simple one-shot chat completion (OpenRouter > Groq)."""
    llm = get_llm(temperature=temperature)
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    for attempt in range(3):
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


def chat_json(prompt: str, system_prompt: str = "", temperature: float = 0) -> dict:
    """Chat completion that parses JSON from response."""
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
    print(f"OpenRouter API Key: {'SET' if os.getenv('OPENROUTER_API_KEY') else 'MISSING'}")
    print(f"Groq API Key: {'SET' if GROQ_API_KEY else 'MISSING'}")
    try:
        result = chat("Say 'LLM is working!' in exactly those words.")
        print(f"Response: {result}")
        print("[OK] LLM connection successful!")
    except Exception as e:
        print(f"[FAIL] LLM connection failed: {e}")
