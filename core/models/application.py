"""
Canonical Application Models — Phase 7 P0
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Application(BaseModel):
    id: Optional[int] = None
    job_id: Optional[int] = None
    attempt_number: int = 1
    previous_application_id: Optional[int] = None
    candidate_id: str = "primary_candidate"
    job_title_snapshot: Optional[str] = None
    company_snapshot: Optional[str] = None
    current_state: str = "DISCOVERED"
    last_state_change_at: Optional[str] = None
    created_at: Optional[str] = None
    submitted_at: Optional[str] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    match_snapshot: Optional[str] = None
    priority_snapshot: Optional[str] = None


class ApplicationEvent(BaseModel):
    id: Optional[int] = None
    application_id: int
    event_type: str
    timestamp: Optional[str] = None
    actor: str = "user"
    payload: Optional[str] = None
    evidence_ref: Optional[str] = None


class ApplicationOutcome(BaseModel):
    application_id: int
    outcome: str = "NONE"
    decided_at: Optional[str] = None
    reason: Optional[str] = None
    offer_details: Optional[str] = None
