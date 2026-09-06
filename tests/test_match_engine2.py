"""
Match Engine 2.0 — Phase 5B-1 Structural Foundation Tests
==========================================================

Pure model validation, serialization, and contract tests.

Tests cover ONLY the Phase 5B-1 structural foundation:
  - SkillInventoryStatus enum values
  - CanonicalCandidateInput validation
  - DETERMINED/UNDETERMINED state representations
  - CanonicalJobInput validation
  - MatchResult serialization/deserialization
  - MatchResult wraps baseline MatchAnalysis
  - Mutable list field independence
  - Exact/alias relationship representation
  - Related skills structural separation
  - MatchEngine2 structural boundary
  - Existing MatchService/MatchAnalysis compatibility

NO tests for actual matching, scoring, ranking, or evaluation behavior.
"""

import unittest
from datetime import datetime

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    CanonicalJobRequirement,
    MatchResult,
    RequirementEvaluation,
    RequirementStatus,
    SkillInventoryStatus,
    SkillRelationshipType,
)


class TestSkillInventoryStatus(unittest.TestCase):
    """Test 1: SkillInventoryStatus enum values."""

    def test_determined_value(self):
        self.assertEqual(SkillInventoryStatus.DETERMINED.value, "determined")

    def test_undetermined_value(self):
        self.assertEqual(SkillInventoryStatus.UNDETERMINED.value, "undetermined")

    def test_exactly_two_members(self):
        self.assertEqual(len(SkillInventoryStatus), 2)

    def test_string_enum(self):
        self.assertIsInstance(SkillInventoryStatus.DETERMINED, str)
        self.assertIsInstance(SkillInventoryStatus.UNDETERMINED, str)


class TestRequirementStatus(unittest.TestCase):
    """RequirementStatus enum values."""

    def test_all_values(self):
        self.assertEqual(RequirementStatus.SATISFIED.value, "satisfied")
        self.assertEqual(RequirementStatus.PARTIALLY_SATISFIED.value, "partially_satisfied")
        self.assertEqual(RequirementStatus.MISSING.value, "missing")
        self.assertEqual(RequirementStatus.UNKNOWN.value, "unknown")

    def test_exactly_four_members(self):
        self.assertEqual(len(RequirementStatus), 4)


class TestSkillRelationshipType(unittest.TestCase):
    """SkillRelationshipType hierarchy."""

    def test_hierarchy_ordering(self):
        """Exact > Alias > Transferable > Related > None."""
        self.assertTrue(SkillRelationshipType.EXACT > SkillRelationshipType.ALIAS)
        self.assertTrue(SkillRelationshipType.ALIAS > SkillRelationshipType.TRANSFERABLE)
        self.assertTrue(SkillRelationshipType.TRANSFERABLE > SkillRelationshipType.RELATED)
        self.assertTrue(SkillRelationshipType.RELATED > SkillRelationshipType.NONE)

    def test_exact_is_best(self):
        self.assertTrue(SkillRelationshipType.EXACT > SkillRelationshipType.NONE)

    def test_none_is_worst(self):
        self.assertTrue(SkillRelationshipType.NONE < SkillRelationshipType.EXACT)


