"""
Skill Matcher — Phase 5B-2 Comprehensive Tests
===============================================

Covers A-N from test matrix, golden dataset, and edge cases.
"""

import unittest

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    CanonicalJobRequirement,
    RequirementStatus,
    SkillInventoryStatus,
    SkillRelationshipType,
)
from core.services.skill_matcher import SkillMatcher, _classify_pair


class TestClassifyPair(unittest.TestCase):
    """Direct _classify_pair tests."""

    def test_exact_same_raw_and_canonical(self):
        self.assertEqual(_classify_pair("Python", "Python", "Python", "Python"), SkillRelationshipType.EXACT)

    def test_alias_different_raw_same_canonical(self):
        self.assertEqual(_classify_pair("Python", "python", "Python", "Python"), SkillRelationshipType.ALIAS)
        self.assertEqual(_classify_pair("PostgreSQL", "postgres", "PostgreSQL", "PostgreSQL"), SkillRelationshipType.ALIAS)

    def test_alias_reverse(self):
        self.assertEqual(_classify_pair("PostgreSQL", "PostgreSQL", "PostgreSQL", "postgresql"), SkillRelationshipType.ALIAS)

    def test_transferable(self):
        self.assertEqual(_classify_pair("PostgreSQL", "PostgreSQL", "SQL", "SQL"), SkillRelationshipType.TRANSFERABLE)
        self.assertEqual(_classify_pair("PyTorch", "PyTorch", "Machine Learning", "Machine Learning"), SkillRelationshipType.TRANSFERABLE)

    def test_related_same_category(self):
        self.assertEqual(_classify_pair("FastAPI", "FastAPI", "Flask", "Flask"), SkillRelationshipType.RELATED)
        self.assertEqual(_classify_pair("React", "React", "Vue", "Vue"), SkillRelationshipType.RELATED)

    def test_none_cross_category(self):
        self.assertEqual(_classify_pair("Python", "Python", "Docker", "Docker"), SkillRelationshipType.NONE)
        self.assertEqual(_classify_pair("Git", "Git", "Python", "Python"), SkillRelationshipType.NONE)

    def test_none_other_category(self):
        # Unknown categories are 'other' -> never RELATED
        self.assertEqual(_classify_pair("Foobar", "Foobar", "Bazqux", "Bazqux"), SkillRelationshipType.NONE)

    def test_empty_canonical(self):
        self.assertEqual(_classify_pair("", "", "Python", "Python"), SkillRelationshipType.NONE)
        self.assertEqual(_classify_pair("Python", "Python", "", ""), SkillRelationshipType.NONE)


