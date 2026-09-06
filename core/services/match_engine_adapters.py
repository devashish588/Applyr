"""
Match Engine 2.0 — Adapter Interfaces (Phase 5B-1)
====================================================

Structural adapter skeletons converting existing domain models into
the canonical Match Engine 2.0 input contracts.

Phase 5B-1 scope: interface/skeleton ONLY.
NO real matching, LLM calls, or external API calls.
NO modification of CandidateIntelligenceService or JobIntelligenceService.
NO alteration of production matching behavior.
"""

import logging
from typing import Optional

from core.models.match_engine import (
    CandidateLocationEntry,
    CanonicalCandidateInput,
    CanonicalJobInput,
    CanonicalJobRequirement,
    ExperienceAvailability,
    LocationAvailability,
    RoleAvailability,
    RoleEntry,
    SeniorityAvailability,
    SkillInventoryStatus,
    StructuredExperienceRequirement,
    StructuredLocationRequirement,
    StructuredRoleRequirement,
    StructuredSeniorityRequirement,
)

logger = logging.getLogger(__name__)

# Confidence threshold below which extraction is considered unreliable
CONFIDENCE_THRESHOLD = 0.3


class CandidateAdapter:
    """Converts CanonicalCandidateProfile → CanonicalCandidateInput.

    Determination logic (from approved Phase 5A §1.6 / §1.7, amended 5B-6):
      - If build_candidate_intelligence() returns a valid profile
        with overall_confidence >= CONFIDENCE_THRESHOLD → DETERMINED
      - If build_candidate_intelligence() raises exception → UNDETERMINED
      - If overall_confidence < CONFIDENCE_THRESHOLD → UNDETERMINED
      - DETERMINED status applies to the inventory as a whole,
        NOT to individual skills

    Seniority availability — final authoritative contract (5B-6 amendment):
      overall_confidence < 0.3 → UNDETERMINED (has precedence, regardless of seniority_origin)
      otherwise: seniority_origin == EXPLICIT_USER and supported/normalizable → DETERMINED
                 else (INFERRED / unsupported) → UNDETERMINED
    """

    def adapt(self, profile: "CanonicalCandidateProfile") -> CanonicalCandidateInput:
        """Convert a successfully built CanonicalCandidateProfile → CanonicalCandidateInput.

        Precondition: `profile` was successfully produced by
        CandidateIntelligenceService.build_candidate_intelligence()
        without exception. Caller is responsible for exception handling.

        Sets DETERMINED if overall_confidence >= CONFIDENCE_THRESHOLD,
        UNDETERMINED otherwise.

        Seniority: overall_confidence < 0.3 → UNDETERMINED regardless of
        seniority_origin (has precedence); otherwise EXPLICIT_USER + supported
        → DETERMINED else UNDETERMINED.
        """
        if profile.overall_confidence < CONFIDENCE_THRESHOLD:
            # Extraction unreliable → UNDETERMINED
            return CanonicalCandidateInput(
                skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
                skill_inventory=[],
                skill_inventory_raw=[],
                seniority=profile.seniority,
                target_roles=list(profile.target_roles),
                preferred_locations=list(profile.preferred_locations),
                remote_preference=profile.remote_preference,
                experience_years=sum(e.years for e in profile.experience),
                experience_availability=ExperienceAvailability.UNDETERMINED,
                role_availability=RoleAvailability.UNDETERMINED,
                role_entries=[],
                location_availability=LocationAvailability.UNDETERMINED,
                candidate_location_entries=[],
                seniority_availability=SeniorityAvailability.UNDETERMINED,
                candidate_seniority_raw=None,
                candidate_seniority_normalized=None,
                candidate_seniority_source=None,
                candidate_name=profile.name,
                candidate_id=profile.candidate_id,
            )

        # Extraction succeeded with sufficient confidence → DETERMINED
        # 5B-2 FIX (correction round): Preserve ALL raw occurrences so
        # ["python3","py"] both → Python reach SkillMatcher and EXACT can
        # beat ALIAS. Profile.skill_occurrences preserves every occurrence
        # in input order; profile.skills remains deduplicated for backward
        # compatibility with existing consumers. Adapter prefers occurrences.
        occ = getattr(profile, "skill_occurrences", None)
        # Provenance → availability (honest, no fabrication of NO_REQUIREMENT)
        from core.models.candidate_intelligence import CandidateProvenance

        def _to_exp_avail(prov):
            if prov in (CandidateProvenance.DETERMINED_EMPTY, CandidateProvenance.DETERMINED_POPULATED):
                return ExperienceAvailability.DETERMINED
            # Fallback for old profiles without provenance: if experience list non-empty and confidence ok, treat as DETERMINED
            if prov == CandidateProvenance.SOURCE_UNAVAILABLE and getattr(profile, "experience", []) and profile.overall_confidence >= CONFIDENCE_THRESHOLD:
                return ExperienceAvailability.DETERMINED
            return ExperienceAvailability.UNDETERMINED

        def _to_role_avail(prov):
            if prov in (CandidateProvenance.DETERMINED_EMPTY, CandidateProvenance.DETERMINED_POPULATED):
                return RoleAvailability.DETERMINED
            if prov == CandidateProvenance.SOURCE_UNAVAILABLE and (getattr(profile, "current_role", None) or getattr(profile, "experience", [])) and profile.overall_confidence >= CONFIDENCE_THRESHOLD:
                return RoleAvailability.DETERMINED
            return RoleAvailability.UNDETERMINED

        def _to_loc_avail(prov):
            if prov in (CandidateProvenance.DETERMINED_EMPTY, CandidateProvenance.DETERMINED_POPULATED):
                return LocationAvailability.DETERMINED
            if prov == CandidateProvenance.SOURCE_UNAVAILABLE and (getattr(profile, "location", None) or getattr(profile, "preferred_locations", [])) and profile.overall_confidence >= CONFIDENCE_THRESHOLD:
                return LocationAvailability.DETERMINED
            return LocationAvailability.UNDETERMINED

        exp_avail = _to_exp_avail(getattr(profile, "experience_provenance", CandidateProvenance.SOURCE_UNAVAILABLE))
        role_avail = _to_role_avail(getattr(profile, "role_provenance", CandidateProvenance.SOURCE_UNAVAILABLE))
        loc_avail = _to_loc_avail(getattr(profile, "location_provenance", CandidateProvenance.SOURCE_UNAVAILABLE))
        # Seniority: provenance-driven, INFERRED remains distinct (never DETERMINED)
        from core.services.seniority_normalizer import normalize_seniority

        # Use provenance field directly — preserves INFERRED vs SOURCE_UNAVAILABLE
        sen_prov = getattr(profile, "seniority_provenance", None)
        # Fallback for old profiles without field: derive from origin
        if sen_prov is None:
            seniority_origin = getattr(profile, "seniority_origin", None)
            is_explicit_fb = False
            try:
                is_explicit_fb = str(seniority_origin).split(".")[-1] == "EXPLICIT_USER"
            except Exception:
                pass
            sen_prov = CandidateProvenance.DETERMINED_POPULATED if is_explicit_fb else CandidateProvenance.INFERRED
        # Backward compat: old profiles default SOURCE_UNAVAILABLE but with explicit seniority should be DETERMINED
        if sen_prov == CandidateProvenance.SOURCE_UNAVAILABLE:
            seniority_origin_fb = getattr(profile, "seniority_origin", None)
            is_explicit_fb2 = False
            try:
                is_explicit_fb2 = str(seniority_origin_fb).split(".")[-1] == "EXPLICIT_USER"
            except Exception:
                pass
            if is_explicit_fb2 and getattr(profile, "overall_confidence", 0) >= CONFIDENCE_THRESHOLD:
                from core.services.seniority_normalizer import normalize_seniority as _norm2

                if _norm2(getattr(profile, "seniority", None)):
                    sen_prov = CandidateProvenance.DETERMINED_POPULATED

        if sen_prov == CandidateProvenance.DETERMINED_POPULATED:
            seniority_raw = getattr(profile, "seniority", None)
            cand_norm = normalize_seniority(seniority_raw)
            if cand_norm:
                seniority_avail: SeniorityAvailability = SeniorityAvailability.DETERMINED
                cand_sen_raw: str | None = seniority_raw
                cand_sen_norm: str | None = cand_norm
                cand_sen_src: str | None = "explicit_seniority"
            else:
                seniority_avail = SeniorityAvailability.UNDETERMINED
                cand_sen_raw = None
                cand_sen_norm = None
                cand_sen_src = None
        else:
            # INFERRED, SOURCE_UNAVAILABLE, EXTRACTION_FAILED/UNPARSEABLE, DETERMINED_EMPTY → UNDETERMINED
            seniority_avail = SeniorityAvailability.UNDETERMINED
            cand_sen_raw = None
            cand_sen_norm = None
            cand_sen_src = None

        role_entries = _build_role_entries(profile)
        loc_entries = _build_location_entries(profile)
        if occ:
            return CanonicalCandidateInput(
                skill_inventory_status=SkillInventoryStatus.DETERMINED,
                skill_inventory=[s.normalized_name for s in occ],
                skill_inventory_raw=[s.name for s in occ],
                seniority=profile.seniority,
                target_roles=list(profile.target_roles),
                preferred_locations=list(profile.preferred_locations),
                remote_preference=profile.remote_preference,
                experience_years=sum(e.years for e in profile.experience),
                experience_availability=exp_avail,
                role_availability=role_avail,
                role_entries=role_entries,
                location_availability=loc_avail,
                candidate_location_entries=loc_entries,
                seniority_availability=seniority_avail,
                candidate_seniority_raw=cand_sen_raw,
                candidate_seniority_normalized=cand_sen_norm,
                candidate_seniority_source=cand_sen_src,
                candidate_name=profile.name,
                candidate_id=profile.candidate_id,
            )
        return CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=[s.normalized_name for s in profile.skills],
            skill_inventory_raw=[s.name for s in profile.skills],
            seniority=profile.seniority,
            target_roles=list(profile.target_roles),
            preferred_locations=list(profile.preferred_locations),
            remote_preference=profile.remote_preference,
            experience_years=sum(e.years for e in profile.experience),
            experience_availability=exp_avail,
            role_availability=role_avail,
            role_entries=role_entries,
            location_availability=loc_avail,
            candidate_location_entries=loc_entries,
            seniority_availability=seniority_avail,
            candidate_seniority_raw=cand_sen_raw,
            candidate_seniority_normalized=cand_sen_norm,
            candidate_seniority_source=cand_sen_src,
            candidate_name=profile.name,
            candidate_id=profile.candidate_id,
        )

    def adapt_safe(
        self,
        profile_data: Optional[dict] = None,
        resume_data: Optional[dict] = None,
    ) -> CanonicalCandidateInput:
        """Safe adapter that catches extraction failures → UNDETERMINED.

        This is the Phase 5A §1.6 Case B boundary:
        if build_candidate_intelligence() raises, the inventory
        is UNDETERMINED and any populated skills are non-authoritative.
        """
        try:
            from core.services.candidate_intelligence_service import (
                get_candidate_intelligence_service,
            )

            svc = get_candidate_intelligence_service()
            profile = svc.build_candidate_intelligence(profile_data, resume_data)
            return self.adapt(profile)
        except Exception as e:
            logger.error(f"[CandidateAdapter] Extraction failed → UNDETERMINED: {e}")
            return CanonicalCandidateInput(
                skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
                skill_inventory=[],
                skill_inventory_raw=[],
                experience_availability=ExperienceAvailability.UNDETERMINED,
                role_availability=RoleAvailability.UNDETERMINED,
                role_entries=[],
                location_availability=LocationAvailability.UNDETERMINED,
                candidate_location_entries=[],
                seniority_availability=SeniorityAvailability.UNDETERMINED,
                candidate_seniority_raw=None,
                candidate_seniority_normalized=None,
                candidate_seniority_source=None,
            )


