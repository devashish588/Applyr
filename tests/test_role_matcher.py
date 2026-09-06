"""
Role Matcher — Phase 5B-4 Tests
"""

import unittest

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    RequirementStatus,
    RoleAvailability,
    RoleEntry,
    RoleRelationshipType,
    SkillInventoryStatus,
    StructuredRoleRequirement,
)
from core.services.role_matcher import RoleMatcher, ROLE_ALIAS_MAP


class TestRoleNormalizer(unittest.TestCase):
    def test_whitespace(self):
        from core.services.role_normalizer import normalize_title
        self.assertEqual(normalize_title("  Backend Engineer  "), "Backend Engineer")

    def test_casing(self):
        from core.services.role_normalizer import normalize_title
        self.assertEqual(normalize_title("backend engineer"), "backend engineer")
        # Existing behavior preserves case except sr/jr
        self.assertEqual(normalize_title("Sr Backend Engineer"), "Senior Backend Engineer")

    def test_sr_jr(self):
        from core.services.role_normalizer import normalize_title
        self.assertEqual(normalize_title("Sr. Backend Engineer"), "Senior Backend Engineer")
        self.assertEqual(normalize_title("Jr Frontend Engineer"), "Junior Frontend Engineer")

    def test_job_intelligence_preserved(self):
        from core.services.job_intelligence_service import JobIntelligenceService
        svc = JobIntelligenceService()
        self.assertEqual(svc._normalize_title("Sr Backend Engineer"), "Senior Backend Engineer")
        self.assertEqual(svc._normalize_title("  Backend Engineer "), "Backend Engineer")


class TestRoleExact(unittest.TestCase):
    def setUp(self):
        self.m = RoleMatcher()

    def _eval(self, cand_entries, job_req):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw=r, normalized=n, is_current=False) for r, n in cand_entries],
        )
        job = CanonicalJobInput(role_requirement=job_req)
        return self.m.evaluate(cand, job)[0]

    def test_exact(self):
        req = StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED")
        ev = self._eval([("Backend Engineer", "Backend Engineer")], req)
        self.assertEqual(ev.relationship, RoleRelationshipType.EXACT)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_alias(self):
        req = StructuredRoleRequirement(raw="Software Developer", normalized="Software Developer", required=True, kind="STRUCTURED")
        ev = self._eval([("Software Engineer", "Software Engineer")], req)
        self.assertEqual(ev.relationship, RoleRelationshipType.ALIAS)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_ml_alias(self):
        req = StructuredRoleRequirement(raw="Machine Learning Engineer", normalized="Machine Learning Engineer", required=True, kind="STRUCTURED")
        ev = self._eval([("ML Engineer", "ML Engineer")], req)
        self.assertEqual(ev.relationship, RoleRelationshipType.ALIAS)

    def test_false_positive_engineer(self):
        req = StructuredRoleRequirement(raw="Software Engineer", normalized="Software Engineer", required=True, kind="STRUCTURED")
        ev = self._eval([("Engineer", "Engineer")], req)
        self.assertEqual(ev.relationship, RoleRelationshipType.NONE)
        self.assertEqual(ev.status, RequirementStatus.MISSING)

    def test_unrelated(self):
        req = StructuredRoleRequirement(raw="Backend Developer", normalized="Backend Developer", required=True, kind="STRUCTURED")
        ev = self._eval([("Frontend Developer", "Frontend Developer")], req)
        self.assertEqual(ev.relationship, RoleRelationshipType.NONE)
        self.assertEqual(ev.status, RequirementStatus.MISSING)


class TestRoleTransferable(unittest.TestCase):
    def test_directed(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Data Analyst", normalized="Data Analyst")],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Data Scientist", normalized="Data Scientist", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.relationship, RoleRelationshipType.TRANSFERABLE)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)
        # Reverse not implied
        cand2 = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Data Scientist", normalized="Data Scientist")],
        )
        job2 = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Data Analyst", normalized="Data Analyst", required=True, kind="STRUCTURED"))
        ev2 = m.evaluate(cand2, job2)[0]
        self.assertEqual(ev2.relationship, RoleRelationshipType.NONE)
        self.assertEqual(ev2.status, RequirementStatus.MISSING)

    def test_unmapped_missing(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="DevOps Engineer", normalized="DevOps Engineer")],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.relationship, RoleRelationshipType.NONE)


