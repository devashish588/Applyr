"""
Canonical Job Intelligence Models — Applyr 2.0
================================================

Typed models for structured job representation, skill classification,
ATS detection, evidence tracking, and explainable confidence scores.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobSourceOrigin(str, Enum):
    """Origin classification for job facts."""
    EXPLICIT_JD = "explicit_jd"
    EXPLICIT_METADATA = "explicit_metadata"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class JobProvenance(str, Enum):
    """Per-dimension provenance (job) — preserves why UNKNOWN vs NO_REQUIREMENT."""
    SOURCE_UNAVAILABLE = "source_unavailable"
    EXTRACTION_FAILED = "extraction_failed"
    EXTRACTION_UNPARSEABLE = "extraction_unparseable"
    NO_REQUIREMENT = "no_requirement"
    DETERMINED_REQUIREMENT = "determined_requirement"
    UNDETERMINED = "undetermined"  # JD present but no structured requirement can be established, not NO_REQUIREMENT


class JobIntelligenceEvidence(BaseModel):
    """Evidence traceability entry explaining where a job fact originated."""
    source: str  # e.g. "jd_text", "job_metadata", "url_parsing"
    confidence: float = 1.0
    origin: JobSourceOrigin = JobSourceOrigin.EXPLICIT_JD
    details: Optional[str] = None


class JobSkillIntelligence(BaseModel):
    """Normalized skill entity with required/preferred classification."""
    name: str
    normalized_name: str
    category: str = "other"
    required: bool = True
    evidence: List[JobIntelligenceEvidence] = Field(default_factory=list)
    confidence: float = 1.0


class JobLocationInfo(BaseModel):
    """Structured location representation."""
    raw: Optional[str] = None
    normalized: Optional[str] = None
    remote_type: str = "unknown"  # remote, hybrid, onsite, unknown
    evidence: List[JobIntelligenceEvidence] = Field(default_factory=list)


class JobCompensationInfo(BaseModel):
    """Structured compensation representation."""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    period: str = "yearly"  # yearly, monthly, hourly
    evidence: List[JobIntelligenceEvidence] = Field(default_factory=list)


class JobTechnologyInfo(BaseModel):
    """Technology stack extracted from job description."""
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    devops: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)


class ATSInfo(BaseModel):
    """ATS/platform detection from URL or job metadata."""
    platform: Optional[str] = None  # greenhouse, lever, ashby, workday, linkedin, other
    application_url: Optional[str] = None
    evidence: List[JobIntelligenceEvidence] = Field(default_factory=list)


class CanonicalJobProfile(BaseModel):
    """Canonical representation of job intelligence."""
    job_id: Optional[int] = None
    title: Optional[str] = None
    normalized_title: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    application_url: Optional[str] = None

    location: Optional[JobLocationInfo] = None

    employment_type: Optional[str] = None  # full-time, part-time, contract, internship
    seniority: Optional[str] = None  # JUNIOR, MID, SENIOR, LEAD, PRINCIPAL
    experience_years: Optional[str] = None  # e.g. "3-5 years"

    compensation: Optional[JobCompensationInfo] = None

    required_skills: List[JobSkillIntelligence] = Field(default_factory=list)
    preferred_skills: List[JobSkillIntelligence] = Field(default_factory=list)
    all_skills_normalized: List[str] = Field(default_factory=list)
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict)

    responsibilities: List[str] = Field(default_factory=list)
    key_requirements: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

    technology: Optional[JobTechnologyInfo] = None

    role_family: Optional[str] = None  # backend, frontend, fullstack, data, devops, etc.
    domain: Optional[str] = None  # fintech, healthtech, saas, ecommerce, etc.
    inferred_seniority: Optional[str] = None
    confidence: float = 0.0
    evidence: List[JobIntelligenceEvidence] = Field(default_factory=list)

    ats: Optional[ATSInfo] = None

    posted_date: Optional[str] = None
    discovered_date: Optional[str] = None

    jd_text_length: int = 0
    has_description: bool = False
    # Provenance per dimension (additive, defaults preserve pre-5B-7 behavior)
    experience_provenance: JobProvenance = JobProvenance.SOURCE_UNAVAILABLE
    role_provenance: JobProvenance = JobProvenance.SOURCE_UNAVAILABLE
    location_provenance: JobProvenance = JobProvenance.SOURCE_UNAVAILABLE
    seniority_provenance: JobProvenance = JobProvenance.SOURCE_UNAVAILABLE
