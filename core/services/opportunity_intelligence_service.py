"""
Opportunity Intelligence Service — Phase 16 (Foundation) + Phase 17 (Shortlisting Strictness)
==============================================================================================

Informational-only, deterministic, no LLM/embeddings/ML.
- Competition / Background remain UNKNOWN foundation (later phases).
- Shortlisting Strictness is computed by an explicit rule hierarchy over
  structured Job Intelligence (never raw-JD reparsing, never Match/Priority).

Dependency direction (one-way, no cycles):
  Raw Job -> Job Intelligence -> Shortlisting Strictness
  Match / Priority are NEVER influenced by this service.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.models.opportunity_intelligence import (
    OpportunityDeterminationStatus,
    OpportunityEvidence,
    OpportunityIntelligence,
    OpportunitySignal,
    OpportunitySignalLevel,
)

logger = logging.getLogger(__name__)

# ── Phase 17 named thresholds (conservative, transparent, no hidden weights) ──
# Rationale: typical must-have lists are 1-3 skills (broad), 4-5 (meaningful),
# 6+ (highly specific). Totals combine independent mandatory filters.
# NOTE: shortlisting judges sparseness partly by raw JD length (verbose prose
# without must-haves must not become LOW or HIGH); background judges by
# extracted requirements sections (company prose must not imply domain need).
MIN_JD_LENGTH_FOR_DETERMINATION = 80  # below this the JD is too sparse to judge; avoids false LOW
MODERATE_REQUIRED_SKILLS = 4  # several required skills -> meaningful constraints
HIGH_REQUIRED_SKILLS = 6  # many required skills -> highly specific screening profile
MODERATE_TOTAL_CONSTRAINTS = 4  # meaningful number of mandatory conditions
HIGH_TOTAL_CONSTRAINTS = 7  # multiple simultaneous strict requirements
NARROW_RANGE_WIDTH = 3  # e.g. "5-8 years" (width 3) or "3-5 years" (width 2) is narrow/explicit
MIN_EXPERIENCE_FOR_MODERATE = 3  # explicit threshold at/above this is a meaningful filter

# Domain terms that, when appearing inside the structured requirements section
# (key_requirements), indicate an explicit mandatory domain filter. This is NOT
# background-fit transferability, only filter presence.
_DOMAIN_KEYWORDS = (
    "banking", "finance", "fintech", "healthcare", "health tech", "hipaa",
    "sap", "salesforce", "pharma", "insurance", "automotive", "aerospace",
)

_MANDATORY_HINTS = ("required", "must have", "must-have", "mandatory", "minimum")

# ── Phase 18: Background Fit Sensitivity vocabulary ──
# Domain / regulated / specialized-platform terms. Technology names that are
# broadly transferable (Python, React, AWS, Kubernetes, …) are deliberately
# ABSENT here: technology specificity ≠ domain specificity.
_BACKGROUND_DOMAIN_KEYWORDS = (
    "banking", "finance", "fintech", "payments", "payment",
    "credit risk", "credit-risk", "basel", "ifrs9", "ifrs 9",
    "healthcare", "health tech", "clinical", "hipaa",
    "claims processing", "pharma", "insurance", "underwriting",
)
# Specialized enterprise platforms where prior implementation experience is a
# genuine background filter. Generic tools (Jira, Slack, Git, …) are absent.
_SPECIALIZED_PLATFORMS = (
    "sap", "s/4hana", "successfactors", "success factors",
    "salesforce", "workday", "servicenow", "cpq",
)
# Context words proving the term is about prior background, not education alone.
_BACKGROUND_CONTEXT_WORDS = (
    "experience", "background", "implementation", "implement",
    "workflow", "modelling", "modeling", "migration", "claims", "risk",
)

# ── Phase 19: Competition Intensity vocabulary ──
# Broad role families with structurally large candidate pools (existing
# normalized role_family values only — never a popularity-ranked title list).
_BROAD_ROLE_FAMILIES = {"backend", "frontend", "fullstack", "data", "devops", "mobile"}
# Ubiquitous, widely transferable technologies. Small and conservative: only
# skills taught across bootcamps, universities, and most engineering orgs.
# Anything outside this set is treated as neutral-to-specialized, never as
# evidence against competition by itself.
_COMMON_TRANSFERABLE_SKILLS = {
    "Python", "SQL", "Java", "JavaScript", "TypeScript", "React",
    "HTML", "CSS", "AWS", "Docker", "Git", "Node.js",
}
# Seniority bars that narrow the eligible pool (supporting evidence for LOW only).
_NARROWING_SENIORITY = {"SENIOR", "LEAD", "PRINCIPAL"}
# Freshness window (days) matching the existing priority freshness threshold.
_FRESH_WINDOW_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_job_record(job_id: int) -> Optional[Dict[str, Any]]:
    """TEST-aware single-job fetch (production by default, isolated TEST when set)."""
    try:
        from core.services.application_service import _resolve_database_url
        import psycopg2
        from psycopg2.extras import RealDictCursor

        url = _resolve_database_url()
        if not url:
            return None
        conn = psycopg2.connect(url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        return None


def build_foundation(job_id: Optional[int] = None) -> OpportunityIntelligence:
    """Safe initial contract: all signals UNKNOWN/UNDETERMINED, no evidence, null confidence."""
    return OpportunityIntelligence(
        job_id=job_id,
        competition_intensity=OpportunitySignal(),
        background_fit_sensitivity=OpportunitySignal(),
        shortlisting_strictness=OpportunitySignal(),
        determination_status=OpportunityDeterminationStatus.UNDETERMINED,
        evidence=[],
        confidence=None,
        computed_at=_now(),
    )


def _parse_experience_span(experience_years: Optional[str]) -> Tuple[Optional[float], Optional[float], bool]:
    """Parse normalized experience_years ("X-Y years" / "X+ years" / "X years").

    Consumes Job Intelligence normalized output only (never raw-JD reparsing).
    Returns (min_years, max_years_or_None, is_narrow_range).
    """
    if not experience_years:
        return None, None, False
    s = experience_years.strip().lower()
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*years?\s*$", s)
    if m:
        try:
            lo, hi = float(m.group(1)), float(m.group(2))
            return lo, hi, (hi - lo) <= NARROW_RANGE_WIDTH
        except Exception:
            return None, None, False
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*\+\s*years?\s*$", s)
    if m:
        try:
            return float(m.group(1)), None, False
        except Exception:
            return None, None, False
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*years?\s*$", s)
    if m:
        try:
            return float(m.group(1)), None, False
        except Exception:
            return None, None, False
    return None, None, False


def _mandatory_items_in_requirements(items: List[str], requirements_text: str) -> List[str]:
    """Keep only items explicitly appearing in the structured requirements section.

    Prevents "degree/cert preferred elsewhere in the JD" from counting as mandatory.
    """
    req = (requirements_text or "").lower()
    if not req:
        return []
    out = []
    for it in items or []:
        if it and str(it).lower() in req:
            out.append(str(it))
    return out


def evaluate_shortlisting_strictness(job_profile) -> OpportunitySignal:
    """Deterministic, side-effect free evaluator over structured Job Intelligence.

    Counts only REQUIRED/mandatory filters (preferred never counts alone).
    Returns LOW/MODERATE/HIGH when evidence is sufficient, else UNKNOWN/UNDETERMINED.
    Input is never mutated.
    """
    from core.models.job_intelligence import JobProvenance

    def _unknown(reason: str = "Not enough evidence.") -> OpportunitySignal:
        return OpportunitySignal(
            level=OpportunitySignalLevel.UNKNOWN,
            status=OpportunityDeterminationStatus.UNDETERMINED,
            confidence=None,
            evidence=[],
        )

    if job_profile is None:
        return _unknown()

    required_skills = list(getattr(job_profile, "required_skills", None) or [])
    preferred_skills = list(getattr(job_profile, "preferred_skills", None) or [])
    n_required = len(required_skills)
    n_preferred = len(preferred_skills)
    exp_years = getattr(job_profile, "experience_years", None)
    exp_prov = getattr(job_profile, "experience_provenance", JobProvenance.SOURCE_UNAVAILABLE)
    loc = getattr(job_profile, "location", None)
    loc_prov = getattr(job_profile, "location_provenance", JobProvenance.SOURCE_UNAVAILABLE)
    seniority = getattr(job_profile, "seniority", None)
    sen_prov = getattr(job_profile, "seniority_provenance", JobProvenance.SOURCE_UNAVAILABLE)
    education = list(getattr(job_profile, "education", None) or [])
    certifications = list(getattr(job_profile, "certifications", None) or [])
    key_requirements = list(getattr(job_profile, "key_requirements", None) or [])
    qualifications = list(getattr(job_profile, "qualifications", None) or [])
    has_description = bool(getattr(job_profile, "has_description", False))
    jd_len = int(getattr(job_profile, "jd_text_length", 0) or 0)
    req_text = " ".join([str(x) for x in (key_requirements + qualifications)])

    exp_present = bool(exp_years) and exp_prov == JobProvenance.DETERMINED_REQUIREMENT
    exp_min, exp_max, exp_narrow = _parse_experience_span(exp_years) if exp_present else (None, None, False)

    remote_type = str(getattr(loc, "remote_type", "unknown") if loc else "unknown").lower()
    loc_raw = str(getattr(loc, "raw", None) or getattr(loc, "normalized", None) or "").strip()
    hard_location = (
        remote_type == "onsite"
        and bool(loc_raw)
        and loc_prov == JobProvenance.DETERMINED_REQUIREMENT
    )

    sen_determined = bool(seniority) and sen_prov == JobProvenance.DETERMINED_REQUIREMENT

    mandatory_certs = _mandatory_items_in_requirements(certifications, req_text)
    mandatory_edu = _mandatory_items_in_requirements(education, req_text)
    edu_constraint = 1 if mandatory_edu else 0

    domain_hit = None
    if req_text:
        low_req = req_text.lower()
        for kw in _DOMAIN_KEYWORDS:
            if kw in low_req and any(h in low_req for h in _MANDATORY_HINTS):
                domain_hit = kw
                break

    # ── UNKNOWN rule first: never turn sparse/unparseable into LOW ──
    if not has_description or jd_len < MIN_JD_LENGTH_FOR_DETERMINATION:
        if n_required == 0 and not exp_present and not mandatory_certs and not mandatory_edu and not domain_hit and not hard_location:
            return _unknown()
    if (
        n_required == 0
        and not exp_present
        and not mandatory_certs
        and not mandatory_edu
        and not domain_hit
        and not hard_location
        and exp_prov in (JobProvenance.SOURCE_UNAVAILABLE, JobProvenance.UNDETERMINED, JobProvenance.EXTRACTION_UNPARSEABLE)
        and not req_text.strip()
    ):
        return _unknown()

    evidence: List[OpportunityEvidence] = []
    if exp_present and exp_years:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"explicit experience requirement ({exp_years})",
            source="EXPERIENCE_REQUIREMENT",
            confidence=None,
            details=str(exp_years),
        ))
        if exp_narrow:
            evidence.append(OpportunityEvidence(
                signal="SHORTLISTING_STRICTNESS",
                reason=f"narrow experience range ({exp_years})",
                source="EXPERIENCE_REQUIREMENT",
                confidence=None,
                details=str(exp_years),
            ))
    if n_required:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"{n_required} mandatory technical skill{'s' if n_required != 1 else ''}",
            source="REQUIREMENT",
            confidence=None,
            details=f"{n_required} required, {n_preferred} preferred (preferred excluded)",
        ))
    for c in mandatory_certs[:2]:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"mandatory certification ({c})",
            source="CERTIFICATION_REQUIREMENT",
            confidence=None,
            details=str(c),
        ))
    if edu_constraint:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"mandatory education requirement ({mandatory_edu[0]})",
            source="REQUIREMENT",
            confidence=None,
            details=str(mandatory_edu[0]),
        ))
    if domain_hit:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"mandatory domain experience ({domain_hit})",
            source="DOMAIN_REQUIREMENT",
            confidence=None,
            details=str(domain_hit),
        ))
    if hard_location and loc_raw:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"hard location requirement ({loc_raw})",
            source="LOCATION_REQUIREMENT",
            confidence=None,
            details=str(loc_raw),
        ))
    if sen_determined and seniority:
        evidence.append(OpportunityEvidence(
            signal="SHORTLISTING_STRICTNESS",
            reason=f"explicit seniority requirement ({seniority})",
            source="REQUIREMENT",
            confidence=None,
            details=str(seniority),
        ))

    hard_non_skill = len(mandatory_certs[:2]) + edu_constraint + (1 if domain_hit else 0) + (1 if hard_location else 0)
    total = (
        (1 if exp_present else 0)
        + (1 if exp_narrow else 0)
        + n_required
        + len(mandatory_certs[:2])
        + edu_constraint
        + (1 if domain_hit else 0)
        + (1 if hard_location else 0)
        + (1 if sen_determined else 0)
    )

    def _determined(level: OpportunitySignalLevel) -> OpportunitySignal:
        return OpportunitySignal(level=level, status=OpportunityDeterminationStatus.DETERMINED, confidence=None, evidence=evidence)

    # ── HIGH: multiple restrictive mandatory filters or very narrow profile ──
    if n_required >= HIGH_REQUIRED_SKILLS and (exp_present or mandatory_certs or domain_hit or hard_location):
        return _determined(OpportunitySignalLevel.HIGH)
    if exp_narrow and n_required >= 5 and (mandatory_certs or domain_hit or hard_location or edu_constraint):
        return _determined(OpportunitySignalLevel.HIGH)
    if hard_non_skill >= 2 and n_required >= HIGH_REQUIRED_SKILLS - 2:
        return _determined(OpportunitySignalLevel.HIGH)
    if total >= HIGH_TOTAL_CONSTRAINTS:
        return _determined(OpportunitySignalLevel.HIGH)

    # ── MODERATE: meaningful required constraints, not highly restrictive ──
    if exp_present and n_required >= 3:
        return _determined(OpportunitySignalLevel.MODERATE)
    if n_required >= MODERATE_REQUIRED_SKILLS:
        return _determined(OpportunitySignalLevel.MODERATE)
    if total >= MODERATE_TOTAL_CONSTRAINTS:
        return _determined(OpportunitySignalLevel.MODERATE)
    if (mandatory_certs or domain_hit or hard_location or edu_constraint) and n_required >= 2:
        return _determined(OpportunitySignalLevel.MODERATE)
    if exp_narrow and n_required >= 2:
        return _determined(OpportunitySignalLevel.MODERATE)
    if exp_present and (exp_min or 0) >= MIN_EXPERIENCE_FOR_MODERATE and n_required >= 2:
        return _determined(OpportunitySignalLevel.MODERATE)

    return _determined(OpportunitySignalLevel.LOW)


def evaluate_background_fit_sensitivity(job_profile) -> OpportunitySignal:
    """Deterministic, side-effect free evaluator over structured Job Intelligence.

    Describes the JOB's transferability requirements, never the candidate.
    Company industry, title prestige, seniority, generic tech stack, and bare
    years-of-experience never count. Required domain/background evidence can
    yield HIGH; preferred-only evidence yields at most MODERATE. Sparse or
    unavailable evidence yields UNKNOWN/UNDETERMINED (never LOW).
    Input is never mutated.
    """
    from core.models.job_intelligence import JobProvenance

    def _unknown() -> OpportunitySignal:
        return OpportunitySignal(
            level=OpportunitySignalLevel.UNKNOWN,
            status=OpportunityDeterminationStatus.UNDETERMINED,
            confidence=None,
            evidence=[],
        )

    if job_profile is None:
        return _unknown()

    key_requirements = list(getattr(job_profile, "key_requirements", None) or [])
    qualifications = list(getattr(job_profile, "qualifications", None) or [])
    has_description = bool(getattr(job_profile, "has_description", False))
    req_text = " ".join(str(x) for x in key_requirements)
    qual_text = " ".join(str(x) for x in qualifications)
    low_req = req_text.lower()
    low_qual = qual_text.lower()

    def _has_hint(text: str) -> bool:
        return any(h in text for h in _MANDATORY_HINTS)

    # Mandatory domain hits: domain term + mandatory hint + background context,
    # all inside the structured requirements section (never company/title alone).
    mandatory_domain: List[str] = []
    for kw in _BACKGROUND_DOMAIN_KEYWORDS:
        if kw in low_req and _has_hint(low_req) and any(c in low_req for c in _BACKGROUND_CONTEXT_WORDS):
            mandatory_domain.append(kw)
    # Mandatory specialized-platform implementation hits.
    mandatory_platform: List[str] = []
    for plat in _SPECIALIZED_PLATFORMS:
        if plat in low_req and _has_hint(low_req) and any(
            w in low_req for w in ("implementation", "implement", "migration", "cpq")
        ):
            mandatory_platform.append(plat)
    # Preferred-only domain context: term in qualifications (preferred sections)
    # or in requirements without mandatory force. Never HIGH on its own.
    preferred_domain: List[str] = []
    for kw in _BACKGROUND_DOMAIN_KEYWORDS + _SPECIALIZED_PLATFORMS:
        if kw in low_qual and kw not in mandatory_domain and kw not in mandatory_platform:
            preferred_domain.append(kw)
    if not mandatory_domain and not mandatory_platform:
        for kw in _BACKGROUND_DOMAIN_KEYWORDS + _SPECIALIZED_PLATFORMS:
            if kw in low_req and kw not in preferred_domain:
                preferred_domain.append(kw)

    # ── UNKNOWN rule first: insufficient evidence must not become LOW ──
    # Requirements/qualifications sections are the inspected surface. If neither
    # was extracted (sparse prose, parser miss), there is no defensible basis:
    # UNKNOWN, even for long JDs. If sections were inspected, absence of domain
    # terms is determined absence and may support LOW below.
    if not has_description or (not req_text.strip() and not qual_text.strip()):
        return _unknown()

    evidence: List[OpportunityEvidence] = []
    for kw in mandatory_domain:
        evidence.append(OpportunityEvidence(
            signal="BACKGROUND_FIT_SENSITIVITY",
            reason=f"mandatory {kw} domain/background experience",
            source="DOMAIN_REQUIREMENT",
            confidence=None,
            details=str(kw),
        ))
    for plat in mandatory_platform:
        evidence.append(OpportunityEvidence(
            signal="BACKGROUND_FIT_SENSITIVITY",
            reason=f"mandatory prior {plat} implementation experience",
            source="DOMAIN_REQUIREMENT",
            confidence=None,
            details=str(plat),
        ))
    for kw in preferred_domain[:3]:
        evidence.append(OpportunityEvidence(
            signal="BACKGROUND_FIT_SENSITIVITY",
            reason=f"preferred {kw} background context (transferable)",
            source="DOMAIN_REQUIREMENT",
            confidence=None,
            details=str(kw),
        ))

    def _determined(level: OpportunitySignalLevel) -> OpportunitySignal:
        return OpportunitySignal(level=level, status=OpportunityDeterminationStatus.DETERMINED, confidence=None, evidence=evidence)

    # ── HIGH: strong explicit mandatory background filters ──
    if mandatory_domain or mandatory_platform:
        return _determined(OpportunitySignalLevel.HIGH)
    # ── MODERATE: meaningful preferred/transferable context, not exclusive ──
    if preferred_domain:
        return _determined(OpportunitySignalLevel.MODERATE)
    return _determined(OpportunitySignalLevel.LOW)


def _fresh_within_days(date_str: Optional[str], days: int = _FRESH_WINDOW_DAYS) -> bool:
    """True if the ISO date is within the freshness window. Unparseable/missing -> False (never decisive alone)."""
    if not date_str:
        return False
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days <= days
    except Exception:
        return False


def evaluate_competition_intensity(job_profile) -> OpportunitySignal:
    """Deterministic, side-effect free ESTIMATE of crowding from job/context signals.

    Consumes only structured Job Intelligence (role family, location, required
    skills, seniority, experience range, dates). Never candidate data, Match,
    Priority, applicant counts, views, company prestige, or source counts.
    Counts independent broadening indicators; any single one alone (remote,
    title, freshness, seniority, company) can never decide HIGH or LOW.
    Input is never mutated.
    """
    from core.models.job_intelligence import JobProvenance

    def _unknown() -> OpportunitySignal:
        return OpportunitySignal(
            level=OpportunitySignalLevel.UNKNOWN,
            status=OpportunityDeterminationStatus.UNDETERMINED,
            confidence=None,
            evidence=[],
        )

    if job_profile is None:
        return _unknown()

    role_family = str(getattr(job_profile, "role_family", None) or "").lower()
    title = str(getattr(job_profile, "title", None) or "")
    loc = getattr(job_profile, "location", None)
    remote_type = str(getattr(loc, "remote_type", "unknown") if loc else "unknown").lower()
    loc_raw = str(getattr(loc, "raw", None) or getattr(loc, "normalized", None) or "").strip()
    required_skills = list(getattr(job_profile, "required_skills", None) or [])
    req_names = [str(getattr(s, "normalized_name", "") or "") for s in required_skills]
    n_required = len(req_names)
    exp_years = getattr(job_profile, "experience_years", None)
    exp_prov = getattr(job_profile, "experience_provenance", JobProvenance.SOURCE_UNAVAILABLE)
    seniority = str(getattr(job_profile, "seniority", None) or "").upper() or None
    sen_prov = getattr(job_profile, "seniority_provenance", JobProvenance.SOURCE_UNAVAILABLE)
    has_description = bool(getattr(job_profile, "has_description", False))
    discovered = getattr(job_profile, "discovered_date", None) or getattr(job_profile, "posted_date", None)

    # ── Broadening indicators (each necessary-never-sufficient alone) ──
    broad_role = role_family in _BROAD_ROLE_FAMILIES
    geo_open = remote_type == "remote" or not loc_raw
    common_skills = (
        n_required >= 3 and all(n in _COMMON_TRANSFERABLE_SKILLS for n in req_names)
    )
    fresh = _fresh_within_days(discovered)
    broad_count = sum([broad_role, geo_open, common_skills, fresh])

    # ── Narrowing factors (supporting evidence for LOW only) ──
    hard_city = (
        remote_type == "onsite" and bool(loc_raw)
    )
    senior_bar = bool(seniority) and seniority in _NARROWING_SENIORITY and sen_prov == JobProvenance.DETERMINED_REQUIREMENT
    _, _, exp_narrow = _parse_experience_span(exp_years) if exp_prov == JobProvenance.DETERMINED_REQUIREMENT else (None, None, False)
    specialized_pool = (
        n_required >= 2 and sum(1 for n in req_names if n not in _COMMON_TRANSFERABLE_SKILLS) > n_required / 2
    )
    narrow_count = sum([hard_city, senior_bar, exp_narrow, specialized_pool])

    # ── UNKNOWN rule first: sparse metadata must not become LOW ──
    has_role = bool(role_family or title.strip())
    has_geo = bool(loc_raw or remote_type != "unknown")
    has_reqs = bool(n_required or (exp_years and exp_prov == JobProvenance.DETERMINED_REQUIREMENT))
    if not has_description and n_required == 0:
        return _unknown()
    if sum([has_role, has_geo, has_reqs]) < 2:
        return _unknown()

    evidence: List[OpportunityEvidence] = []
    if broad_role:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason=f"common role family ({role_family}) with a broad candidate pool",
            source="ROLE_FAMILY",
            confidence=None,
            details=str(role_family),
        ))
    if geo_open:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason="no location restriction (remote or no stated work location)",
            source="LOCATION",
            confidence=None,
            details=remote_type,
        ))
    if common_skills:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason=f"{n_required} required skills, all widely transferable",
            source="REQUIREMENT",
            confidence=None,
            details=", ".join(req_names[:6]),
        ))
    if fresh:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason="recently posted/discovered opportunity",
            source="FRESHNESS",
            confidence=None,
            details=str(discovered),
        ))
    if hard_city and loc_raw:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason=f"onsite requirement narrows the pool ({loc_raw})",
            source="LOCATION",
            confidence=None,
            details=str(loc_raw),
        ))
    if senior_bar and seniority:
        evidence.append(OpportunityEvidence(
            signal="COMPETITION_INTENSITY",
            reason=f"explicit seniority bar ({seniority}) narrows the pool",
            source="REQUIREMENT",
            confidence=None,
            details=str(seniority),
        ))

    def _determined(level: OpportunitySignalLevel, ev: List[OpportunityEvidence]) -> OpportunitySignal:
        return OpportunitySignal(level=level, status=OpportunityDeterminationStatus.DETERMINED, confidence=None, evidence=ev)

    # ── HIGH: multiple independent broad-pool indicators ──
    if broad_count >= 3:
        return _determined(OpportunitySignalLevel.HIGH, evidence)
    # ── LOW: at most one broad indicator plus genuine narrowing ──
    if broad_count <= 1 and narrow_count >= 1:
        return _determined(OpportunitySignalLevel.LOW, evidence)
    # ── MODERATE: mixed or default determined state ──
    return _determined(OpportunitySignalLevel.MODERATE, evidence)


class OpportunityIntelligenceService:
    """Constructs results; persists only if 012 table exists (no runtime DDL)."""

    def build_for_job(self, job: Dict[str, Any] | None) -> OpportunityIntelligence:
        job_id = None
        try:
            if isinstance(job, dict):
                job_id = job.get("id")
        except Exception:
            job_id = None
        # Competition (Phase 19), Background (Phase 18), Shortlisting (Phase 17)
        # are computed independently from the same profile; none influences the others.
        shortlisting = OpportunitySignal()
        background = OpportunitySignal()
        competition = OpportunitySignal()
        whole_evidence: List[OpportunityEvidence] = []
        try:
            from core.services.job_intelligence_service import get_job_intelligence_service
            j_service = get_job_intelligence_service()
            profile = j_service.build_job_intelligence(job or {})
            shortlisting = evaluate_shortlisting_strictness(profile)
            background = evaluate_background_fit_sensitivity(profile)
            competition = evaluate_competition_intensity(profile)
            whole_evidence = list(shortlisting.evidence) + list(background.evidence) + list(competition.evidence)
        except Exception:
            shortlisting = OpportunitySignal()
            background = OpportunitySignal()
            competition = OpportunitySignal()
            whole_evidence = []
        determination = (
            OpportunityDeterminationStatus.DETERMINED
            if shortlisting.status == OpportunityDeterminationStatus.DETERMINED
            or background.status == OpportunityDeterminationStatus.DETERMINED
            or competition.status == OpportunityDeterminationStatus.DETERMINED
            else OpportunityDeterminationStatus.UNDETERMINED
        )
        return OpportunityIntelligence(
            job_id=job_id,
            competition_intensity=competition,
            background_fit_sensitivity=background,
            shortlisting_strictness=shortlisting,
            determination_status=determination,
            evidence=whole_evidence,
            confidence=None,
            computed_at=_now(),
        )

    def get_for_job(self, job_id: int) -> Optional[OpportunityIntelligence]:
        """Return persisted record if present, else lazily compute UNKNOWN foundation (no write)."""
        persisted = self._load_persisted(job_id)
        if persisted is not None:
            return persisted
        # Lazily compute foundation without persisting (cheap, no N+1 risk for single job).
        # TEST-aware fetch (like StudioService._safe_conn) so isolated tests do not hit production.
        job = _fetch_job_record(job_id)
        if not job:
            return None
        return self.build_for_job(job)

    def save_for_job(self, job_id: int, result: Optional[OpportunityIntelligence] = None) -> Optional[OpportunityIntelligence]:
        """Persist result if 012 table exists; preserve unrelated signals; fail-open if missing."""
        if result is None:
            try:
                from core.services.job_intelligence_service import get_job_intelligence_service
                result = self.build_for_job(_fetch_job_record(job_id) or {"id": job_id})
            except Exception:
                result = build_foundation(job_id=job_id)
        else:
            # Preserve background/shortlisting already stored (only competition updates
            # in Phase 19; Phases 17-18 signals must remain intact).
            try:
                existing = self._load_persisted(job_id)
                if existing is not None:
                    merged_evidence = (
                        [e for e in existing.evidence if e.signal != "COMPETITION_INTENSITY"]
                        + [e for e in result.evidence if e.signal == "COMPETITION_INTENSITY"]
                    )
                    det = (
                        OpportunityDeterminationStatus.DETERMINED
                        if existing.shortlisting_strictness.status == OpportunityDeterminationStatus.DETERMINED
                        or existing.background_fit_sensitivity.status == OpportunityDeterminationStatus.DETERMINED
                        or result.competition_intensity.status == OpportunityDeterminationStatus.DETERMINED
                        else OpportunityDeterminationStatus.UNDETERMINED
                    )
                    result = result.model_copy(update={
                        "background_fit_sensitivity": existing.background_fit_sensitivity,
                        "shortlisting_strictness": existing.shortlisting_strictness,
                        "determination_status": det,
                        "evidence": merged_evidence,
                    })
            except Exception:
                pass
        try:
            from core.services.application_service import _resolve_database_url
            import psycopg2

            url = _resolve_database_url()
            if not url:
                return result
            conn = psycopg2.connect(url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO job_opportunity_intelligence
                           (job_id, competition_intensity, background_fit_sensitivity, shortlisting_strictness,
                            determination_status, evidence_json, confidence, computed_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (job_id) DO UPDATE SET
                             competition_intensity=EXCLUDED.competition_intensity,
                             background_fit_sensitivity=EXCLUDED.background_fit_sensitivity,
                             shortlisting_strictness=EXCLUDED.shortlisting_strictness,
                             determination_status=EXCLUDED.determination_status,
                             evidence_json=EXCLUDED.evidence_json,
                             confidence=EXCLUDED.confidence,
                             computed_at=EXCLUDED.computed_at""",
                        (
                            job_id,
                            result.competition_intensity.level.value,
                            result.background_fit_sensitivity.level.value,
                            result.shortlisting_strictness.level.value,
                            result.determination_status.value,
                            json.dumps([e.model_dump() for e in result.evidence]),
                            result.confidence,
                            result.computed_at or _now(),
                        ),
                    )
                conn.commit()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            # Missing table or DB unavailable: fail-open, do not break Job Details
            logger.debug("[opportunity] persist skipped: %s", type(e).__name__)
        return result

    def _load_persisted(self, job_id: int) -> Optional[OpportunityIntelligence]:
        try:
            from core.services.application_service import _resolve_database_url
            import psycopg2
            from psycopg2.extras import RealDictCursor

            url = _resolve_database_url()
            if not url:
                return None
            conn = psycopg2.connect(url)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM job_opportunity_intelligence WHERE job_id=%s", (job_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    d = dict(row)
                    evidence = []
                    if d.get("evidence_json"):
                        try:
                            raw = json.loads(d["evidence_json"]) if isinstance(d["evidence_json"], str) else d["evidence_json"]
                            from core.models.opportunity_intelligence import OpportunityEvidence
                            evidence = [OpportunityEvidence(**e) for e in (raw or []) if isinstance(e, dict)]
                        except Exception:
                            evidence = []
                    def _sig(col: str) -> OpportunitySignal:
                        try:
                            lvl = OpportunitySignalLevel(d.get(col) or "UNKNOWN")
                        except Exception:
                            lvl = OpportunitySignalLevel.UNKNOWN
                        st = (
                            OpportunityDeterminationStatus.UNDETERMINED
                            if lvl == OpportunitySignalLevel.UNKNOWN
                            else OpportunityDeterminationStatus.DETERMINED
                        )
                        return OpportunitySignal(level=lvl, status=st, confidence=d.get("confidence"), evidence=[])
                    try:
                        det = OpportunityDeterminationStatus(d.get("determination_status") or "UNDETERMINED")
                    except Exception:
                        det = OpportunityDeterminationStatus.UNDETERMINED
                    short_sig = _sig("shortlisting_strictness")
                    if short_sig.status == OpportunityDeterminationStatus.DETERMINED:
                        short_sig = short_sig.model_copy(update={"evidence": [e for e in evidence if e.signal == "SHORTLISTING_STRICTNESS"] or evidence})
                    comp_sig = _sig("competition_intensity")
                    if comp_sig.status == OpportunityDeterminationStatus.DETERMINED:
                        comp_sig = comp_sig.model_copy(update={"evidence": [e for e in evidence if e.signal == "COMPETITION_INTENSITY"] or evidence})
                    bg_sig = _sig("background_fit_sensitivity")
                    if bg_sig.status == OpportunityDeterminationStatus.DETERMINED:
                        bg_sig = bg_sig.model_copy(update={"evidence": [e for e in evidence if e.signal == "BACKGROUND_FIT_SENSITIVITY"] or evidence})
                    return OpportunityIntelligence(
                        job_id=job_id,
                        competition_intensity=comp_sig,
                        background_fit_sensitivity=bg_sig,
                        shortlisting_strictness=short_sig,
                        determination_status=det,
                        evidence=evidence,
                        confidence=d.get("confidence"),
                        computed_at=d.get("computed_at"),
                    )
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            # Debug-only diagnostic so operators can distinguish "computed but
            # persistence unavailable" (e.g. 012 not applied) from other states.
            # Silent at default INFO level; nothing reaches the browser.
            logger.debug("[opportunity] load skipped: %s", type(e).__name__)
            return None
        return None


_service: Optional[OpportunityIntelligenceService] = None


def get_opportunity_intelligence_service() -> OpportunityIntelligenceService:
    global _service
    if _service is None:
        _service = OpportunityIntelligenceService()
    return _service
