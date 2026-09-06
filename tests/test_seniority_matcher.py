"""
Seniority Matcher — Phase 5B-6 Tests
"""

import unittest

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    RequirementStatus,
    SeniorityAvailability,
    SkillInventoryStatus,
    StructuredSeniorityRequirement,
)
from core.services.seniority_matcher import SeniorityMatcher
from core.services.seniority_normalizer import normalize_seniority


class TestSeniorityExact(unittest.TestCase):
    def setUp(self):
        self.m = SeniorityMatcher()

    def _eval(self, cand_level, cand_avail, job_raw, job_norm, job_kind="STRUCTURED"):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=cand_avail,
            candidate_seniority_raw=cand_level,
            candidate_seniority_normalized=normalize_seniority(cand_level) if cand_level else None,
            candidate_seniority_source="explicit_seniority" if cand_avail == SeniorityAvailability.DETERMINED else None,
        )
        job_req = StructuredSeniorityRequirement(raw=job_raw, normalized_level=job_norm, kind=job_kind, required=True) if job_raw is not None or job_norm is not None or job_kind != "STRUCTURED" else None
        # For None case, create AMBIGUOUS
        if job_raw is None and job_norm is None and job_kind == "STRUCTURED":
            job_req = StructuredSeniorityRequirement(raw=None, normalized_level=None, kind="AMBIGUOUS", required=True)
        job = CanonicalJobInput(seniority_requirement=job_req)
        return self.m.evaluate(cand, job)[0] if self.m.evaluate(cand, job) else None

    def test_exact_junior(self):
        ev = self._eval("JUNIOR", SeniorityAvailability.DETERMINED, "JUNIOR", "JUNIOR")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)
        self.assertEqual(ev.relationship, "EXACT")

    def test_exact_mid(self):
        ev = self._eval("MID", SeniorityAvailability.DETERMINED, "MID", "MID")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_exact_senior(self):
        ev = self._eval("SENIOR", SeniorityAvailability.DETERMINED, "SENIOR", "SENIOR")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_underqualified_mid_to_senior(self):
        ev = self._eval("MID", SeniorityAvailability.DETERMINED, "SENIOR", "SENIOR")
        self.assertEqual(ev.status, RequirementStatus.MISSING)
        self.assertEqual(ev.relationship, "LOWER_THAN_REQUIRED")

    def test_underqualified_junior_to_senior(self):
        ev = self._eval("JUNIOR", SeniorityAvailability.DETERMINED, "SENIOR", "SENIOR")
        self.assertEqual(ev.status, RequirementStatus.MISSING)

    def test_higher_senior_to_junior(self):
        ev = self._eval("SENIOR", SeniorityAvailability.DETERMINED, "JUNIOR", "JUNIOR")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)
        self.assertEqual(ev.relationship, "HIGHER_THAN_REQUIRED")

    def test_higher_staff_to_senior(self):
        ev = self._eval("STAFF", SeniorityAvailability.DETERMINED, "SENIOR", "SENIOR")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_higher_principal_to_senior(self):
        ev = self._eval("PRINCIPAL", SeniorityAvailability.DETERMINED, "SENIOR", "SENIOR")
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)


class TestSeniorityExperienceSeparation(unittest.TestCase):
    def test_years_not_seniority(self):
        # 5 years + no explicit seniority -> UNDETERMINED -> UNKNOWN
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=SeniorityAvailability.UNDETERMINED,
            candidate_seniority_raw=None,
            candidate_seniority_normalized=None,
            experience_years=5.0,
        )
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestTargetRoles(unittest.TestCase):
    def test_target_roles_not_seniority(self):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=SeniorityAvailability.DETERMINED,
            candidate_seniority_raw="MID",
            candidate_seniority_normalized="MID",
            candidate_seniority_source="explicit_seniority",
            target_roles=["Senior AI Engineer"],
        )
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.MISSING)  # MID vs SENIOR, not SATISFIED via target_roles