class TestCanonicalCandidateInput(unittest.TestCase):
    """Tests 2-6: CanonicalCandidateInput validation and state representations."""

    def test_02_basic_validation(self):
        """Test 2: CanonicalCandidateInput can be constructed with valid data."""
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python", "Docker"],
        )
        self.assertEqual(candidate.skill_inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(candidate.skill_inventory, ["Python", "Docker"])

    def test_03_determined_populated(self):
        """Test 3: DETERMINED + populated inventory is representable."""
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python", "Docker", "PostgreSQL"],
            skill_inventory_raw=["python", "docker", "PostgreSQL"],
            seniority="SENIOR",
            target_roles=["Backend Engineer"],
            experience_years=5.0,
        )
        self.assertEqual(candidate.skill_inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(len(candidate.skill_inventory), 3)
        self.assertEqual(candidate.seniority, "SENIOR")

    def test_04_determined_empty(self):
        """Test 4: DETERMINED + empty inventory is representable.
        This is the critical authoritative-absence case from Phase 5A.
        """
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=[],
        )
        self.assertEqual(candidate.skill_inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(candidate.skill_inventory, [])

    def test_05_undetermined_empty(self):
        """Test 5: UNDETERMINED + empty inventory is representable."""
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
            skill_inventory=[],
        )
        self.assertEqual(candidate.skill_inventory_status, SkillInventoryStatus.UNDETERMINED)
        self.assertEqual(candidate.skill_inventory, [])

    def test_06_undetermined_populated_distinguishable(self):
        """Test 6: UNDETERMINED + populated inventory is representable and
        structurally distinguishable from authoritative inventory.
        """
        auth = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
        )
        stale = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
            skill_inventory=["Python"],  # non-authoritative stale data
        )
        # Same skills but structurally distinguishable by status
        self.assertEqual(auth.skill_inventory, stale.skill_inventory)
        self.assertNotEqual(auth.skill_inventory_status, stale.skill_inventory_status)
        self.assertEqual(auth.skill_inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(stale.skill_inventory_status, SkillInventoryStatus.UNDETERMINED)


class TestCanonicalJobInput(unittest.TestCase):
    """Test 7: Canonical job input validation."""

    def test_07_basic_job_input(self):
        job = CanonicalJobInput(
            job_id=42,
            title="Senior Backend Engineer",
            company="Acme Corp",
            requirements=[
                CanonicalJobRequirement(raw_name="Python", canonical_name="Python", required=True),
                CanonicalJobRequirement(raw_name="Docker", canonical_name="Docker", required=True),
                CanonicalJobRequirement(raw_name="Redis", canonical_name="Redis", required=False),
            ],
        )
        self.assertEqual(job.job_id, 42)
        self.assertEqual(len(job.requirements), 3)
        self.assertTrue(job.requirements[0].required)
        self.assertFalse(job.requirements[2].required)


class TestMatchResultSerialization(unittest.TestCase):
    """Tests 8-9: MatchResult serialization and MatchAnalysis wrapping."""

    def test_08_serialization_roundtrip(self):
        """Test 8: MatchResult serialization/deserialization."""
        result = MatchResult(
            inventory_status=SkillInventoryStatus.DETERMINED,
            requirement_evaluations=[
                RequirementEvaluation(
                    requirement=CanonicalJobRequirement(
                        raw_name="Python", canonical_name="Python"
                    ),
                    status=RequirementStatus.MISSING,
                ),
            ],
            satisfied_requirements=[],
            missing_requirements=["Python"],
            engine_version="2.0.0-skeleton",
        )
        # Serialize
        json_str = result.model_dump_json()
        # Deserialize
        restored = MatchResult.model_validate_json(json_str)
        self.assertEqual(restored.inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(len(restored.requirement_evaluations), 1)
        self.assertEqual(restored.engine_version, "2.0.0-skeleton")

    def test_09_wraps_baseline_match_analysis(self):
        """Test 9: MatchResult preserves/wraps baseline MatchAnalysis (strongly typed)."""
        from core.models import MatchAnalysis

        baseline = MatchAnalysis(
            job_id=42,
            final_score=75,
            recommendation="Apply",
        )
        result = MatchResult(
            baseline_analysis=baseline,
            inventory_status=SkillInventoryStatus.DETERMINED,
        )
        self.assertIsNotNone(result.baseline_analysis)
        self.assertIsInstance(result.baseline_analysis, MatchAnalysis)
        self.assertEqual(result.baseline_analysis.final_score, 75)
        self.assertEqual(result.baseline_analysis.recommendation, "Apply")
        # Confirm MatchResult metadata does NOT affect baseline score
        self.assertEqual(result.analysis_completeness, 0.0)
        self.assertEqual(result.match_confidence, 0.0)

    def test_09b_baseline_type_safety(self):
        """Test 9b: baseline_analysis is strongly typed Optional[MatchAnalysis], not Any."""
        import typing
        from core.models.match_engine import MatchResult as MR

        hints = typing.get_type_hints(MR)
        ann = hints.get("baseline_analysis")
        ann_str = str(ann)
        # Must reference MatchAnalysis, must not be Any
        self.assertIn("MatchAnalysis", ann_str)
        self.assertNotIn("Any", ann_str)

    def test_09c_baseline_rejects_unrelated_value(self):
        """Test 9c: baseline_analysis rejects unrelated value where validation applies."""
        from pydantic import ValidationError

        # An int cannot be coerced to MatchAnalysis — should raise ValidationError
        with self.assertRaises(ValidationError):
            MatchResult(baseline_analysis=12345)  # type: ignore[arg-type]

        # None is allowed (Optional)
        result = MatchResult(baseline_analysis=None)
        self.assertIsNone(result.baseline_analysis)

        # Valid MatchAnalysis is accepted
        from core.models import MatchAnalysis

        baseline = MatchAnalysis(job_id=1, final_score=50, recommendation="Consider")
        result2 = MatchResult(baseline_analysis=baseline)
        self.assertEqual(result2.baseline_analysis.final_score, 50)


class TestMutableListDefaults(unittest.TestCase):
    """Test 10: Mutable list fields use independent defaults."""

    def test_10_independent_defaults(self):
        """Each instance gets its own list, not a shared mutable default."""
        a = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
        )
        b = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
        )
        a.skill_inventory.append("Python")
        self.assertEqual(len(a.skill_inventory), 1)
        self.assertEqual(len(b.skill_inventory), 0)

    def test_10b_match_result_independent_lists(self):
        r1 = MatchResult()
        r2 = MatchResult()
        r1.satisfied_requirements.append("Python")
        self.assertEqual(len(r1.satisfied_requirements), 1)
        self.assertEqual(len(r2.satisfied_requirements), 0)


