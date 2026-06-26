"""
Core domain models for Applyr AI job application platform.

This module defines the data structures used throughout the application,
ensuring type safety and consistency across all services.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class Status(str, Enum):
    """Application status enum."""
    DISCOVERED = "discovered"
    SCORED = "scored"
    TAILOR = "tailor"
    RECRUITER_FOUND = "recruiter_found"
    DRAFTED = "drafted"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    DELIVERED = "delivered"
    RESPONDED = "responded"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class Source(str, Enum):
    """Job source enum."""
    LINKEDIN = "linkedin"
    INTERNSHALA = "internshala"
    NAUKRI = "naukri"
    WELLFOUND = "wellfound"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    FOUNDIT = "foundit"
    CUTSHORT = "cutshort"
    INSTAHYRE = "instahyre"
    HIRIST = "hirist"
    UNSTOP = "unstop"
    YCOMBINATOR = "ycombinator"
    OTTA = "otta"
    WORKATSTARTUP = "workatastartup"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"
    REMOTIVE = "remotive"
    FLEXJOBS = "flexjobs"
    ANGELO = "angel.co"
    STARTUP_JOBS = "startup.jobs"
    JOIN = "join.com"
    JOBS_TOGETHER = "jobs.together"
    CORD = "cord.co"
    AI_JOBS = "aijobs.net"
    AI_JOBS_NET = "ai-jobs.net"
    MACHINE_LEARNING_JOBS = "machinelearningjobs.com"
    DATA_SCIENCE_JOBS = "datasciencejobs.com"
    DEVS_JOBS_SCIENCE = "devjobs.science"
    HIMALAYAS_APP = "himalayas.app"
    GETRO = "getro.com"
    LEVELS_FYI_JOBS = "levels.fyi/jobs"
    JOBS_NETFLIX = "jobs.netflix.com"
    CAREERS_GOOGLE = "careers.google.com"
    AMAZON_JOBS = "amazon.jobs"
    JOBS_MICROSOFT = "jobs.careers.microsoft.com"
    CAREERS_META = "careers.meta.com"
    CAREERS_IBM = "careers.ibm.com"
    CAREERS_ORACLE = "careers.oracle.com"
    CAREERS_ADOBE = "careers.adobe.com"
    CAREERS_SALESFORCE = "careers.salesforce.com"
    CAREERS_INTUIT = "careers.intuit.com"
    CAREERS_ATLASSIAN = "careers.atlassian.com"
    CAREERS_AIRBNB = "careers.airbnb.com"
    CAREERS_UBER = "careers.uber.com"
    CAREERS_LYFT = "careers.lyft.com"
    CAREERS_STRIPE = "careers.stripe.com"
    CAREERS_DATABRICKS = "careers.databricks.com"
    CAREERS_SNOWFLAKE = "careers.snowflake.com"
    CAREERS_NVIDIA = "careers.nvidia.com"
    CAREERS_TESLA = "careers.tesla.com"
    CAREERS_PALANTIR = "careers.palantir.com"
    CAREERS_HUBSPOT = "careers.hubspot.com"
    CAREERS_ZOMATO = "careers.zomato.com"
    CAREERS_SWIGGY = "careers.swiggy.com"
    CAREERS_RAZORPAY = "careers.razorpay.com"
    CAREERS_CRED = "careers.cred.club"
    CAREERS_ZERODHA = "careers.zerodha.com"
    CAREERS_PHONEPE = "careers.phonepe.com"
    CAREERS_PAYTM = "careers.paytm.com"
    CAREERS_FLIPKART = "careers.flipkart.com"
    CAREERS_MEESHO = "careers.meesho.com"
    CAREERS_GROWW = "careers.groww.in"
    CAREERS_URBANCOMPANY = "careers.urbancompany.com"


class RecruiterSource(str, Enum):
    """Recruiter discovery source enum."""
    HUNTER = "hunter"
    CLEARBIT = "clearbit"
    APOLLO = "apollo"


class ApplicationStage(str, Enum):
    """Application tracker status enum."""
    SAVED = "saved"
    TAILORED = "tailored"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


class EmailProvider(str, Enum):
    """Email provider enum."""
    RESEND = "resend"
    GMAIL = "gmail"


class FieldEvidence(BaseModel):
    """Evidence for a parsed field — value, source, confidence."""
    value: Any
    source: str
    confidence: float


class ParserEvidence(BaseModel):
    """Parser evidence for all resume fields."""
    fields: Dict[str, FieldEvidence] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    sections_detected: List[str] = Field(default_factory=list)
    name: Optional[FieldEvidence] = None
    email: Optional[FieldEvidence] = None
    phone: Optional[FieldEvidence] = None
    skills: Optional[FieldEvidence] = None
    experience: Optional[FieldEvidence] = None
    projects: Optional[FieldEvidence] = None
    education: Optional[FieldEvidence] = None
    certifications: Optional[FieldEvidence] = None
    roles: Optional[FieldEvidence] = None


class Resume(BaseModel):
    """Resume model representing parsed resume data with evidence tracking."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    skills_categorized: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    scored_roles: List[Dict[str, Any]] = Field(default_factory=list)
    quality_score: float = 0.0
    quality_breakdown: Dict[str, Any] = Field(default_factory=dict)
    total_pages: int = 0
    sections_detected: List[str] = Field(default_factory=list)
    sections_missing: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: Optional[ParserEvidence] = None
    parse_log: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
    source_path: Optional[str] = None
    parsed_at: Optional[str] = None

    @validator('skills', pre=True)
    def ensure_skills_list(cls, v):
        if v is None:
            return []
        return v

    @validator('experience', pre=True)
    def ensure_experience_list(cls, v):
        if v is None:
            return []
        return v

    @validator('projects', pre=True)
    def ensure_projects_list(cls, v):
        if v is None:
            return []
        return v

    @validator('education', pre=True)
    def ensure_education_list(cls, v):
        if v is None:
            return []
        return v

    @validator('certifications', pre=True)
    def ensure_certifications_list(cls, v):
        if v is None:
            return []
        if v and isinstance(v[0], dict):
            return [d.get("name") or json.dumps(d) for d in v]
        return v

    @validator('roles', pre=True)
    def ensure_roles_list(cls, v):
        if v is None:
            return []
        return v

    @validator('sections_detected', pre=True)
    def ensure_sections_detected_list(cls, v):
        if v is None:
            return []
        return v

    @validator('sections_missing', pre=True)
    def ensure_sections_missing_list(cls, v):
        if v is None:
            return []
        return v

    @validator('parse_log', pre=True)
    def ensure_parse_log_list(cls, v):
        if v is None:
            return []
        return v


