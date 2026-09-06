"""
Experience Matcher — Phase 5B-3 Test Hardening
===============================================

Focused regression for:
  experience_years is None → no evaluation
  unsupported present → UNPARSEABLE → UNKNOWN (preserved raw + evidence source)
  malformed → UNKNOWN
  supported 3+ years remains MINIMUM normal
"""

import unittest

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    ExperienceAvailability,
    RequirementStatus,
    SkillInventoryStatus,
    StructuredExperienceRequirement,
)
from core.services.experience_matcher import ExperienceMatcher
from core.services.match_engine_adapters import JobAdapter


class TestExperienceAdapterBoundary(unittest.TestCase):
    """5B-3 hardening: adapter preserves no-requirement vs unparseable."""

    def test_experience_years_none_produces_no_requirement(self):
        # Case 1: _parse_experience(None) still None (parsing function alone)
        job = JobAdapter()._parse_experience(None)
        self.assertIsNone(job)
        # Via full adapter with has_description False (no JD) → SOURCE_UNAVAILABLE → UNKNOWN (not no evaluation)
        from types import SimpleNamespace

        profile = SimpleNamespace(
            experience_years=None,
            required_skills=[],
            preferred_skills=[],
            job_id=1,
            title="Engineer",
            company="Acme",
            location=None,
            seniority=None,
            has_description=False,
            experience_provenance="source_unavailable",
        )
        ci = JobAdapter().adapt(profile)  # type: ignore[arg-type]
        self.assertIsNotNone(ci.experience_requirement)
        assert ci.experience_requirement is not None
        # has_description False with no authoritative NO_REQUIREMENT → SOURCE_UNAVAILABLE, not UNPARSEABLE
        self.assertEqual(ci.experience_requirement.kind, "SOURCE_UNAVAILABLE")
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            experience_years=5.0,
            experience_availability=ExperienceAvailability.DETERMINED,
        )
        evs = ExperienceMatcher().evaluate(cand, ci)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].status, RequirementStatus.UNKNOWN)

    def test_unsupported_up_to_preserved_as_unparseable(self):
        # Case 2: unsupported "up to 5 years"
        req = JobAdapter._parse_experience("up to 5 years")
        self.assertIsNotNone(req)
        assert req is not None
        self.assertEqual(req.kind, "UNPARSEABLE")
        self.assertEqual(req.raw, "up to 5 years")
        self.assertTrue(req.required)

        # Via adapter
        from types import SimpleNamespace

        profile = SimpleNamespace(
            experience_years="up to 5 years",
            required_skills=[],
            preferred_skills=[],
            job_id=2,
            title="Engineer",
            company="Acme",
            location=None,
            seniority=None,
        )
        ci = JobAdapter().adapt(profile)  # type: ignore[arg-type]
        self.assertIsNotNone(ci.experience_requirement)
        assert ci.experience_requirement is not None
        self.assertEqual(ci.experience_requirement.kind, "UNPARSEABLE")
        self.assertEqual(ci.experience_requirement.raw, "up to 5 years")

        # Matcher produces exactly one UNKNOWN with preserved raw + source
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            experience_years=4.0,
            experience_availability=ExperienceAvailability.DETERMINED,
        )
        evs = ExperienceMatcher().evaluate(cand, ci)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].status, RequirementStatus.UNKNOWN)
        self.assertEqual(evs[0].requirement.raw, "up to 5 years")
        self.assertEqual(evs[0].evidence_source, "requirement_unparseable")

    def test_malformed_unsupported_produces_unknown(self):
        # Case 3: malformed already rejected — "five years" not matched by patterns
        req = JobAdapter._parse_experience("five years")
        self.assertIsNotNone(req)
        assert req is not None
        self.assertEqual(req.kind, "UNPARSEABLE")

        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            experience_years=3.0,
            experience_availability=ExperienceAvailability.DETERMINED,
        )
        job = CanonicalJobInput(
            experience_requirement=StructuredExperienceRequirement(
                raw="five years", min_years=None, max_years=None, kind="UNPARSEABLE", required=True
            )
        )
        evs = ExperienceMatcher().evaluate(cand, job)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].status, RequirementStatus.UNKNOWN)
        self.assertEqual(evs[0].requirement.raw, "five years")

    def test_supported_3plus_remains_minimum(self):
        # Case 4: supported "3+ years" normal
        req = JobAdapter._parse_experience("3+ years")
        self.assertIsNotNone(req)
        assert req is not None
        self.assertEqual(req.kind, "MINIMUM")
        self.assertEqual(req.min_years, 3.0)

        # Evaluated normally: DETERMINED 2 vs 3+ → MISSING, 3 vs 3+ → SATISFIED
        matcher = ExperienceMatcher()
        c2 = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            experience_years=2.0,
            experience_availability=ExperienceAvailability.DETERMINED,
        )
        c3 = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            experience_years=3.0,
            experience_availability=ExperienceAvailability.DETERMINED,
        )
        job = CanonicalJobInput(experience_requirement=req)
        self.assertEqual(matcher.evaluate(c2, job)[0].status, RequirementStatus.MISSING)
        self.assertEqual(matcher.evaluate(c3, job)[0].status, RequirementStatus.SATISFIED)


if __name__ == "__main__":
    unittest.main()
