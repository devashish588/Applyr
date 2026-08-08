"""
Match Service -- Unified job scoring engine
============================================

Single source of truth for:
- Job scoring & recommendation
- Match breakdown for UI panels
- Email generation (avoids claiming missing skills)
- Resume tailoring (skills to highlight)
- "Why this score?" explanations

Weights: 40% Skill | 25% Experience | 20% Role | 10% Location | 5% Seniority
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from core.models import (
    MatchAnalysis,
    MatchComponent,
    Job,
    Profile,
    Resume,
    SeniorityLevel,
)
from core.schemas import (
    MatchAnalysis as SchemaMatchAnalysis,
    ResumeParsed,
    to_resume_parsed,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Positional safety guards (PR-4)
# ---------------------------------------------------------------------------

_RESUME_KEYS = {"skills", "experience", "raw_text", "skills_categorized", "education"}
_JOB_KEYS = {"title", "jd_text", "required_skills", "company"}


def _is_resume_object(obj: Any) -> bool:
    """Return True only if *obj* is a ResumeParsed, Resume, or dict that
    structurally looks like a resume. Ordinary ints / strings / lists never pass."""
    if isinstance(obj, (ResumeParsed, Resume)):
        return True
    if isinstance(obj, dict):
        return bool(_RESUME_KEYS & set(obj.keys()))
    return False


def _is_job_object(obj: Any) -> bool:
    """Return True only if *obj* is a Job model or a dict that structurally
    looks like a job. Ordinary ints / strings / lists never pass."""
    if isinstance(obj, Job):
        return True
    if isinstance(obj, dict):
        return bool(_JOB_KEYS & set(obj.keys()))
    return False


class MatchService:
    """Unified job scoring engine. Produces a single MatchAnalysis used by all consumers."""

    SKILL_WEIGHT = 0.40
    EXPERIENCE_WEIGHT = 0.25
    ROLE_WEIGHT = 0.20
    LOCATION_WEIGHT = 0.10
    SENIORITY_WEIGHT = 0.05

    def __init__(self, profile: Optional[Profile] = None, resume: Optional[Resume] = None):
        self.profile = profile or Profile()
        self.resume = resume

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        job_id: Any = 0,
        job_title: str = "",
        job_location: str = "",
        jd_text: str = "",
        required_skills: Optional[List[str]] = None,
        resume: Optional[Any] = None,
        job: Optional[Any] = None,
    ) -> MatchAnalysis:
        """Run full match analysis for a single job.

        Supports calling conventions:
        - Legacy positional: analyze(101, "Title", "Location", "JD text", ["Python"])
        - Legacy keyword: analyze(job_id=101, job_title="Title", ...)
        - New positional: analyze(resume_obj, job_obj)
        - New keyword: analyze(resume=resume_obj, job=job_obj)
        """
        # Resolve positional resume/job inputs safely via guards
        effective_resume = resume
        effective_job = job

        if effective_resume is None and effective_job is None:
            if _is_resume_object(job_id) and _is_job_object(job_title):
                effective_resume = job_id
                effective_job = job_title
                job_id = 0
                job_title = ""

        # Coerce candidate resume cleanly without mutating self.resume
        active_resume = self._coerce_resume(effective_resume) if effective_resume is not None else self.resume

        # Extract job attributes if a job object was provided
        if effective_job is not None:
            jd = effective_job.model_dump() if isinstance(effective_job, Job) else (effective_job if isinstance(effective_job, dict) else {})
            job_id = jd.get("id") or jd.get("job_id") or job_id
            job_title = jd.get("title") or jd.get("job_title") or job_title
            job_location = jd.get("location") or jd.get("job_location") or job_location
            jd_text = jd.get("jd_text") or jd.get("description") or jd_text
            required_skills = jd.get("required_skills") or required_skills

        # None-resume guard: return safe result if no resume is available
        if active_resume is None:
            return self._empty_analysis(job_id, job_title)

        skills = required_skills or []
        candidate_name = active_resume.name if active_resume else None
        candidate_roles = (
            self.profile.target_roles
            or self.profile.inferred_roles
            or (active_resume.roles if active_resume else [])
        )

        # Detect seniority levels
        candidate_seniority = self._detect_candidate_seniority(active_resume)
        job_seniority = SeniorityLevel.detect_from_title(job_title)

        # --- Component scoring ---
        skill_match = self._score_skills(jd_text, skills, active_resume)
        experience_match = self._score_experience(jd_text, active_resume)
        role_match = self._score_role(job_title, candidate_roles)
        location_match = self._score_location(job_location)
        seniority_match = self._score_seniority(candidate_seniority, job_seniority)

        # Seniority penalty
        seniority_penalty = SeniorityLevel.penalty(candidate_seniority, job_seniority)

        # Compute weighted final score & integer clamping
        components = [skill_match, experience_match, role_match, location_match, seniority_match]
        raw_score = sum(c.score * c.weight for c in components)
        final_score = max(0, min(100, raw_score - seniority_penalty * 0.05 * 100))
        final_score_int = max(0, min(100, int(round(final_score))))

        # Recommendation
        if final_score_int >= 70:
            recommendation = "Apply"
        elif final_score_int >= 50:
            recommendation = "Consider"
        else:
            recommendation = "Skip"

        # Skills to highlight (top 5 matched skills)
        skills_to_highlight = skill_match.matched[:5]

        # Matched/missing requirements
        matched_reqs = [f"Skill: {s}" for s in skill_match.matched]
        matched_reqs += [f"Role: matches {job_title}"] if role_match.score >= 50 else []
        matched_reqs += [f"Location: {job_location}"] if location_match.score >= 50 else []
        if experience_match.score >= 50:
            matched_reqs += ["Experience level aligned"]

        missing_reqs = [f"Missing skill: {s}" for s in skill_match.missing]
        missing_reqs += ["Seniority gap"] if seniority_penalty > 0 else []
        if role_match.score < 50:
            missing_reqs += [f"Role mismatch with {job_title}"]
        if location_match.score < 50 and location_match.score > 0:
            missing_reqs += [f"Location mismatch: {job_location}"]

        # Explanations & supporting evidence
        why = self._build_why_this_score(
            skill_match, experience_match, role_match,
            location_match, seniority_match, seniority_penalty, final_score_int
        )
        explanation = (
            f"Candidate {'matches' if final_score_int >= 50 else 'falls short of'} "
            f"job requirements with a {final_score_int}% match. "
            f"{len(skill_match.matched)} of {len(skills or [])} required skills matched. "
            f"Recommendation: {recommendation}."
        )
        supporting = self._build_supporting_sentences(
            skill_match, experience_match, role_match,
            location_match, seniority_match, seniority_penalty,
            job_title, job_location,
        )

        return MatchAnalysis(
            job_id=job_id,
            candidate_name=candidate_name,
            skill_match=skill_match,
            experience_match=experience_match,
            role_match=role_match,
            location_match=location_match,
            seniority_match=seniority_match,
            final_score=final_score_int,
            recommendation=recommendation,
            all_required_skills=skills,
            skills_to_highlight=skills_to_highlight,
            candidate_seniority=candidate_seniority.value if candidate_seniority else None,
            job_seniority=job_seniority.value if job_seniority else None,
            seniority_penalty=seniority_penalty,
            estimated_experience_years=self._estimate_experience_years(active_resume),
            explanation=explanation,
            why_this_score=why,
            matched_requirements=matched_reqs,
            missing_requirements=missing_reqs,
            analyzed_at=datetime.now().isoformat(),
        )

    def to_json(self, analysis: MatchAnalysis) -> str:
        """Serialize MatchAnalysis to JSON string for DB storage."""
        return analysis.model_dump_json()

    def from_json(self, json_str: str) -> Optional[MatchAnalysis]:
        """Deserialize MatchAnalysis from JSON string."""
        if not json_str:
            return None
        try:
            return MatchAnalysis.model_validate_json(json_str)
        except Exception as e:
            logger.warning("Failed to parse MatchAnalysis from JSON: %s", e)
            return None

    def to_schema(self, analysis: MatchAnalysis) -> SchemaMatchAnalysis:
        """Convert rich MatchAnalysis to compact core.schemas contract."""
        return SchemaMatchAnalysis(
            final_score=max(0, min(100, int(round(analysis.final_score)))),
            recommendation=analysis.recommendation,
            explanation=analysis.explanation,
            skills_to_highlight=list(analysis.skills_to_highlight),
            why_this_score=analysis.why_this_score,
            supporting_sentences=self._build_supporting_sentences(
                analysis.skill_match,
                analysis.experience_match,
                analysis.role_match,
                analysis.location_match,
                analysis.seniority_match,
                analysis.seniority_penalty,
            ),
        )

    # ------------------------------------------------------------------ #
    # Helper coercion and safe defaults
    # ------------------------------------------------------------------ #

    def _coerce_resume(self, obj: Any) -> Optional[Resume]:
        """Coerce a ResumeParsed, Resume, or dict into a Resume instance without state mutation."""
        if obj is None:
            return None
        if isinstance(obj, Resume):
            return obj
        if isinstance(obj, (ResumeParsed, dict)):
            try:
                rp = to_resume_parsed(obj) if isinstance(obj, dict) else obj
                return Resume(**rp.model_dump())
            except Exception:
                if isinstance(obj, dict):
                    return Resume(**obj)
                return Resume(**obj.model_dump())
        return None

    def _empty_analysis(self, job_id: Any = 0, job_title: str = "") -> MatchAnalysis:
        """Return a safe deterministic result when no candidate resume exists."""
        return MatchAnalysis(
            job_id=job_id,
            final_score=0,
            recommendation="Skip",
            explanation="No candidate resume provided — unable to evaluate match.",
            why_this_score="No candidate data available for scoring.",
            skills_to_highlight=[],
            matched_requirements=[],
            missing_requirements=[f"Resume required for matching against {job_title}" if job_title else "Resume required"],
            analyzed_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------ #
    # Skill Match (40%)
    # ------------------------------------------------------------------ #

    def _score_skills(
        self, jd_text: str, required_skills: List[str], resume: Optional[Resume] = None
    ) -> MatchComponent:
        """Score skill match: 40% of total."""
        candidate_skills = self._get_candidate_skills(resume)
        component = MatchComponent(weight=self.SKILL_WEIGHT, label="Skills Match", max_score=100)

        if not required_skills:
            component.score = 60
            component.details = ["No specific skills required listed"]
            component.matched = candidate_skills[:5]
            component.weighted_score = component.score * component.weight
            return component

        jd_lower = jd_text.lower() if jd_text else ""
        matched = []
        missing = []

        for skill in required_skills:
            skill_lower = skill.lower().strip()
            in_candidate = any(
                cs.lower() == skill_lower or cs.lower().startswith(skill_lower)
                for cs in candidate_skills
            )
            in_jd = skill_lower in jd_lower if jd_text else True

            if in_candidate or (in_candidate and in_jd):
                matched.append(skill)
            else:
                missing.append(skill)

        for cs in candidate_skills:
            cs_lower = cs.lower()
            if cs_lower in jd_lower and cs not in matched:
                matched.append(cs)

        total = len(required_skills) if required_skills else 1
        skill_ratio = len(matched) / max(total, 1)
        score = min(100, skill_ratio * 100)

        component.score = round(score, 1)
        component.matched = matched
        component.missing = missing
        component.details = [
            f"Matched {len(matched)} of {total} required skills",
            f"Missing {len(missing)} skills" if missing else "All required skills matched",
        ]
        component.weighted_score = component.score * component.weight
        return component

    # ------------------------------------------------------------------ #
    # Experience Match (25%)
    # ------------------------------------------------------------------ #

    def _score_experience(self, jd_text: str, resume: Optional[Resume] = None) -> MatchComponent:
        """Score experience match: 25% of total."""
        component = MatchComponent(weight=self.EXPERIENCE_WEIGHT, label="Experience Match", max_score=100)
        candidate_years = self._estimate_experience_years(resume)
        req_years = self._extract_required_years(jd_text)
        jd_lower = jd_text.lower() if jd_text else ""

        details = [f"Candidate has ~{candidate_years:.1f} years of experience"]

        if req_years:
            details.append(f"Job requires ~{req_years} years")
            if candidate_years >= req_years:
                ratio = min(1.0, candidate_years / max(req_years, 1))
                score = 60 + ratio * 40
                details.append("Meets experience requirement")
            elif candidate_years >= req_years * 0.7:
                score = 50
                details.append("Slightly below experience requirement")
            else:
                score = max(10, 50 * (candidate_years / max(req_years, 1)))
                details.append("Below experience requirement")
        else:
            if candidate_years >= 2:
                score = 85
                details.append("No specific experience requirement -- candidate has solid background")
            elif candidate_years >= 0.5:
                score = 65
                details.append("Entry-level position inferred")
            else:
                score = 40
                details.append("Limited experience detected")

        exp_buzzwords = [
            "led", "managed", "built", "designed", "developed", "architected",
            "team lead", "cross-functional", "stakeholder", "delivered",
            "migrated", "optimized", "scaled", "mentored", "owned"
        ]
        found_buzz = [w for w in exp_buzzwords if w in jd_lower]
        if found_buzz:
            bonus = min(15, len(found_buzz) * 3)
            score = min(100, score + bonus)
            details.append(f"Experience level bonus: +{bonus}")

        component.score = round(score, 1)
        component.details = details
        component.matched = [f"~{candidate_years:.1f} years experience"]
        if req_years and candidate_years < req_years:
            component.missing = [f"Requires ~{req_years} years (candidate has ~{candidate_years:.1f})"]
        else:
            component.missing = []
        component.weighted_score = component.score * component.weight
        return component

    # ------------------------------------------------------------------ #
    # Role Match (20%)
    # ------------------------------------------------------------------ #

    def _score_role(self, job_title: str, candidate_roles: List[str]) -> MatchComponent:
        """Score role match: 20% of total."""
        component = MatchComponent(weight=self.ROLE_WEIGHT, label="Role Match", max_score=100)
        job_lower = job_title.lower().strip() if job_title else ""

        if not job_lower or not candidate_roles:
            component.score = 50
            component.details = ["No role data available for comparison"]
            component.weighted_score = component.score * component.weight
            return component

        job_tokens = set(re.split(r"\W+", job_lower))
        job_tokens.discard("engineer")
        job_tokens.discard("developer")
        job_tokens.discard("manager")

        best_match = 0
        best_role = ""
        for role in candidate_roles:
            role_lower = role.lower()
            role_tokens = set(re.split(r"\W+", role_lower))

            if role_lower == job_lower:
                best_match = 100
                best_role = role
                break

            if role_lower in job_lower or job_lower in role_lower:
                best_match = max(best_match, 85)

            overlap = job_tokens & role_tokens
            if overlap:
                score = min(80, len(overlap) / max(len(job_tokens), 1) * 100)
                if score > best_match:
                    best_match = score
                    best_role = role

            role_words = set(role_lower.split())
            job_words = set(job_lower.split())
            word_overlap = role_words & job_words
            if word_overlap:
                score = min(70, len(word_overlap) / max(len(job_words), 1) * 100)
                if score > best_match:
                    best_match = score
                    best_role = role

        component.score = round(best_match, 1)
        component.matched = [best_role] if best_role else []
        component.missing = [job_title] if best_match < 50 else []
        component.details = [
            f"Candidate roles: {', '.join(candidate_roles[:3])}",
            f"Job title: {job_title}",
            f"Match quality: {'exact' if best_match >= 90 else 'strong' if best_match >= 70 else 'partial' if best_match >= 40 else 'weak'}",
        ]
        component.weighted_score = component.score * component.weight
        return component

    # ------------------------------------------------------------------ #
    # Location Match (10%)
    # ------------------------------------------------------------------ #

    def _score_location(self, job_location: str) -> MatchComponent:
        """Score location match: 10% of total."""
        component = MatchComponent(weight=self.LOCATION_WEIGHT, label="Location Match", max_score=100)
        loc_lower = job_location.lower().strip() if job_location else ""
        target_locs = [l.lower().strip() for l in self.profile.target_locations if l]
        remote_ok = self.profile.remote_ok

        if not loc_lower:
            component.score = 80
            component.details = ["No location specified -- assuming flexible"]
            component.weighted_score = component.score * component.weight
            return component

        is_remote = "remote" in loc_lower or "anywhere" in loc_lower

        if is_remote and remote_ok:
            component.score = 100
            component.details = ["Remote position + remote preference enabled"]
            component.matched = ["Remote work"]
            component.weighted_score = component.score * component.weight
            return component

        if is_remote:
            component.score = 70
            component.details = ["Remote position (no remote preference set)"]
            component.weighted_score = component.score * component.weight
            return component

        if target_locs:
            for target in target_locs:
                if target in loc_lower or loc_lower in target:
                    component.score = 100
                    component.details = [f"Location matches target: {job_location}"]
                    component.matched = [job_location]
                    component.weighted_score = component.score * component.weight
                    return component

            for target in target_locs:
                target_parts = set(re.split(r"[,/\s]+", target))
                loc_parts = set(re.split(r"[,/\s]+", loc_lower))
                overlap = target_parts & loc_parts
                if overlap:
                    overlap.discard("")
                    if overlap:
                        score = min(80, len(overlap) / max(len(loc_parts), 1) * 100)
                        component.score = round(score, 1)
                        component.details = [f"Partial location overlap: {', '.join(overlap)}"]
                        component.missing = [f"Preferred: {', '.join(target_locs)}"]
                        component.weighted_score = component.score * component.weight
                        return component

            component.score = 20
            component.details = [f"Location mismatch: {job_location} vs target {', '.join(target_locs)}"]
            component.missing = [f"Not in target locations: {', '.join(target_locs)}"]
            component.weighted_score = component.score * component.weight
            return component

        component.score = 60
        component.details = [f"Location: {job_location} (no location preference set)"]
        component.weighted_score = component.score * component.weight
        return component

    # ------------------------------------------------------------------ #
    # Seniority Match (5%)
    # ------------------------------------------------------------------ #

    def _score_seniority(
        self,
        candidate_seniority: Optional[SeniorityLevel],
        job_seniority: Optional[SeniorityLevel],
    ) -> MatchComponent:
        """Score seniority match: 5% of total."""
        component = MatchComponent(weight=self.SENIORITY_WEIGHT, label="Seniority Match", max_score=100)

        if not candidate_seniority or not job_seniority:
            component.score = 70
            component.details = ["Seniority comparison not available"]
            component.weighted_score = component.score * component.weight
            return component

        if candidate_seniority >= job_seniority:
            component.score = 100
            component.details = [f"Candidate: {candidate_seniority.value}, Job: {job_seniority.value}"]
            component.matched = [f"Candidate {candidate_seniority.value} meets {job_seniority.value} requirement"]
        else:
            gap = list(SeniorityLevel).index(job_seniority) - list(SeniorityLevel).index(candidate_seniority)
            penalty = SeniorityLevel.penalty(candidate_seniority, job_seniority)
            score = max(0, 100 - penalty * 2)
            component.score = round(score, 1)
            component.details = [
                f"Candidate: {candidate_seniority.value}, Job requires: {job_seniority.value}",
                f"Seniority gap: {gap} level(s), penalty: -{penalty} points",
            ]
            component.missing = [f"Job requires {job_seniority.value} level, candidate is {candidate_seniority.value}"]

        component.weighted_score = component.score * component.weight
        return component

    # ------------------------------------------------------------------ #
    # Internal Helpers
    # ------------------------------------------------------------------ #

    def _get_candidate_skills(self, resume: Optional[Resume] = None) -> List[str]:
        """Collect all candidate skills from profile and resume."""
        active_resume = resume or self.resume
        skills = []
        if active_resume and active_resume.skills:
            skills.extend(active_resume.skills)
        if self.profile.skills:
            for cat in self.profile.skills.values():
                if isinstance(cat, list):
                    skills.extend(cat)
        seen = set()
        deduped = []
        for s in skills:
            if s.lower() not in seen:
                seen.add(s.lower())
                deduped.append(s)
        return deduped

    def _estimate_experience_years(self, resume: Optional[Resume] = None) -> float:
        """Estimate total years of experience from resume."""
        active_resume = resume or self.resume
        if active_resume and active_resume.experience:
            total = 0.0
            for exp in active_resume.experience:
                start = exp.get("start_date", "") if isinstance(exp, dict) else getattr(exp, "start_date", "")
                end = exp.get("end_date") if isinstance(exp, dict) else getattr(exp, "end_date", None)
                start_year = self._extract_year(start)
                if start_year:
                    end_year = self._extract_year(end) if end else datetime.now().year
                    if end_year:
                        total += max(0, end_year - start_year)
            if total > 0:
                return round(total, 1)
        if active_resume and active_resume.roles:
            t = " ".join(active_resume.roles).lower()
            if "senior" in t or "staff" in t or "principal" in t:
                return 6.0
            if "mid" in t:
                return 3.0
            if "junior" in t:
                return 1.0
            if "intern" in t:
                return 0.0
        return 2.0

    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        if not date_str:
            return None
        date_str = str(date_str).strip().lower()
        if date_str in ("present", "current", "now", ""):
            return datetime.now().year
        match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if match:
            return int(match.group())
        return None

    def _extract_required_years(self, jd_text: str) -> Optional[float]:
        if not jd_text:
            return None
        jd_lower = jd_text.lower()
        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)",
            r"(?:experience|exp)\s*(?:of|:)?\s*(\d+)\+?\s*(?:years?|yrs?)",
            r"minimum\s*(?:of)?\s*(\d+)\+?\s*(?:years?|yrs?)",
            r"at\s*least\s*(\d+)\+?\s*(?:years?|yrs?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, jd_lower)
            if match:
                return float(match.group(1))
        return None

    def _detect_candidate_seniority(self, resume: Optional[Resume] = None) -> Optional[SeniorityLevel]:
        active_resume = resume or self.resume
        if active_resume and active_resume.roles:
            for role in active_resume.roles:
                detected = SeniorityLevel.detect_from_title(role)
                if detected:
                    return detected
        if self.profile.seniority:
            try:
                return SeniorityLevel(self.profile.seniority)
            except ValueError:
                pass
        years = self._estimate_experience_years(active_resume)
        return SeniorityLevel.from_years(years) if years > 0 else None

    def _build_why_this_score(
        self,
        skill: MatchComponent,
        experience: MatchComponent,
        role: MatchComponent,
        location: MatchComponent,
        seniority: MatchComponent,
        penalty: int,
        final_score: Union[int, float],
    ) -> str:
        lines = []
        if skill.matched:
            lines.append(f"Matched {len(skill.matched)} skills ({skill.score:.0f}%): {', '.join(skill.matched[:6])}")
        if skill.missing:
            lines.append(f"Missing {len(skill.missing)} skills: {', '.join(skill.missing[:6])}")
        lines.append(f"Skill weight: 40% x {skill.score:.0f} = {skill.score * 0.40:.1f} pts")
        lines.append(f"Experience: {experience.score:.0f}% | Weight 25% x {experience.score:.0f} = {experience.score * 0.25:.1f} pts")
        lines.append(f"Role: {role.score:.0f}% | Weight 20% x {role.score:.0f} = {role.score * 0.20:.1f} pts")
        lines.append(f"Location: {location.score:.0f}% | Weight 10% x {location.score:.0f} = {location.score * 0.10:.1f} pts")
        lines.append(f"Seniority: {seniority.score:.0f}% | Weight 5% x {seniority.score:.0f} = {seniority.score * 0.05:.1f} pts")
        if penalty > 0:
            lines.append(f"Seniority penalty: -{penalty * 0.05 * 100:.0f} pts (job exceeds candidate level)")
        raw = sum(c.score * c.weight for c in [skill, experience, role, location, seniority])
        lines.append(f"Raw weighted score: {raw:.1f}")
        if penalty > 0:
            lines.append(f"After penalty: {final_score:.0f}")
        lines.append(f"Final score: {final_score:.0f}")
        return "\n".join(lines)

    def _build_supporting_sentences(
        self,
        skill: MatchComponent,
        experience: MatchComponent,
        role: MatchComponent,
        location: MatchComponent,
        seniority: MatchComponent,
        penalty: int,
        job_title: str = "",
        job_location: str = "",
    ) -> List[str]:
        sentences: List[str] = []
        if skill.matched:
            top = ", ".join(skill.matched[:5])
            sentences.append(f"Candidate skills overlap with job requirements: {top}.")
        if skill.missing:
            top_miss = ", ".join(skill.missing[:5])
            sentences.append(f"Required skills not found in candidate profile: {top_miss}.")
        if experience.details:
            for d in experience.details[:2]:
                sentences.append(d)
        if role.matched:
            sentences.append(f"Candidate role '{role.matched[0]}' aligns with job title '{job_title}'.")
        elif role.score < 50 and job_title:
            sentences.append(f"Candidate roles do not closely match '{job_title}'.")
        if location.matched:
            sentences.append(f"Location match: {', '.join(location.matched)}.")
        elif location.score < 50 and job_location:
            sentences.append(f"Location '{job_location}' does not match candidate preferences.")
        if seniority.matched:
            sentences.append(seniority.matched[0])
        if penalty > 0 and seniority.missing:
            sentences.append(seniority.missing[0])
        return sentences


# Singleton-like factory
_match_service: Optional[MatchService] = None


def get_match_service(profile: Optional[Profile] = None, resume: Optional[Resume] = None) -> MatchService:
    """Get or create a MatchService instance."""
    global _match_service
    if profile and resume:
        return MatchService(profile=profile, resume=resume)
    if _match_service is None:
        _match_service = MatchService()
    return _match_service