class TestRoleRelated(unittest.TestCase):
    def test_related_no_credit(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer")],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Frontend Developer", normalized="Frontend Developer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        # No RELATED credit in 5B-4
        self.assertEqual(ev.relationship, RoleRelationshipType.NONE)
        self.assertEqual(ev.status, RequirementStatus.MISSING)


class TestRoleUnknown(unittest.TestCase):
    def test_undetermined(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, role_availability=RoleAvailability.UNDETERMINED, role_entries=[])
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)

    def test_determined_empty(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, role_availability=RoleAvailability.DETERMINED, role_entries=[])
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)

    def test_unparseable(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, role_availability=RoleAvailability.DETERMINED, role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer")])
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend", normalized=None, required=True, kind="UNPARSEABLE"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)

    def test_no_requirement(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, role_availability=RoleAvailability.DETERMINED, role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer")])
        job = CanonicalJobInput(role_requirement=None)
        self.assertEqual(m.evaluate(cand, job), [])

    def test_family_only_no_satisfied(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer")],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw=None, normalized=None, role_family="backend", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        # RELATED is non-credit-bearing, so family-only must not produce SATISFIED
        self.assertNotEqual(ev.status, RequirementStatus.SATISFIED)
        self.assertEqual(ev.relationship, RoleRelationshipType.NONE)


class TestRoleHistory(unittest.TestCase):
    def test_historical_wins(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[
                RoleEntry(raw="Product Manager", normalized="Product Manager", is_current=True),
                RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=False),
            ],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.relationship, RoleRelationshipType.EXACT)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_history_order_determinism(self):
        m = RoleMatcher()
        cand_a = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[
                RoleEntry(raw="Product Manager", normalized="Product Manager", is_current=True),
                RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=False),
            ],
        )
        cand_b = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[
                RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=False),
                RoleEntry(raw="Product Manager", normalized="Product Manager", is_current=True),
            ],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        self.assertEqual(m.evaluate(cand_a, job)[0].relationship, m.evaluate(cand_b, job)[0].relationship)
        self.assertEqual(m.evaluate(cand_a, job)[0].status, m.evaluate(cand_b, job)[0].status)

    def test_dedup(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[
                RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=False),
                RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=True),
            ],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.relationship, RoleRelationshipType.EXACT)

    def test_duplicate_via_adapter(self):
        # current_role duplicated in experience history must not double-count but preserve provenance
        from types import SimpleNamespace

        profile = SimpleNamespace(
            current_role="Backend Engineer",
            experience=[SimpleNamespace(title="Backend Engineer", years=2.0), SimpleNamespace(title="Backend Engineer", years=1.0)],
            target_roles=[],
            preferred_locations=[],
            remote_preference="any",
            skills=[],
            skill_occurrences=[],
            overall_confidence=0.9,
            seniority="MID",
            name="Test",
            candidate_id="test",
        )
        from core.services.match_engine_adapters import CandidateAdapter

        cand = CandidateAdapter().adapt(profile)
        # Deduped to single entry, is_current True
        self.assertEqual(len(cand.role_entries), 1)
        self.assertTrue(cand.role_entries[0].is_current)

    def test_target_roles_not_satisfied(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[],  # no authoritative history
            target_roles=["Software Engineer"],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Software Engineer", normalized="Software Engineer", required=True, kind="STRUCTURED"))
        # Even though target_roles contains match, authoritative entries empty → UNKNOWN
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestRoleEvidence(unittest.TestCase):
    def test_evidence_preserved(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=True)],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", role_family="backend", required=True, kind="STRUCTURED"))
        ev = m.evaluate(cand, job)[0]
        self.assertEqual(ev.candidate_raw, "Backend Engineer")
        self.assertEqual(ev.job_raw, "Backend Engineer")
        self.assertEqual(ev.job_role_family, "backend")
        self.assertTrue(ev.is_current_role)


class TestRoleDeterminism(unittest.TestCase):
    def test_deterministic(self):
        m = RoleMatcher()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer"), RoleEntry(raw="Software Engineer", normalized="Software Engineer")],
        )
        job = CanonicalJobInput(role_requirement=StructuredRoleRequirement(raw="Software Engineer", normalized="Software Engineer", required=True, kind="STRUCTURED"))
        e1 = m.evaluate(cand, job)[0]
        e2 = m.evaluate(cand, job)[0]
        self.assertEqual(e1.relationship, e2.relationship)
        self.assertEqual(e1.status, e2.status)


class TestMatchEngine2Role(unittest.TestCase):
    def test_composition(self):
        from core.services.match_engine2 import MatchEngine2
        from core.models.match_engine import ExperienceAvailability

        engine = MatchEngine2()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
            skill_inventory_raw=["Python"],
            experience_years=3.0,
            experience_availability=ExperienceAvailability.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=True)],
        )
        job = CanonicalJobInput(
            requirements=[],
            experience_requirement=None,
            role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", required=True, kind="STRUCTURED"),
        )
        result = engine.analyze(cand, job)
        self.assertEqual(len(result.role_evaluations), 1)
        self.assertEqual(result.role_evaluations[0].status, RequirementStatus.SATISFIED)
        self.assertEqual(len(result.requirement_evaluations), 0)

    def test_regression_skill_unchanged(self):
        from core.services.match_engine2 import MatchEngine2
        engine = MatchEngine2()
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
            skill_inventory_raw=["Python"],
            role_availability=RoleAvailability.UNDETERMINED,
            role_entries=[],
        )
        job = CanonicalJobInput(
            requirements=[],
            role_requirement=None,
        )
        result = engine.analyze(cand, job)
        self.assertEqual(result.role_evaluations, [])


if __name__ == "__main__":
    unittest.main()
