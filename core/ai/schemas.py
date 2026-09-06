"""
AI Gateway Schemas — Applyr 2.0
================================

Typed request and response models for the centralized AI Gateway.
"""

from dataclasses import dataclass, field
import uuid
from typing import Any, Dict, List, Optional


@dataclass
class AIRequest:
    """Typed request parameters for AI Gateway calls."""

    task: str = "chat"
    prompt: str = ""
    system_prompt: str = ""
    messages: Optional[List[Dict[str, str]]] = None
    provider_preference: Optional[str] = None
    model_preference: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None

    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"req_{uuid.uuid4().hex[:12]}"


@dataclass
class AIResponse:
    """Typed response returned by AI Gateway and providers."""

    text: str
    provider: str
    model: str
    request_id: str
    latency_ms: float = 0.0
    fallback_used: bool = False
    attempts: int = 1
    usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
