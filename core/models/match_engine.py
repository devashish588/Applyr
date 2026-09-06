"""
Match Engine 2.0 — Canonical Models & Contracts (Phase 5B-1)
=============================================================

Structural foundation for Match Engine 2.0.

This module defines the canonical contracts specified by the approved
Phase 5A design. It implements ONLY structural models:

- SkillInventoryStatus (DETERMINED / UNDETERMINED)
- RequirementStatus (SATISFIED / PARTIALLY_SATISFIED / MISSING / UNKNOWN)
- SkillRelationshipType (EXACT / ALIAS / TRANSFERABLE / RELATED / NONE)
- CanonicalCandidateInput (adapter output for candidate data)
- CanonicalJobRequirement (structured job requirement)
- CanonicalJobInput (adapter output for job data)
- RequirementEvaluation (per-requirement evaluation result)
- MatchResult (composition-based result wrapping MatchAnalysis)

NO matching logic, scoring, ranking, or evaluation is implemented.
MatchService remains the sole authoritative numerical scorer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from core.models import MatchAnalysis  # noqa: F401 — re-exported for type resolution; no circular import (verified: __init__.py does not import match_engine.py)


# ---------------------------------------------------------------------------
# ExperienceAvailability — honest provenance for experience (5B-3)
# ---------------------------------------------------------------------------

class ExperienceAvailability(str, Enum):
    """Experience provenance — honest, not skill-confidence-derived.

    DETERMINED: trustworthy experience extraction completed, value structurally
        valid, 0.0 allowed as authoritative zero.
    UNDETERMINED: source unavailable, extraction failed, invalid/untrustworthy,
        mandatory stage failed. Current architecture cannot yet reliably
        distinguish DETERMINED 0 from UNDETERMINED empty via adapter alone
        (see design); unit tests use directly constructed DETERMINED inputs,
        adapter integration for DETERMINED 0 is deferred until provenance field
        lands on CanonicalCandidateProfile.
    """
    DETERMINED = "determined"
    UNDETERMINED = "undetermined"


class RoleAvailability(str, Enum):
    """Role provenance — DETERMINED includes valid empty inventory; UNDETERMINED is unavailable/failed."""
    DETERMINED = "determined"
    UNDETERMINED = "undetermined"


class SeniorityAvailability(str, Enum):
    """Seniority provenance — only EXPLICIT_USER is DETERMINED (no INFERRED)."""
    DETERMINED = "determined"
    UNDETERMINED = "undetermined"


class SeniorityLevel(str, Enum):
    """IC seniority taxonomy — repository-backed only."""
    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    STAFF = "STAFF"
    PRINCIPAL = "PRINCIPAL"


class LocationAvailability(str, Enum):
    """Location provenance — honest, not inferred."""
    DETERMINED = "determined"
    UNDETERMINED = "undetermined"


class LocationRelationshipType(str, Enum):
    """EXACT > CITY_ALIAS > REMOTE_COMPATIBLE > NONE"""
    EXACT = "exact"
    CITY_ALIAS = "city_alias"
    REMOTE_COMPATIBLE = "remote_compatible"
    NONE = "none"


# ---------------------------------------------------------------------------
# §1.1 — SkillInventoryStatus
# ---------------------------------------------------------------------------

class SkillInventoryStatus(str, Enum):
    """Inventory determination status.

    DETERMINED means the skill extraction pipeline successfully:
      1. Obtained and parsed source data
      2. Completed extraction without exception/timeout
      3. Completed normalization/validation
      4. Produced a valid, intentional inventory result

    The resulting inventory MAY legitimately be empty ([]).
    An empty DETERMINED inventory is authoritative absence.

    UNDETERMINED means the inventory could not be reliably determined
    (source unavailable, parse failure, extraction failure, timeout,
    validation failure, unreliable result, incomplete processing).
    Any skills associated with an UNDETERMINED inventory are
    non-authoritative and MUST NOT be treated as canonical.
    """
    DETERMINED = "determined"
    UNDETERMINED = "undetermined"


# ---------------------------------------------------------------------------
# §1.4 — RequirementStatus
# ---------------------------------------------------------------------------

class RequirementStatus(str, Enum):
    """Requirement satisfaction state.

    SATISFIED:             Exact or alias match found in candidate inventory.
    PARTIALLY_SATISFIED:   Transferable skill found (partial credit).
    MISSING:               DETERMINED inventory, skill absent (no credit).
    UNKNOWN:               UNDETERMINED inventory, cannot evaluate.
    """
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    MISSING = "missing"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# §1.5 — SkillRelationshipType
# ---------------------------------------------------------------------------

class SkillRelationshipType(str, Enum):
    """Relationship between a candidate skill and a job requirement.

    Hierarchy (best to worst):
        EXACT > ALIAS > TRANSFERABLE > RELATED > NONE

    Exact:        canonical values equal AND raw values identical (case-sensitive).
    Alias:        canonical values equal AND raw values differ (case-sensitive).
    Transferable: different canonical skill, but directly transferable.
    Related:      related technology — informational only, no numerical credit.
    None:         no relationship found.
    """
    EXACT = "exact"
    ALIAS = "alias"
    TRANSFERABLE = "transferable"
    RELATED = "related"
    NONE = "none"

    def __lt__(self, other: "SkillRelationshipType") -> bool:
        order = list(SkillRelationshipType)
        return order.index(self) > order.index(other)  # lower index = better

    def __le__(self, other: "SkillRelationshipType") -> bool:
        order = list(SkillRelationshipType)
        return order.index(self) >= order.index(other)

    def __gt__(self, other: "SkillRelationshipType") -> bool:
        order = list(SkillRelationshipType)
        return order.index(self) < order.index(other)

    def __ge__(self, other: "SkillRelationshipType") -> bool:
        order = list(SkillRelationshipType)
        return order.index(self) <= order.index(other)


# ---------------------------------------------------------------------------
# §1.4 — CanonicalCandidateInput
# ---------------------------------------------------------------------------

class CanonicalCandidateInput(BaseModel):
    """Adapter output consumed by the Match Engine 2.0 evaluator.

    Produced by CandidateAdapter from CanonicalCandidateProfile (Phase 3).

    The skill_inventory_status determines whether skill_inventory
    is authoritative:
      - DETERMINED + [skills]  → authoritative, evaluate each requirement (5B-2+)
      - DETERMINED + []        → authoritative empty, every requirement → MISSING
      - UNDETERMINED + [...]   → non-authoritative, every requirement → UNKNOWN
      - UNDETERMINED + []      → unknown, every requirement → UNKNOWN

    Invariant — skill_inventory ↔ skill_inventory_raw:
      Both lists are generated from the same canonical skill sequence
      (CandidateAdapter iterates profile.skills once, appending
      normalized_name → skill_inventory and name → skill_inventory_raw
      in the same order). Therefore len(skill_inventory) ==
      len(skill_inventory_raw) and indexes correspond by construction.
      No additional runtime validation is required in 5B-1; the adapter
      is the single writer and guarantees correspondence.
    """
    skill_inventory_status: SkillInventoryStatus
    skill_inventory: List[str] = Field(default_factory=list)

    # Raw skill names preserving original case for exact vs alias distinction
    # Index-corresponds with skill_inventory; same length, same order.
    skill_inventory_raw: List[str] = Field(default_factory=list)

    seniority: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: str = "any"
    experience_years: float = 0.0
    experience_availability: ExperienceAvailability = ExperienceAvailability.UNDETERMINED

    # Role — authoritative evidence is experience[].title + current_role; target_roles is non-authoritative
    role_availability: RoleAvailability = RoleAvailability.UNDETERMINED
    role_entries: List["RoleEntry"] = Field(default_factory=list)  # authoritative, deduplicated, raw+normalized

    # Location — candidate_location_entries preserve raw+city+normalized; location_availability honest
    location_availability: LocationAvailability = LocationAvailability.UNDETERMINED
    candidate_location_entries: List["CandidateLocationEntry"] = Field(default_factory=list)

    # Seniority — only EXPLICIT_USER is DETERMINED (no INFERRED)
    seniority_availability: SeniorityAvailability = SeniorityAvailability.UNDETERMINED
    candidate_seniority_raw: Optional[str] = None
    candidate_seniority_normalized: Optional[str] = None
    candidate_seniority_source: Optional[str] = None  # explicit_seniority

    candidate_name: Optional[str] = None
    candidate_id: str = "primary_candidate"


class RoleEntry(BaseModel):
    """Authoritative candidate role entry — raw + normalized, deduplicated."""
    raw: str
    normalized: str
    is_current: bool = False


class RoleRelationshipType(str, Enum):
    """EXACT > ALIAS > TRANSFERABLE > NONE — RELATED deferred, no credit."""
    EXACT = "exact"
    ALIAS = "alias"
    TRANSFERABLE = "transferable"
    NONE = "none"


class StructuredRoleRequirement(BaseModel):
    """Job role requirement — STRUCTURED vs UNPARSEABLE."""
    raw: Optional[str] = None
    normalized: Optional[str] = None
    role_family: Optional[str] = None
    required: bool = True
    kind: str = "STRUCTURED"  # STRUCTURED | UNPARSEABLE


class RoleEvaluation(BaseModel):
    """Deterministic role evaluation — only SATISFIED / MISSING / UNKNOWN."""
    candidate_raw: Optional[str] = None
    candidate_normalized: Optional[str] = None
    job_raw: Optional[str] = None
    job_normalized: Optional[str] = None
    job_role_family: Optional[str] = None
    relationship: RoleRelationshipType = RoleRelationshipType.NONE
    status: RequirementStatus  # SATISFIED | MISSING | UNKNOWN (never PARTIALLY_SATISFIED)
    is_current_role: Optional[bool] = None
    evidence_source: Optional[str] = None


class CandidateLocationEntry(BaseModel):
    """Candidate location entry — raw + city + normalized, with preferred flag."""
    raw: str
    city: Optional[str] = None
    normalized_city: Optional[str] = None
    is_preferred: bool = False


class StructuredLocationRequirement(BaseModel):
    """Job location requirement — cities + remote_type."""
    raw: Optional[str] = None
    cities: List[str] = Field(default_factory=list)  # city components before normalization
    normalized_cities: List[str] = Field(default_factory=list)  # after normalize_city
    remote_type: str = "unknown"  # remote/hybrid/onsite/unknown
    kind: str = "STRUCTURED"  # STRUCTURED | UNPARSEABLE
    required: bool = True


class LocationEvaluation(BaseModel):
    """Deterministic location evaluation — SATISFIED / MISSING / UNKNOWN only."""
    candidate_raw: Optional[str] = None
    candidate_city: Optional[str] = None
    candidate_normalized_city: Optional[str] = None
    job_raw: Optional[str] = None
    job_city: Optional[str] = None
    job_normalized_city: Optional[str] = None
    job_remote_type: Optional[str] = None
    relationship: LocationRelationshipType = LocationRelationshipType.NONE
    status: RequirementStatus
    evidence_source: Optional[str] = None


# ---------------------------------------------------------------------------
# Canonical Job Requirement & Input
# ---------------------------------------------------------------------------

class CanonicalJobRequirement(BaseModel):
    """A single structured job requirement.

    Represents a skill or qualification required by the job.
    The raw_name preserves the original casing from the JD.
    The canonical_name is the normalized form for matching.
    """
    raw_name: str
    canonical_name: str
    required: bool = True  # True = required, False = preferred/nice-to-have
    category: str = "other"


class StructuredSeniorityRequirement(BaseModel):
    """Job seniority requirement — STRUCTURED vs UNPARSEABLE vs MULTI_LEVEL vs AMBIGUOUS."""
    raw: Optional[str] = None
    normalized_level: Optional[str] = None  # one of SeniorityLevel values or None
    required: bool = True
    kind: str = "STRUCTURED"  # STRUCTURED | UNPARSEABLE | MULTI_LEVEL | AMBIGUOUS


class SeniorityEvaluation(BaseModel):
    """Per-seniority evaluation — SATISFIED / MISSING / UNKNOWN only."""
    candidate_raw: Optional[str] = None
    candidate_normalized: Optional[str] = None
    candidate_source: Optional[str] = None  # explicit_seniority
    job_raw: Optional[str] = None
    job_normalized: Optional[str] = None
    relationship: str = "NONE"  # EXACT | HIGHER_THAN_REQUIRED | LOWER_THAN_REQUIRED | INCOMPARABLE | NONE | AMBIGUOUS
    status: RequirementStatus
    evidence_source: Optional[str] = None


class StructuredExperienceRequirement(BaseModel):
    """Structured experience requirement derived from CanonicalJobProfile.experience_years.

    Produced by JobAdapter from Job Intelligence; consumed by ExperienceMatcher.
    Job Intelligence owns parsing (EXPERIENCE_PATTERNS); adapter only translates.
    """
    raw: str
    min_years: Optional[float] = None
    max_years: Optional[float] = None
    kind: str = "MINIMUM"  # MINIMUM | RANGE | MAXIMUM
    inclusive_max: bool = True
    required: bool = True


class ExperienceEvaluation(BaseModel):
    """Per-experience-requirement evaluation (5B-3, no PARTIALLY_SATISFIED)."""
    requirement: StructuredExperienceRequirement
    candidate_years: Optional[float] = None
    candidate_evidence: Optional[str] = None
    status: RequirementStatus  # SATISFIED | MISSING | UNKNOWN only for experience path
    evidence_source: Optional[str] = None  # e.g., "candidate_experience" / "job_intelligence"


class CanonicalJobInput(BaseModel):
    """Adapter output for job data consumed by Match Engine 2.0.

    Produced by JobAdapter from CanonicalJobProfile (Phase 4)
    or from the existing Job model.
    """
    job_id: Optional[int] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    jd_text: Optional[str] = None

    requirements: List[CanonicalJobRequirement] = Field(default_factory=list)
    experience_requirement: Optional[StructuredExperienceRequirement] = None
    role_requirement: Optional[StructuredRoleRequirement] = None
    location_requirement: Optional[StructuredLocationRequirement] = None
    seniority_requirement: Optional[StructuredSeniorityRequirement] = None


# ---------------------------------------------------------------------------
# §1.4 / §3 — RequirementEvaluation
# ---------------------------------------------------------------------------

class RequirementEvaluation(BaseModel):
    """Per-requirement evaluation result.

    Records the evaluation of a single job requirement against
    the candidate's skill inventory.

    If skill_inventory_status is UNDETERMINED, status MUST be UNKNOWN
    regardless of matched_skill or relationship_type.

    matched_skill is the canonical candidate skill that yielded the best
    relationship. matched_skill_raw is the raw candidate skill that yielded
    it — required to distinguish EXACT (raw == job raw, case-sensitive)
    from ALIAS (raw != job raw) without re-reading input arrays.
    """
    requirement: CanonicalJobRequirement
    status: RequirementStatus
    relationship_type: SkillRelationshipType = SkillRelationshipType.NONE
    matched_skill: Optional[str] = None  # The candidate skill that matched (canonical)
    matched_skill_raw: Optional[str] = None  # Raw candidate skill that yielded the relationship
    related_skills: List[str] = Field(default_factory=list)  # Informational only


# ---------------------------------------------------------------------------
# §3 — MatchResult (composition-based)
# ---------------------------------------------------------------------------

class MatchResult(BaseModel):
    """Composition-based result aggregating requirement evaluations.

    This does NOT replace MatchAnalysis from MatchService.
    MatchService remains the sole authoritative numerical scorer.

    MatchResult wraps the baseline MatchAnalysis and adds
    Match Engine 2.0 structured analysis / evidence / gaps.

    analysis_completeness and match_confidence do NOT change
    the authoritative MatchService final_score.
    """
    # Baseline — preserved from MatchService (strongly typed, not Any)
    baseline_analysis: Optional[MatchAnalysis] = None

    # Match Engine 2.0 analysis
    inventory_status: SkillInventoryStatus = SkillInventoryStatus.UNDETERMINED
    requirement_evaluations: List[RequirementEvaluation] = Field(default_factory=list)
    experience_evaluations: List[ExperienceEvaluation] = Field(default_factory=list)
    role_evaluations: List[RoleEvaluation] = Field(default_factory=list)
    location_evaluations: List[LocationEvaluation] = Field(default_factory=list)
    seniority_evaluations: List[SeniorityEvaluation] = Field(default_factory=list)

    # Metadata (informational — does NOT affect MatchService final_score)
    analysis_completeness: float = 0.0
    data_completeness: float = 0.0
    match_confidence: float = 0.0

    # Gaps / evidence
    satisfied_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    unknown_requirements: List[str] = Field(default_factory=list)
    partial_requirements: List[str] = Field(default_factory=list)

    # Engine metadata
    engine_version: str = "2.1.0-skill-matcher"
    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
