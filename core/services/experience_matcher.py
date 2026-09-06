"""
Experience Matcher — Phase 5B-3 Deterministic Experience Matching
=================================================================

Pure, deterministic, evidence-based experience matching.

Produces only SATISFIED / MISSING / UNKNOWN (never PARTIALLY_SATISFIED).
No EXPERIENCE_PATTERNS, no regex parsing — consumes StructuredExperienceRequirement.
Integer months internally: months = round(years * 12).
"""

from __future__ import annotations

import math
from typing import List, Optional

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    ExperienceAvailability,
    ExperienceEvaluation,
    RequirementStatus,
    StructuredExperienceRequirement,
)


def _to_months(years: Optional[float]) -> Optional[int]:
    if years is None:
        return None
    if not isinstance(years, (int, float)) or not math.isfinite(years):
        return None
    if years < 0:
        return None
    return int(round(float(years) * 12))


class ExperienceMatcher:
    """Deterministic experience matcher. No PARTIALLY_SATISFIED."""

    def evaluate(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
    ) -> List[ExperienceEvaluation]:
        req = job.experience_requirement
        if req is None:
            return []

        # Candidate availability gate
        if candidate.experience_availability != ExperienceAvailability.DETERMINED:
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=None,
                    candidate_evidence=None,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="candidate_experience_unavailable",
                )
            ]

        # Validate candidate value
        c_years = candidate.experience_years
        if not isinstance(c_years, (int, float)) or not math.isfinite(c_years) or c_years < 0:
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=None,
                    candidate_evidence=None,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="candidate_experience_invalid",
                )
            ]

        # Validate requirement — UNPARSEABLE from JobAdapter → UNKNOWN (BLOCKER 1)
        if req.kind == "UNPARSEABLE":
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=c_years,
                    candidate_evidence=f"DETERMINED {c_years} years",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="requirement_unparseable",
                )
            ]
        if req.min_years is not None and (not math.isfinite(req.min_years) or req.min_years < 0):
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=c_years,
                    candidate_evidence=f"DETERMINED {c_years} years",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="requirement_invalid",
                )
            ]
        if req.max_years is not None and (not math.isfinite(req.max_years) or req.max_years < 0):
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=c_years,
                    candidate_evidence=f"DETERMINED {c_years} years",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="requirement_invalid",
                )
            ]
        if req.min_years is not None and req.max_years is not None and req.min_years > req.max_years:
            return [
                ExperienceEvaluation(
                    requirement=req,
                    candidate_years=c_years,
                    candidate_evidence=f"DETERMINED {c_years} years",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="requirement_invalid_min_gt_max",
                )
            ]

        # Months-based comparison
        c_months = _to_months(c_years)
        min_months = _to_months(req.min_years) if req.min_years is not None else None
        max_months = _to_months(req.max_years) if req.max_years is not None else None

        if c_months is None:
            status = RequirementStatus.UNKNOWN
        else:
            # Kind-aware comparison
            if req.kind == "MINIMUM":
                # raw "2 years" is MINIMUM per product policy
                status = RequirementStatus.SATISFIED if c_months >= min_months else RequirementStatus.MISSING
            elif req.kind == "MAXIMUM":
                if req.inclusive_max:
                    status = RequirementStatus.SATISFIED if c_months <= max_months else RequirementStatus.MISSING
                else:
                    status = RequirementStatus.SATISFIED if c_months < max_months else RequirementStatus.MISSING
            elif req.kind == "RANGE":
                # inclusive on both ends for RANGE
                if c_months < min_months:
                    status = RequirementStatus.MISSING
                elif c_months > max_months:
                    status = RequirementStatus.MISSING
                else:
                    status = RequirementStatus.SATISFIED
            else:
                status = RequirementStatus.UNKNOWN

        # Never emit PARTIALLY_SATISFIED
        assert status != RequirementStatus.PARTIALLY_SATISFIED

        return [
            ExperienceEvaluation(
                requirement=req,
                candidate_years=c_years,
                candidate_evidence=f"DETERMINED {c_years} years",
                status=status,
                evidence_source="candidate_experience",
            )
        ]


_exp_matcher: Optional[ExperienceMatcher] = None


def get_experience_matcher() -> ExperienceMatcher:
    global _exp_matcher
    if _exp_matcher is None:
        _exp_matcher = ExperienceMatcher()
    return _exp_matcher