class TestExactVsAlias(unittest.TestCase):
    """Test 11: Alias/exact contract representation without incorrect raw normalization."""

    def test_11_exact_preserves_case(self):
        """Exact: canonical values equal AND raw values identical case-sensitively."""
        eval_exact = RequirementEvaluation(
            requirement=CanonicalJobRequirement(raw_name="Python", canonical_name="Python"),
            status=RequirementStatus.SATISFIED,
            relationship_type=SkillRelationshipType.EXACT,
            matched_skill="Python",
        )
        # Raw names identical → EXACT
        self.assertEqual(eval_exact.relationship_type, SkillRelationshipType.EXACT)
        self.assertEqual(eval_exact.requirement.raw_name, "Python")
        self.assertEqual(eval_exact.matched_skill, "Python")

    def test_11b_alias_different_raw(self):
        """Alias: canonical values equal AND raw values differ case-sensitively."""
        eval_alias = RequirementEvaluation(
            requirement=CanonicalJobRequirement(raw_name="python", canonical_name="Python"),
            status=RequirementStatus.SATISFIED,
            relationship_type=SkillRelationshipType.ALIAS,
            matched_skill="Python3",  # raw candidate value differs
        )
        # Canonical match but raw names differ → ALIAS
        self.assertEqual(eval_alias.relationship_type, SkillRelationshipType.ALIAS)
        self.assertNotEqual(eval_alias.requirement.raw_name, eval_alias.matched_skill)


class TestRelatedSkillsSeparation(unittest.TestCase):
    """Test 12: Related skills remain structurally separate from selected evaluation."""

    def test_12_related_informational_only(self):
        """Related skills are informational and do not change the status to SATISFIED."""
        evaluation = RequirementEvaluation(
            requirement=CanonicalJobRequirement(raw_name="Kubernetes", canonical_name="Kubernetes"),
            status=RequirementStatus.MISSING,
            relationship_type=SkillRelationshipType.RELATED,
            matched_skill=None,
            related_skills=["Docker", "Docker Compose"],  # informational only
        )
        # Status is MISSING even though related skills exist
        self.assertEqual(evaluation.status, RequirementStatus.MISSING)
        self.assertEqual(evaluation.relationship_type, SkillRelationshipType.RELATED)
        self.assertEqual(len(evaluation.related_skills), 2)
        # Related skills do NOT change status
        self.assertNotEqual(evaluation.status, RequirementStatus.SATISFIED)


