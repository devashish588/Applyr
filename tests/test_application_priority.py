"""
Application Priority — Phase 6 Tests
"""

import unittest
from datetime import datetime, timezone, timedelta

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    RequirementStatus,
    SkillInventoryStatus,
    StructuredExperienceRequirement,
    StructuredRoleRequirement,
    StructuredLocationRequirement,
    StructuredSeniorityRequirement,
    CandidateLocationEntry,
    RoleEntry,
    ExperienceAvailability,
    RoleAvailability,
    LocationAvailability,
    SeniorityAvailability,
    RequirementEvaluation,
    ExperienceEvaluation,
    RoleEvaluation,
    LocationEvaluation,
    SeniorityEvaluation,
)
from core.models.match_engine import CanonicalJobRequirement
from core.services.application_priority_service import ApplicationPriorityService


def _make_match_result(
    required_satisfied=0,
    required_missing=0,
    preferred_missing=0,
    unknown=0,
    seniority_status=None,
    experience_status=None,
):
    from core.models.match_engine import MatchResult, RequirementEvaluation, ExperienceEvaluation, RoleEvaluation, LocationEvaluation, SeniorityEvaluation

    req_evals = []
    for i in range(required_satisfied):
        req_evals.append(
            RequirementEvaluation(
                requirement=CanonicalJobRequirement(raw_name=f"Skill{i}", canonical_name=f"Skill{i}", required=True),
                status=RequirementStatus.SATISFIED,
            )
        )
    for i in range(required_missing):
        req_evals.append(
            RequirementEvaluation(
                requirement=CanonicalJobRequirement(raw_name=f"ReqMissing{i}", canonical_name=f"ReqMissing{i}", required=True),
                status=RequirementStatus.MISSING,
            )
        )
    for i in range(preferred_missing):
        req_evals.append(
            RequirementEvaluation(
                requirement=CanonicalJobRequirement(raw_name=f"Pref{i}", canonical_name=f"Pref{i}", required=False),
                status=RequirementStatus.MISSING,
            )
        )
    for i in range(unknown):
        req_evals.append(
            RequirementEvaluation(
                requirement=CanonicalJobRequirement(raw_name=f"Unk{i}", canonical_name=f"Unk{i}", required=True),
                status=RequirementStatus.UNKNOWN,
            )
        )

    exp_evals = []
    if experience_status:
        exp_evals.append(
            ExperienceEvaluation(
                requirement=StructuredExperienceRequirement(raw="3+ years", min_years=3, kind="MINIMUM"),
                candidate_years=2 if experience_status == "MISSING" else 4,
                status=RequirementStatus.MISSING if experience_status == "MISSING" else RequirementStatus.UNKNOWN if experience_status == "UNKNOWN" else RequirementStatus.SATISFIED,
            )
        )
    role_evals = []
    if experience_status == "ROLE_MISSING":
        role_evals.append(
            RoleEvaluation(
                candidate_raw="Frontend", candidate_normalized="Frontend", job_raw="Backend", job_normalized="Backend", relationship="NONE", status=RequirementStatus.MISSING, is_current_role=False
            )
        )

    mr = MatchResult(
        requirement_evaluations=req_evals,
        experience_evaluations=exp_evals,
        role_evaluations=role_evals,
        location_evaluations=[],
        seniority_evaluations=[],
        inventory_status=SkillInventoryStatus.DETERMINED,
        analysis_completeness=1.0 if unknown == 0 else 0.5,
    )
    if seniority_status:
        mr.seniority_evaluations = [
            SeniorityEvaluation(
                candidate_raw="MID",
                candidate_normalized="MID",
                candidate_source="explicit_seniority",
                job_raw="SENIOR",
                job_normalized="SENIOR",
                relationship="LOWER_THAN_REQUIRED" if seniority_status == "MISSING" else "UNKNOWN",
                status=RequirementStatus.MISSING if seniority_status == "MISSING" else RequirementStatus.UNKNOWN,
            )
        ]
    return mr