class TestSkillMatcherDirect(unittest.TestCase):
    """Direct SkillMatcher tests via CanonicalCandidateInput."""

    def setUp(self):
        self.matcher = SkillMatcher()

    def _eval(self, cand_skills, cand_raws, job_reqs):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=cand_skills,
            skill_inventory_raw=cand_raws,
        )
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name=r, canonical_name=c) for r, c in job_reqs])
        return self.matcher.evaluate(cand, job)

    def test_exact(self):
        evs = self._eval(["Python"], ["Python"], [("Python", "Python")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(evs[0].status, RequirementStatus.SATISFIED)
        self.assertEqual(evs[0].matched_skill, "Python")
        self.assertEqual(evs[0].matched_skill_raw, "Python")

    def test_alias_casing(self):
        evs = self._eval(["Python"], ["python"], [("Python", "Python")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.ALIAS)
        self.assertEqual(evs[0].status, RequirementStatus.SATISFIED)
        self.assertEqual(evs[0].matched_skill_raw, "python")

    def test_transferable(self):
        evs = self._eval(["PostgreSQL"], ["PostgreSQL"], [("SQL", "SQL")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.TRANSFERABLE)
        self.assertEqual(evs[0].status, RequirementStatus.PARTIALLY_SATISFIED)

    def test_related(self):
        evs = self._eval(["FastAPI"], ["FastAPI"], [("Flask", "Flask")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.RELATED)
        self.assertEqual(evs[0].status, RequirementStatus.MISSING)
        self.assertIn("FastAPI", evs[0].related_skills)

    def test_none(self):
        evs = self._eval(["Python"], ["Python"], [("Docker", "Docker")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.NONE)
        self.assertEqual(evs[0].status, RequirementStatus.MISSING)

    def test_precedence_exact_beats_alias(self):
        # ["python","Python"] vs Python -> EXACT wins even though alias appears first
        evs = self._eval(["Python", "Python"], ["python", "Python"], [("Python", "Python")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.EXACT)

    def test_precedence_reverse_order(self):
        evs = self._eval(["Python", "Python"], ["Python", "python"], [("Python", "Python")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.EXACT)

    def test_undetermined_all_unknown(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.UNDETERMINED, skill_inventory=["Python"], skill_inventory_raw=["Python"])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python")])
        evs = self.matcher.evaluate(cand, job)
        self.assertEqual(evs[0].status, RequirementStatus.UNKNOWN)

    def test_determined_empty_all_missing(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=[], skill_inventory_raw=[])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python")])
        evs = self.matcher.evaluate(cand, job)
        self.assertEqual(evs[0].status, RequirementStatus.MISSING)

    def test_duplicates_handled(self):
        evs = self._eval(["Python", "Python", "Python"], ["Python", "python", "Python"], [("Python", "Python")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(evs[0].status, RequirementStatus.SATISFIED)

    def test_multiple_candidates_strongest_wins(self):
        evs = self._eval(["FastAPI", "Django", "Flask"], ["FastAPI", "Django", "Flask"], [("Flask", "Flask")])
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.EXACT)

    def test_malformed_empty_requirement(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=["Python"], skill_inventory_raw=["Python"])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="", canonical_name="")])
        evs = self.matcher.evaluate(cand, job)
        self.assertEqual(evs[0].status, RequirementStatus.UNKNOWN)

    def test_whitespace_handling(self):
        # Canonicals with whitespace-only are NONE
        evs = self._eval(["   "], ["   "], [("Python", "Python")])
        # Empty canonical after strip? Actually "   " canonical is "   " not empty but our check does strip.
        # Our _classify_pair checks strip() -> NONE if whitespace only
        self.assertEqual(evs[0].relationship_type, SkillRelationshipType.NONE)

    def test_deterministic_repeatability(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=["Python", "FastAPI"], skill_inventory_raw=["python", "FastAPI"])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python"), CanonicalJobRequirement(raw_name="Flask", canonical_name="Flask")])
        evs1 = self.matcher.evaluate(cand, job)
        evs2 = self.matcher.evaluate(cand, job)
        self.assertEqual([(e.status, e.relationship_type) for e in evs1], [(e.status, e.relationship_type) for e in evs2])

    def test_required_vs_preferred(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=["Python"], skill_inventory_raw=["Python"])
        job = CanonicalJobInput(requirements=[
            CanonicalJobRequirement(raw_name="Python", canonical_name="Python", required=True),
            CanonicalJobRequirement(raw_name="Redis", canonical_name="Redis", required=False),
        ])
        evs = self.matcher.evaluate(cand, job)
        self.assertEqual(evs[0].status, RequirementStatus.SATISFIED)
        self.assertTrue(evs[0].requirement.required)
        self.assertEqual(evs[1].status, RequirementStatus.MISSING)
        self.assertFalse(evs[1].requirement.required)


class TestGoldenDataset(unittest.TestCase):
    """Golden dataset (small, maintainable)."""

    def test_golden(self):
        cases = [
            # (candidate_canonicals, candidate_raws, job_canonical, expected_relationship, expected_status)
            ((["Python"], ["Python"], "Python"), SkillRelationshipType.EXACT, RequirementStatus.SATISFIED),
            ((["Python"], ["python"], "Python"), SkillRelationshipType.ALIAS, RequirementStatus.SATISFIED),
            ((["PostgreSQL"], ["postgres"], "PostgreSQL"), SkillRelationshipType.ALIAS, RequirementStatus.SATISFIED),
            ((["PostgreSQL"], ["PostgreSQL"], "PostgreSQL"), SkillRelationshipType.EXACT, RequirementStatus.SATISFIED),
            ((["PostgreSQL"], ["PostgreSQL"], "SQL"), SkillRelationshipType.TRANSFERABLE, RequirementStatus.PARTIALLY_SATISFIED),
            ((["FastAPI"], ["FastAPI"], "Flask"), SkillRelationshipType.RELATED, RequirementStatus.MISSING),
            ((["Git"], ["Git"], "Python"), SkillRelationshipType.NONE, RequirementStatus.MISSING),
            ((["PyTorch"], ["PyTorch"], "Machine Learning"), SkillRelationshipType.TRANSFERABLE, RequirementStatus.PARTIALLY_SATISFIED),
            ((["Python", "Python"], ["python", "Python"], "Python"), SkillRelationshipType.EXACT, RequirementStatus.SATISFIED),
            ((["PostgreSQL", "PostgreSQL"], ["postgres", "PostgreSQL"], "PostgreSQL"), SkillRelationshipType.EXACT, RequirementStatus.SATISFIED),
        ]
        m = SkillMatcher()
        for (cans, raws, job_can), exp_rel, exp_status in cases:
            with self.subTest(candidate=cans, job=job_can):
                cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=cans, skill_inventory_raw=raws)
                job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name=job_can, canonical_name=job_can)])
                ev = m.evaluate(cand, job)[0]
                self.assertEqual(ev.relationship_type, exp_rel)
                self.assertEqual(ev.status, exp_status)


class TestGeneralCaseOccurrences(unittest.TestCase):
    """5B-2 correction: general case with aliases sharing canonical."""

    def setUp(self):
        self.m = SkillMatcher()

    def _eval(self, cans, raws, job_raw, job_can):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=cans, skill_inventory_raw=raws)
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name=job_raw, canonical_name=job_can)])
        return self.m.evaluate(cand, job)[0]

    def test_A_python3_py_job_python3_exact(self):
        ev = self._eval(["Python","Python"], ["python3","py"], "python3", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_B_py_python3_job_python3_exact(self):
        ev = self._eval(["Python","Python"], ["py","python3"], "python3", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)

    def test_C_python3_py_job_Python_alias(self):
        ev = self._eval(["Python","Python"], ["python3","py"], "Python", "Python")
        self.assertIn(ev.relationship_type, (SkillRelationshipType.ALIAS, SkillRelationshipType.EXACT))
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_D_python_Python_job_Python_exact(self):
        ev = self._eval(["Python","Python"], ["python","Python"], "Python", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)

    def test_E_python_job_Python_alias(self):
        ev = self._eval(["Python"], ["python"], "Python", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.ALIAS)

    def test_F_python3_job_python3_exact(self):
        ev = self._eval(["Python"], ["python3"], "python3", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)

    def test_G_exact_later_wins(self):
        ev = self._eval(["Python","Python"], ["py","python3"], "python3", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)

    def test_H_exact_first_wins(self):
        ev = self._eval(["Python","Python"], ["python3","py"], "python3", "Python")
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)


