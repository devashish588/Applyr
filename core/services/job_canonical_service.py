"""
Job Canonical / Dedup / Freshness Service — Phase 9
Deterministic, no LLM, preserves UNKNOWN semantics.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from core.services.location_normalizer import extract_city, normalize_city
from core.services.role_normalizer import normalize_title

# Tracking params to strip (common UTM + ad click ids) — safe to remove
# NOTE: "ref" is NOT stripped — it can carry requisition identity (e.g., ?ref=123)
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "utm_reader", "utm_viz_id", "utm_pulse",
    "gclid", "fbclid", "msclkid", "igshid", "dclid", "gbraid", "wbraid",
    "yclid", "ttclid", "_hsenc", "_hsmi", "mc_eid", "mkt_tok",
    "vero_id", "rb_clickid", "srsltid", "ref_src",
}

# Source reliability tiers — deterministic, no fake precision
# High: direct company careers; Medium-high: well-known boards; Medium: aggregators; Low: unknown generic
_SOURCE_RELIABILITY_MAP = {
    # High — direct careers
    "greenhouse.io": "high",
    "boards.greenhouse.io": "high",
    "lever.co": "high",
    "jobs.lever.co": "high",
    "ashbyhq.com": "high",
    "jobs.ashbyhq.com": "high",
    "workday": "high",
    "myworkdayjobs.com": "high",
    " Taleo": "high",
    # Medium-high — well-known boards
    "linkedin.com": "high",
    "wellfound.com": "medium_high",
    "indeed.com": "medium_high",
    "glassdoor.com": "medium_high",
    "naukri.com": "medium_high",
    "ycombinator.com": "medium_high",
    "otta.com": "medium_high",
    "builtin.com": "medium_high",
    # Medium — aggregators / remote boards
    "remoteok.com": "medium",
    "weworkremotely.com": "medium",
    "remotive.com": "medium",
    "arc.dev": "medium",
    "aijobs.net": "medium",
    "ai-jobs.net": "medium",
    "remote.co": "medium",
}


def _normalize_company(company: Optional[str]) -> str:
    if not company or not company.strip():
        return ""
    # Collapse whitespace, strip, lower, remove common punctuation noise
    s = " ".join(company.strip().split())
    # Lower for canonical; preserve original case in display but hash lower
    # Remove trailing Inc, Ltd, LLC noise? Keep conservative: only trim punctuation . , 
    s = s.strip(" .,")
    return s.lower()


def _normalize_location(location: Optional[str]) -> str:
    if not location or not location.strip():
        return ""
    city = extract_city(location)  # first comma component
    if city:
        return normalize_city(city)
    return normalize_city(location)


def canonicalize_url(url: Optional[str]) -> Optional[str]:
    """Return canonical URL with tracking params stripped, host lower, path normalized.
    Returns None if url falsy or not http. Preserves meaningful query params sorted.
    """
    if not url or not url.strip():
        return None
    url = url.strip()
    if not url.lower().startswith("http"):
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return url  # fallback raw
    # Host lower, strip default ports
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and parsed.scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and parsed.scheme == "https":
        netloc = netloc[:-4]
    # Path: lower? Keep case but strip trailing slash (except root), decode not needed
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = ""
    # Query: strip tracking params, sort remaining
    qsl = parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [(k, v) for k, v in qsl if k.lower() not in _TRACKING_PARAMS]
    filtered.sort(key=lambda kv: (kv[0].lower(), kv[1]))
    query = urlencode(filtered, doseq=True)
    # Fragment always stripped (tracking)
    canonical = urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))
    return canonical


def _url_host(url_canonical: Optional[str]) -> str:
    if not url_canonical:
        return ""
    try:
        return urlparse(url_canonical).netloc.lower()
    except Exception:
        return ""


def compute_canonical_id(title: Optional[str], company: Optional[str], location: Optional[str], url: Optional[str]) -> str:
    """Deterministic hash of normalized components.
    Includes url host to avoid false merges (same title/company/city but different host -> different id).
    Title/company are normalized via existing normalizers; location via city; url via host extracted from canonical URL.
    Returns hex digest 16 chars (64-bit) — stable, collision low but not cryptographic requirement.
    """
    t = normalize_title(title or "").strip().lower()
    # Collapse title extra spaces after normalize (which already does)
    t = " ".join(t.split())
    c = _normalize_company(company)
    loc = _normalize_location(location)
    url_c = canonicalize_url(url)
    host = _url_host(url_c)
    # Host included to prevent aggressive cross-host merges; empty host for manual/no-url means hash without host bias
    raw = f"{c}|{t}|{loc}|{host}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _host_matches(host: str, trusted: str) -> bool:
    """Exact host or legitimate subdomain (foo.trusted.com). Case already lower."""
    if not host or not trusted:
        return False
    host = host.lower().strip()
    trusted = trusted.lower().strip()
    if host == trusted:
        return True
    # legitimate subdomain: ends with .trusted
    if host.endswith("." + trusted):
        return True
    return False


def determine_source_reliability(source: Optional[str], url: Optional[str]) -> str:
    """Deterministic tier: high / medium_high / medium / neutral. No fake precision.
    Uses exact hostname / subdomain matching, not substring.
    """
    # Check url host first (parsed, not substring)
    host = ""
    if url:
        cu = canonicalize_url(url) or url
        try:
            host = urlparse(cu).netloc.lower()
        except Exception:
            host = ""
    src = (source or "").strip().lower()
    # Try host map — exact or subdomain
    for key, tier in _SOURCE_RELIABILITY_MAP.items():
        k = key.strip().lower()
        if _host_matches(host, k):
            return tier
        # Source field may be bare ("linkedin") or hostname ("linkedin.com")
        # Bare: "linkedin" should match "linkedin.com" via prefix before dot
        if src:
            if _host_matches(src, k):
                return tier
            # bare token match: source "linkedin" matches trusted "linkedin.com"
            if "." not in src and k.startswith(src + "."):
                return tier
            # also direct contains for source like "boards.greenhouse.io" exact
            if src == k:
                return tier
    if host or src:
        return "neutral"
    return "neutral"


def freshness_state(scraped_at: Optional[str], last_seen_at: Optional[str] = None, now: Optional[datetime] = None) -> str:
    """Return NEW/FRESH/AGING/STALE/UNKNOWN.
    NEW: 0-2 days since scraped_at (original discovery)
    FRESH: 3-14 days
    AGING: 15-30 days
    STALE: >30 days
    UNKNOWN: null/unparseable scraped_at
    last_seen_at is intentionally IGNORED for age — it tracks most recent observation,
    not original discovery, and must not rejuvenate freshness (Phase 6 contract).
    """
    s = scraped_at
    if not s:
        return "UNKNOWN"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return "UNKNOWN"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    days = (now - dt).days
    if days < 0:
        # Future date (clock skew) treat as NEW
        return "NEW"
    if days <= 2:
        return "NEW"
    if days <= 14:
        return "FRESH"
    if days <= 30:
        return "AGING"
    return "STALE"


def freshness_details(scraped_at: Optional[str], last_seen_at: Optional[str] = None, now: Optional[datetime] = None) -> Dict[str, Optional[str]]:
    """Explainable freshness factors."""
    state = freshness_state(scraped_at, last_seen_at, now=now)
    return {
        "freshness_state": state,
        "scraped_at": scraped_at,
        "last_seen_at": last_seen_at,
        "is_fresh": "true" if state in ("NEW", "FRESH") else "false" if state in ("AGING", "STALE") else "unknown",
    }


def resolve_canonical_target(conn, canonical_id: str, job_id: int) -> Optional[int]:
    """Given a canonical_id, find the authoritative canonical job id (smallest id where is_duplicate_of IS NULL).
    Prevents chain A->B->C by always pointing to ultimate canonical (recursive).
    Uses indexed canonical_id lookup.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, is_duplicate_of FROM jobs WHERE canonical_id = %s ORDER BY id ASC",
            (canonical_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        # Find first canonical (is_duplicate_of IS NULL)
        for rid, dup in rows:
            if dup is None and rid != job_id:
                # Follow chain if this canonical itself points somewhere (should not, but handle)
                # Resolve ultimate
                ultimate = rid
                # Walk is_duplicate_of if needed
                visited = set()
                while True:
                    if ultimate in visited:
                        break
                    visited.add(ultimate)
                    cur.execute("SELECT is_duplicate_of FROM jobs WHERE id = %s", (ultimate,))
                    r = cur.fetchone()
                    if not r or r[0] is None:
                        break
                    try:
                        nxt = int(r[0])
                    except Exception:
                        break
                    ultimate = nxt
                return ultimate
        # No other canonical found; this job is canonical itself
        return None


def compute_job_quality(
    has_description: bool,
    source: Optional[str],
    application_url: Optional[str],
    freshness: str,
    is_duplicate: bool,
) -> Dict[str, str]:
    """Explainable factors, no opaque single number."""
    factors: Dict[str, str] = {}
    factors["has_description"] = "true" if has_description else "false"
    factors["source_identified"] = "true" if bool(source and source.strip()) else "false"
    factors["application_url_available"] = "true" if bool(application_url and application_url.strip().startswith("http")) else "false"
    factors["freshness_state"] = freshness or "UNKNOWN"
    factors["is_duplicate"] = "true" if is_duplicate else "false"
    # Surface safe_to_surface: false if duplicate (should hide duplicate card) else true
    # Stale is still surfaceable — we do NOT hide stale, we badge it.
    factors["is_stale"] = "true" if freshness == "STALE" else "false"
    return factors
