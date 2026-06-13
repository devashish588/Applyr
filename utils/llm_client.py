"""
Central LLM client for Applyr - all agents use this.
Configured to use Groq API via OpenAI-compatible endpoint.
"""
import os
import json
import re
import time
import logging
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

logger = logging.getLogger(__name__)

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def get_llm(temperature: float = 0, model: Optional[str] = None) -> ChatOpenAI:
    """Get a ChatOpenAI instance configured for Groq API.

    Args:
        temperature: LLM temperature (0 = deterministic, 1 = creative)
        model: Override model name. Defaults to GROQ_MODEL env var.

    Returns:
        ChatOpenAI instance pointed at Groq.
    """
    return ChatOpenAI(
        model=model or GROQ_MODEL,
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        temperature=temperature,
        max_retries=3,
        request_timeout=60,
    )


def get_fast_llm(temperature: float = 0) -> ChatOpenAI:
    """Get a fast/cheap LLM for simple tasks (scoring, classification)."""
    return ChatOpenAI(
        model=GROQ_FAST_MODEL,
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        temperature=temperature,
        max_retries=3,
        request_timeout=30,
    )


def chat(prompt: str, system_prompt: str = "", temperature: float = 0) -> str:
    """Simple one-shot chat completion via Groq.

    Args:
        prompt: User message
        system_prompt: System instructions
        temperature: LLM temperature

    Returns:
        LLM response text
    """
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
    """Chat completion that parses JSON from response.

    Args:
        prompt: User message
        system_prompt: System instructions (should ask for JSON output)
        temperature: LLM temperature

    Returns:
        Parsed JSON dict
    """
    response = chat(prompt, system_prompt, temperature)
    return parse_json_response(response)


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response text.

    Handles markdown code fences, extra text around JSON, etc.
    """
    cleaned = text.strip()

    # Remove markdown code fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # Try to find JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON array
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            return {"items": json.loads(match.group(0))}
        raise


# Quick connectivity test
if __name__ == "__main__":
    load_dotenv()
    print(f"Groq API Key: {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"Model: {GROQ_MODEL}")
    print(f"Base URL: {GROQ_BASE_URL}")

    try:
        result = chat("Say 'Groq API is working!' in exactly those words.")
        print(f"Response: {result}")
        print("[OK] Groq API connection successful!")
    except Exception as e:
        print(f"[FAIL] Groq API connection failed: {e}")
