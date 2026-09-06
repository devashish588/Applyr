"""
Application Priority Service — deterministic tier ranking
=========================================================

Precedence:
  1. UNKNOWN count >=2 → REVIEW
  2. required skill MISSING → COLD
  3. seniority LOWER_THAN_REQUIRED → COLD
  4. UNKNOWN count ==1 → WARM
  5. else fresh → HOT else WARM

No numeric score, no probability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from core.models.application_priority import ApplicationPriority
from core.models.match_engine import MatchResult, RequirementStatus
from core.services.job_quality_service import assess_job_quality


def _parse_discovered(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Handle ISO with or without timezone
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _freshness(discovered: Optional[str]) -> str:
    dt = _parse_discovered(discovered)
    if dt is None:
        return "UNKNOWN"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (now - dt).days
    if days <= 14:
        return "fresh"
    if days > 30:
        return "stale"
    return "fresh"  # 15-30 considered fresh enough for WARM, not stale


def _count_unknown(match_result: MatchResult) -> int:
    cnt = 0
    for ev in match_result.requirement_evaluations:
        if ev.status == RequirementStatus.UNKNOWN:
            cnt += 1
    for ev in match_result.experience_evaluations:
        if ev.status == RequirementStatus.UNKNOWN:
            cnt += 1
    for ev in match_result.role_evaluations:
        if ev.status == RequirementStatus.UNKNOWN:
            cnt += 1
    for ev in match_result.location_evaluations:
        if ev.status == RequirementStatus.UNKNOWN:
            cnt += 1
    for ev in match_result.seniority_evaluations:
        if ev.status == RequirementStatus.UNKNOWN:
            cnt += 1
    return cnt


def _has_required_skill_missing(match_result: MatchResult) -> bool:
    for ev in match_result.requirement_evaluations:
        if ev.requirement.required and ev.status == RequirementStatus.MISSING:
            return True
    return False


def _has_seniority_lower(match_result: MatchResult) -> bool:
    for ev in match_result.seniority_evaluations:
        if ev.relationship == "LOWER_THAN_REQUIRED" and ev.status == RequirementStatus.MISSING:
            return True
        # Alternative: status MISSING with LOWER relationship
        if ev.status == RequirementStatus.MISSING and ev.relationship == "LOWER_THAN_REQUIRED":
            return True
    return False


def _has_seniority_missing(match_result: MatchResult) -> bool:
    # Seniority MISSING is always LOWER_THAN_REQUIRED per SeniorityMatcher
    for ev in match_result.seniority_evaluations:
        if ev.status == RequirementStatus.MISSING:
            return True
    return False


class ApplicationPriorityService:
    def evaluate(
        self,
        job_id: int,
        match_result: MatchResult,
        discovered_date: Optional[str],
        has_description: bool,
        source: Optional[str],
        application_url: Optional[str],
        recruiter_email_exists: bool,
    ) -> ApplicationPriority:
        unknown_cnt = _count_unknown(match_result)
        has_required_missing = _has_required_skill_missing(match_result)
        has_seniority_lower = _has_seniority_missing(match_result)  # all seniority MISSING is LOWER in this model

        # Freshness
        fresh_status = _freshness(discovered_date)
        is_fresh = fresh_status == "fresh"

        # Job quality factors (explainable, not scored)
        quality_factors = assess_job_quality(has_description, source, application_url)

        # Precedence
        if unknown_cnt >= 2:
            tier = "REVIEW"
            explanation = f"Insufficient evidence: {unknown_cnt} dimensions UNKNOWN."
        elif has_required_missing:
            tier = "COLD"
            explanation = "Missing required skill."
        elif has_seniority_lower:
            tier = "COLD"
            explanation = "Seniority below required level."
        elif unknown_cnt == 1:
            tier = "WARM"
            explanation = "One dimension UNKNOWN, no required blocker."
        else:
            if is_fresh:
                tier = "HOT"
                explanation = "Strong determined fit with no required blockers and fresh discovery."
            else:
                tier = "WARM"
                explanation = "Strong fit but not fresh or freshness unknown."

        # Factors
        req_satisfied = sum(1 for e in match_result.requirement_evaluations if e.status == RequirementStatus.SATISFIED)
        req_missing = sum(1 for e in match_result.requirement_evaluations if e.status == RequirementStatus.MISSING and e.requirement.required)
        factors: Dict[str, str] = {
            "match": f"{req_satisfied} required satisfied, {req_missing} required missing, {unknown_cnt} UNKNOWN",
            "freshness": f"{fresh_status} ({discovered_date or 'unknown'})" if fresh_status != "UNKNOWN" else "UNKNOWN",
            "recruiter": "email available" if recruiter_email_exists else "no email",
            "completeness": f"{match_result.analysis_completeness}",
            "effort": "UNKNOWN",
            "job_quality": f"description {'available' if has_description else 'unavailable'}, source {'identified' if source else 'unknown'}, URL {'available' if application_url else 'unavailable'}",
        }

        uncertainty: List[str] = []
        for ev in match_result.requirement_evaluations + match_result.experience_evaluations + match_result.role_evaluations + match_result.location_evaluations + match_result.seniority_evaluations:
            if ev.status == RequirementStatus.UNKNOWN:
                raw = None
                # RequirementEvaluation / ExperienceEvaluation have .requirement
                if hasattr(ev, "requirement") and ev.requirement is not None:
                    raw = getattr(ev.requirement, "raw", None) or getattr(ev.requirement, "raw_name", None)
                # Role/Location/Seniority have job_raw / candidate_raw
                if not raw:
                    raw = getattr(ev, "job_raw", None) or getattr(ev, "candidate_raw", None)
                if not raw:
                    raw = ev.__class__.__name__
                # Truncate if needed
                raw_str = str(raw)[:60] if raw else ev.__class__.__name__
                uncertainty.append(f"{raw_str} UNKNOWN — provenance unavailable")

        return ApplicationPriority(
            job_id=job_id,
            tier=tier,
            factors=factors,
            explanation=explanation,
            uncertainty=uncertainty,
        )

    def rank(
        self,
        items: List[Tuple[int, MatchResult, Optional[str], bool, Optional[str], Optional[str], bool]],
    ) -> List[Tuple[int, ApplicationPriority]]:
        """Rank list of (job_id, match_result, discovered_date, has_description, source, application_url, recruiter_email_exists)."""
        scored: List[Tuple[int, ApplicationPriority]] = []
        for job_id, mr, disc, has_desc, src, url, rec in items:
            pri = self.evaluate(job_id, mr, disc, has_desc, src, url, rec)
            scored.append((job_id, pri))

        tier_order = {"HOT": 0, "WARM": 1, "COLD": 2, "REVIEW": 3}

        def sort_key(item: Tuple[int, ApplicationPriority]):
            pri = item[1]
            # Fresh first, then recruiter, then discovered desc, then job_id asc
            # For tie-break, we need discovered_date; retrieve from original items
            # Find original discovered for this job_id
            orig = next((x for x in items if x[0] == item[0]), None)
            disc = orig[2] if orig else None
            dt = _parse_discovered(disc)
            # Use timestamp for descending (fresh first)
            ts = dt.timestamp() if dt else 0
            # Recruiter true first
            rec = 0 if item[1].factors.get("recruiter") == "email available" else 1
            return (tier_order.get(pri.tier, 4), rec, -ts, item[0])

        scored.sort(key=sort_key)
        return scored


_service: Optional[ApplicationPriorityService] = None


def get_priority_service() -> ApplicationPriorityService:
    global _service
    if _service is None:
        _service = ApplicationPriorityService()
    return _service