class TestAdapterIntegration(unittest.TestCase):
    """Adapter → Matcher integration proving raw preservation."""

    def test_adapter_preserves_exact(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, skill_inventory=["Python", "Python"], skill_inventory_raw=["python", "Python"])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python")])
        ev = SkillMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_adapter_occurrences_end_to_end(self):
        """End-to-end: CandidateIntelligence → Adapter → Matcher preserves EXACT."""
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        from core.services.match_engine_adapters import CandidateAdapter

        svc = get_candidate_intelligence_service()
        profile = svc.build_candidate_intelligence(
            profile_data={"skills": ["python3", "py"]},
            resume_data={"skills_json": [], "parsed_json": {}},
        )
        adapter = CandidateAdapter()
        cand_input = adapter.adapt(profile)
        # Both occurrences preserved
        self.assertEqual(cand_input.skill_inventory, ["Python", "Python"])
        self.assertEqual(cand_input.skill_inventory_raw, ["python3", "py"])
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="python3", canonical_name="Python")])
        ev = SkillMatcher().evaluate(cand_input, job)[0]
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_adapter_occurrences_reverse_order(self):
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        from core.services.match_engine_adapters import CandidateAdapter

        svc = get_candidate_intelligence_service()
        profile = svc.build_candidate_intelligence(
            profile_data={"skills": ["py", "python3"]},
            resume_data={"skills_json": [], "parsed_json": {}},
        )
        cand_input = CandidateAdapter().adapt(profile)
        job = CanonicalJobInput(requirements=[CanonicalJobRequirement(raw_name="python3", canonical_name="Python")])
        ev = SkillMatcher().evaluate(cand_input, job)[0]
        self.assertEqual(ev.relationship_type, SkillRelationshipType.EXACT)


if __name__ == "__main__":
    unittest.main()
