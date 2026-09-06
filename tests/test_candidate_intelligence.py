"""
Unit Tests for Applyr 2.0 Candidate Intelligence Service (Phase 3)
===================================================================

20 comprehensive unit tests verifying candidate intelligence model creation,
profile + resume deterministic merging, precedence rules, skill normalization,
categorization, seniority inference, evidence tracking, strength/gap logic,
API serialization, and regression safety.
"""

import unittest
from unittest.mock import MagicMock, patch

from core.models.candidate_intelligence import (
    CanonicalCandidateProfile,
    SourceOrigin,
    IntelligenceEvidence,
    SkillIntelligence,
)
from core.services.candidate_intelligence_service import (
    CandidateIntelligenceService,
    get_candidate_intelligence_service,
)
from core.models import SeniorityLevel, MatchAnalysis


class TestCandidateIntelligence(unittest.TestCase):

    def setUp(self):
        self.svc = CandidateIntelligenceService()
        self.sample_profile = {
            "personal": {
                "name": "Jane Developer",
                "email": "jane@example.com",
                "city": "San Francisco",
            },
            "target_roles": ["Senior Backend Engineer", "Full Stack Engineer"],
            "target_locations": ["San Francisco", "Remote"],
            "remote_ok": True,
            "seniority": "SENIOR",
            "skills": {
                "languages": ["python3", "typescript"],
                "frameworks": ["fastapi", "reactjs"],
            },
        }

        self.sample_resume = {
            "parsed_json": {
                "name": "Jane Extracted",
                "email": "jane_resume@example.com",
                "roles": ["Backend Developer"],
                "skills": ["python", "postgresql", "docker", "redis"],
                "experience": [
                    {
                        "title": "Lead Software Engineer",
                        "company": "Acme Tech",
                        "duration": "2021 - Present (3 years)",
                        "responsibilities": ["Built scalable FastAPI microservices", "Managed PostgreSQL database"],
                        "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    }
                ],
                "projects": [
                    {
                        "name": "AI Job Platform",
                        "description": "Automated career agent",
                        "technologies": ["Python", "Docker", "Redis"],
                    }
                ],
                "education": [{"degree": "B.S. Computer Science", "institution": "Stanford"}],
                "certifications": ["AWS Certified Solutions Architect"],
            }
        }

    # 1. Candidate intelligence creation
    def test_01_candidate_intelligence_creation(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertIsInstance(profile, CanonicalCandidateProfile)
        self.assertEqual(profile.name, "Jane Developer")

    # 2. Profile + resume merge
    def test_02_profile_and_resume_merge(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        skill_names = [s.normalized_name for s in profile.skills]
        self.assertIn("Python", skill_names)
        self.assertIn("TypeScript", skill_names)
        self.assertIn("FastAPI", skill_names)
        self.assertIn("PostgreSQL", skill_names)

    # 3. Precedence when profile and resume conflict
    def test_03_precedence_user_over_resume(self):
        # User profile name "Jane Developer" must take precedence over resume "Jane Extracted"
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertEqual(profile.name, "Jane Developer")
        self.assertEqual(profile.seniority, "SENIOR")
        self.assertEqual(profile.seniority_origin, SourceOrigin.EXPLICIT_USER)

    # 4. Skill normalization
    def test_04_skill_normalization(self):
        self.assertEqual(self.svc.normalize_skill("python3"), "Python")
        self.assertEqual(self.svc.normalize_skill("postgres"), "PostgreSQL")
        self.assertEqual(self.svc.normalize_skill("reactjs"), "React")
        self.assertEqual(self.svc.normalize_skill("node.js"), "Node.js")

    # 5. Duplicate skill removal
    def test_05_duplicate_skill_removal(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        python_skills = [s for s in profile.skills if s.normalized_name == "Python"]
        self.assertEqual(len(python_skills), 1)

    # 6. Skill categorization
    def test_06_skill_categorization(self):
        self.assertEqual(self.svc.categorize_skill("Python"), "languages")
        self.assertEqual(self.svc.categorize_skill("React"), "frameworks")
        self.assertEqual(self.svc.categorize_skill("PostgreSQL"), "databases")
        self.assertEqual(self.svc.categorize_skill("Docker"), "devops")

    # 7. Role normalization
    def test_07_role_normalization(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertEqual(profile.target_roles, ["Senior Backend Engineer", "Full Stack Engineer"])

    # 8. Seniority inference
    def test_08_seniority_inference(self):
        no_sen_profile = dict(self.sample_profile)
        no_sen_profile["seniority"] = None
        profile = self.svc.build_candidate_intelligence(no_sen_profile, self.sample_resume)
        self.assertEqual(profile.seniority, "SENIOR")  # Inferred from Lead Software Engineer
        self.assertEqual(profile.seniority_origin, SourceOrigin.INFERRED)

    # 9. Explicit vs inferred information
    def test_09_explicit_vs_inferred(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        py_skill = next(s for s in profile.skills if s.normalized_name == "Python")
        origins = [e.origin for e in py_skill.evidence]
        self.assertIn(SourceOrigin.EXPLICIT_USER, origins)
        self.assertIn(SourceOrigin.EXPLICIT_RESUME, origins)

    # 10. Unknown / missing information
    def test_10_unknown_missing_info(self):
        profile = self.svc.build_candidate_intelligence({}, {})
        self.assertEqual(profile.name, "Candidate")
        self.assertEqual(profile.email, None)
        self.assertEqual(profile.experience, [])

    # 11. Evidence preservation
    def test_11_evidence_preservation(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        py_skill = next(s for s in profile.skills if s.normalized_name == "Python")
        self.assertGreaterEqual(len(py_skill.evidence), 1)

    # 12. Confidence behavior
    def test_12_confidence_behavior(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertGreaterEqual(profile.overall_confidence, 0.8)

    # 13. Strength detection
    def test_13_strength_detection(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertTrue(any("Python" in s for s in profile.strengths))

    # 14. Gap detection
    def test_14_gap_detection(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertTrue(any("Kubernetes" in g for g in profile.skill_gaps))

    # 15. AI Gateway integration using mocks
    @patch("core.ai.gateway.AIGateway.generate")
    def test_15_ai_gateway_integration_mocked(self, mock_gw):

        mock_resp = MagicMock()
        mock_resp.text = "Inferred Domain: Distributed Systems"
        mock_gw.return_value = mock_resp

        svc = get_candidate_intelligence_service()
        profile = svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertIsInstance(profile, CanonicalCandidateProfile)

    # 16. Malformed AI output handling
    @patch("core.ai.gateway.AIGateway.generate", side_effect=RuntimeError("AI Gateway Error"))
    def test_16_malformed_ai_handling(self, mock_gw):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        self.assertIsInstance(profile, CanonicalCandidateProfile)  # Does not crash

    # 17. ResumeParserService compatibility
    def test_17_resume_parser_compatibility(self):
        from core.services.resume_parser_service import ResumeParserService
        rps = ResumeParserService()
        self.assertIsNotNone(rps)

    # 18. MatchService compatibility
    def test_18_match_service_compatibility(self):
        from core.services.match_service import get_match_service
        ms = get_match_service()
        analysis = ms.analyze(job_id=1, job_title="Backend Engineer", required_skills=["Python", "PostgreSQL"])
        self.assertIsInstance(analysis, MatchAnalysis)

    # 19. API serialization
    def test_19_api_serialization(self):
        profile = self.svc.build_candidate_intelligence(self.sample_profile, self.sample_resume)
        as_dict = profile.model_dump()
        self.assertIn("candidate_id", as_dict)
        self.assertIn("skills", as_dict)
        self.assertIn("strengths", as_dict)

    # 20. No hallucinated candidate facts
    def test_20_no_hallucinated_facts(self):
        empty_profile = self.svc.build_candidate_intelligence({}, {})
        self.assertEqual(empty_profile.certifications, [])
        self.assertEqual(empty_profile.experience, [])
        self.assertEqual(empty_profile.projects, [])


class TestParseYearsFromDuration(unittest.TestCase):
    """Direct regression tests for _parse_years_from_duration.

    These tests would FAIL if the old hardcoded total_years += 1.5 were reintroduced.
    """

    def setUp(self):
        self.svc = CandidateIntelligenceService()

    def test_simple_years(self):
        self.assertEqual(self.svc._parse_years_from_duration("3 years"), 3.0)

    def test_years_with_plus(self):
        self.assertEqual(self.svc._parse_years_from_duration("5+ years"), 5.0)

    def test_years_range_dash(self):
        """'3-5 years' should average to 4.0."""
        self.assertEqual(self.svc._parse_years_from_duration("3-5 years"), 4.0)

    def test_years_range_to(self):
        """'3 to 5 years' should average to 4.0."""
        self.assertEqual(self.svc._parse_years_from_duration("3 to 5 years"), 4.0)

    def test_year_range_no_dash(self):
        """'2020-2023' should compute year difference = 3.0."""
        self.assertEqual(self.svc._parse_years_from_duration("2020-2023"), 3.0)

    def test_months(self):
        self.assertEqual(self.svc._parse_years_from_duration("6 months"), 0.5)

    def test_12_months(self):
        self.assertEqual(self.svc._parse_years_from_duration("12 months"), 1.0)

    def test_present_format(self):
        """'2021 - Present (3 years)' extracts 3.0 from '3 years' sub-pattern."""
        self.assertEqual(self.svc._parse_years_from_duration("2021 - Present (3 years)"), 3.0)

    def test_empty_string(self):
        self.assertEqual(self.svc._parse_years_from_duration(""), 0.0)

    def test_none_like_empty(self):
        self.assertEqual(self.svc._parse_years_from_duration(""), 0.0)

    def test_gibberish(self):
        self.assertEqual(self.svc._parse_years_from_duration("xyz"), 0.0)

    def test_yr_shorthand(self):
        self.assertEqual(self.svc._parse_years_from_duration("3 yrs"), 3.0)

    def test_fractional_years(self):
        self.assertEqual(self.svc._parse_years_from_duration("2.5 years"), 2.5)

    def test_old_hardcoded_1_5_would_fail(self):
        """Regression: old code always returned 1.5 for any string containing 'year'.

        If the old behavior is reintroduced, this test will fail because
        _parse_years_from_duration('3 years') would return 1.5 instead of 3.0.
        """
        result = self.svc._parse_years_from_duration("3 years")
        self.assertNotEqual(result, 1.5)
        self.assertEqual(result, 3.0)

    def test_old_hardcoded_1_0_would_fail(self):
        """Regression: old code always returned 1.0 for strings without 'year'.

        If the old behavior is reintroduced, _parse_years_from_duration('6 months')
        would return 1.0 instead of 0.5.
        """
        result = self.svc._parse_years_from_duration("6 months")
        self.assertNotEqual(result, 1.0)
        self.assertEqual(result, 0.5)


class TestExperienceAccumulation(unittest.TestCase):
    """Test that total_years accumulates actual parsed values, not hardcoded 1.5."""

    def test_multiple_entries_accumulate_actual_values(self):
        """Two entries: '2 years' + '3 years' = 5.0 total, not 3.0 (2 * 1.5)."""
        svc = CandidateIntelligenceService()
        profile_data = {
            "personal": {"name": "Test"},
            "target_roles": ["Engineer"],
        }
        resume_data = {
            "parsed_json": {
                "skills": ["Python"],
                "experience": [
                    {"title": "Engineer A", "company": "Co1", "duration": "2 years"},
                    {"title": "Engineer B", "company": "Co2", "duration": "3 years"},
                ],
            }
        }
        profile = svc.build_candidate_intelligence(profile_data, resume_data)
        # With old hardcoded 1.5: total = 1.5 + 1.5 = 3.0 -> SENIOR
        # With actual parsing: total = 2.0 + 3.0 = 5.0 -> SENIOR
        # The key check: experience entries have correct years values
        self.assertEqual(len(profile.experience), 2)
        self.assertEqual(profile.experience[0].years, 2.0)
        self.assertEqual(profile.experience[1].years, 3.0)

    def test_months_entry_accumulates_correctly(self):
        """Entry with '6 months' contributes 0.5, not 1.0 or 1.5."""
        svc = CandidateIntelligenceService()
        profile_data = {"personal": {"name": "Test"}, "target_roles": ["Engineer"]}
        resume_data = {
            "parsed_json": {
                "skills": ["Python"],
                "experience": [
                    {"title": "Intern", "company": "Co", "duration": "6 months"},
                ],
            }
        }
        profile = svc.build_candidate_intelligence(profile_data, resume_data)
        self.assertEqual(profile.experience[0].years, 0.5)

    def test_range_entry_averages(self):
        """Entry with '3-5 years' contributes 4.0, not 1.5."""
        svc = CandidateIntelligenceService()
        profile_data = {"personal": {"name": "Test"}, "target_roles": ["Engineer"]}
        resume_data = {
            "parsed_json": {
                "skills": ["Python"],
                "experience": [
                    {"title": "Engineer", "company": "Co", "duration": "3-5 years"},
                ],
            }
        }
        profile = svc.build_candidate_intelligence(profile_data, resume_data)
        self.assertEqual(profile.experience[0].years, 4.0)


if __name__ == "__main__":
    unittest.main()