class TestMatchEngine2Skeleton(unittest.TestCase):
    """Test 13: MatchEngine2 structural boundary."""

    def test_13_instantiation(self):
        """MatchEngine2 can be instantiated without external services."""
        from core.services.match_engine2 import MatchEngine2
        engine = MatchEngine2()
        self.assertIsNotNone(engine)

    def test_13b_analyze_undetermined(self):
        """MatchEngine2.analyze() with UNDETERMINED → all UNKNOWN."""
        from core.services.match_engine2 import MatchEngine2

        engine = MatchEngine2()
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
            skill_inventory=["Python"],  # stale / non-authoritative
        )
        job = CanonicalJobInput(
            job_id=1,
            requirements=[
                CanonicalJobRequirement(raw_name="Python", canonical_name="Python"),
                CanonicalJobRequirement(raw_name="Docker", canonical_name="Docker"),
            ],
        )
        result = engine.analyze(candidate, job)
        self.assertIsInstance(result, MatchResult)
        self.assertEqual(result.inventory_status, SkillInventoryStatus.UNDETERMINED)
        # All evaluations MUST be UNKNOWN
        for evaluation in result.requirement_evaluations:
            self.assertEqual(evaluation.status, RequirementStatus.UNKNOWN)
        self.assertEqual(len(result.unknown_requirements), 2)
        self.assertEqual(len(result.satisfied_requirements), 0)

    def test_13c_analyze_determined_empty(self):
        """MatchEngine2.analyze() with DETERMINED + [] → all MISSING."""
        from core.services.match_engine2 import MatchEngine2

        engine = MatchEngine2()
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=[],
        )
        job = CanonicalJobInput(
            job_id=2,
            requirements=[
                CanonicalJobRequirement(raw_name="Python", canonical_name="Python"),
            ],
        )
        result = engine.analyze(candidate, job)
        self.assertEqual(result.inventory_status, SkillInventoryStatus.DETERMINED)
        # DETERMINED + [] → authoritative absence → MISSING
        for evaluation in result.requirement_evaluations:
            self.assertEqual(evaluation.status, RequirementStatus.MISSING)
        self.assertEqual(len(result.missing_requirements), 1)

    def test_13d_analyze_with_baseline(self):
        """MatchEngine2 preserves baseline_analysis without modification."""
        from core.services.match_engine2 import MatchEngine2
        from core.models import MatchAnalysis

        baseline = MatchAnalysis(job_id=10, final_score=82, recommendation="Apply")
        engine = MatchEngine2()
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
        )
        job = CanonicalJobInput(job_id=10)
        result = engine.analyze(candidate, job, baseline_analysis=baseline)
        # Baseline preserved
        self.assertEqual(result.baseline_analysis.final_score, 82)
        self.assertEqual(result.baseline_analysis.recommendation, "Apply")
        # Engine metadata doesn't affect baseline
        self.assertEqual(result.match_confidence, 0.0)

    def test_13e_determined_populated_skill_matching(self):
        """5B-2: DETERMINED + populated inventory → real skill matching (no fake MISSING, no empty overlay)."""
        from core.services.match_engine2 import MatchEngine2

        engine = MatchEngine2()
        candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python", "Docker"],
            skill_inventory_raw=["Python", "Docker"],
        )
        job = CanonicalJobInput(
            job_id=3,
            requirements=[
                CanonicalJobRequirement(raw_name="Python", canonical_name="Python"),
                CanonicalJobRequirement(raw_name="Kubernetes", canonical_name="Kubernetes"),
            ],
        )
        result = engine.analyze(candidate, job)
        self.assertEqual(result.inventory_status, SkillInventoryStatus.DETERMINED)
        self.assertEqual(len(result.requirement_evaluations), 2)
        # Python exact → SATISFIED
        self.assertEqual(result.requirement_evaluations[0].status, RequirementStatus.SATISFIED)
        self.assertEqual(result.requirement_evaluations[0].relationship_type, SkillRelationshipType.EXACT)
        # Kubernetes related (Docker devops) → MISSING
        self.assertEqual(result.requirement_evaluations[1].status, RequirementStatus.MISSING)
        self.assertEqual(result.requirement_evaluations[1].relationship_type, SkillRelationshipType.RELATED)

    def test_13f_determined_empty_vs_populated_distinguishable(self):
        """DETERMINED+[] (MISSING) is distinguishable from DETERMINED+populated (real evaluation)."""
        from core.services.match_engine2 import MatchEngine2

        engine = MatchEngine2()
        job = CanonicalJobInput(
            job_id=4,
            requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python")],
        )
        empty_candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=[],
        )
        populated_candidate = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=["Python"],
            skill_inventory_raw=["Python"],
        )
        empty_result = engine.analyze(empty_candidate, job)
        populated_result = engine.analyze(populated_candidate, job)
        # Empty → authoritative absence → MISSING
        self.assertEqual(len(empty_result.requirement_evaluations), 1)
        self.assertEqual(empty_result.requirement_evaluations[0].status, RequirementStatus.MISSING)
        # Populated → real evaluation → SATISFIED
        self.assertEqual(len(populated_result.requirement_evaluations), 1)
        self.assertEqual(populated_result.requirement_evaluations[0].status, RequirementStatus.SATISFIED)

    def test_13g_undetermined_distinguishable_from_determined(self):
        """UNDETERMINED remains distinguishable from DETERMINED in results."""
        from core.services.match_engine2 import MatchEngine2

        engine = MatchEngine2()
        job = CanonicalJobInput(
            job_id=5,
            requirements=[CanonicalJobRequirement(raw_name="Python", canonical_name="Python")],
        )
        undetermined = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.UNDETERMINED,
            skill_inventory=[],
        )
        determined_empty = CanonicalCandidateInput(
            skill_inventory_status=SkillInventoryStatus.DETERMINED,
            skill_inventory=[],
        )
        r_und = engine.analyze(undetermined, job)
        r_det = engine.analyze(determined_empty, job)
        self.assertEqual(r_und.requirement_evaluations[0].status, RequirementStatus.UNKNOWN)
        self.assertEqual(r_det.requirement_evaluations[0].status, RequirementStatus.MISSING)
        self.assertNotEqual(r_und.inventory_status, r_det.inventory_status)


