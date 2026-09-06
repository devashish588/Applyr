"""
Studio models — Phase 10
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    status: str  # READY, NOT_FOUND, NOT_AVAILABLE, GENERATION_FAILED, UNKNOWN, DETERMINED, etc.
    detail: Optional[str] = None


class StudioContext(BaseModel):
    job_id: int
    job: Dict
    candidate: Dict
    match: Optional[Dict] = None
    priority: Optional[Dict] = None
    job_quality: Optional[Dict] = None
    skill_gaps: List[Dict] = Field(default_factory=list)
    resume_source: ComponentStatus
    tailored_resume: ComponentStatus
    resume_diff: Optional[Dict] = None
    ats: ComponentStatus
    ats_details: Optional[Dict] = None
    cover_letter: ComponentStatus
    cover_letter_text: Optional[str] = None
    recruiter: ComponentStatus
    recruiter_details: Optional[Dict] = None
    outreach_preview: ComponentStatus
    outreach_text: Optional[str] = None
    autofill: ComponentStatus
    warnings: List[str] = Field(default_factory=list)
    overall_status: str = "PARTIAL"  # COMPLETED, PARTIAL, FAILED
    created_at: Optional[str] = None
    candidate_provenance: Optional[str] = None
    job_provenance: Optional[str] = None
