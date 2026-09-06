"""
Location Normalizer — city-only deterministic normalization
==========================================================

strip, lower, collapse whitespace, small alias map.
No geocoding, no JD parsing.
"""

from __future__ import annotations

import re

_CITY_ALIAS = {
    "bengaluru": "bangalore",
    # New Delhi handling: keep as normalized lower, alias via lower equality
    # "new delhi" is distinct city, not alias for delhi
}


def normalize_city(city: str | None) -> str:
    if not city or not city.strip():
        return ""
    # Collapse internal whitespace
    s = " ".join(city.strip().split())
    low = s.lower()
    # Alias lookup on lower
    if low in _CITY_ALIAS:
        return _CITY_ALIAS[low]
    return low


def extract_city(raw_location: str | None) -> str | None:
    """First comma component as city (deterministic). Returns None if empty."""
    if not raw_location or not raw_location.strip():
        return None
    # First comma-delimited component
    first = raw_location.split(",", 1)[0].strip()
    if not first:
        return None
    return first
