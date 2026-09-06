"""
Seniority Matcher — Phase 5B-6 Deterministic
=============================================

Pure, no from_years, no target_roles, no fuzzy.
Only EXACT / HIGHER / LOWER / INCOMPARABLE / UNKNOWN.
"""

from __future__ import annotations

from typing import List, Optional

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    RequirementStatus,
    SeniorityAvailability,
    SeniorityEvaluation,
)

ORDER = {"INTERN": 0, "JUNIOR": 1, "MID": 2, "SENIOR": 3, "STAFF": 4, "PRINCIPAL": 5}


class SeniorityMatcher:
    def evaluate(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
    ) -> List[SeniorityEvaluation]:
        req = job.seniority_requirement
        if req is None:
            # No job seniority signal currently? Per correction, None should be AMBIGUOUS but
            # our adapter now always produces AMBIGUOUS for None, so this branch is dead.
            # Keep for backward compat if legacy job has no seniority field.
            return []

        # AMBIGUOUS / UNPARSEABLE / MULTI_LEVEL → UNKNOWN
        if req.kind in ("AMBIGUOUS", "UNPARSEABLE", "MULTI_LEVEL"):
            return [
                SeniorityEvaluation(
                    candidate_raw=candidate.candidate_seniority_raw,
                    candidate_normalized=candidate.candidate_seniority_normalized,
                    candidate_source=candidate.candidate_seniority_source,
                    job_raw=req.raw,
                    job_normalized=req.normalized_level,
                    relationship="UNKNOWN" if req.kind == "AMBIGUOUS" else req.kind,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="job_seniority_" + req.kind.lower(),
                )
            ]

        # Candidate UNDETERMINED → UNKNOWN (covers INFERRED)
        if candidate.seniority_availability != SeniorityAvailability.DETERMINED:
            return [
                SeniorityEvaluation(
                    candidate_raw=candidate.candidate_seniority_raw,
                    candidate_normalized=candidate.candidate_seniority_normalized,
                    candidate_source=candidate.candidate_seniority_source,
                    job_raw=req.raw,
                    job_normalized=req.normalized_level,
                    relationship="UNKNOWN",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="candidate_seniority_unavailable",
                )
            ]

        # Candidate determined but no normalized? Should be UNDETERMINED already, but defensive
        cand_norm = candidate.candidate_seniority_normalized
        job_norm = req.normalized_level
        if not cand_norm or not job_norm:
            return [
                SeniorityEvaluation(
                    candidate_raw=candidate.candidate_seniority_raw,
                    candidate_normalized=cand_norm,
                    candidate_source=candidate.candidate_seniority_source,
                    job_raw=req.raw,
                    job_normalized=job_norm,
                    relationship="UNKNOWN",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="seniority_missing_normalized",
                )
            ]

        # Incomparable check: if either not in ORDER (should not happen for STRUCTURED, but defensive)
        if cand_norm not in ORDER or job_norm not in ORDER:
            return [
                SeniorityEvaluation(
                    candidate_raw=candidate.candidate_seniority_raw,
                    candidate_normalized=cand_norm,
                    candidate_source=candidate.candidate_seniority_source,
                    job_raw=req.raw,
                    job_normalized=job_norm,
                    relationship="INCOMPARABLE",
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="seniority_incomparable",
                )
            ]

        cand_rank = ORDER[cand_norm]
        job_rank = ORDER[job_norm]
        if cand_rank == job_rank:
            rel = "EXACT"
            status = RequirementStatus.SATISFIED
        elif cand_rank > job_rank:
            rel = "HIGHER_THAN_REQUIRED"
            status = RequirementStatus.SATISFIED
        else:
            rel = "LOWER_THAN_REQUIRED"
            status = RequirementStatus.MISSING

        return [
            SeniorityEvaluation(
                candidate_raw=candidate.candidate_seniority_raw,
                candidate_normalized=cand_norm,
                candidate_source=candidate.candidate_seniority_source,
                job_raw=req.raw,
                job_normalized=job_norm,
                relationship=rel,
                status=status,
                evidence_source="explicit_seniority",
            )
        ]


_matcher: Optional[SeniorityMatcher] = None


def get_seniority_matcher() -> SeniorityMatcher:
    global _matcher
    if _matcher is None:
        _matcher = SeniorityMatcher()
    return _matcher
