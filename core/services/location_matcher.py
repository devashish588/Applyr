"""
Location Matcher — Phase 5B-5 Deterministic
============================================

City-normalized exact/alias/remote, no substring/fuzzy/LLM.
Precedence: EXACT > CITY_ALIAS > REMOTE_COMPATIBLE > NONE
Only SATISFIED / MISSING / UNKNOWN.
"""

from __future__ import annotations

from typing import List, Optional

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    LocationAvailability,
    LocationEvaluation,
    LocationRelationshipType,
    RequirementStatus,
)
from core.services.location_normalizer import normalize_city


def _is_remote_candidate(pref: str | None) -> str:
    if pref == "remote":
        return "REMOTE"
    if pref is None or pref == "":
        return "UNKNOWN"
    # "any" in repo maps to NON_REMOTE per correction (do not fabricate willingness)
    return "NON_REMOTE"


class LocationMatcher:
    def evaluate(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
    ) -> List[LocationEvaluation]:
        req = job.location_requirement
        if req is None:
            return []  # No requirement

        if req.kind == "UNPARSEABLE":
            return [
                LocationEvaluation(
                    candidate_raw=None,
                    candidate_city=None,
                    candidate_normalized_city=None,
                    job_raw=req.raw,
                    job_city=None,
                    job_normalized_city=None,
                    job_remote_type=req.remote_type,
                    relationship=LocationRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="job_location_unparseable",
                )
            ]

        if candidate.location_availability != LocationAvailability.DETERMINED:
            return [
                LocationEvaluation(
                    candidate_raw=None,
                    candidate_city=None,
                    candidate_normalized_city=None,
                    job_raw=req.raw,
                    job_city=req.cities[0] if req.cities else None,
                    job_normalized_city=req.normalized_cities[0] if req.normalized_cities else None,
                    job_remote_type=req.remote_type,
                    relationship=LocationRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="candidate_location_unavailable",
                )
            ]

        # Remote compatibility check (explicit only)
        cand_remote = _is_remote_candidate(candidate.remote_preference)
        job_remote = req.remote_type  # remote/hybrid/onsite/unknown

        # Remote+remote is SATISFIED via REMOTE_COMPATIBLE if city not required
        # For this phase, remote compatibility is checked before city scan
        # Hybrid is not remote — do not assume
        if job_remote == "unknown" and not req.cities:
            # No city and unknown remote type but requirement exists (edge) -> UNKNOWN
            return [
                LocationEvaluation(
                    candidate_raw=None,
                    candidate_city=None,
                    candidate_normalized_city=None,
                    job_raw=req.raw,
                    job_city=None,
                    job_normalized_city=None,
                    job_remote_type=job_remote,
                    relationship=LocationRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="job_location_unparseable",
                )
            ]

        # If job is remote and candidate is REMOTE, it's compatible regardless of city
        if cand_remote == "REMOTE" and job_remote == "remote":
            # Use first candidate entry as representative
            cand_entry = candidate.candidate_location_entries[0] if candidate.candidate_location_entries else None
            return [
                LocationEvaluation(
                    candidate_raw=cand_entry.raw if cand_entry else None,
                    candidate_city=cand_entry.city if cand_entry else None,
                    candidate_normalized_city=cand_entry.normalized_city if cand_entry else None,
                    job_raw=req.raw,
                    job_city=req.cities[0] if req.cities else None,
                    job_normalized_city=req.normalized_cities[0] if req.normalized_cities else None,
                    job_remote_type=job_remote,
                    relationship=LocationRelationshipType.REMOTE_COMPATIBLE,
                    status=RequirementStatus.SATISFIED,
                    evidence_source="remote_compatible",
                )
            ]

        # Hybrid with remote candidate is NOT automatically compatible -> fall through to city
        # City-based evaluation
        cand_cities = candidate.candidate_location_entries
        if not cand_cities:
            return [
                LocationEvaluation(
                    candidate_raw=None,
                    candidate_city=None,
                    candidate_normalized_city=None,
                    job_raw=req.raw,
                    job_city=req.cities[0] if req.cities else None,
                    job_normalized_city=req.normalized_cities[0] if req.normalized_cities else None,
                    job_remote_type=job_remote,
                    relationship=LocationRelationshipType.NONE,
                    status=RequirementStatus.UNKNOWN,
                    evidence_source="candidate_location_empty",
                )
            ]

        # Exhaustive candidate x job city
        best_rel = LocationRelationshipType.NONE
        best_cand = None
        best_job_city = None
        best_job_norm = None

        for c in cand_cities:
            c_norm = c.normalized_city or normalize_city(c.city or "")
            if not c_norm:
                continue
            for j_city, j_norm in zip(req.cities, req.normalized_cities):
                if not j_norm:
                    continue
                if c_norm == j_norm:
                    rel = LocationRelationshipType.EXACT
                elif c_norm == normalize_city(j_norm) and c_norm != j_norm.lower():
                    # Alias already via normalize_city (bengaluru->bangalore)
                    # If normalize made them equal, it's CITY_ALIAS
                    # Detect alias: raw cities differ but normalized equal
                    # Since both already normalized, check if they were different before alias
                    # Simplified: if normalize_city maps, then it's alias when original cities differ
                    rel = LocationRelationshipType.CITY_ALIAS if c.city and j_city and c.city.lower() != j_city.lower() and c_norm == j_norm else LocationRelationshipType.EXACT
                    # Actually normalize_city already maps bengaluru->bangalore, so equality implies alias if raws differ
                    if c_norm == j_norm:
                        # Determine if alias vs exact by comparing city lower before alias
                        if (c.city or "").lower() != (j_city or "").lower():
                            # Could be alias or case difference — treat as EXACT/CITY_ALIAS both SATISFIED
                            # Distinguish: if lower cities differ, it's alias
                            rel = LocationRelationshipType.CITY_ALIAS
                        else:
                            rel = LocationRelationshipType.EXACT
                else:
                    rel = LocationRelationshipType.NONE

                # Precedence: EXACT > CITY_ALIAS > NONE (REMOTE already handled)
                prec = {LocationRelationshipType.EXACT: 0, LocationRelationshipType.CITY_ALIAS: 1, LocationRelationshipType.REMOTE_COMPATIBLE: 2, LocationRelationshipType.NONE: 3}
                if prec[rel] < prec[best_rel]:
                    best_rel = rel
                    best_cand = c
                    best_job_city = j_city
                    best_job_norm = j_norm

        # For alias via normalize_city, CITY_ALIAS should be SATISFIED
        if best_rel in (LocationRelationshipType.EXACT, LocationRelationshipType.CITY_ALIAS):
            status = RequirementStatus.SATISFIED
        elif best_rel == LocationRelationshipType.REMOTE_COMPATIBLE:
            status = RequirementStatus.SATISFIED
        else:
            status = RequirementStatus.MISSING

        return [
            LocationEvaluation(
                candidate_raw=best_cand.raw if best_cand else None,
                candidate_city=best_cand.city if best_cand else None,
                candidate_normalized_city=best_cand.normalized_city if best_cand else None,
                job_raw=req.raw,
                job_city=best_job_city,
                job_normalized_city=best_job_norm,
                job_remote_type=job_remote,
                relationship=best_rel,
                status=status,
                evidence_source="candidate_preferred" if best_cand and best_cand.is_preferred else "candidate_current",
            )
        ]


_location_matcher = None


def get_location_matcher() -> LocationMatcher:
    global _location_matcher
    if _location_matcher is None:
        _location_matcher = LocationMatcher()
    return _location_matcher
