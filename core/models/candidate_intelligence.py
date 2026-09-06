"""
Canonical Candidate Intelligence Models — Applyr 2.0
=====================================================

Typed models for candidate profile representation, skill categorization,
evidence tracking, and explainable confidence scores.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.models import SeniorityLevel


class SourceOrigin(str, Enum):
    """Origin classification for candidate facts."""
    EXPLICIT_USER = "explicit_user"
    EXPLICIT_RESUME = "explicit_resume"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class CandidateProvenance(str, Enum):
    """Per-dimension provenance (candidate) — preserves why UNKNOWN vs DETERMINED."""
    SOURCE_UNAVAILABLE = "source_unavailable"
    EXTRACTION_FAILED = "extraction_failed"
    EXTRACTION_UNPARSEABLE = "extraction_unparseable"
    DETERMINED_EMPTY = "determined_empty"
    DETERMINED_POPULATED = "determined_populated"
    INFERRED = "inferred"  # Seniority only: INFERRED via title/years, not authoritative


class IntelligenceEvidence(BaseModel):
    """Evidence traceability entry explaining where a candidate fact originated."""
    source: str  # e.g. "profile.json", "resume_experience", "resume_projects"
    confidence: float = 1.0
    origin: SourceOrigin = SourceOrigin.EXPLICIT_RESUME
    details: Optional[str] = None


class SkillIntelligence(BaseModel):
    """Normalized skill entity with category and evidence traceability."""
    name: str
    normalized_name: str
    category: str = "other"  # languages, frameworks, databases, cloud, devops, ai_ml, tools, other
    evidence: List[IntelligenceEvidence] = Field(default_factory=list)
    confidence: float = 1.0


class ExperienceItem(BaseModel):
    """Structured work experience item."""
    title: str
    company: str
    duration: Optional[str] = None
    years: float = 0.0
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """Structured candidate project item."""
    name: str
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)


class CanonicalCandidateProfile(BaseModel):
    """Canonical representation of candidate intelligence."""
    candidate_id: str = "primary_candidate"
    name: str = "Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_role: Optional[str] = None
    seniority: str = "MID"
    seniority_origin: SourceOrigin = SourceOrigin.INFERRED
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: str = "any"
    
    skills: List[SkillIntelligence] = Field(default_factory=list)
    # Full occurrence-level skill evidence for matching (preserves every raw input).
    # skills remains deduplicated by canonical for backward compatibility;
    # skill_occurrences preserves every occurrence in input order so
    # SkillMatcher can evaluate EXACT > ALIAS correctly.
    skill_occurrences: List[SkillIntelligence] = Field(default_factory=list)
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    
    strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    inferred_domains: List[str] = Field(default_factory=list)
    overall_confidence: float = 0.9
    updated_at: str = ""
    # Provenance per dimension (additive, defaults preserve pre-5B-7 behavior as UNDETERMINED-equivalent)
    experience_provenance: CandidateProvenance = CandidateProvenance.SOURCE_UNAVAILABLE
    role_provenance: CandidateProvenance = CandidateProvenance.SOURCE_UNAVAILABLE
    location_provenance: CandidateProvenance = CandidateProvenance.SOURCE_UNAVAILABLE
    seniority_provenance: CandidateProvenance = CandidateProvenance.SOURCE_UNAVAILABLE
