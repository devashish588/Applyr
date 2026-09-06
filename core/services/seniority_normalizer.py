"""
Seniority Normalizer — deterministic, shared
=============================================

Reuse existing SeniorityLevel taxonomy only.
No from_years, no fuzzy.
"""

from __future__ import annotations

from typing import Optional

SUPPORTED = {"INTERN", "JUNIOR", "MID", "SENIOR", "STAFF", "PRINCIPAL"}

_ALIAS = {
    "level 2": "MID",
    "ii": "MID",
    "level2": "MID",
}


def normalize_seniority(raw: Optional[str]) -> Optional[str]:
    if not raw or not raw.strip():
        return None
    s = raw.strip().upper()
    if s in SUPPORTED:
        return s
    low = raw.strip().lower()
    if low in _ALIAS:
        return _ALIAS[low]
    return None
