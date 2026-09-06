"""
Role Normalizer — Shared Deterministic Title Normalization
===========================================================

Extracted from JobIntelligenceService._normalize_title to avoid
CandidateAdapter → JobIntelligenceService private dependency.
Preserves existing behavior: trim, sr/jr/ii/iii handling.
No fuzzy/semantic logic, no Senior stripping.
"""

from __future__ import annotations


_COMMON = {
    "sr": "Senior",
    "jr": "Junior",
    "iii": "III",
    "ii": "II",
    "iv": "IV",
    "sr.": "Senior",
    "jr.": "Junior",
}


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    # Trim, preserve internal whitespace collapsed to single space via split/join
    words = title.strip().split()
    normalized: list[str] = []
    for w in words:
        lower = w.lower().rstrip(".")
        if lower in _COMMON:
            normalized.append(_COMMON[lower])
        else:
            normalized.append(w.strip())
    # Re-join with single space, but preserve original casing except mapped tokens
    return " ".join(normalized)


def is_empty_normalized(title: str | None) -> bool:
    return not normalize_title(title)
