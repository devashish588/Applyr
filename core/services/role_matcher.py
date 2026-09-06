"""
Role Matcher — Phase 5B-4 Deterministic Role Matching
======================================================

Pure, deterministic, conservative. No LLM/fuzzy/API.
Precedence: EXACT > ALIAS > TRANSFERABLE > NONE (RELATED deferred).
Only SATISFIED / MISSING / UNKNOWN (no PARTIALLY_SATISFIED).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    RequirementStatus,
    RoleAvailability,
    RoleEntry,
    RoleEvaluation,
    RoleRelationshipType,
    StructuredRoleRequirement,
)

# Small curated alias map — normalized exact membership
ROLE_ALIAS_MAP: Dict[str, Set[str]] = {
    "Software Engineer": {"Software Developer", "SWE"},
    "Machine Learning Engineer": {"ML Engineer"},
    "Frontend Developer": {"Frontend Engineer"},
    "Frontend Engineer": {"Frontend Developer"},
    "Backend Engineer": {"Backend Developer"},
}

# Directed transferable map — candidate normalized -> {job normalized}
ROLE_TRANSFERABLE_MAP: Dict[str, Set[str]] = {
    "Data Analyst": {"Data Scientist"},
    # Add only explicitly vetted entries; empty is valid conservative default
}


def _classify_role_pair(cand_norm: str, job_norm: Optional[str], job_family: Optional[str]) -> RoleRelationshipType:
    if not cand_norm or not job_norm:
        return RoleRelationshipType.NONE
    # Case-insensitive exact (normalize_title preserves case except sr/jr)
    if cand_norm.strip().lower() == job_norm.strip().lower():
        return RoleRelationshipType.EXACT
    # Alias — case-insensitive normalized membership
    cand_lower = cand_norm.strip().lower()
    job_lower = job_norm.strip().lower()
    # Build lowercased alias lookup
    for key, vals in ROLE_ALIAS_MAP.items():
        key_low = key.lower()
        vals_low = {v.lower() for v in vals}
        if (job_lower == key_low and cand_lower in vals_low) or (cand_lower == key_low and job_lower in vals_low):
            return RoleRelationshipType.ALIAS
    # Directed transferable (case-insensitive)
    for src, dsts in ROLE_TRANSFERABLE_MAP.items():
        if cand_lower == src.lower() and job_lower in {d.lower() for d in dsts}:
            return RoleRelationshipType.TRANSFERABLE
    return RoleRelationshipType.NONE


_PRECEDENCE = {
    RoleRelationshipType.EXACT: 0,
    RoleRelationshipType.ALIAS: 1,
    RoleRelationshipType.TRANSFERABLE: 2,
    RoleRelationshipType.NONE: 3,
}


class RoleMatcher:
    """Deterministic role matcher — single requirement per job."""

    def evaluate(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
    ) -> List[RoleEvaluation]:
        req: Optional[StructuredRoleRequirement] = job.role_requirement
        if req is None:
            return []  # No requirement

        if req.kind != "STRUCTURED":
            return [
                RoleEvaluation(
                    candidate_raw=None,
                    candidate_normalized=None,
                    job_raw=req.raw,
                    job_normalized=req.normalized,
                    job_role_family=req.role_family,
                    relationship=RoleRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    is_current_role=None,
                    evidence_source=f"job_role_{req.kind.lower()}",
                )
            ]

        if candidate.role_availability != RoleAvailability.DETERMINED:
            return [
                RoleEvaluation(
                    candidate_raw=None,
                    candidate_normalized=None,
                    job_raw=req.raw,
                    job_normalized=req.normalized,
                    job_role_family=req.role_family,
                    relationship=RoleRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    is_current_role=None,
                    evidence_source="candidate_role_unavailable",
                )
            ]

        entries: List[RoleEntry] = candidate.role_entries or []
        # Honest empty: DETERMINED + empty → UNKNOWN (not MISSING) per correction
        if not entries:
            return [
                RoleEvaluation(
                    candidate_raw=None,
                    candidate_normalized=None,
                    job_raw=req.raw,
                    job_normalized=req.normalized,
                    job_role_family=req.role_family,
                    relationship=RoleRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    is_current_role=None,
                    evidence_source="candidate_role_empty",
                )
            ]

        best_rel = RoleRelationshipType.NONE
        best_entry: Optional[RoleEntry] = None

        for entry in entries:
            rel = _classify_role_pair(entry.normalized, req.normalized, req.role_family)
            # No RELATED in 5B-4; NONE is fallback
            if _PRECEDENCE[rel] < _PRECEDENCE[best_rel]:
                best_rel = rel
                best_entry = entry
            elif rel == best_rel and best_rel != RoleRelationshipType.NONE:
                # Tie-break: lexicographically smallest normalized, prefer current
                cur_key = (best_entry.normalized, best_entry.raw, not best_entry.is_current)
                cand_key = (entry.normalized, entry.raw, not entry.is_current)
                if cand_key < cur_key:
                    best_entry = entry

        if best_rel in (RoleRelationshipType.EXACT, RoleRelationshipType.ALIAS, RoleRelationshipType.TRANSFERABLE):
            status = RequirementStatus.SATISFIED
        else:
            status = RequirementStatus.MISSING

        return [
            RoleEvaluation(
                candidate_raw=best_entry.raw if best_entry else None,
                candidate_normalized=best_entry.normalized if best_entry else None,
                job_raw=req.raw,
                job_normalized=req.normalized,
                job_role_family=req.role_family,
                relationship=best_rel,
                status=status,
                is_current_role=best_entry.is_current if best_entry else None,
                evidence_source="candidate_history" if best_entry and not best_entry.is_current else "candidate_current_role" if best_entry else None,
            )
        ]


_role_matcher: Optional[RoleMatcher] = None


def get_role_matcher() -> RoleMatcher:
    global _role_matcher
    if _role_matcher is None:
        _role_matcher = RoleMatcher()
    return _role_matcher