class JobAdapter:
    """Converts CanonicalJobProfile or Job → CanonicalJobInput.

    Phase 5B-1 scope: structural skeleton only.
    Real JD parsing / skill extraction belongs to later phases.
    """

    def adapt(self, job_profile: "CanonicalJobProfile") -> CanonicalJobInput:
        """Convert CanonicalJobProfile → CanonicalJobInput.

        Maps structured job intelligence into the canonical
        Match Engine 2.0 job input format.
        """
        requirements = []
        for skill in job_profile.required_skills:
            requirements.append(
                CanonicalJobRequirement(
                    raw_name=skill.name,
                    canonical_name=skill.normalized_name,
                    required=True,
                    category=skill.category,
                )
            )
        for skill in job_profile.preferred_skills:
            requirements.append(
                CanonicalJobRequirement(
                    raw_name=skill.name,
                    canonical_name=skill.normalized_name,
                    required=False,
                    category=skill.category,
                )
            )

        exp_req = self._parse_experience(getattr(job_profile, "experience_years", None))
        role_req = self._parse_role(
            getattr(job_profile, "title", None),
            getattr(job_profile, "normalized_title", None),
            getattr(job_profile, "role_family", None),
        )
        loc_req = self._parse_location(
            getattr(job_profile.location, "raw", None) if getattr(job_profile, "location", None) else None,
            getattr(job_profile.location, "remote_type", "unknown") if getattr(job_profile, "location", None) else "unknown",
        )
        seniority_req = self._parse_seniority(getattr(job_profile, "seniority", None))

        # 5B-7 provenance hardening: parser absence ≠ NO_REQUIREMENT
        # Do NOT fabricate NO_REQUIREMENT; preserve UNKNOWN reason via AMBIGUOUS/UNPARSEABLE.
        from core.models.job_intelligence import JobProvenance

        def _kind_for_prov(prov):
            # Preserve provenance reason, do not fabricate UNPARSEABLE for SOURCE_UNAVAILABLE
            if prov == JobProvenance.SOURCE_UNAVAILABLE:
                return "SOURCE_UNAVAILABLE"
            if prov == JobProvenance.EXTRACTION_UNPARSEABLE:
                return "UNPARSEABLE"
            if prov == JobProvenance.UNDETERMINED:
                return "UNDETERMINED"
            if prov == JobProvenance.EXTRACTION_FAILED:
                return "EXTRACTION_FAILED"
            return "UNPARSEABLE"

        if exp_req is None and getattr(job_profile, "experience_provenance", JobProvenance.SOURCE_UNAVAILABLE) != JobProvenance.NO_REQUIREMENT:
            _prov = getattr(job_profile, "experience_provenance", JobProvenance.SOURCE_UNAVAILABLE)
            exp_req = StructuredExperienceRequirement(raw=getattr(job_profile, "experience_years", "") or "", kind=_kind_for_prov(_prov), required=True)
        if role_req is None and getattr(job_profile, "role_provenance", JobProvenance.SOURCE_UNAVAILABLE) != JobProvenance.NO_REQUIREMENT:
            _prov = getattr(job_profile, "role_provenance", JobProvenance.SOURCE_UNAVAILABLE)
            role_req = StructuredRoleRequirement(raw=getattr(job_profile, "title", None), normalized=None, role_family=None, required=True, kind=_kind_for_prov(_prov))
        if loc_req is None and getattr(job_profile, "location_provenance", JobProvenance.SOURCE_UNAVAILABLE) != JobProvenance.NO_REQUIREMENT:
            _prov = getattr(job_profile, "location_provenance", JobProvenance.SOURCE_UNAVAILABLE)
            loc_req = StructuredLocationRequirement(raw=getattr(job_profile.location, "raw", None) if getattr(job_profile, "location", None) else None, cities=[], normalized_cities=[], remote_type="unknown", kind=_kind_for_prov(_prov), required=True)
        return CanonicalJobInput(
            job_id=job_profile.job_id,
            title=job_profile.title,
            company=job_profile.company,
            location=job_profile.location.raw if job_profile.location else None,
            seniority=job_profile.seniority,
            jd_text=None,
            requirements=requirements,
            experience_requirement=exp_req,
            role_requirement=role_req,
            location_requirement=loc_req,
            seniority_requirement=seniority_req,
        )

    def adapt_from_legacy(
        self,
        job_id: int = 0,
        job_title: str = "",
        required_skills: Optional[list] = None,
        job_location: str = "",
        jd_text: str = "",
    ) -> CanonicalJobInput:
        """Convert legacy Job/dict fields → CanonicalJobInput.

        Provides backward compatibility with existing MatchService
        calling conventions.
        """
        requirements = []
        for skill in (required_skills or []):
            requirements.append(
                CanonicalJobRequirement(
                    raw_name=skill,
                    canonical_name=skill,  # No normalization in 5B-1
                    required=True,
                )
            )

        # Legacy location parsed as single city; remote unknown
        loc_req = self._parse_location(job_location, "unknown") if job_location else None
        # Legacy seniority: no provenance → AMBIGUOUS if no title seniority, else parsed
        seniority_req = self._parse_seniority(None)
        return CanonicalJobInput(
            job_id=job_id,
            title=job_title,
            location=job_location,
            jd_text=jd_text,
            requirements=requirements,
            experience_requirement=None,
            role_requirement=self._parse_role(job_title, None, None),
            location_requirement=loc_req,
            seniority_requirement=seniority_req,
        )

    @staticmethod
    def _parse_experience(exp_str: Optional[str]) -> Optional[StructuredExperienceRequirement]:
        """Translate CanonicalJobProfile.experience_years string → structured requirement.

        Reuses existing Job Intelligence output; does not re-parse JD text.
        Ownership remains Job Intelligence; this is translation only.
        Distinguishes: None (no requirement) vs UNPARSEABLE (exists but unsupported/malformed → UNKNOWN).
        No new regexes for unsupported forms; they remain UNPARSEABLE by design.
        """
        if exp_str is None:
            return None
        if not exp_str.strip():
            # Empty string treated as no requirement (defensive)
            return None
        s = exp_str.strip()
        import re

        # Range: "3-5 years" / "3–5 years"
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*years?\s*$", s, re.IGNORECASE)
        if m:
            return StructuredExperienceRequirement(
                raw=s, min_years=float(m.group(1)), max_years=float(m.group(2)), kind="RANGE", inclusive_max=True, required=True
            )
        # Minimum: "3+ years"
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\+\s*years?\s*$", s, re.IGNORECASE)
        if m:
            return StructuredExperienceRequirement(raw=s, min_years=float(m.group(1)), max_years=None, kind="MINIMUM", required=True)
        # Bare "2 years" → MINIMUM per 5B-3 product policy
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*years?\s*$", s, re.IGNORECASE)
        if m:
            return StructuredExperienceRequirement(raw=s, min_years=float(m.group(1)), max_years=None, kind="MINIMUM", required=True)
        # Present but unsupported/malformed → preserve as UNPARSEABLE → UNKNOWN (BLOCKER 1)
        return StructuredExperienceRequirement(raw=s, min_years=None, max_years=None, kind="UNPARSEABLE", required=True)

    @staticmethod
    def _parse_location(
        raw: Optional[str],
        remote_type: str = "unknown",
    ) -> Optional[StructuredLocationRequirement]:
        """Translate JobLocationInfo → StructuredLocationRequirement.

        Safe multi-location split on ` / `, ` | `, ` OR ` (not comma).
        City = first comma component, normalized via LocationNormalizer.
        No requirement if raw empty and remote_type unknown → None.
        Present but no valid city → UNPARSEABLE.
        """
        from core.models.match_engine import StructuredLocationRequirement
        from core.services.location_normalizer import extract_city, normalize_city
        import re

        has_raw = bool(raw and raw.strip())
        is_unknown_remote = (remote_type or "unknown").lower() == "unknown"
        if not has_raw and is_unknown_remote:
            return None
        raw_str = raw.strip() if has_raw else ""
        remote = (remote_type or "unknown").lower()

        # Split multi-location (safe delimiters only)
        parts: list[str] = []
        if has_raw:
            # Split on " / ", " | ", " OR " (case-insensitive, requires spaces)
            split_parts = re.split(r"\s+/\s+|\s+\|\s+|\s+OR\s+", raw_str, flags=re.IGNORECASE)
            parts = [p.strip() for p in split_parts if p.strip()]
        else:
            parts = []

        # Remote-only without city (e.g., remote_type remote and no raw) is still structured
        if not parts and remote in ("remote", "hybrid", "onsite"):
            return StructuredLocationRequirement(
                raw=raw_str if has_raw else None,
                cities=[],
                normalized_cities=[],
                remote_type=remote,
                kind="STRUCTURED",
                required=True,
            )

        cities: list[str] = []
        normalized: list[str] = []
        for p in parts:
            city = extract_city(p)
            if not city:
                # Any unparseable city makes the whole requirement unparseable
                return StructuredLocationRequirement(
                    raw=raw_str,
                    cities=[],
                    normalized_cities=[],
                    remote_type=remote,
                    kind="UNPARSEABLE",
                    required=True,
                )
            cities.append(city)
            normalized.append(normalize_city(city))

        # If raw was present but no cities (should not happen) → unparseable
        if has_raw and not cities:
            return StructuredLocationRequirement(
                raw=raw_str, cities=[], normalized_cities=[], remote_type=remote, kind="UNPARSEABLE", required=True
            )

        return StructuredLocationRequirement(
            raw=raw_str if has_raw else None,
            cities=cities,
            normalized_cities=normalized,
            remote_type=remote,
            kind="STRUCTURED",
            required=True,
        )

    @staticmethod
    def _parse_seniority(raw_seniority: Optional[str]) -> Optional[StructuredSeniorityRequirement]:
        """Translate job seniority string → StructuredSeniorityRequirement.

        None → AMBIGUOUS (cannot distinguish NO_REQUIREMENT vs UNDETERMINED without provenance).
        Multi-level ("/" or " to ") → MULTI_LEVEL.
        Unsupported level (LEAD etc.) → UNPARSEABLE.
        Supported → STRUCTURED.
        """
        if raw_seniority is None:
            return StructuredSeniorityRequirement(raw=None, normalized_level=None, required=True, kind="AMBIGUOUS")
        s = raw_seniority.strip()
        if not s:
            return StructuredSeniorityRequirement(raw=s, normalized_level=None, required=True, kind="UNPARSEABLE")
        # Multi-level detection
        low = s.lower()
        if "/" in s or " to " in low or " or " in low:
            # Check if both sides contain seniority-like tokens
            # Conservative: any "/" or " to " in seniority raw is ambiguous
            return StructuredSeniorityRequirement(raw=s, normalized_level=None, required=True, kind="MULTI_LEVEL")
        from core.services.seniority_normalizer import normalize_seniority

        norm = normalize_seniority(s)
        if norm:
            return StructuredSeniorityRequirement(raw=s, normalized_level=norm, required=True, kind="STRUCTURED")
        return StructuredSeniorityRequirement(raw=s, normalized_level=None, required=True, kind="UNPARSEABLE")

    @staticmethod
    def _parse_role(
        title: Optional[str],
        normalized_title: Optional[str],
        role_family: Optional[str],
    ) -> Optional[StructuredRoleRequirement]:
        """Translate job title/role_family → StructuredRoleRequirement.

        No JD re-parse; preserves raw. No requirement if all signals absent → None.
        Unparseable raw with empty normalized and no family → UNPARSEABLE.
        """
        has_title = bool(title and title.strip())
        has_norm = bool(normalized_title and normalized_title.strip())
        has_family = bool(role_family and role_family.strip())
        if not has_title and not has_norm and not has_family:
            return None
        # If raw title exists but normalized empty and no family, treat as UNPARSEABLE
        if has_title and not has_norm and not has_family:
            return StructuredRoleRequirement(
                raw=title, normalized=None, role_family=None, required=True, kind="UNPARSEABLE"
            )
        from core.services.role_normalizer import normalize_title

        norm_val = normalized_title.strip() if has_norm else (normalize_title(title) if has_title else None)
        # Normalize fallback via shared normalizer to ensure case/whitespace consistency
        if norm_val is not None and not norm_val.strip():
            norm_val = None
        return StructuredRoleRequirement(
            raw=title,
            normalized=norm_val,
            role_family=role_family.strip() if has_family else None,
            required=True,
            kind="STRUCTURED",
        )