class TestPriorityTiers(unittest.TestCase):
    def setUp(self):
        self.svc = ApplicationPriorityService()
        self.now = datetime.now(timezone.utc)
        self.fresh = (self.now - timedelta(days=5)).isoformat()
        self.stale = (self.now - timedelta(days=40)).isoformat()

    def test_strong_fresh_hot(self):
        mr = _make_match_result(required_satisfied=3, unknown=0)
        pri = self.svc.evaluate(1, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "HOT")

    def test_strong_stale_warm(self):
        mr = _make_match_result(required_satisfied=3, unknown=0)
        pri = self.svc.evaluate(1, mr, self.stale, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "WARM")

    def test_freshness_unknown_warm(self):
        mr = _make_match_result(required_satisfied=3, unknown=0)
        pri = self.svc.evaluate(1, mr, None, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "WARM")

    def test_one_unknown_warm(self):
        mr = _make_match_result(required_satisfied=2, unknown=1)
        pri = self.svc.evaluate(1, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "WARM")

    def test_two_unknown_review(self):
        mr = _make_match_result(required_satisfied=1, unknown=2)
        pri = self.svc.evaluate(1, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "REVIEW")

    def test_required_missing_cold(self):
        mr = _make_match_result(required_satisfied=2, required_missing=1, unknown=0)
        pri = self.svc.evaluate(1, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "COLD")

    def test_required_missing_plus_one_unknown_cold(self):
        mr = _make_match_result(required_missing=1, unknown=1)
        pri = self.svc.evaluate(2, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "COLD")

    def test_required_missing_plus_two_unknown_review(self):
        mr = _make_match_result(required_missing=1, unknown=2)
        pri = self.svc.evaluate(3, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "REVIEW")

    def test_seniority_lower_cold(self):
        mr = _make_match_result(seniority_status="MISSING")
        pri = self.svc.evaluate(4, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri.tier, "COLD")

    def test_preferred_missing_not_cold(self):
        mr = _make_match_result(preferred_missing=1, unknown=0)
        pri = self.svc.evaluate(5, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertNotEqual(pri.tier, "COLD")
        self.assertIn(pri.tier, ("WARM", "HOT"))

    def test_experience_missing_not_cold(self):
        mr = _make_match_result(experience_status="MISSING")
        # Experience MISSING should be WARM, not COLD (only seniority/required skill are hard)
        # Our current svc treats only required skill and seniority as hard, so experience MISSING stays WARM/HOT
        pri = self.svc.evaluate(6, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertNotEqual(pri.tier, "COLD")

    def test_unparseable_review(self):
        mr = _make_match_result(unknown=1)
        # Simulate unparseable as UNKNOWN
        pri = self.svc.evaluate(7, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertIn(pri.tier, ("WARM", "REVIEW"))

    def test_empty_evaluation_neutral(self):
        from core.models.match_engine import MatchResult

        mr = MatchResult(requirement_evaluations=[], experience_evaluations=[], role_evaluations=[], location_evaluations=[], seniority_evaluations=[])
        pri = self.svc.evaluate(8, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertIn(pri.tier, ("HOT", "WARM"))

    def test_recruiter_tie_breaker(self):
        mr = _make_match_result(required_satisfied=2, unknown=0)
        # Two jobs same tier, recruiter should win tie-break
        items = [
            (1, mr, self.fresh, True, "greenhouse", "http://apply", False),
            (2, mr, self.fresh, True, "greenhouse", "http://apply", True),
        ]
        ranked = self.svc.rank(items)
        self.assertEqual(ranked[0][0], 2)  # recruiter true first

    def test_recruiter_cannot_promote_cold(self):
        mr_cold = _make_match_result(required_missing=1, unknown=0)
        pri = self.svc.evaluate(9, mr_cold, self.fresh, True, "greenhouse", "http://apply", True)
        self.assertEqual(pri.tier, "COLD")

    def test_recruiter_cannot_promote_review(self):
        mr_review = _make_match_result(unknown=2)
        pri = self.svc.evaluate(10, mr_review, self.fresh, True, "greenhouse", "http://apply", True)
        self.assertEqual(pri.tier, "REVIEW")

    def test_deterministic_tie(self):
        mr = _make_match_result(required_satisfied=2, unknown=0)
        items = [
            (2, mr, self.fresh, True, "greenhouse", "http://apply", False),
            (1, mr, self.fresh, True, "greenhouse", "http://apply", False),
        ]
        ranked = self.svc.rank(items)
        # Same tier, same freshness, sorted by job_id asc after recruiter
        self.assertEqual([r[0] for r in ranked], [1, 2])

    def test_legacy_preserved(self):
        # Priority does not modify MatchResult
        mr = _make_match_result(required_satisfied=2)
        orig_len = len(mr.requirement_evaluations)
        self.svc.evaluate(11, mr, self.fresh, True, "greenhouse", "http://apply", False)
        self.assertEqual(len(mr.requirement_evaluations), orig_len)


class TestAdversarialPriority(unittest.TestCase):
    def test_empty_not_satisfied(self):
        from core.models.match_engine import MatchResult

        mr = MatchResult(requirement_evaluations=[])
        self.assertEqual(len(mr.requirement_evaluations), 0)

    def test_unknown_not_missing(self):
        mr = _make_match_result(unknown=1)
        pri = ApplicationPriorityService().evaluate(12, mr, None, True, "greenhouse", "http://apply", False)
        self.assertNotEqual(pri.tier, "COLD")

    def test_freshness_unknown_not_hot(self):
        mr = _make_match_result(required_satisfied=3, unknown=0)
        pri = ApplicationPriorityService().evaluate(13, mr, None, True, "greenhouse", "http://apply", False)
        self.assertNotEqual(pri.tier, "HOT")
        self.assertEqual(pri.tier, "WARM")


class TestHeterogeneousIntegrationRegression(unittest.TestCase):
    """Regression for 500 on /api/jobs/prioritized — SeniorityEvaluation has no .requirement"""

    def test_heterogeneous_match_result_does_not_raise(self):
        from core.models.match_engine import MatchResult, SeniorityEvaluation, LocationEvaluation, RoleEvaluation, ExperienceEvaluation
        from core.models.match_engine import CanonicalJobRequirement, StructuredExperienceRequirement, StructuredRoleRequirement, StructuredLocationRequirement, StructuredSeniorityRequirement

        # Build a realistic heterogeneous MatchResult as MatchEngine2 would
        from core.models.match_engine import RoleRelationshipType as RRT, LocationRelationshipType as LRT

        mr = MatchResult(
            requirement_evaluations=[
                RequirementEvaluation(
                    requirement=CanonicalJobRequirement(raw_name="Python", canonical_name="Python", required=True),
                    status=RequirementStatus.SATISFIED,
                )
            ],
            experience_evaluations=[
                ExperienceEvaluation(
                    requirement=StructuredExperienceRequirement(raw="3+ years", min_years=3, kind="MINIMUM"),
                    candidate_years=4,
                    status=RequirementStatus.SATISFIED,
                )
            ],
            role_evaluations=[
                RoleEvaluation(
                    candidate_raw="Backend Engineer",
                    candidate_normalized="Backend Engineer",
                    job_raw="Backend Engineer",
                    job_normalized="Backend Engineer",
                    relationship=RRT.EXACT,
                    status=RequirementStatus.SATISFIED,
                    is_current_role=True,
                )
            ],
            location_evaluations=[
                LocationEvaluation(
                    candidate_raw="Bangalore, India",
                    candidate_city="Bangalore",
                    candidate_normalized_city="bangalore",
                    job_raw="Bangalore, India",
                    job_city="Bangalore",
                    job_normalized_city="bangalore",
                    job_remote_type="onsite",
                    relationship=LRT.EXACT,
                    status=RequirementStatus.SATISFIED,
                )
            ],
            seniority_evaluations=[
                SeniorityEvaluation(
                    candidate_raw="SENIOR",
                    candidate_normalized="SENIOR",
                    candidate_source="explicit_seniority",
                    job_raw="SENIOR",
                    job_normalized="SENIOR",
                    relationship="EXACT",
                    status=RequirementStatus.SATISFIED,
                )
            ],
        )
        # This previously raised AttributeError: 'SeniorityEvaluation' object has no attribute 'requirement'
        svc = ApplicationPriorityService()
        pri = svc.evaluate(99, mr, None, True, "greenhouse", "http://apply", False)
        self.assertIn(pri.tier, ("HOT", "WARM", "COLD", "REVIEW"))
        # Also test UNKNOWN seniority does not raise
        mr2 = MatchResult(
            requirement_evaluations=[],
            experience_evaluations=[],
            role_evaluations=[],
            location_evaluations=[],
            seniority_evaluations=[
                SeniorityEvaluation(
                    candidate_raw="SENIOR",
                    candidate_normalized="SENIOR",
                    candidate_source="explicit_seniority",
                    job_raw="SENIOR",
                    job_normalized="SENIOR",
                    relationship="UNKNOWN",
                    status=RequirementStatus.UNKNOWN,
                )
            ],
        )
        pri2 = svc.evaluate(100, mr2, None, True, "greenhouse", "http://apply", False)
        self.assertEqual(pri2.tier, "WARM")  # 1 UNKNOWN → WARM

    def test_production_path_via_match_engine2(self):
        from core.models.match_engine import CanonicalCandidateInput, CanonicalJobInput, SkillInventoryStatus, ExperienceAvailability, RoleAvailability, LocationAvailability, SeniorityAvailability, RoleEntry, CandidateLocationEntry, StructuredSeniorityRequirement
        from core.services.match_engine2 import MatchEngine2

        cand = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
            skill_inventory_raw=["Python"],
            experience_years=4,
            experience_availability=ExperienceAvailability.DETERMINED,
            role_availability=RoleAvailability.DETERMINED,
            role_entries=[RoleEntry(raw="Backend Engineer", normalized="Backend Engineer", is_current=True)],
            location_availability=LocationAvailability.DETERMINED,
            candidate_location_entries=[CandidateLocationEntry(raw="Bangalore, India", city="Bangalore", normalized_city="bangalore")],
            seniority_availability=SeniorityAvailability.DETERMINED,
            candidate_seniority_raw="SENIOR",
            candidate_seniority_normalized="SENIOR",
            candidate_seniority_source="explicit_seniority",
        )
        job = CanonicalJobInput(
            requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python", required=True)],
            experience_requirement=StructuredExperienceRequirement(raw="3+ years", min_years=3, kind="MINIMUM"),
            role_requirement=StructuredRoleRequirement(raw="Backend Engineer", normalized="Backend Engineer", kind="STRUCTURED"),
            location_requirement=StructuredLocationRequirement(raw="Bangalore, India", cities=["Bangalore"], normalized_cities=["bangalore"], remote_type="onsite", kind="STRUCTURED"),
            seniority_requirement=StructuredSeniorityRequirement(raw="SENIOR", normalized_level="SENIOR", kind="STRUCTURED"),
        )
        mr = MatchEngine2().analyze(cand, job)
        svc = ApplicationPriorityService()
        pri = svc.evaluate(101, mr, None, True, "greenhouse", "http://apply", False)
        self.assertIn(pri.tier, ("HOT", "WARM", "COLD", "REVIEW"))


if __name__ == "__main__":
    unittest.main()
