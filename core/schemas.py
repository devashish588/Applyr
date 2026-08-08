"""
Canonical Pydantic schemas for Applyr — compact, validated contracts.

This file intentionally re-uses existing core.models types when appropriate to
avoid duplication and preserve backward compatibility. These schemas provide a
stable contract for agents, services, and the API to share structured data.

Do not add heavy abstractions here — keep fields minimal and forgiving.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

# Reuse the richer Resume model when available to avoid duplication.
try:
    from .models import Resume as CoreResume, ParserEvidence
except Exception:  # pragma: no cover - import fallback for tests/environment
    CoreResume = None
    ParserEvidence = None


class ResumeParsed(BaseModel):
    """Canonical parsed resume structure used across Applyr.

    Fields intentionally mirror core.models.Resume where possible.
    """

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    skills_categorized: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    quality_score: float = 0.0
    confidence: float = 0.0
    evidence: Optional[ParserEvidence] = None
    raw_text: Optional[str] = None
    source_path: Optional[str] = None
    parsed_at: Optional[str] = None

    @validator("skills", "experience", "projects", "education", "certifications", "roles", pre=True)
    def _ensure_list(cls, v):
        if v is None:
            return []
        return v


class TailoredMaterial(BaseModel):
    """Tailoring result produced by the tailoring agent.

    Keep fields conservative and compatible with agents/18-job-application-agent
    outputs (tailored_resume_path, cover_letter_path, tailored_bullets, cover_letter).
    """

    tailored_bullets: List[str] = Field(default_factory=list)
    cover_letter: Optional[str] = None
    skills_to_highlight: List[str] = Field(default_factory=list)
    keywords_matched: List[str] = Field(default_factory=list)
    keywords_missing: List[str] = Field(default_factory=list)
    tailored_resume_path: Optional[str] = None
    tailored_resume_pdf_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    cover_letter_pdf_path: Optional[str] = None
    fit_score: Optional[int] = None
    materials: Dict[str, Any] = Field(default_factory=dict)

    @validator("tailored_bullets", "skills_to_highlight", "keywords_matched", "keywords_missing", pre=True)
    def _ensure_lists(cls, v):
        if v is None:
            return []
        return v


class MatchAnalysis(BaseModel):
    """Explainable match analysis returned by match service.

    final_score is required (int 0-100). Other fields are optional but helpful
    for UI and provenance.
    """

    final_score: int = Field(..., ge=0, le=100)
    recommendation: Optional[str] = None
    explanation: Optional[str] = None
    skills_to_highlight: List[str] = Field(default_factory=list)
    why_this_score: Optional[str] = None
    supporting_sentences: List[str] = Field(default_factory=list)

    @validator("skills_to_highlight", "supporting_sentences", pre=True)
    def _ensure_list_fields(cls, v):
        if v is None:
            return []
        return v


class AssetPaths(BaseModel):
    """Canonical assets associated with a job or application record."""

    tailored_resume_path: Optional[str] = None
    tailored_resume_pdf_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    cover_letter_pdf_path: Optional[str] = None


class Template(BaseModel):
    """Simple template holder for resume/cover templates.

    For Phase 1 templates may be stored in localStorage or the DB later. Keep
    this minimal: a name, type, and content string.
    """

    name: str
    kind: str = Field(..., pattern=r"^(resume|cover)$")
    content: str
    last_updated: Optional[str] = None


# Backwards compatibility helpers
def to_resume_parsed(obj: Any) -> ResumeParsed:
    """Coerce input (dict or CoreResume) to ResumeParsed."""
    if CoreResume and isinstance(obj, CoreResume):
        # CoreResume is already a pydantic model — dump and re-parse into our schema
        return ResumeParsed(**obj.model_dump())
    if isinstance(obj, dict):
        return ResumeParsed(**obj)
    # fallback: best-effort convert via attribute access
    data = {}
    for k in ("name", "email", "phone", "skills", "experience", "raw_text"):
        data[k] = getattr(obj, k, None)
    return ResumeParsed(**data)