class Profile(BaseModel):
    """Profile model representing user profile and preferences."""
    inferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    seniority: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    remote_ok: bool = False
    personal: Dict[str, Any] = Field(default_factory=dict)
    skills: Dict[str, List[str]] = Field(default_factory=dict)

    @validator('inferred_roles', pre=True)
    def ensure_inferred_roles_list(cls, v):
        if v is None:
            return []
        return v

    @validator('preferred_locations', pre=True)
    def ensure_preferred_locations_list(cls, v):
        if v is None:
            return []
        return v

    @validator('keywords', pre=True)
    def ensure_keywords_list(cls, v):
        if v is None:
            return []
        return v

    @validator('target_roles', pre=True)
    def ensure_target_roles_list(cls, v):
        if v is None:
            return []
        return v

    @validator('target_locations', pre=True)
    def ensure_target_locations_list(cls, v):
        if v is None:
            return []
        return v

    @validator('skills', pre=True)
    def ensure_skills_dict(cls, v):
        if v is None:
            return {}
        return v


class Job(BaseModel):
    """Job model representing a job listing."""
    id: Optional[int] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None
    hr_email: Optional[str] = None
    description_snippet: Optional[str] = None
    jd_text: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    fit_score: int = 0
    status: str = Status.DISCOVERED
    scraped_at: Optional[str] = None
    applied_at: Optional[str] = None
    cover_letter_path: Optional[str] = None
    tailored_resume_path: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    match_details_json: Optional[str] = None

    @validator('required_skills', pre=True)
    def ensure_required_skills_list(cls, v):
        if v is None:
            return []
        return v


