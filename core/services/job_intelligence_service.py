"""
Job Intelligence Service — Applyr 2.0
======================================

Converts raw Job data into a Canonical Job Intelligence representation.

Deterministic Precedence Rules:
  Explicit Job Metadata (fields on Job model)
    > Explicit JD Text Parsing (regex + keyword extraction)
    > Inferred Information (AI Gateway / heuristics)

No database migrations introduced. Derived from existing job data.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from core.models.job_intelligence import (
    ATSInfo,
    CanonicalJobProfile,
    JobCompensationInfo,
    JobIntelligenceEvidence,
    JobLocationInfo,
    JobSkillIntelligence,
    JobSourceOrigin,
    JobTechnologyInfo,
)

logger = logging.getLogger(__name__)

# Reuse the same normalization and categorization from Candidate Intelligence
from core.services.candidate_intelligence_service import (
    SKILL_NORMALIZATION_MAP,
    SKILL_CATEGORY_MAP,
)

# ── Remote keyword detection ──────────────────────────────────────────
REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "anywhere", "distributed", "fully remote"}
HYBRID_KEYWORDS = {"hybrid", "flexible", "partial remote", "2 days in office", "3 days in office"}
ONSITE_KEYWORDS = {"onsite", "on-site", "in office", "in-office", "office based", "office-based"}

# ── Employment type patterns ──────────────────────────────────────────
EMPLOYMENT_TYPE_PATTERNS = [
    (r"\bfull[\s-]?time\b", "full-time"),
    (r"\bpart[\s-]?time\b", "part-time"),
    (r"\bcontract\b", "contract"),
    (r"\bintern(ship)?\b", "internship"),
    (r"\bfreelance\b", "freelance"),
    (r"\btemp(orary)?\b", "temporary"),
]

# ── Experience year extraction ────────────────────────────────────────
EXPERIENCE_PATTERNS = [
    r"(\d{1,2})\s*[\+\-]\s*(\d{1,2})\s*(?:\+\s*)?years?(?:\s+of)?(?:\s+experience)?",
    r"(\d{1,2})\s+to\s+(\d{1,2})\s*years?(?:\s+of)?(?:\s+experience)?",
    r"(\d{1,2})\s*\+\s*years?(?:\s+of)?(?:\s+experience)?",
    r"(\d{1,2})\s*years?(?:\s+of)?(?:\s+experience)?",
    r"(\d{1,2})\s*yr?s?(?:\s+of)?(?:\s+experience)?",
    r"minimum\s+of\s+(\d{1,2})\s*years?",
]

# ── Seniority patterns ────────────────────────────────────────────────
SENIORITY_PATTERNS = [
    (r"\b(junior|jr\.?|entry[\s-]?level|intern)\b", "JUNIOR"),
    (r"\b(mid[\s-]?level|intermediate)\b", "MID"),
    (r"\b(senior|sr\.?|experienced)\b", "SENIOR"),
    (r"\b(lead|principal|staff|architect)\b", "LEAD"),
    (r"\b(director|vp|head of)\b", "PRINCIPAL"),
]

# ── Salary / compensation patterns ────────────────────────────────────
SALARY_PATTERNS = [
    r"\$\s*(\d{1,3}(?:,\d{3})*(?:k)?)\s*[-–to]+\s*\$\s*(\d{1,3}(?:,\d{3})*(?:k)?)\s*/?\s*(year|month|hour|annual|yr|mo|hr)?",
    r"(\d{1,3}(?:,\d{3})*(?:k)?)\s*[-–to]+\s*(\d{1,3}(?:,\d{3})*(?:k)?)\s*(?:USD|EUR|GBP|INR|CAD|AUD)?\s*/?\s*(year|month|hour|annual|yr|mo|hr)?",
    r"(?:salary|compensation|pay)(?:\s+range)?(?:\s*:)?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:k)?)\s*[-–to]+\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:k)?)",
]

# ── ATS platform detection ────────────────────────────────────────────
ATS_PATTERNS = {
    "greenhouse": r"boards\.greenhouse\.io|greenhouse\.com",
    "lever": r"lever\.co",
    "ashby": r"ashbyhq\.com|jobs\.ashby",
    "workday": r"myworkdayjobs\.com|workday\.com",
    "linkedin": r"linkedin\.com/jobs|linkedin\.com/company",
    "indeed": r"indeed\.com",
    "glassdoor": r"glassdoor\.com",
    "smartrecruiters": r"smartrecruiters\.com",
    "icims": r"icims\.com",
    "taleo": r"taleo\.net|oracle\.com/taleo",
    "jobvite": r"jobvite\.com",
    "breezy": r"breezy\.hr",
    "recruitee": r"recruitee\.com",
    "teamtailor": r"teamtailor\.com",
    "workable": r"workable\.com",
}

# ── Role family classification ────────────────────────────────────────
ROLE_FAMILY_KEYWORDS = {
    "backend": ["backend", "back-end", "server-side", "api", "rest", "microservices"],
    "frontend": ["frontend", "front-end", "client-side", "ui", "ux", "react", "vue", "angular"],
    "fullstack": ["fullstack", "full-stack", "full stack"],
    "data": ["data scientist", "data engineer", "data analyst", "machine learning", "ml engineer", "ai engineer"],
    "devops": ["devops", "sre", "site reliability", "infrastructure", "cloud engineer", "platform engineer"],
    "mobile": ["mobile", "ios", "android", "react native", "flutter"],
    "security": ["security", "cybersecurity", "infosec", "application security"],
    "design": ["designer", "ux designer", "ui designer", "product designer", "graphic designer"],
    "product": ["product manager", "product owner", "pm"],
}

# ── Domain classification ─────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "fintech": ["fintech", "banking", "financial", "payments", "trading", "crypto", "blockchain", "defi"],
    "healthtech": ["health", "medical", "clinical", "patient", "healthcare", "biotech", "pharma"],
    "saas": ["saas", "software as a service", "b2b", "enterprise software", "cloud platform"],
    "ecommerce": ["ecommerce", "e-commerce", "retail", "marketplace", "shopping"],
    "edtech": ["education", "edtech", "learning", "training", "lms"],
    "gaming": ["gaming", "game", "unity", "unreal", "esports"],
    "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "nlp", "computer vision", "genai", "generative ai"],
    "cybersecurity": ["cybersecurity", "information security", "appsec", "penetration testing"],
    "climate": ["climate", "clean energy", "sustainability", "green", "carbon"],
}


class JobIntelligenceService:
    """Service generating canonical job intelligence from raw job data."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ── Public API ────────────────────────────────────────────────────

    def build_job_intelligence(
        self,
        job_data: Optional[Dict[str, Any]] = None,
    ) -> CanonicalJobProfile:
        """
        Convert raw job data dict or Job model into CanonicalJobProfile.
        Applies deterministic precedence: Metadata > JD Parsing > Inferred.
        """
        if job_data is None:
            return CanonicalJobProfile()

        job = self._normalize_to_dict(job_data)
        jd_text = job.get("jd_text") or job.get("description") or ""
        title = job.get("title") or ""
        company = job.get("company") or ""
        url = job.get("url") or ""
        source = job.get("source") or ""
        location_raw = job.get("location") or ""
        job_type = job.get("type") or ""

        evidence: List[JobIntelligenceEvidence] = []

        # 1. Identity
        identity_ev = self._build_identity_evidence(job)

        # 2. Location
        location = self._parse_location(location_raw, jd_text)

        # 3. Employment type
        employment_type = self._parse_employment_type(jd_text, job_type)

        # 4. Seniority
        seniority, seniority_ev = self._parse_seniority(title, jd_text)

        # 5. Experience requirements
        experience_years = self._parse_experience_years(jd_text)

        # 6. Compensation
        compensation = self._parse_compensation(jd_text)

        # 7. Skills — required vs preferred
        required_skills, preferred_skills = self._parse_skills(jd_text)

        # 8. Responsibilities & requirements
        responsibilities = self._extract_section(jd_text, [
            "responsibilities", "what you'll do", "what you will do",
            "about the role", "role description", "job description",
        ])
        key_requirements = self._extract_section(jd_text, [
            "requirements", "must have", "must-have", "qualifications",
            "what we're looking for", "what we are looking for", "you should have",
        ])
        qualifications_list = self._extract_section(jd_text, [
            "qualifications", "education", "nice to have", "nice-to-have",
            "bonus", "preferred qualifications",
        ])
        education = self._parse_education(jd_text)
        certifications = self._parse_certifications(jd_text)

        # 9. Technology
        technology = self._extract_technology(jd_text, required_skills + preferred_skills)

        # 10. ATS detection
        ats = self._detect_ats(url, job)

        # 11. Role family & domain inference (deterministic, no AI)
        role_family = self._infer_role_family(title, jd_text)
        domain = self._infer_domain(jd_text, company)

        # 12. Compute confidence
        all_skills = required_skills + preferred_skills
        confidence = self._compute_confidence(
            has_title=bool(title),
            has_jd=bool(jd_text),
            has_skills=bool(all_skills),
            has_location=bool(location_raw),
            jd_length=len(jd_text),
        )

        # Normalize skills
        all_normalized = list(dict.fromkeys(
            s.normalized_name for s in all_skills
        ))
        skills_by_category: Dict[str, List[str]] = {}
        for s in all_skills:
            cat = s.category
            if cat not in skills_by_category:
                skills_by_category[cat] = []
            if s.normalized_name not in skills_by_category[cat]:
                skills_by_category[cat].append(s.normalized_name)

        from core.models.job_intelligence import JobProvenance

        # Provenance (additive, honest — no fabrication of NO_REQUIREMENT, no keyword heuristics)
        has_jd = bool(jd_text and jd_text.strip())
        if experience_years:
            import re as _re
            _is_supported = bool(
                _re.match(r"^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*years?\s*$", experience_years, re.IGNORECASE)
                or _re.match(r"^\s*(\d+(?:\.\d+)?)\+\s*years?\s*$", experience_years, re.IGNORECASE)
                or _re.match(r"^\s*(\d+(?:\.\d+)?)\s*years?\s*$", experience_years, re.IGNORECASE)
            )
            exp_prov = JobProvenance.DETERMINED_REQUIREMENT if _is_supported else JobProvenance.EXTRACTION_UNPARSEABLE
        elif not has_jd:
            exp_prov = JobProvenance.SOURCE_UNAVAILABLE
        else:
            exp_prov = JobProvenance.UNDETERMINED
        if title or role_family:
            role_prov = JobProvenance.DETERMINED_REQUIREMENT
        elif not has_jd:
            role_prov = JobProvenance.SOURCE_UNAVAILABLE
        else:
            role_prov = JobProvenance.UNDETERMINED
        loc_has_raw = bool(location.raw if location else None)
        loc_has = bool(loc_has_raw or (location.remote_type != "unknown" if location else False))
        if loc_has:
            loc_prov = JobProvenance.DETERMINED_REQUIREMENT
        elif not has_jd:
            loc_prov = JobProvenance.SOURCE_UNAVAILABLE
        else:
            loc_prov = JobProvenance.UNDETERMINED
        sen_has = bool(seniority)
        if sen_has:
            from core.services.seniority_normalizer import normalize_seniority

            _sen_norm = normalize_seniority(seniority) if sen_has else None
            if _sen_norm:
                sen_prov = JobProvenance.DETERMINED_REQUIREMENT
            else:
                sen_prov = JobProvenance.EXTRACTION_UNPARSEABLE
        elif not has_jd:
            sen_prov = JobProvenance.SOURCE_UNAVAILABLE
        else:
            sen_prov = JobProvenance.UNDETERMINED

        return CanonicalJobProfile(
            job_id=job.get("id"),
            title=title or None,
            normalized_title=self._normalize_title(title) or None,
            company=company or None,
            source=source or None,
            application_url=url or (ats.application_url if ats else None) or None,
            location=location,
            employment_type=employment_type,
            seniority=seniority,
            experience_years=experience_years,
            compensation=compensation,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            all_skills_normalized=all_normalized,
            skills_by_category=skills_by_category,
            responsibilities=responsibilities,
            key_requirements=key_requirements,
            qualifications=qualifications_list,
            education=education,
            certifications=certifications,
            technology=technology,
            role_family=role_family,
            domain=domain,
            inferred_seniority=seniority,
            confidence=confidence,
            evidence=evidence,
            ats=ats,
            posted_date=job.get("scraped_at") or None,
            discovered_date=job.get("scraped_at") or None,
            jd_text_length=len(jd_text),
            has_description=bool(jd_text),
            experience_provenance=exp_prov,
            role_provenance=role_prov,
            location_provenance=loc_prov,
            seniority_provenance=sen_prov,
        )

    # ── Identity ──────────────────────────────────────────────────────

    def _build_identity_evidence(self, job: Dict) -> List[JobIntelligenceEvidence]:
        ev = []
        if job.get("title"):
            ev.append(JobIntelligenceEvidence(
                source="job_metadata", confidence=1.0, origin=JobSourceOrigin.EXPLICIT_METADATA,
            ))
        if job.get("jd_text"):
            ev.append(JobIntelligenceEvidence(
                source="jd_text", confidence=1.0, origin=JobSourceOrigin.EXPLICIT_JD,
            ))
        return ev

    # ── Title normalization ───────────────────────────────────────────
    # Delegates to shared RoleNormalizer (deterministic, no behavior change)

    def _normalize_title(self, title: str) -> str:
        from core.services.role_normalizer import normalize_title

        return normalize_title(title)

    # ── Location ──────────────────────────────────────────────────────

    def _parse_location(self, raw: str, jd_text: str) -> JobLocationInfo:
        ev = []
        remote_type = "unknown"
        combined = f"{raw} {jd_text[:500]}".lower()

        if any(kw in combined for kw in REMOTE_KEYWORDS):
            remote_type = "remote"
            ev.append(JobIntelligenceEvidence(
                source="jd_text" if any(kw in jd_text.lower() for kw in REMOTE_KEYWORDS) else "job_metadata",
                confidence=0.9, origin=JobSourceOrigin.EXPLICIT_JD,
            ))
        elif any(kw in combined for kw in HYBRID_KEYWORDS):
            remote_type = "hybrid"
            ev.append(JobIntelligenceEvidence(
                source="jd_text", confidence=0.85, origin=JobSourceOrigin.EXPLICIT_JD,
            ))
        elif any(kw in combined for kw in ONSITE_KEYWORDS):
            remote_type = "onsite"
            ev.append(JobIntelligenceEvidence(
                source="jd_text", confidence=0.8, origin=JobSourceOrigin.EXPLICIT_JD,
            ))

        normalized = raw.strip() if raw else None
        return JobLocationInfo(
            raw=raw or None,
            normalized=normalized,
            remote_type=remote_type,
            evidence=ev,
        )

    # ── Employment type ───────────────────────────────────────────────

    def _parse_employment_type(self, jd_text: str, job_type: str) -> Optional[str]:
        if job_type:
            for _, emp_type in EMPLOYMENT_TYPE_PATTERNS:
                if emp_type in job_type.lower():
                    return emp_type
            return job_type
        combined = jd_text.lower()
        for pattern, emp_type in EMPLOYMENT_TYPE_PATTERNS:
            if re.search(pattern, combined):
                return emp_type
        return None

    # ── Seniority ─────────────────────────────────────────────────────

    def _parse_seniority(self, title: str, jd_text: str) -> Tuple[Optional[str], List[JobIntelligenceEvidence]]:
        ev = []
        combined = f"{title} {jd_text[:1000]}".lower()

        # Title takes precedence
        for pattern, level in SENIORITY_PATTERNS:
            if re.search(pattern, title.lower()):
                ev.append(JobIntelligenceEvidence(
                    source="job_title", confidence=0.95, origin=JobSourceOrigin.EXPLICIT_METADATA,
                ))
                return level, ev

        # JD text fallback
        for pattern, level in SENIORITY_PATTERNS:
            if re.search(pattern, combined):
                ev.append(JobIntelligenceEvidence(
                    source="jd_text", confidence=0.8, origin=JobSourceOrigin.EXPLICIT_JD,
                ))
                return level, ev

        return None, ev

    # ── Experience years ──────────────────────────────────────────────

    def _parse_experience_years(self, jd_text: str) -> Optional[str]:
        for pattern in EXPERIENCE_PATTERNS:
            match = re.search(pattern, jd_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2 and groups[1]:
                    return f"{groups[0]}-{groups[1]} years"
                return f"{groups[0]}+ years"
        return None

    # ── Compensation ──────────────────────────────────────────────────

    def _parse_compensation(self, jd_text: str) -> Optional[JobCompensationInfo]:
        for pattern in SALARY_PATTERNS:
            match = re.search(pattern, jd_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                min_sal = self._parse_salary_number(groups[0]) if groups[0] else None
                max_sal = self._parse_salary_number(groups[1]) if len(groups) > 1 and groups[1] else None
                period_raw = groups[2] if len(groups) > 2 and groups[2] else "yearly"
                period = self._normalize_period(period_raw)
                currency = "USD" if "$" in jd_text[match.start():match.end()] else None

                if min_sal or max_sal:
                    return JobCompensationInfo(
                        salary_min=min_sal,
                        salary_max=max_sal,
                        currency=currency,
                        period=period,
                        evidence=[JobIntelligenceEvidence(
                            source="jd_text", confidence=0.85, origin=JobSourceOrigin.EXPLICIT_JD,
                        )],
                    )
        return None

    def _parse_salary_number(self, s: str) -> Optional[int]:
        if not s:
            return None
        s = s.replace(",", "").replace("$", "").strip()
        multiplier = 1
        if s.lower().endswith("k"):
            s = s[:-1]
            multiplier = 1000
        try:
            return int(float(s) * multiplier)
        except (ValueError, TypeError):
            return None

    def _normalize_period(self, raw: str) -> str:
        if not raw:
            return "yearly"
        raw = raw.lower().strip()
        if raw in ("year", "annual", "yr", "yearly"):
            return "yearly"
        if raw in ("month", "mo", "monthly"):
            return "monthly"
        if raw in ("hour", "hr", "hourly"):
            return "hourly"
        return "yearly"

    # ── Skills parsing (required vs preferred) ────────────────────────

    def _parse_skills(self, jd_text: str) -> Tuple[List[JobSkillIntelligence], List[JobSkillIntelligence]]:
        if not jd_text:
            return [], []

        text_lower = jd_text.lower()

        # Split into required vs preferred sections
        required_text, preferred_text = self._split_required_preferred(jd_text)

        required_raw = self._extract_skill_candidates(required_text)
        preferred_raw = self._extract_skill_candidates(preferred_text)

        # Remove preferred skills from required if duplicated
        preferred_norm = set()
        for s in preferred_raw:
            norm = self._normalize_skill(s)
            if norm:
                preferred_norm.add(norm)

        required_skills = []
        seen = set()
        for s in required_raw:
            norm = self._normalize_skill(s)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            if norm in preferred_norm:
                continue
            cat = self._categorize_skill(norm)
            required_skills.append(JobSkillIntelligence(
                name=s,
                normalized_name=norm,
                category=cat,
                required=True,
                confidence=0.9,
                evidence=[JobIntelligenceEvidence(
                    source="jd_text_required", confidence=0.9, origin=JobSourceOrigin.EXPLICIT_JD,
                )],
            ))

        preferred_skills = []
        seen = set()
        for s in preferred_raw:
            norm = self._normalize_skill(s)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            cat = self._categorize_skill(norm)
            preferred_skills.append(JobSkillIntelligence(
                name=s,
                normalized_name=norm,
                category=cat,
                required=False,
                confidence=0.85,
                evidence=[JobIntelligenceEvidence(
                    source="jd_text_preferred", confidence=0.85, origin=JobSourceOrigin.EXPLICIT_JD,
                )],
            ))

        return required_skills, preferred_skills

    def _split_required_preferred(self, jd_text: str) -> Tuple[str, str]:
        """Split JD text into required and preferred sections.
        
        Only splits on section-header-like occurrences of preferred markers,
        not incidental inline mentions. All markers must appear at or near
        the start of a line to be treated as a section header.
        """
        lines = jd_text.split("\n")
        preferred_start = None

        # All markers — must appear at line start (or after bullet prefix) to trigger
        section_markers = [
            "nice to have", "nice-to-have",
            "preferred qualifications", "preferred requirements",
            "preferred skills", "preferred experience",
            "preferred",
            "good to have", "good-to-have",
            "bonus qualifications", "bonus skills",
            "bonus",
            "optional",
        ]

        for i, line in enumerate(lines):
            line_start = jd_text.index(line) if line in jd_text else sum(len(l) + 1 for l in lines[:i])
            stripped = line.strip()
            lower = stripped.lower()

            # Check if line starts with any section marker (possibly after bullet prefix)
            for marker in section_markers:
                for prefix in ("", "- ", "* ", "## "):
                    if lower.startswith(prefix + marker):
                        # Verify it's a header-like line (short, or at line start)
                        idx = line_start + lower.index(marker)
                        if preferred_start is None or idx < preferred_start:
                            preferred_start = idx
                        break
                else:
                    continue
                break

        if preferred_start is not None:
            return jd_text[:preferred_start], jd_text[preferred_start:]
        return jd_text, ""

    def _extract_skill_candidates(self, text: str) -> List[str]:
        """Extract potential skill names from text."""
        if not text:
            return []

        skills = []

        # Check for explicit skill lists (bullet points)
        lines = text.split("\n")
        in_skill_section = False
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if any(kw in lower for kw in ["skill", "technolog", "tech stack", "requirements"]):
                in_skill_section = True
                continue
            if in_skill_section:
                if stripped.startswith(("-", "•", "·", "*")) or re.match(r"^\d+\.", stripped):
                    skill_text = re.sub(r"^[-•·*\d.]+\s*", "", stripped).strip()
                    if skill_text and len(skill_text) < 60:
                        # Split compound lines on "and", commas, slashes
                        parts = re.split(r"\s+and\s+|,\s*|/|\s*\bor\b\s*", skill_text)
                        for part in parts:
                            part = part.strip().rstrip(".")
                            if part and len(part) < 40 and not any(
                                skip in part.lower() for skip in [
                                    "experience", "years", "year", "knowledge",
                                    "ability", "understanding", "familiar",
                                    "degree", "bachelor", "master", "minimum",
                                    "required", "preferred", "strong", "good",
                                    "excellent", "proven", "least",
                                ]
                            ):
                                skills.append(part)
                elif stripped == "" or (len(stripped) > 100 and " " in stripped):
                    in_skill_section = False

        # Fallback: use known skill keywords from normalization map
        if not skills:
            text_lower = text.lower()
            for alias, canonical in SKILL_NORMALIZATION_MAP.items():
                if len(alias) >= 2 and re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
                    skills.append(canonical)

        return skills

    # ── Section extraction ────────────────────────────────────────────

    def _extract_section(self, jd_text: str, headers: List[str]) -> List[str]:
        """Extract bullet points under a matching section header."""
        if not jd_text:
            return []

        lines = jd_text.split("\n")
        items: List[str] = []
        capturing = False

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()

            # Check if this line is a section header
            is_header = any(h in lower for h in headers)
            if is_header:
                capturing = True
                continue

            if capturing:
                if stripped.startswith(("-", "•", "·", "*")) or re.match(r"^\d+\.", stripped):
                    item = re.sub(r"^[-•·*\d.]+\s*", "", stripped).strip()
                    if item and len(item) < 300:
                        items.append(item)
                elif stripped == "":
                    continue
                elif len(stripped) > 200:
                    # Likely a new paragraph, stop capturing
                    capturing = False
                elif not stripped.startswith(("-", "•", "·", "*")) and re.match(r"^[A-Z]", stripped):
                    # Likely a new header
                    capturing = False

        return items

    # ── Education ─────────────────────────────────────────────────────

    def _parse_education(self, jd_text: str) -> List[str]:
        if not jd_text:
            return []
        education = []
        text_lower = jd_text.lower()

        degree_patterns = [
            (r"\bph\.?d\b", "PhD"),
            (r"\bmaster'?s?\b", "Master's degree"),
            (r"\bbachelor'?s?\b", "Bachelor's degree"),
            (r"\bassociate'?s?\b", "Associate's degree"),
        ]

        for pattern, label in degree_patterns:
            if re.search(pattern, text_lower):
                education.append(label)

        field_patterns = [
            r"(?:degree in|studying|background in|education in)\s+([A-Za-z\s,]+?)(?:\.|,|\n|$)",
        ]
        for fp in field_patterns:
            match = re.search(fp, jd_text, re.IGNORECASE)
            if match:
                field = match.group(1).strip()
                if field and len(field) < 80:
                    education.append(f"Field: {field}")

        return list(dict.fromkeys(education))

    # ── Certifications ────────────────────────────────────────────────

    def _parse_certifications(self, jd_text: str) -> List[str]:
        if not jd_text:
            return []
        certs = []
        text_lower = jd_text.lower()
        known_certs = [
            "aws certified", "gcp certified", "azure certified", "ccna", "ccnp",
            "comptia", "pmp", "cerp", "cissp", "ceh", "oscp",
            "kubernetes certification", "cka", "ckad",
            "google cloud professional", "aws solutions architect",
        ]
        for cert in known_certs:
            if cert in text_lower:
                certs.append(cert.title())
        return certs

    # ── Technology extraction ─────────────────────────────────────────

    def _extract_technology(self, jd_text: str, skills: List[JobSkillIntelligence]) -> JobTechnologyInfo:
        if not jd_text:
            return JobTechnologyInfo()

        tech = JobTechnologyInfo()
        by_cat: Dict[str, List[str]] = {}

        for s in skills:
            cat = s.category
            if cat not in by_cat:
                by_cat[cat] = []
            if s.normalized_name not in by_cat[cat]:
                by_cat[cat].append(s.normalized_name)

        tech.languages = by_cat.get("languages", [])
        tech.frameworks = by_cat.get("frameworks", [])
        tech.databases = by_cat.get("databases", [])
        tech.cloud = by_cat.get("cloud", [])
        tech.devops = by_cat.get("devops", [])
        tech.ai_ml = by_cat.get("ai_ml", [])
        tech.tools = by_cat.get("tools", [])

        return tech

    # ── ATS detection ─────────────────────────────────────────────────

    def _detect_ats(self, url: str, job: Dict) -> Optional[ATSInfo]:
        if not url:
            return None

        for platform, pattern in ATS_PATTERNS.items():
            if re.search(pattern, url, re.IGNORECASE):
                return ATSInfo(
                    platform=platform,
                    application_url=url,
                    evidence=[JobIntelligenceEvidence(
                        source="url_parsing", confidence=0.95, origin=JobSourceOrigin.EXPLICIT_METADATA,
                    )],
                )

        return ATSInfo(
            platform="other",
            application_url=url,
            evidence=[JobIntelligenceEvidence(
                source="url_parsing", confidence=0.5, origin=JobSourceOrigin.INFERRED,
            )],
        )

    # ── Role family inference ─────────────────────────────────────────

    def _infer_role_family(self, title: str, jd_text: str) -> Optional[str]:
        combined = f"{title} {jd_text[:2000]}".lower()
        scores: Dict[str, int] = {}
        for family, keywords in ROLE_FAMILY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[family] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    # ── Domain inference ──────────────────────────────────────────────

    def _infer_domain(self, jd_text: str, company: str) -> Optional[str]:
        combined = f"{jd_text[:3000]} {company}".lower()
        scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    # ── Confidence scoring ────────────────────────────────────────────

    def _compute_confidence(
        self,
        has_title: bool,
        has_jd: bool,
        has_skills: bool,
        has_location: bool,
        jd_length: int,
    ) -> float:
        score = 0.0
        if has_title:
            score += 0.25
        if has_jd:
            score += 0.30
        if has_skills:
            score += 0.25
        if has_location:
            score += 0.10
        if jd_length > 500:
            score += 0.10
        elif jd_length > 200:
            score += 0.05
        return round(min(score, 1.0), 2)

    # ── Helpers ───────────────────────────────────────────────────────

    def _normalize_to_dict(self, job_data: Any) -> Dict[str, Any]:
        if isinstance(job_data, dict):
            return job_data
        if hasattr(job_data, "dict"):
            return job_data.dict()
        if hasattr(job_data, "model_dump"):
            return job_data.model_dump()
        return {}

    def _normalize_skill(self, skill: str) -> str:
        if not skill:
            return ""
        cleaned = skill.strip()
        lower = cleaned.lower()
        return SKILL_NORMALIZATION_MAP.get(lower, cleaned.title())

    def _categorize_skill(self, skill_name: str) -> str:
        norm = self._normalize_skill(skill_name) if skill_name != skill_name.title() else skill_name
        for cat, skill_set in SKILL_CATEGORY_MAP.items():
            if norm in skill_set:
                return cat
        return "other"


# Singleton Factory
_job_intelligence_instance: Optional[JobIntelligenceService] = None


def get_job_intelligence_service() -> JobIntelligenceService:
    global _job_intelligence_instance
    if _job_intelligence_instance is None:
        _job_intelligence_instance = JobIntelligenceService()
    return _job_intelligence_instance
