"""
Job Quality — observable data quality only
==========================================

No desirability score, no ATS ranking.
Extended in Phase 9 with freshness, duplicate, source reliability explainable factors.
"""

from __future__ import annotations

from typing import Dict, Optional


def assess_job_quality(
    has_description: bool,
    source: Optional[str],
    application_url: Optional[str],
) -> Dict[str, str]:
    """Return explainable factors, not a score. Backward compatible."""
    factors: Dict[str, str] = {}
    factors["has_description"] = "true" if has_description else "false"
    factors["source_identified"] = "true" if bool(source and source.strip()) else "false"
    factors["application_url_available"] = "true" if bool(application_url and application_url.strip().startswith("http")) else "false"
    return factors


def assess_job_quality_extended(
    has_description: bool,
    source: Optional[str],
    application_url: Optional[str],
    canonical_id: Optional[str] = None,
    is_duplicate: bool = False,
    freshness_state: Optional[str] = None,
    source_reliability: Optional[str] = None,
) -> Dict[str, str]:
    """Extended explainable JobQuality — used by Phase 9 API. Preserves underlying factors."""
    factors = assess_job_quality(has_description, source, application_url)
    # Reliability
    if source_reliability:
        factors["source_reliability"] = source_reliability
    else:
        # Derive if not provided
        try:
            from core.services.job_canonical_service import determine_source_reliability
            factors["source_reliability"] = determine_source_reliability(source, application_url)
        except Exception:
            factors["source_reliability"] = "neutral"
    factors["freshness_state"] = freshness_state or "UNKNOWN"
    factors["is_duplicate"] = "true" if is_duplicate else "false"
    # Canonical present?
    factors["canonical_id"] = canonical_id or "unknown"
    # Safe to surface: false only for duplicates (not stale — stale is still surfaced with badge)
    factors["is_stale"] = "true" if freshness_state == "STALE" else "false"
    return factors
