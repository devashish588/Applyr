"""
Candidate Intelligence Service — Applyr 2.0
============================================

Combines profile.json, parsed resume data, and preferences into a normalized,
explainable Canonical Candidate Representation.

Deterministic Precedence Rules:
  Explicit User Profile (profile.json)
    > Explicit Resume Evidence (ResumeParserService)
    > Inferred Information (AI Gateway / Heuristics)
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from core.models import SeniorityLevel
from core.models.candidate_intelligence import (
    CanonicalCandidateProfile,
    ExperienceItem,
    IntelligenceEvidence,
    ProjectItem,
    SkillIntelligence,
    SourceOrigin,
)

logger = logging.getLogger(__name__)

# Deterministic Skill Normalization Dictionary
SKILL_NORMALIZATION_MAP = {
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "docker": "Docker",
    "aws": "AWS",
    "amazon web services": "AWS",
    "fastapi": "FastAPI",
    "fast-api": "FastAPI",
    "flask": "Flask",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "git": "Git",
    "github": "GitHub",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "restful": "REST APIs",
}

# Skill Taxonomy Categorization
SKILL_CATEGORY_MAP = {
    "languages": {"Python", "TypeScript", "JavaScript", "SQL", "Java", "C++", "Go", "Rust", "HTML", "CSS"},
    "frameworks": {"React", "FastAPI", "Flask", "Node.js", "Django", "Express", "Next.js", "Vue", "Angular", "Tailwind CSS"},
    "databases": {"PostgreSQL", "MongoDB", "Redis", "MySQL", "SQLite", "DynamoDB"},
    "cloud": {"AWS", "GCP", "Azure", "Cloudflare"},
    "devops": {"Docker", "Kubernetes", "Git", "GitHub", "CI/CD", "Terraform"},
    "ai_ml": {"PyTorch", "TensorFlow", "Scikit-Learn", "LangChain", "OpenAI", "LLMs", "NLP"},
    "tools": {"REST APIs", "GraphQL", "PyPDF", "Vite", "Webpack", "Postman"},
}


class CandidateIntelligenceService:
    """Service generating canonical candidate intelligence."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def normalize_skill(self, skill: str) -> str:
        """Deterministically normalize skill strings."""
        if not skill:
            return ""
        cleaned = skill.strip()
        lower = cleaned.lower()
        return SKILL_NORMALIZATION_MAP.get(lower, cleaned.title())

    def categorize_skill(self, skill_name: str) -> str:
        """Categorize a normalized skill name into standard technical domains."""
        norm = self.normalize_skill(skill_name)
        for cat, skill_set in SKILL_CATEGORY_MAP.items():
            if norm in skill_set:
                return cat
        return "other"

    def build_candidate_intelligence(
        self,
        profile_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
    ) -> CanonicalCandidateProfile:
        """
        Build CanonicalCandidateProfile by merging profile.json & parsed resume data.
        Applies deterministic precedence: User Profile > Resume Evidence > Inferred.
        """
        profile = self._load_default_profile() if profile_data is None else profile_data
        resume = self._load_default_resume_data() if resume_data is None else resume_data

        pj = resume.get("parsed_json", {}) if resume else {}
        if isinstance(pj, str):
            try:
                pj = json.loads(pj)
            except Exception:
                pj = {}

        # 1. Identity & Precedence
        personal = profile.get("personal", {})
        name = personal.get("name") or pj.get("name") or "Candidate"
        email = personal.get("email") or pj.get("email")
        phone = personal.get("phone") or pj.get("phone")
        location = personal.get("city") or personal.get("location") or pj.get("location")

        target_roles = profile.get("target_roles") or profile.get("job_preferences", {}).get("target_roles") or pj.get("roles") or ["Software Engineer"]
        preferred_locations = profile.get("target_locations") or profile.get("job_preferences", {}).get("target_locations") or []

        # 2. Skills Processing & Traceability
        raw_user_skills = profile.get("skills", {})
        user_skills_list = []
        if isinstance(raw_user_skills, list):
            user_skills_list = raw_user_skills
        elif isinstance(raw_user_skills, dict):
            for v in raw_user_skills.values():
                if isinstance(v, list):
                    user_skills_list.extend(v)

        resume_skills = resume.get("skills_json") or pj.get("skills", [])
        if isinstance(resume_skills, dict):
            r_list = []
            for v in resume_skills.values():
                if isinstance(v, list):
                    r_list.extend(v)
            resume_skills = r_list

        skills_dict: Dict[str, SkillIntelligence] = {}
        # Occurrence-level preservation for SkillMatcher (5B-2): every raw input
        # that normalizes to a non-empty canonical is kept in order, regardless
        # of canonical deduplication. This allows ["python3","py"] both → Python
        # to reach the matcher so EXACT can beat ALIAS.
        skill_occurrences: List[SkillIntelligence] = []

        # Process user profile skills (EXPLICIT_USER)
        for s in user_skills_list:
            norm = self.normalize_skill(s)
            if not norm:
                continue
            cat = self.categorize_skill(norm)
            # Preserve occurrence before deduplication
            skill_occurrences.append(
                SkillIntelligence(
                    name=s,
                    normalized_name=norm,
                    category=cat,
                    confidence=1.0,
                    evidence=[IntelligenceEvidence(source="profile.json", confidence=1.0, origin=SourceOrigin.EXPLICIT_USER)],
                )
            )
            if norm in skills_dict:
                skills_dict[norm].evidence.append(
                    IntelligenceEvidence(source="profile.json", confidence=1.0, origin=SourceOrigin.EXPLICIT_USER)
                )
                skills_dict[norm].confidence = 1.0
            else:
                skills_dict[norm] = SkillIntelligence(
                    name=s,
                    normalized_name=norm,
                    category=cat,
                    confidence=1.0,
                    evidence=[IntelligenceEvidence(source="profile.json", confidence=1.0, origin=SourceOrigin.EXPLICIT_USER)],
                )

        # Process resume skills (EXPLICIT_RESUME)
        for s in resume_skills:
            norm = self.normalize_skill(s)
            if not norm:
                continue
            cat = self.categorize_skill(norm)
            skill_occurrences.append(
                SkillIntelligence(
                    name=s,
                    normalized_name=norm,
                    category=cat,
                    confidence=0.9,
                    evidence=[IntelligenceEvidence(source="resume_parsed", confidence=0.95, origin=SourceOrigin.EXPLICIT_RESUME)],
                )
            )
            if norm in skills_dict:
                skills_dict[norm].evidence.append(
                    IntelligenceEvidence(source="resume_parsed", confidence=0.95, origin=SourceOrigin.EXPLICIT_RESUME)
                )
                skills_dict[norm].confidence = 1.0
            else:
                skills_dict[norm] = SkillIntelligence(
                    name=s,
                    normalized_name=norm,
                    category=cat,
                    confidence=0.9,
                    evidence=[IntelligenceEvidence(source="resume_parsed", confidence=0.9, origin=SourceOrigin.EXPLICIT_RESUME)],
                )

        # Categorized Skill Lists
        skills_by_category: Dict[str, List[str]] = {}
        for skill_obj in skills_dict.values():
            cat = skill_obj.category
            if cat not in skills_by_category:
                skills_by_category[cat] = []
            skills_by_category[cat].append(skill_obj.normalized_name)

        # 3. Work Experience & Seniority Inference
        exp_list: List[ExperienceItem] = []
        raw_exp = pj.get("experience", [])
        total_years = 0.0

        for exp in raw_exp:
            if isinstance(exp, dict):
                title = exp.get("title") or "Software Engineer"
                comp = exp.get("company") or "Company"
                dur = exp.get("duration") or exp.get("dates") or ""
                resp = exp.get("responsibilities") or exp.get("bullets") or []
                techs = [self.normalize_skill(t) for t in exp.get("technologies", []) if t]
                parsed_years = self._parse_years_from_duration(dur)
                exp_list.append(
                    ExperienceItem(
                        title=title,
                        company=comp,
                        duration=dur,
                        years=parsed_years,
                        responsibilities=resp if isinstance(resp, list) else [str(resp)],
                        technologies=techs,
                    )
                )
                total_years += parsed_years

        # Infer Seniority
        profile_seniority = profile.get("seniority")
        current_title = exp_list[0].title if exp_list else (target_roles[0] if target_roles else "Software Engineer")
        title_lower = current_title.lower()
        if "lead" in title_lower or "principal" in title_lower or "staff" in title_lower or "senior" in title_lower or "sr" in title_lower:
            detected_sen = SeniorityLevel.SENIOR
        else:
            detected_sen = SeniorityLevel.detect_from_title(current_title) or SeniorityLevel.from_years(total_years)

        if profile_seniority:
            final_seniority = str(profile_seniority).upper()
            seniority_origin = SourceOrigin.EXPLICIT_USER
        else:
            final_seniority = detected_sen.name if hasattr(detected_sen, "name") else str(detected_sen).upper()
            seniority_origin = SourceOrigin.INFERRED


        # 4. Projects
        proj_list: List[ProjectItem] = []
        for prj in pj.get("projects", []):
            if isinstance(prj, dict):
                p_name = prj.get("name") or prj.get("title") or "Project"
                p_desc = prj.get("description") or ""
                p_techs = [self.normalize_skill(t) for t in prj.get("technologies", []) if t]
                proj_list.append(
                    ProjectItem(
                        name=p_name,
                        description=p_desc,
                        technologies=p_techs,
                    )
                )

        # 5. Strengths & Skill Gaps
        strengths, skill_gaps = self.evaluate_strengths_and_gaps(
            skills=list(skills_dict.keys()),
            target_roles=target_roles,
            experiences=exp_list,
        )

        # Provenance (additive, preserves why UNKNOWN vs DETERMINED)
        from core.models.candidate_intelligence import CandidateProvenance

        # Experience provenance — distinguish SOURCE_UNAVAILABLE vs DETERMINED_EMPTY vs UNPARSEABLE
        has_exp_source = "experience" in pj
        raw_exp_list = pj.get("experience") if isinstance(pj.get("experience"), list) else []
        if not has_exp_source:
            exp_prov = CandidateProvenance.SOURCE_UNAVAILABLE
        elif not isinstance(raw_exp_list, list) or len(raw_exp_list) == 0:
            # Source present but empty list → authoritative empty
            exp_prov = CandidateProvenance.DETERMINED_EMPTY
        elif not exp_list:
            # Source present, raw had entries but none survived (all filtered) → unparseable
            exp_prov = CandidateProvenance.EXTRACTION_UNPARSEABLE
        elif all(e.years == 0.0 for e in exp_list) and any((d.get("duration") or "").strip() for d in raw_exp_list if isinstance(d, dict)):
            # All durations present but unparseable → unparseable
            exp_prov = CandidateProvenance.EXTRACTION_UNPARSEABLE
        elif exp_list:
            exp_prov = CandidateProvenance.DETERMINED_POPULATED
        else:
            exp_prov = CandidateProvenance.DETERMINED_EMPTY

        # Role provenance — authoritative title evidence exists; unparseable if titles present but all normalize empty
        has_role_source = bool(current_title or exp_list)
        if not has_role_source:
            # Check if source key existed
            has_role_key = bool(current_title) or any("title" in (e if isinstance(e, dict) else {}) for e in raw_exp_list)
            if not has_role_key and "roles" not in pj and "current_role" not in profile:
                role_prov = CandidateProvenance.SOURCE_UNAVAILABLE
            else:
                role_prov = CandidateProvenance.DETERMINED_EMPTY
        else:
            has_role_title = any((e.title or "").strip() for e in exp_list) or bool((current_title or "").strip())
            if not has_role_title:
                role_prov = CandidateProvenance.DETERMINED_EMPTY
            else:
                # Check if all titles normalize to empty
                from core.services.role_normalizer import normalize_title

                if all(not normalize_title((e.title or "").strip()) for e in exp_list if (e.title or "").strip()) and not normalize_title((current_title or "").strip()):
                    role_prov = CandidateProvenance.EXTRACTION_UNPARSEABLE
                else:
                    role_prov = CandidateProvenance.DETERMINED_POPULATED

        # Location provenance
        has_loc_source = bool(location or preferred_locations)
        has_loc_key = "city" in (profile.get("personal", {}) or {}) or "location" in (profile.get("personal", {}) or {}) or bool(preferred_locations) or "location" in pj
        if not has_loc_source and not has_loc_key:
            loc_prov = CandidateProvenance.SOURCE_UNAVAILABLE
        elif not has_loc_source and has_loc_key:
            # Key present but value empty/whitespace → unparseable
            loc_prov = CandidateProvenance.EXTRACTION_UNPARSEABLE
        elif location or preferred_locations:
            # Check if all location strings are unparseable (extract_city fails)
            from core.services.location_normalizer import extract_city

            all_locs = ([location] if location else []) + list(preferred_locations)
            if all(not extract_city(loc) for loc in all_locs if loc and loc.strip()):
                loc_prov = CandidateProvenance.EXTRACTION_UNPARSEABLE
            else:
                loc_prov = CandidateProvenance.DETERMINED_POPULATED
        else:
            loc_prov = CandidateProvenance.DETERMINED_EMPTY

        # Seniority provenance — explicit only; INFERRED preserved distinctly
        if seniority_origin == SourceOrigin.EXPLICIT_USER:
            sen_prov = CandidateProvenance.DETERMINED_POPULATED
        elif seniority_origin == SourceOrigin.INFERRED:
            sen_prov = CandidateProvenance.INFERRED
        else:
            sen_prov = CandidateProvenance.SOURCE_UNAVAILABLE

        return CanonicalCandidateProfile(
            candidate_id="primary_candidate",
            name=name,
            email=email,
            phone=phone,
            location=location,
            current_role=current_title,
            seniority=final_seniority,
            seniority_origin=seniority_origin,
            target_roles=target_roles,
            preferred_locations=preferred_locations,
            remote_preference=profile.get("remote_ok", True) and "remote" or "any",
            skills=list(skills_dict.values()),
            skill_occurrences=skill_occurrences,
            skills_by_category=skills_by_category,
            experience=exp_list,
            projects=proj_list,
            education=pj.get("education", []),
            certifications=pj.get("certifications", []),
            strengths=strengths,
            skill_gaps=skill_gaps,
            inferred_domains=list(skills_by_category.keys()),
            overall_confidence=0.95 if (user_skills_list and resume_skills) else 0.85,
            updated_at=datetime.now(timezone.utc).isoformat(),
            experience_provenance=exp_prov,
            role_provenance=role_prov,
            location_provenance=loc_prov,
            seniority_provenance=sen_prov,
        )

    def evaluate_strengths_and_gaps(
        self,
        skills: List[str],
        target_roles: List[str],
        experiences: Optional[List[ExperienceItem]] = None,
    ) -> Tuple[List[str], List[str]]:
        """Identify evidence-backed candidate strengths and relevant skill gaps."""
        strengths = []
        skill_gaps = []
        skill_set = set(skills)

        # Strengths based on evidence
        if "Python" in skill_set and ("FastAPI" in skill_set or "Flask" in skill_set):
            strengths.append("Strong Python Backend Stack (Python, REST APIs)")
        if "React" in skill_set and ("TypeScript" in skill_set or "JavaScript" in skill_set):
            strengths.append("Modern Frontend Stack (React, TypeScript)")
        if "PostgreSQL" in skill_set or "MongoDB" in skill_set:
            strengths.append("Database Management & Optimization")

        if not strengths:
            strengths.append(f"Technical background in {', '.join(skills[:3]) if skills else 'Software Engineering'}")

        # Relevant gaps based on target roles
        role_str = " ".join(target_roles).lower()
        if ("backend" in role_str or "full stack" in role_str or "software" in role_str) and "Docker" not in skill_set:
            skill_gaps.append("Containerization (Docker)")
        if "cloud" in role_str or "devops" in role_str or "backend" in role_str:
            if "AWS" not in skill_set and "GCP" not in skill_set:
                skill_gaps.append("Cloud Platforms (AWS / GCP)")
        if "backend" in role_str and "Kubernetes" not in skill_set:
            skill_gaps.append("Orchestration (Kubernetes)")

        return strengths, skill_gaps

    def _parse_years_from_duration(self, duration: str) -> float:
        """Extract years of experience from a duration string.
        
        Handles formats like:
        - "3 years", "3+ years", "3-5 years", "3 to 5 years", "2 yrs"
        - "Jan 2020 - Present" (calculates approximate years)
        - "2020-2023" (calculates approximate years)
        - Returns 0.0 if no parseable duration found.
        """
        if not duration:
            return 0.0
        dur = duration.strip().lower()

        # Range patterns first (must precede simple "X years" to avoid partial match)
        # Pattern: "X to Y years" or "X-Y years"
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*years?', dur)
        if m:
            return (float(m.group(1)) + float(m.group(2))) / 2.0

        # Pattern: "X years" or "X+ years" or "X yr"
        m = re.search(r'(\d+(?:\.\d+)?)\s*\+?\s*years?', dur)
        if m:
            return float(m.group(1))

        # Pattern: "X months"
        m = re.search(r'(\d+)\s*months?', dur)
        if m:
            return round(int(m.group(1)) / 12.0, 1)

        # Pattern: year ranges like "2020-2023" or "Jan 2020 - Dec 2023"
        year_matches = re.findall(r'20\d{2}', dur)
        if len(year_matches) >= 2:
            years = abs(int(year_matches[-1]) - int(year_matches[0]))
            return float(max(years, 0))

        # Pattern: "X+ yrs"
        m = re.search(r'(\d+)\s*yrs?', dur)
        if m:
            return float(m.group(1))

        return 0.0

    def _load_default_profile(self) -> Dict[str, Any]:
        """Load user profile from profile.json fallback."""
        from pathlib import Path
        profile_path = os.getenv("PROFILE_PATH", "profile.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[candidate_service] Failed to read {profile_path}: {e}")
        return {}

    def _load_default_resume_data(self) -> Dict[str, Any]:
        """Load parsed resume from active master resume (TEST-aware), fallback to legacy."""
        try:
            from core.services.master_resume_service import get_master_resume_service
            active = get_master_resume_service().get_active()
            if active and active.get("status") == "READY":
                # Normalize to resume_data shape for existing pipeline (UNKNOWN preserved when absent)
                return {
                    "filename": active.get("filename"),
                    "file_size": active.get("file_size"),
                    "uploaded_at": active.get("uploaded_at"),
                    "parsed_at": active.get("parsed_at"),
                    "parse_status": "success",
                    "parsed_json": active.get("parsed_json") or {},
                    "skills_json": active.get("skills_json") or [],
                    "roles_json": active.get("roles_json") or [],
                    "health_json": active.get("health_json") or {},
                }
            if active is None:
                return {}
        except Exception as e:
            logger.warning(f"[candidate_service] Master resume lookup failed, falling back: {type(e).__name__}")
        try:
            from db.db_client import get_db
            db = get_db()
            data = db.get_resume_data()
            return data or {}
        except Exception as e:
            logger.warning(f"[candidate_service] Failed to get DB resume data: {e}")
            return {}


# Singleton Factory
_candidate_service_instance: Optional[CandidateIntelligenceService] = None

def get_candidate_intelligence_service() -> CandidateIntelligenceService:
    global _candidate_service_instance
    if _candidate_service_instance is None:
        _candidate_service_instance = CandidateIntelligenceService()
    return _candidate_service_instance
