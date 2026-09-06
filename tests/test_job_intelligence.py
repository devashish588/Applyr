"""
Job Intelligence Tests — Applyr 2.0
====================================

Comprehensive tests covering:
  - Job conversion
  - Normalization
  - Duplicate skills
  - Required vs preferred skills
  - Experience
  - Seniority
  - Role family
  - Technology
  - Domain
  - Location
  - Salary
  - ATS detection
  - Freshness
  - Evidence
  - Confidence
  - Missing/partial data
  - Hallucination prevention
  - MatchService compatibility
"""

import unittest
from unittest.mock import patch, MagicMock

from core.models.job_intelligence import (
    CanonicalJobProfile,
    JobSkillIntelligence,
    JobLocationInfo,
    JobCompensationInfo,
    ATSInfo,
    JobTechnologyInfo,
)
from core.services.job_intelligence_service import (
    JobIntelligenceService,
    get_job_intelligence_service,
)


class TestJobIntelligence(unittest.TestCase):
    """Tests for the Job Intelligence module."""

    def setUp(self):
        self.service = JobIntelligenceService()
        self.sample_job = {
            "id": 42,
            "title": "Senior Backend Engineer",
            "company": "TechCorp",
            "location": "San Francisco, CA",
            "url": "https://boards.greenhouse.io/techcorp/jobs/123",
            "source": "linkedin",
            "type": "full-time",
            "jd_text": (
                "We are looking for a Senior Backend Engineer to join our team.\n\n"
                "Responsibilities:\n"
                "- Design and build scalable APIs\n"
                "- Optimize database queries\n"
                "- Mentor junior engineers\n\n"
                "Requirements:\n"
                "- 5+ years of experience\n"
                "- Python and FastAPI\n"
                "- PostgreSQL\n"
                "- AWS\n"
                "- Docker\n\n"
                "Nice to have:\n"
                "- Kubernetes\n"
                "- GraphQL\n"
                "- Machine learning experience\n\n"
                "Salary: $150,000 - $200,000 / year\n\n"
                "This is a remote position."
            ),
            "scraped_at": "2025-01-15T10:00:00",
        }

        self.minimal_job = {
            "id": 1,
            "title": "Software Engineer",
            "company": "StartupCo",
        }

        self.empty_job = {}

    # ── Test 01: Model creation ───────────────────────────────────────

    def test_01_model_creation(self):
        """CanonicalJobProfile can be instantiated with defaults."""
        profile = CanonicalJobProfile()
        self.assertIsInstance(profile, CanonicalJobProfile)
        self.assertIsNone(profile.title)
        self.assertEqual(profile.required_skills, [])
        self.assertEqual(profile.confidence, 0.0)

    # ── Test 02: Full job conversion ──────────────────────────────────

    def test_02_full_job_conversion(self):
        """Full job data produces a complete canonical profile."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsInstance(profile, CanonicalJobProfile)
        self.assertEqual(profile.job_id, 42)
        self.assertEqual(profile.title, "Senior Backend Engineer")
        self.assertEqual(profile.company, "TechCorp")
        self.assertTrue(profile.has_description)
        self.assertGreater(profile.jd_text_length, 0)

    # ── Test 03: Title normalization ──────────────────────────────────

    def test_03_title_normalization(self):
        """Title is normalized (Senior, not sr.)."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.normalized_title, "Senior Backend Engineer")

    def test_03b_title_normalization_jr(self):
        """Junior abbreviation is expanded."""
        job = {"title": "Jr. Frontend Developer", "company": "Co", "jd_text": "React TypeScript"}
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.normalized_title, "Junior Frontend Developer")

    # ── Test 04: Skill normalization ──────────────────────────────────

    def test_04_skill_normalization(self):
        """Skills are normalized to canonical names."""
        self.assertEqual(self.service._normalize_skill("python3"), "Python")
        self.assertEqual(self.service._normalize_skill("postgres"), "PostgreSQL")
        self.assertEqual(self.service._normalize_skill("reactjs"), "React")
        self.assertEqual(self.service._normalize_skill("k8s"), "Kubernetes")
        self.assertEqual(self.service._normalize_skill("ts"), "TypeScript")

    def test_04b_unknown_skill_gets_title(self):
        """Unknown skills get .title() applied."""
        self.assertEqual(self.service._normalize_skill("mycustomlib"), "Mycustomlib")

    # ── Test 05: Duplicate skills removed ─────────────────────────────

    def test_05_duplicate_skills_removed(self):
        """Duplicate skills across sections are deduplicated."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": (
                "Requirements:\n- Python\n- Python\n- Python\n\n"
                "Nice to have:\n- Python\n- Docker"
            ),
        }
        profile = self.service.build_job_intelligence(job)
        all_names = [s.normalized_name for s in profile.required_skills + profile.preferred_skills]
        # Python should appear only once total
        self.assertEqual(all_names.count("Python"), 1)

    # ── Test 06: Required vs preferred skills ─────────────────────────

    def test_06_required_vs_preferred_skills(self):
        """Skills are correctly split into required and preferred."""
        profile = self.service.build_job_intelligence(self.sample_job)
        required_names = [s.normalized_name for s in profile.required_skills]
        preferred_names = [s.normalized_name for s in profile.preferred_skills]
        self.assertIn("Python", required_names)
        self.assertIn("FastAPI", required_names)
        self.assertIn("PostgreSQL", required_names)
        self.assertIn("Kubernetes", preferred_names)
        self.assertIn("GraphQL", preferred_names)

    def test_06b_required_skills_marked_required(self):
        """Required skills have required=True."""
        profile = self.service.build_job_intelligence(self.sample_job)
        for s in profile.required_skills:
            self.assertTrue(s.required)

    def test_06c_preferred_skills_marked_not_required(self):
        """Preferred skills have required=False."""
        profile = self.service.build_job_intelligence(self.sample_job)
        for s in profile.preferred_skills:
            self.assertFalse(s.required)

    # ── Test 07: Experience parsing ───────────────────────────────────

    def test_07_experience_years_extracted(self):
        """Experience requirements are extracted from JD."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsNotNone(profile.experience_years)
        self.assertIn("5", profile.experience_years)

    def test_07b_experience_range(self):
        """Experience range is captured correctly."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "We need 3-5 years of experience with Python.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.experience_years, "3-5 years")

    def test_07c_no_experience(self):
        """No experience mentioned returns None."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "Join our team!"}
        profile = self.service.build_job_intelligence(job)
        self.assertIsNone(profile.experience_years)

    # ── Test 08: Seniority detection ──────────────────────────────────

    def test_08_seniority_from_title(self):
        """Seniority is detected from job title."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.seniority, "SENIOR")

    def test_08b_seniority_junior(self):
        """Junior seniority detected."""
        job = {"title": "Junior Developer", "company": "Co", "jd_text": "Entry level position"}
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.seniority, "JUNIOR")

    def test_08c_seniority_lead(self):
        """Lead seniority detected."""
        job = {"title": "Lead Engineer", "company": "Co", "jd_text": "Lead a team of engineers"}
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.seniority, "LEAD")

    def test_08d_seniority_from_jd(self):
        """Seniority falls back to JD text."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "We are looking for a senior engineer"}
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.seniority, "SENIOR")

    # ── Test 09: Role family inference ────────────────────────────────

    def test_09_role_family_backend(self):
        """Backend role family is inferred."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.role_family, "backend")

    def test_09b_role_family_frontend(self):
        """Frontend role family is inferred."""
        job = {
            "title": "Frontend Developer",
            "company": "Co",
            "jd_text": "Build client-side UI with React and Vue. Experience with frontend frameworks required.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.role_family, "frontend")

    def test_09c_role_family_devops(self):
        """DevOps role family is inferred."""
        job = {
            "title": "DevOps Engineer",
            "company": "Co",
            "jd_text": "Manage infrastructure, CI/CD pipelines, site reliability.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.role_family, "devops")

    # ── Test 10: Technology extraction ────────────────────────────────

    def test_10_technology_extraction(self):
        """Technology is extracted and categorized from skills."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsNotNone(profile.technology)
        self.assertIn("Python", profile.technology.languages)
        self.assertIn("FastAPI", profile.technology.frameworks)
        self.assertIn("PostgreSQL", profile.technology.databases)
        self.assertIn("AWS", profile.technology.cloud)
        self.assertIn("Docker", profile.technology.devops)

    # ── Test 11: Domain inference ─────────────────────────────────────

    def test_11_domain_inference(self):
        """Domain is inferred from JD text."""
        job = {
            "title": "Engineer",
            "company": "FinPay",
            "jd_text": "Build payment processing systems for our fintech platform. Banking and trading experience preferred.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.domain, "fintech")

    def test_11b_domain_saas(self):
        """SaaS domain is inferred."""
        job = {
            "title": "Engineer",
            "company": "CloudApp",
            "jd_text": "Build our B2B SaaS platform. Enterprise software experience required.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.domain, "saas")

    # ── Test 12: Location parsing ─────────────────────────────────────

    def test_12_location_remote(self):
        """Remote location type is detected."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsNotNone(profile.location)
        self.assertEqual(profile.location.remote_type, "remote")

    def test_12b_location_hybrid(self):
        """Hybrid location type is detected."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "location": "New York, NY",
            "jd_text": "This is a hybrid position. 2 days in office.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.location.remote_type, "hybrid")

    def test_12c_location_onsite(self):
        """Onsite location type is detected."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "location": "Austin, TX",
            "jd_text": "This position is onsite at our office.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.location.remote_type, "onsite")

    def test_12d_location_raw_preserved(self):
        """Raw location is preserved."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.location.raw, "San Francisco, CA")

    # ── Test 13: Salary / compensation ────────────────────────────────

    def test_13_salary_parsed(self):
        """Salary range is extracted."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsNotNone(profile.compensation)
        self.assertEqual(profile.compensation.salary_min, 150000)
        self.assertEqual(profile.compensation.salary_max, 200000)
        self.assertEqual(profile.compensation.period, "yearly")

    def test_13b_no_salary(self):
        """No salary returns None."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "Join our team!"}
        profile = self.service.build_job_intelligence(job)
        self.assertIsNone(profile.compensation)

    # ── Test 14: ATS detection ────────────────────────────────────────

    def test_14_ats_greenhouse(self):
        """Greenhouse ATS is detected from URL."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsNotNone(profile.ats)
        self.assertEqual(profile.ats.platform, "greenhouse")

    def test_14b_ats_lever(self):
        """Lever ATS is detected."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "url": "https://jobs.lever.co/company/abc123",
            "jd_text": "Join us!",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.ats.platform, "lever")

    def test_14c_ats_ashby(self):
        """Ashby ATS is detected."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "url": "https://jobs.ashbyhq.com/company/role-123",
            "jd_text": "Join us!",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.ats.platform, "ashby")

    def test_14d_no_url_no_ats(self):
        """No URL means no ATS detected."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "Join us!"}
        profile = self.service.build_job_intelligence(job)
        self.assertIsNone(profile.ats)

    # ── Test 15: Education parsing ────────────────────────────────────

    def test_15_education_extracted(self):
        """Education requirements are extracted."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "Bachelor's degree in Computer Science required. Master's preferred.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertIn("Bachelor's degree", profile.education)
        self.assertIn("Master's degree", profile.education)

    # ── Test 16: Certifications ───────────────────────────────────────

    def test_16_certifications_extracted(self):
        """Certifications are extracted from JD."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "AWS Certified Solutions Architect preferred. CKA certification is a plus.",
        }
        profile = self.service.build_job_intelligence(job)
        cert_names = [c.lower() for c in profile.certifications]
        self.assertTrue(any("aws" in c for c in cert_names))
        self.assertTrue(any("cka" in c for c in cert_names))

    # ── Test 17: Evidence tracking ────────────────────────────────────

    def test_17_skills_have_evidence(self):
        """Skills carry evidence entries."""
        profile = self.service.build_job_intelligence(self.sample_job)
        for skill in profile.required_skills:
            self.assertTrue(len(skill.evidence) > 0)
            self.assertIsNotNone(skill.evidence[0].source)

    def test_17b_location_has_evidence(self):
        """Location carries evidence."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertTrue(len(profile.location.evidence) > 0)

    # ── Test 18: Confidence scoring ───────────────────────────────────

    def test_18_confidence_with_full_data(self):
        """Full data yields high confidence."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertGreaterEqual(profile.confidence, 0.8)

    def test_18b_confidence_with_minimal_data(self):
        """Minimal data yields lower confidence."""
        profile = self.service.build_job_intelligence(self.minimal_job)
        self.assertGreater(profile.confidence, 0.0)
        self.assertLess(profile.confidence, 0.8)

    def test_18c_confidence_empty_data(self):
        """Empty data yields zero confidence."""
        profile = self.service.build_job_intelligence(self.empty_job)
        self.assertEqual(profile.confidence, 0.0)

    # ── Test 19: Missing/partial data handling ────────────────────────

    def test_19_minimal_job_handled(self):
        """Minimal job data does not crash the service."""
        profile = self.service.build_job_intelligence(self.minimal_job)
        self.assertIsInstance(profile, CanonicalJobProfile)
        self.assertEqual(profile.title, "Software Engineer")
        self.assertEqual(profile.company, "StartupCo")

    def test_19b_empty_job_handled(self):
        """Empty job dict returns empty profile."""
        profile = self.service.build_job_intelligence(self.empty_job)
        self.assertIsInstance(profile, CanonicalJobProfile)
        self.assertIsNone(profile.title)

    def test_19c_none_input(self):
        """None input returns empty profile."""
        profile = self.service.build_job_intelligence(None)
        self.assertIsInstance(profile, CanonicalJobProfile)

    # ── Test 20: Hallucination prevention ─────────────────────────────

    def test_20_no_hallucinated_skills(self):
        """No skills are fabricated when JD is empty."""
        job = {"title": "Engineer", "company": "Co", "jd_text": ""}
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.required_skills, [])
        self.assertEqual(profile.preferred_skills, [])

    def test_20b_no_hallucinated_salary(self):
        """No salary is fabricated when not in JD."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "Build great things."}
        profile = self.service.build_job_intelligence(job)
        self.assertIsNone(profile.compensation)

    def test_20c_no_hallucinated_experience(self):
        """No experience is fabricated when not mentioned."""
        job = {"title": "Engineer", "company": "Co", "jd_text": "Join us!"}
        profile = self.service.build_job_intelligence(job)
        self.assertIsNone(profile.experience_years)

    # ── Test 21: Skills by category ───────────────────────────────────

    def test_21_skills_by_category(self):
        """Skills are categorized correctly."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIn("languages", profile.skills_by_category)
        self.assertIn("Python", profile.skills_by_category["languages"])
        self.assertIn("frameworks", profile.skills_by_category)
        self.assertIn("FastAPI", profile.skills_by_category["frameworks"])

    # ── Test 22: All skills normalized list ───────────────────────────

    def test_22_all_skills_normalized(self):
        """all_skills_normalized contains deduplicated normalized names."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertIsInstance(profile.all_skills_normalized, list)
        self.assertEqual(len(profile.all_skills_normalized), len(set(profile.all_skills_normalized)))

    # ── Test 23: Employment type ──────────────────────────────────────

    def test_23_employment_type(self):
        """Employment type is parsed from JD."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.employment_type, "full-time")

    def test_23b_employment_type_contract(self):
        """Contract type is detected."""
        job = {
            "title": "Contractor",
            "company": "Co",
            "jd_text": "6 month contract position.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertEqual(profile.employment_type, "contract")

    # ── Test 24: Responsibilities extraction ──────────────────────────

    def test_24_responsibilities_extracted(self):
        """Responsibilities are extracted from JD."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertTrue(len(profile.responsibilities) > 0)
        self.assertTrue(any("API" in r or "api" in r.lower() for r in profile.responsibilities))

    # ── Test 25: Singleton factory ────────────────────────────────────

    def test_25_singleton_factory(self):
        """Singleton factory returns same instance."""
        s1 = get_job_intelligence_service()
        s2 = get_job_intelligence_service()
        self.assertIs(s1, s2)
        self.assertIsInstance(s1, JobIntelligenceService)

    # ── Test 26: Skill categorization ─────────────────────────────────

    def test_26_skill_categorization(self):
        """Skills are categorized into standard domains."""
        self.assertEqual(self.service._categorize_skill("Python"), "languages")
        self.assertEqual(self.service._categorize_skill("React"), "frameworks")
        self.assertEqual(self.service._categorize_skill("PostgreSQL"), "databases")
        self.assertEqual(self.service._categorize_skill("AWS"), "cloud")
        self.assertEqual(self.service._categorize_skill("Docker"), "devops")

    # ── Test 27: MatchService compatibility ───────────────────────────

    def test_27_match_service_not_broken(self):
        """Importing and using MatchService still works."""
        from core.services.match_service import MatchService
        self.assertIsNotNone(MatchService)

    def test_27b_candidate_intelligence_not_broken(self):
        """Candidate Intelligence service still works."""
        from core.services.candidate_intelligence_service import CandidateIntelligenceService
        svc = CandidateIntelligenceService()
        self.assertIsNotNone(svc)

    # ── Test 28: Model serialization ──────────────────────────────────

    def test_28_model_serialization(self):
        """CanonicalJobProfile can be serialized to dict."""
        profile = self.service.build_job_intelligence(self.sample_job)
        d = profile.model_dump()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["job_id"], 42)
        self.assertEqual(d["title"], "Senior Backend Engineer")

    # ── Test 29: jd_text_length tracking ──────────────────────────────

    def test_29_jd_text_length(self):
        """jd_text_length reflects actual JD length."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertGreater(profile.jd_text_length, 100)
        self.assertTrue(profile.has_description)

    def test_29b_no_description(self):
        """No JD text means has_description=False."""
        job = {"title": "Engineer", "company": "Co"}
        profile = self.service.build_job_intelligence(job)
        self.assertFalse(profile.has_description)
        self.assertEqual(profile.jd_text_length, 0)

    # ── Test 30: Posted date from metadata ────────────────────────────

    def test_30_posted_date(self):
        """Posted date comes from scraped_at metadata."""
        profile = self.service.build_job_intelligence(self.sample_job)
        self.assertEqual(profile.posted_date, "2025-01-15T10:00:00")
        self.assertEqual(profile.discovered_date, "2025-01-15T10:00:00")


class TestExperienceToSeparator(unittest.TestCase):
    """Regression tests for 'X to Y years' experience format parsing."""

    def setUp(self):
        self.service = JobIntelligenceService()

    def test_3_to_5_years(self):
        """'3 to 5 years' is parsed and represented consistently with '3-5 years'."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "We need 3 to 5 years of experience with Python.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertIsNotNone(profile.experience_years)
        # The parser should produce "3-5 years" format for both separators
        self.assertIn("3", profile.experience_years)
        self.assertIn("5", profile.experience_years)

    def test_3_to_5_years_matches_dash_format(self):
        """'3 to 5 years' and '3-5 years' produce the same representation."""
        job_to = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "Require 3 to 5 years of experience.",
        }
        job_dash = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "Require 3-5 years of experience.",
        }
        profile_to = self.service.build_job_intelligence(job_to)
        profile_dash = self.service.build_job_intelligence(job_dash)
        self.assertEqual(profile_to.experience_years, profile_dash.experience_years)

    def test_2_plus_years(self):
        """'2+ years' format is still parsed correctly."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "We require 2+ years of experience.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertIsNotNone(profile.experience_years)
        self.assertIn("2", profile.experience_years)

    def test_3_dash_5_years(self):
        """'3-5 years' format continues to work."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": "Need 3-5 years of Python experience.",
        }
        profile = self.service.build_job_intelligence(job)
        self.assertIsNotNone(profile.experience_years)
        self.assertEqual(profile.experience_years, "3-5 years")


class TestPreferredSectionSplitting(unittest.TestCase):
    """Regression tests for preferred-section false positive prevention."""

    def setUp(self):
        self.service = JobIntelligenceService()

    def test_inline_preferred_not_split(self):
        """Incidental 'preferred' in body text does NOT create a preferred section split."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": (
                "Requirements:\n"
                "- Python\n"
                "- SQL\n\n"
                "We prefer candidates with strong communication skills. "
                "Preferred experience is helpful but not required.\n"
                "- Docker\n"
                "- Kubernetes\n"
            ),
        }
        profile = self.service.build_job_intelligence(job)
        # Docker/Kubernetes should be in required_skills since "preferred" appears
        # inline (not as a section header), so the split should NOT separate them
        required_names = [s.normalized_name for s in profile.required_skills]
        preferred_names = [s.normalized_name for s in profile.preferred_skills]
        # All skills should be in required since there's no section-header split
        self.assertIn("Python", required_names)
        self.assertIn("SQL", required_names)
        self.assertIn("Docker", required_names)
        self.assertIn("Kubernetes", required_names)
        self.assertEqual(preferred_names, [])

    def test_genuine_preferred_section(self):
        """Actual 'Preferred:' section header correctly splits skills."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": (
                "Required Skills:\n"
                "Python\n"
                "SQL\n\n"
                "Preferred:\n"
                "Docker\n"
                "Kubernetes\n"
            ),
        }
        profile = self.service.build_job_intelligence(job)
        required_names = [s.normalized_name for s in profile.required_skills]
        preferred_names = [s.normalized_name for s in profile.preferred_skills]
        self.assertIn("Python", required_names)
        self.assertIn("SQL", required_names)
        self.assertIn("Docker", preferred_names)
        self.assertIn("Kubernetes", preferred_names)

    def test_nice_to_have_section(self):
        """'Nice to have:' section header correctly splits skills."""
        job = {
            "title": "Engineer",
            "company": "Co",
            "jd_text": (
                "Requirements:\n"
                "Python\n\n"
                "Nice to have:\n"
                "Redis\n"
            ),
        }
        profile = self.service.build_job_intelligence(job)
        required_names = [s.normalized_name for s in profile.required_skills]
        preferred_names = [s.normalized_name for s in profile.preferred_skills]
        self.assertIn("Python", required_names)
        self.assertIn("Redis", preferred_names)


if __name__ == "__main__":
    unittest.main()