class Recruiter(BaseModel):
    """Recruiter model representing a recruiter contact."""
    id: Optional[int] = None
    company: Optional[str] = None
    job_id: Optional[int] = None
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    confidence: int = 0
    source: Optional[str] = None
    linkedin: Optional[str] = None
    contact_type: Optional[str] = None
    rank_score: int = 0
    discovered_at: Optional[str] = None


class StartupCompany(BaseModel):
    """Startup discovery result used for ranking remote-first companies."""
    id: Optional[int] = None
    company: Optional[str] = None
    domain: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    job_count: int = 0
    resume_match_score: int = 0
    role_match_score: int = 0
    tech_stack_match: int = 0
    experience_match: int = 0
    remote_compatibility: int = 0
    overall_score: int = 0
    matched_roles: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    rank_reason: Optional[str] = None
    careers_page_url: Optional[str] = None
    discovered_at: Optional[str] = None


class ApplicationTracker(BaseModel):
    """Application tracker entry."""
    id: Optional[int] = None
    company: Optional[str] = None
    role: Optional[str] = None
    job_url: Optional[str] = None
    source: Optional[str] = None
    date_applied: Optional[str] = None
    referral_contact: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    email_status: str = "pending"
    application_status: str = ApplicationStage.SAVED
    follow_up_date: Optional[str] = None
    second_follow_up_date: Optional[str] = None
    notes: Optional[str] = None
    ats_before: int = 0
    ats_after: int = 0
    careers_page_url: Optional[str] = None
    linkedin_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Email(BaseModel):
    """Email model representing an email draft or sent message."""
    id: Optional[int] = None
    job_id: Optional[int] = None
    hr_email: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    status: str = "drafted"
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class Application(BaseModel):
    """Application model representing a job application."""
    id: Optional[int] = None
    job_id: Optional[int] = None
    title: Optional[str] = None
    company: Optional[str] = None
    fit_score: int = 0
    status: str = Status.DISCOVERED
    email_to: Optional[str] = None
    subject: Optional[str] = None
    applied_at: Optional[str] = None
    tailored_resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None


class PipelineRun(BaseModel):
    """Pipeline run model representing a pipeline execution."""
    run_id: str
    triggered_by: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    jobs_found: int = 0
    jobs_filtered: int = 0
    applications_drafted: int = 0
    jobs_applied: int = 0
    applications_submitted: int = 0
    emails_drafted: int = 0
    emails_sent: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    status: str = "pending"
    applications: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None


class SearchStrategy(BaseModel):
    """Search strategy model representing the search configuration."""
    roles: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    query: Optional[str] = None
    source: Optional[str] = None


class Company(BaseModel):
    """Company model representing a company."""
    name: Optional[str] = None
    domain: Optional[str] = None
    extraction_confidence: float = 0.0
    enriched: bool = False
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class PipelineEvent(BaseModel):
    """Pipeline event model representing a pipeline event."""
    event_id: str
    event_type: str
    timestamp: str
    run_id: str
    data: Dict[str, Any]
    source: str


class SystemHealth(BaseModel):
    """System health model representing system health status."""
    groq: Dict[str, Any] = Field(default_factory=dict)
    gemini: Dict[str, Any] = Field(default_factory=dict)
    tavily: Dict[str, Any] = Field(default_factory=dict)
    scrapingbee: Dict[str, Any] = Field(default_factory=dict)
    hunter: Dict[str, Any] = Field(default_factory=dict)
    clearbit: Dict[str, Any] = Field(default_factory=dict)
    resume_parser: Dict[str, Any] = Field(default_factory=dict)
    email: Dict[str, Any] = Field(default_factory=dict)
    recruiter_discovery: Dict[str, Any] = Field(default_factory=dict)


