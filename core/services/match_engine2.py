"""
Match Engine 2.0 — Orchestration Skeleton (Phase 5B-1)
=======================================================

Structural MatchEngine2 skeleton establishing the orchestration boundary.

Phase 5B-1 scope:
  - Exposes the public `analyze()` entry point
  - Returns a structural MatchResult skeleton
  - Does NOT implement actual matching, evaluation, scoring, or ranking
  - Does NOT call external services or LLMs
  - Does NOT replace or redirect existing MatchService behavior

MatchService (core/services/match_service.py) remains the sole
authoritative numerical scorer with preserved 40/25/20/10/5 weights.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from core.models import MatchAnalysis

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

logger = logging.getLogger(__name__)

ENGINE_VERSION = "2.1.0-skill-matcher"


class MatchEngine2:
    """Match Engine 2.0 orchestrator (Phase 5B-1 skeleton).

    This class establishes the structural boundary for the future
    Match Engine 2.0. In Phase 5B-1 it returns placeholder results
    that correctly reflect the inventory status semantics from
    the approved Phase 5A design.

    It does NOT:
      - Implement skill matching
      - Implement requirement evaluation
      - Implement gap calculation
      - Implement numerical scoring
      - Implement ranking
      - Implement confidence/completeness calculation
      - Call LLMs, embeddings, or external services
      - Replace or redirect existing MatchService behavior
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def analyze(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
        baseline_analysis: Optional[MatchAnalysis] = None,
    ) -> MatchResult:
        """Structural entry point for Match Engine 2.0 analysis.

        In Phase 5B-1, this method:
          1. Validates the inventory status contract
          2. Produces structurally correct placeholder evaluations ONLY
             for the cases where no matching logic is required:
             - UNDETERMINED → UNKNOWN
             - DETERMINED + [] → MISSING (authoritative absence)
          3. For DETERMINED + populated inventory, returns an EMPTY
             overlay (no evaluations) — real matching belongs to 5B-2+.
          4. Returns a MatchResult skeleton wrapping the baseline.

        No actual matching, scoring, or evaluation logic is implemented.
        No fake MISSING is emitted for DETERMINED + populated (5B-2+ only).

        Args:
            candidate: Canonical candidate input from CandidateAdapter.
            job: Canonical job input from JobAdapter.
            baseline_analysis: Optional MatchAnalysis from existing
                MatchService (preserved as-is, not modified).

        Returns:
            MatchResult with structural placeholder evaluations or empty overlay.
        """
        # 5B-2 + 5B-3 + 5B-4 + 5B-5 + 5B-6: deterministic matchers
        if (
            candidate.skill_inventory_status == SkillInventoryStatus.DETERMINED
            and candidate.skill_inventory
        ):
            from core.services.experience_matcher import get_experience_matcher
            from core.services.location_matcher import get_location_matcher
            from core.services.role_matcher import get_role_matcher
            from core.services.seniority_matcher import get_seniority_matcher
            from core.services.skill_matcher import get_skill_matcher

            skill_evals = get_skill_matcher().evaluate(candidate, job)
            exp_evals = get_experience_matcher().evaluate(candidate, job)
            role_evals = get_role_matcher().evaluate(candidate, job)
            loc_evals = get_location_matcher().evaluate(candidate, job)
            sen_evals = get_seniority_matcher().evaluate(candidate, job)

            satisfied = [e.requirement.canonical_name for e in skill_evals if e.status == RequirementStatus.SATISFIED]
            missing = [e.requirement.canonical_name for e in skill_evals if e.status == RequirementStatus.MISSING]
            unknown = [e.requirement.canonical_name for e in skill_evals if e.status == RequirementStatus.UNKNOWN]
            partial = [e.requirement.canonical_name for e in skill_evals if e.status == RequirementStatus.PARTIALLY_SATISFIED]

            # Analysis completeness: fraction of candidate dimensions DETERMINED (informational, never alters score)
            try:
                from core.models.match_engine import ExperienceAvailability, LocationAvailability, RoleAvailability, SeniorityAvailability

                dims = [
                    candidate.skill_inventory_status.value == "determined",
                    candidate.experience_availability.value == "determined",
                    candidate.role_availability.value == "determined",
                    candidate.location_availability.value == "determined",
                    candidate.seniority_availability.value == "determined",
                ]
                completeness = round(sum(1 for d in dims if d) / len(dims), 2) if dims else 0.0
            except Exception:
                completeness = 0.0

            return MatchResult(
                baseline_analysis=baseline_analysis,
                inventory_status=candidate.skill_inventory_status,
                requirement_evaluations=skill_evals,
                experience_evaluations=exp_evals,
                role_evaluations=role_evals,
                location_evaluations=loc_evals,
                seniority_evaluations=sen_evals,
                analysis_completeness=completeness,
                data_completeness=completeness,
                match_confidence=0.0,
                satisfied_requirements=satisfied,
                missing_requirements=missing,
                unknown_requirements=unknown,
                partial_requirements=partial,
                engine_version=ENGINE_VERSION,
                analyzed_at=datetime.now(timezone.utc).isoformat(),
            )

        evaluations = []

        for req in job.requirements:
            evaluation = self._placeholder_evaluate(candidate, req)
            evaluations.append(evaluation)

        # Categorize requirements by status
        satisfied = [e.requirement.canonical_name for e in evaluations if e.status == RequirementStatus.SATISFIED]
        missing = [e.requirement.canonical_name for e in evaluations if e.status == RequirementStatus.MISSING]
        unknown = [e.requirement.canonical_name for e in evaluations if e.status == RequirementStatus.UNKNOWN]
        partial = [e.requirement.canonical_name for e in evaluations if e.status == RequirementStatus.PARTIALLY_SATISFIED]

        from core.services.experience_matcher import get_experience_matcher
        from core.services.location_matcher import get_location_matcher
        from core.services.role_matcher import get_role_matcher
        from core.services.seniority_matcher import get_seniority_matcher

        exp_evals = get_experience_matcher().evaluate(candidate, job)
        role_evals = get_role_matcher().evaluate(candidate, job)
        loc_evals = get_location_matcher().evaluate(candidate, job)
        sen_evals = get_seniority_matcher().evaluate(candidate, job)
        try:
            from core.models.match_engine import ExperienceAvailability, LocationAvailability, RoleAvailability, SeniorityAvailability

            dims2 = [
                candidate.skill_inventory_status.value == "determined",
                candidate.experience_availability.value == "determined",
                candidate.role_availability.value == "determined",
                candidate.location_availability.value == "determined",
                candidate.seniority_availability.value == "determined",
            ]
            completeness2 = round(sum(1 for d in dims2 if d) / len(dims2), 2) if dims2 else 0.0
        except Exception:
            completeness2 = 0.0

        return MatchResult(
            baseline_analysis=baseline_analysis,
            inventory_status=candidate.skill_inventory_status,
            requirement_evaluations=evaluations,
            experience_evaluations=exp_evals,
            role_evaluations=role_evals,
            location_evaluations=loc_evals,
            seniority_evaluations=sen_evals,
            analysis_completeness=completeness2,
            data_completeness=completeness2,
            match_confidence=0.0,       # Not calculated in 5B-1
            satisfied_requirements=satisfied,
            missing_requirements=missing,
            unknown_requirements=unknown,
            partial_requirements=partial,
            engine_version=ENGINE_VERSION,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

    def _placeholder_evaluate(
        self,
        candidate: CanonicalCandidateInput,
        requirement: CanonicalJobRequirement,
    ) -> RequirementEvaluation:
        """Produce a structurally correct placeholder evaluation.

        This method applies ONLY the Phase 5A inventory status semantics
        that do NOT require matching logic:
          - UNDETERMINED → UNKNOWN (regardless of skill_inventory contents)
          - DETERMINED + [] → MISSING (authoritative absence)

        DETERMINED + populated is handled by analyze() as an empty overlay
        and never reaches this method with a fake MISSING.

        No actual skill matching is performed.
        """
        if candidate.skill_inventory_status == SkillInventoryStatus.UNDETERMINED:
            # Phase 5A §1.4: UNDETERMINED → every requirement → UNKNOWN
            return RequirementEvaluation(
                requirement=requirement,
                status=RequirementStatus.UNKNOWN,
                relationship_type=SkillRelationshipType.NONE,
                matched_skill=None,
            )

        # DETERMINED + [] → authoritative absence → MISSING
        # (The DETERMINED + populated case is handled as empty overlay in analyze())
        return RequirementEvaluation(
            requirement=requirement,
            status=RequirementStatus.MISSING,
            relationship_type=SkillRelationshipType.NONE,
            matched_skill=None,
        )
