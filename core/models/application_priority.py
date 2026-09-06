"""
Application Priority — deterministic tier model
==============================================

No numeric score, no probability. Tier only.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ApplicationPriority(BaseModel):
    job_id: int
    tier: str  # HOT | WARM | COLD | REVIEW
    factors: Dict[str, str] = Field(default_factory=dict)
    explanation: str = ""
    uncertainty: List[str] = Field(default_factory=list)
    # Optional match reference for debugging, not scoring
    match_tier_detail: Optional[str] = None