class TestExistingMatchServiceCompatibility(unittest.TestCase):
    """Test 14: Existing MatchService/MatchAnalysis compatibility."""

    def test_14_match_service_unchanged(self):
        """MatchService can still be instantiated and used normally."""
        from core.services.match_service import get_match_service
        from core.models import MatchAnalysis

        ms = get_match_service()
        analysis = ms.analyze(
            job_id=1,
            job_title="Backend Engineer",
            required_skills=["Python", "PostgreSQL"],
        )
        self.assertIsInstance(analysis, MatchAnalysis)
        self.assertIsInstance(analysis.final_score, (int, float))
        self.assertIn(analysis.recommendation, ["Apply", "Consider", "Skip"])

    def test_14b_match_analysis_weights_preserved(self):
        """MatchService weights are preserved: 40/25/20/10/5."""
        from core.services.match_service import MatchService

        self.assertAlmostEqual(MatchService.SKILL_WEIGHT, 0.40)
        self.assertAlmostEqual(MatchService.EXPERIENCE_WEIGHT, 0.25)
        self.assertAlmostEqual(MatchService.ROLE_WEIGHT, 0.20)
        self.assertAlmostEqual(MatchService.LOCATION_WEIGHT, 0.10)
        self.assertAlmostEqual(MatchService.SENIORITY_WEIGHT, 0.05)


class TestAdapterInterfaces(unittest.TestCase):
    """Adapter skeleton interface tests."""

    def test_candidate_adapter_instantiation(self):
        from core.services.match_engine_adapters import CandidateAdapter
        adapter = CandidateAdapter()
        self.assertIsNotNone(adapter)

    def test_job_adapter_instantiation(self):
        from core.services.match_engine_adapters import JobAdapter
        adapter = JobAdapter()
        self.assertIsNotNone(adapter)

    def test_job_adapter_from_legacy(self):
        from core.services.match_engine_adapters import JobAdapter
        adapter = JobAdapter()
        job_input = adapter.adapt_from_legacy(
            job_id=42,
            job_title="Backend Engineer",
            required_skills=["Python", "Docker"],
            job_location="Remote",
        )
        self.assertIsInstance(job_input, CanonicalJobInput)
        self.assertEqual(job_input.job_id, 42)
        self.assertEqual(len(job_input.requirements), 2)


if __name__ == "__main__":
    unittest.main()