class SeniorityLevel(str, Enum):
    """Seniority level enum for both candidate and job."""
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"

    def __lt__(self, other):
        levels = list(SeniorityLevel)
        return levels.index(self) < levels.index(other)

    def __le__(self, other):
        levels = list(SeniorityLevel)
        return levels.index(self) <= levels.index(other)

    def __gt__(self, other):
        levels = list(SeniorityLevel)
        return levels.index(self) > levels.index(other)

    def __ge__(self, other):
        levels = list(SeniorityLevel)
        return levels.index(self) >= levels.index(other)

    @classmethod
    def from_years(cls, years: float) -> "SeniorityLevel":
        if years < 0.5:
            return cls.INTERN
        elif years < 2:
            return cls.JUNIOR
        elif years < 5:
            return cls.MID
        elif years < 8:
            return cls.SENIOR
        elif years < 12:
            return cls.STAFF
        else:
            return cls.PRINCIPAL

    @classmethod
    def detect_from_title(cls, title: str) -> Optional["SeniorityLevel"]:
        if not title:
            return None
        t = title.lower()
        if "principal" in t or "staff" in t:
            return cls.PRINCIPAL if "principal" in t else cls.STAFF
        if "senior" in t or "sr" in t.replace(".", "").split():
            return cls.SENIOR
        if "mid" in t or "level 2" in t or "ii" in t.split():
            return cls.MID
        if "junior" in t or "jr" in t.replace(".", "").split() or "entry" in t:
            return cls.JUNIOR
        if "intern" in t:
            return cls.INTERN
        return None

    @classmethod
    def penalty(cls, candidate: Optional["SeniorityLevel"], job: Optional["SeniorityLevel"]) -> int:
        """Penalty when job seniority exceeds candidate level. Returns 0-50 points."""
        if not candidate or not job:
            return 0
        if job > candidate:
            levels = list(cls)
            gap = levels.index(job) - levels.index(candidate)
            # 10 points per level gap, max 50
            return min(gap * 10, 50)
        return 0


class MatchComponent(BaseModel):
    """A single component of a job match analysis."""
    score: float = 0.0
    max_score: float = 100.0
    weight: float = 0.0
    weighted_score: float = 0.0
    label: str = ""
    details: List[str] = Field(default_factory=list)
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class MatchAnalysis(BaseModel):
    """Unified match analysis — single source of truth for scoring, recommendation, and UI."""
    job_id: int = 0
    candidate_name: Optional[str] = None

    skill_match: MatchComponent = Field(default_factory=lambda: MatchComponent(weight=0.40, label="Skills Match", max_score=100))
    experience_match: MatchComponent = Field(default_factory=lambda: MatchComponent(weight=0.25, label="Experience Match", max_score=100))
    role_match: MatchComponent = Field(default_factory=lambda: MatchComponent(weight=0.20, label="Role Match", max_score=100))
    location_match: MatchComponent = Field(default_factory=lambda: MatchComponent(weight=0.10, label="Location Match", max_score=100))
    seniority_match: MatchComponent = Field(default_factory=lambda: MatchComponent(weight=0.05, label="Seniority Match", max_score=100))

    final_score: float = 0.0
    recommendation: str = "Skip"
    all_required_skills: List[str] = Field(default_factory=list)
    skills_to_highlight: List[str] = Field(default_factory=list)

    candidate_seniority: Optional[str] = None
    job_seniority: Optional[str] = None
    seniority_penalty: int = 0
    estimated_experience_years: float = 0.0

    explanation: str = ""
    why_this_score: str = ""
    matched_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)

    analyzed_at: str = ""


# Export all models for easy import
__all__ = [
    "Status",
    "Source",
    "RecruiterSource",
    "ApplicationStage",
    "EmailProvider",
    "FieldEvidence",
    "ParserEvidence",
    "Resume",
    "Profile",
    "Profile",
    "Job",
    "Recruiter",
    "StartupCompany",
    "ApplicationTracker",
    "Email",
    "Application",
    "PipelineRun",
    "SearchStrategy",
    "Company",
    "PipelineEvent",
    "SystemHealth",
    "SeniorityLevel",
    "MatchComponent",
    "MatchAnalysis",
]