def _build_location_entries(profile: "CanonicalCandidateProfile") -> List[CandidateLocationEntry]:
    """Build candidate location entries from location + preferred_locations."""
    from core.services.location_normalizer import extract_city, normalize_city

    entries: List[CandidateLocationEntry] = []
    seen: set[str] = set()

    # Current location (single)
    cur_raw = (getattr(profile, "location", None) or "").strip()
    if cur_raw:
        # Current location may contain multi-location delimiters — split safely
        import re

        parts = re.split(r"\s+/\s+|\s+\|\s+|\s+OR\s+", cur_raw, flags=re.IGNORECASE)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            city = extract_city(p)
            if not city:
                continue
            norm = normalize_city(city)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            entries.append(CandidateLocationEntry(raw=p, city=city, normalized_city=norm, is_preferred=False))

    # Preferred locations (each entry is one location, but also handle if it contains delimiters)
    for pref in getattr(profile, "preferred_locations", []) or []:
        if not pref or not pref.strip():
            continue
        import re

        parts = re.split(r"\s+/\s+|\s+\|\s+|\s+OR\s+", pref.strip(), flags=re.IGNORECASE)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            city = extract_city(p)
            if not city:
                continue
            norm = normalize_city(city)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            entries.append(CandidateLocationEntry(raw=p, city=city, normalized_city=norm, is_preferred=True))

    return entries


def _build_role_entries(profile: "CanonicalCandidateProfile") -> List[RoleEntry]:
    """Build deduplicated authoritative role entries from current_role + experience titles."""
    from core.services.role_normalizer import normalize_title

    entries: List[RoleEntry] = []
    seen_norm: set[str] = set()

    # Experience history in order (authoritative)
    for exp in getattr(profile, "experience", []) or []:
        raw = (exp.title or "").strip()
        if not raw:
            continue
        norm = normalize_title(raw)
        if not norm or norm in seen_norm:
            continue
        seen_norm.add(norm)
        is_current = bool(profile.current_role and normalize_title(profile.current_role) == norm)
        entries.append(RoleEntry(raw=raw, normalized=norm, is_current=is_current))

    # current_role if not already covered (deduplicate)
    cur_raw = (getattr(profile, "current_role", None) or "").strip()
    if cur_raw:
        cur_norm = normalize_title(cur_raw)
        if cur_norm and cur_norm not in seen_norm:
            entries.append(RoleEntry(raw=cur_raw, normalized=cur_norm, is_current=True))

    # target_roles intentionally excluded — non-authoritative
    return entries
