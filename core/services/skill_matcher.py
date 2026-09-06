"""
Skill Matcher — Phase 5B-2 Deterministic Skill Matching
========================================================

Pure, deterministic, evidence-based skill matching for MatchEngine2.

Precedence: EXACT > ALIAS > TRANSFERABLE > RELATED > NONE
Full candidate inventory is always evaluated (no early break).
UNKNOWN ≠ MISSING invariant preserved via SkillInventoryStatus gate.

No LLM, no embeddings, no external calls.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

from core.models.match_engine import (
    CanonicalCandidateInput,
    CanonicalJobInput,
    CanonicalJobRequirement,
    RequirementEvaluation,
    RequirementStatus,
    SkillInventoryStatus,
    SkillRelationshipType,
)
from core.services.candidate_intelligence_service import SKILL_CATEGORY_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transferable map — directed candidate_canonical -> {job_canonical}
# Minimal, conservative, reviewed. Uses actual canonical names.
# ---------------------------------------------------------------------------
TRANSFERABLE_MAP: Dict[str, Set[str]] = {
    "PostgreSQL": {"SQL"},
    "MySQL": {"SQL"},
    "SQLite": {"SQL"},
    "PyTorch": {"Machine Learning"},
    "TensorFlow": {"Machine Learning"},
    "Scikit-Learn": {"Machine Learning"},
    "React": {"JavaScript"},
    "FastAPI": {"Python"},
    "Flask": {"Python"},
    "Django": {"Python"},
    "Node.js": {"JavaScript"},
    "TypeScript": {"JavaScript"},
}

# Reverse map not needed — direction is candidate -> requirement
# If bidirectional desired, add explicit entry both ways.


def _category_of(canonical: str) -> str:
    for cat, members in SKILL_CATEGORY_MAP.items():
        if canonical in members:
            return cat
    return "other"


def _classify_pair(
    cand_canonical: str,
    cand_raw: str,
    job_canonical: str,
    job_raw: str,
) -> SkillRelationshipType:
    """Classify one candidate skill vs one job requirement.

    EXACT: canonical equal AND raw identical (case-sensitive)
    ALIAS: canonical equal AND raw differs (case-sensitive)
    TRANSFERABLE: directed map entry
    RELATED: same non-other category
    NONE: otherwise

    Empty/whitespace canonicals are treated as NONE.
    """
    # Defensive: empty canonical -> NONE
    if not cand_canonical or not cand_canonical.strip() or not job_canonical or not job_canonical.strip():
        return SkillRelationshipType.NONE

    # Same canonical -> EXACT or ALIAS (case-sensitive raw comparison)
    if cand_canonical == job_canonical:
        if cand_raw == job_raw:
            return SkillRelationshipType.EXACT
        return SkillRelationshipType.ALIAS

    # Transferable (directed)
    if job_canonical in TRANSFERABLE_MAP.get(cand_canonical, set()):
        return SkillRelationshipType.TRANSFERABLE

    # Related (same non-other category, not transferable)
    cand_cat = _category_of(cand_canonical)
    job_cat = _category_of(job_canonical)
    if cand_cat != "other" and cand_cat == job_cat:
        return SkillRelationshipType.RELATED

    return SkillRelationshipType.NONE


# Precedence rank: lower is better
_PRECEDENCE: Dict[SkillRelationshipType, int] = {
    SkillRelationshipType.EXACT: 0,
    SkillRelationshipType.ALIAS: 1,
    SkillRelationshipType.TRANSFERABLE: 2,
    SkillRelationshipType.RELATED: 3,
    SkillRelationshipType.NONE: 4,
}


class SkillMatcher:
    """Deterministic skill matcher.

    Pure function: evaluate(candidate, job) -> evaluations.
    No mutation of inputs. Handles malformed inputs safely.
    """

    def evaluate(
        self,
        candidate: CanonicalCandidateInput,
        job: CanonicalJobInput,
    ) -> List[RequirementEvaluation]:
        """Evaluate all job requirements against candidate inventory.

        Caller (MatchEngine2) is responsible for UNDETERMINED→UNKNOWN and
        DETERMINED+[]→MISSING gates. This method assumes DETERMINED +
        non-empty inventory. It still defensively handles UNDETERMINED and
        empty cases.

        Returns evaluations in job.requirements order.
        """
        # Defensive: UNDETERMINED → all UNKNOWN (should not reach here in normal flow)
        if candidate.skill_inventory_status == SkillInventoryStatus.UNDETERMINED:
            return [
                RequirementEvaluation(
                    requirement=req,
                    status=RequirementStatus.UNKNOWN,
                    relationship_type=SkillRelationshipType.NONE,
                    matched_skill=None,
                    matched_skill_raw=None,
                    related_skills=[],
                )
                for req in job.requirements
            ]

        # Defensive: DETERMINED + [] → all MISSING
        if not candidate.skill_inventory:
            return [
                RequirementEvaluation(
                    requirement=req,
                    status=RequirementStatus.MISSING,
                    relationship_type=SkillRelationshipType.NONE,
                    matched_skill=None,
                    matched_skill_raw=None,
                    related_skills=[],
                )
                for req in job.requirements
            ]

        # Build parallel lists safely — handle length mismatch via zip with fallback
        # skill_inventory_raw index-corresponds; if mismatch, use canonical as raw
        canonicals = candidate.skill_inventory
        raws = candidate.skill_inventory_raw
        if len(raws) != len(canonicals):
            logger.warning(
                "[SkillMatcher] skill_inventory_raw length mismatch (%d vs %d); using canonical as fallback raw",
                len(raws),
                len(canonicals),
            )
            # Pad or truncate raws to match canonicals
            if len(raws) < len(canonicals):
                raws = list(raws) + [canonicals[i] for i in range(len(raws), len(canonicals))]
            else:
                raws = list(raws[: len(canonicals)])

        evaluations: List[RequirementEvaluation] = []

        for req in job.requirements:
            try:
                ev = self._evaluate_one(canonicals, raws, req)
            except Exception as e:
                logger.warning("[SkillMatcher] evaluator error for %s: %s → UNKNOWN", req.canonical_name, e)
                ev = RequirementEvaluation(
                    requirement=req,
                    status=RequirementStatus.UNKNOWN,
                    relationship_type=SkillRelationshipType.NONE,
                    matched_skill=None,
                    matched_skill_raw=None,
                    related_skills=[],
                )
            evaluations.append(ev)

        return evaluations

    def _evaluate_one(
        self,
        cand_canonicals: List[str],
        cand_raws: List[str],
        req: CanonicalJobRequirement,
    ) -> RequirementEvaluation:
        """Evaluate a single requirement against full candidate inventory."""
        # Malformed requirement -> UNKNOWN
        if not req.canonical_name or not req.canonical_name.strip():
            return RequirementEvaluation(
                requirement=req,
                status=RequirementStatus.UNKNOWN,
                relationship_type=SkillRelationshipType.NONE,
                matched_skill=None,
                matched_skill_raw=None,
                related_skills=[],
            )

        # Classify all candidate skills against this requirement
        best_rel = SkillRelationshipType.NONE
        best_canonical: str | None = None
        best_raw: str | None = None
        related_skills: List[str] = []

        for cand_can, cand_raw in zip(cand_canonicals, cand_raws):
            rel = _classify_pair(cand_can, cand_raw, req.canonical_name, req.raw_name)
            if rel == SkillRelationshipType.RELATED:
                related_skills.append(cand_can)
            # Select strongest via precedence; deterministic tie-break
            if _PRECEDENCE[rel] < _PRECEDENCE[best_rel]:
                best_rel = rel
                best_canonical = cand_can
                best_raw = cand_raw
            elif rel == best_rel and best_rel != SkillRelationshipType.NONE:
                # Same precedence — lexicographically smallest (canonical, raw)
                # Ensures deterministic choice independent of input order
                current_key = (best_canonical or "", best_raw or "")
                candidate_key = (cand_can, cand_raw)
                if candidate_key < current_key:
                    best_canonical = cand_can
                    best_raw = cand_raw

        # Related skills list: sorted, deduped, for stable evidence
        related_skills = sorted(set(related_skills))

        # Determine status from best relationship
        # UNDETERMINED already handled above; here DETERMINED + non-empty
        if best_rel in (SkillRelationshipType.EXACT, SkillRelationshipType.ALIAS):
            status = RequirementStatus.SATISFIED
        elif best_rel == SkillRelationshipType.TRANSFERABLE:
            status = RequirementStatus.PARTIALLY_SATISFIED
        else:
            # RELATED or NONE → MISSING (authoritative absence)
            status = RequirementStatus.MISSING

        # For MISSING with RELATED, keep related_skills; for SATISFIED, clear it
        if status == RequirementStatus.SATISFIED:
            related_skills = []

        return RequirementEvaluation(
            requirement=req,
            status=status,
            relationship_type=best_rel,
            matched_skill=best_canonical,
            matched_skill_raw=best_raw,
            related_skills=related_skills,
        )


# Singleton helper for MatchEngine2
_skill_matcher_instance: SkillMatcher | None = None


def get_skill_matcher() -> SkillMatcher:
    global _skill_matcher_instance
    if _skill_matcher_instance is None:
        _skill_matcher_instance = SkillMatcher()
    return _skill_matcher_instance