class TestSeniorityInferred(unittest.TestCase):
    def test_inferred_unknown(self):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=SeniorityAvailability.UNDETERMINED,
            candidate_seniority_raw="SENIOR",
            candidate_seniority_normalized="SENIOR",
            candidate_seniority_source="inferred",
        )
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestJobAmbiguous(unittest.TestCase):
    def test_job_none_ambiguous(self):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=SeniorityAvailability.DETERMINED,
            candidate_seniority_raw="SENIOR",
            candidate_seniority_normalized="SENIOR",
            candidate_seniority_source="explicit_seniority",
        )
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw=None, normalized_level=None, kind="AMBIGUOUS"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestSeniorityLead(unittest.TestCase):
    def test_lead_unknown(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="SENIOR", candidate_seniority_normalized="SENIOR", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="LEAD", normalized_level=None, kind="UNPARSEABLE"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)

    def test_principal_vs_lead_unknown(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="PRINCIPAL", candidate_seniority_normalized="PRINCIPAL", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="LEAD", normalized_level=None, kind="UNPARSEABLE"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestManagement(unittest.TestCase):
    def test_manager_unknown(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="SENIOR", candidate_seniority_normalized="SENIOR", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="MANAGER", normalized_level=None, kind="UNPARSEABLE"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestPrincipalStaff(unittest.TestCase):
    def test_principal_principal(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="PRINCIPAL", candidate_seniority_normalized="PRINCIPAL", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="PRINCIPAL", normalized_level="PRINCIPAL", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_staff_staff(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="STAFF", candidate_seniority_normalized="STAFF", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="STAFF", normalized_level="STAFF", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)


class TestNumbered(unittest.TestCase):
    def test_ii_mid(self):
        self.assertEqual(normalize_seniority("level 2"), "MID")
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="level 2", candidate_seniority_normalized="MID", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="MID", normalized_level="MID", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.SATISFIED)

    def test_iii_unknown(self):
        self.assertIsNone(normalize_seniority("III"))
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="INTERN", candidate_seniority_normalized="INTERN", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="III", normalized_level=None, kind="UNPARSEABLE"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestMultiLevel(unittest.TestCase):
    def test_multi_level_unknown(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="SENIOR", candidate_seniority_normalized="SENIOR", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="Senior/Staff", normalized_level=None, kind="MULTI_LEVEL"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)


class TestSeniorityEvidence(unittest.TestCase):
    def test_evidence_preserved(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="SENIOR", candidate_seniority_normalized="SENIOR", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"))
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.candidate_raw, "SENIOR")
        self.assertEqual(ev.candidate_normalized, "SENIOR")
        self.assertEqual(ev.candidate_source, "explicit_seniority")


class TestSeniorityDeterminism(unittest.TestCase):
    def test_deterministic(self):
        cand = CanonicalCandidateInput(skill_inventory_status=SkillInventoryStatus.DETERMINED, seniority_availability=SeniorityAvailability.DETERMINED, candidate_seniority_raw="SENIOR", candidate_seniority_normalized="SENIOR", candidate_seniority_source="explicit_seniority")
        job = CanonicalJobInput(seniority_requirement=StructuredSeniorityRequirement(raw="MID", normalized_level="MID", kind="STRUCTURED"))
        e1 = SeniorityMatcher().evaluate(cand, job)[0]
        e2 = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(e1.relationship, e2.relationship)
        self.assertEqual(e1.status, e2.status)


class TestMatchEngine2Seniority(unittest.TestCase):
    def test_composition(self):
        from core.services.match_engine2 import MatchEngine2
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
            skill_inventory_raw=["Python"],
            seniority_availability=SeniorityAvailability.DETERMINED,
            candidate_seniority_raw="SENIOR",
            candidate_seniority_normalized="SENIOR",
            candidate_seniority_source="explicit_seniority",
        )
        job = CanonicalJobInput(
            requirements=[],
            seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"),
        )
        result = MatchEngine2().analyze(cand, job)
        self.assertEqual(len(result.seniority_evaluations), 1)
        self.assertEqual(result.seniority_evaluations[0].status, RequirementStatus.SATISFIED)

class TestCandidateAdapterSeniorityConfidenceGate(unittest.TestCase):
    """5B-6 amendment: overall_confidence <0.3 has precedence over EXPLICIT_USER."""

    def test_case_a_explicit_normal_confidence_determined(self):
        from core.models.candidate_intelligence import CanonicalCandidateProfile, SourceOrigin
        from core.services.match_engine_adapters import CandidateAdapter

        profile = CanonicalCandidateProfile(
            seniority="SENIOR",
            seniority_origin=SourceOrigin.EXPLICIT_USER,
            overall_confidence=0.9,
            experience=[],
        )
        out = CandidateAdapter().adapt(profile)
        self.assertEqual(out.seniority_availability, SeniorityAvailability.DETERMINED)
        self.assertEqual(out.candidate_seniority_normalized, "SENIOR")
        self.assertEqual(out.candidate_seniority_source, "explicit_seniority")
        self.assertEqual(out.candidate_seniority_raw, "SENIOR")

    def test_case_b_inferred_high_confidence_undetermined(self):
        from core.models.candidate_intelligence import CanonicalCandidateProfile, SourceOrigin
        from core.services.match_engine_adapters import CandidateAdapter

        profile = CanonicalCandidateProfile(
            seniority="SENIOR",
            seniority_origin=SourceOrigin.INFERRED,
            overall_confidence=0.9,
            experience=[],
        )
        out = CandidateAdapter().adapt(profile)
        self.assertEqual(out.seniority_availability, SeniorityAvailability.UNDETERMINED)
        self.assertIsNone(out.candidate_seniority_normalized)

    def test_case_c_explicit_low_confidence_undetermined(self):
        from core.models.candidate_intelligence import CanonicalCandidateProfile, SourceOrigin
        from core.services.match_engine_adapters import CandidateAdapter

        profile = CanonicalCandidateProfile(
            seniority="SENIOR",
            seniority_origin=SourceOrigin.EXPLICIT_USER,
            overall_confidence=0.2,
            experience=[],
        )
        out = CandidateAdapter().adapt(profile)
        self.assertEqual(out.seniority_availability, SeniorityAvailability.UNDETERMINED)
        self.assertIsNone(out.candidate_seniority_normalized)
        self.assertIsNone(out.candidate_seniority_source)

    def test_case_d_undetermined_produces_unknown(self):
        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            seniority_availability=SeniorityAvailability.UNDETERMINED,
            candidate_seniority_raw="SENIOR",
            candidate_seniority_normalized="SENIOR",
            candidate_seniority_source="explicit_seniority",
        )
        job = CanonicalJobInput(
            seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED", required=True)
        )
        ev = SeniorityMatcher().evaluate(cand, job)[0]
        self.assertEqual(ev.status, RequirementStatus.UNKNOWN)
        self.assertEqual(ev.relationship, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
