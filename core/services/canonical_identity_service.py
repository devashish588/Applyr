"""
Canonical Identity Service — cross-source tiered resolver (Task 33 Final).
Host must NOT be primary identity. Source is observation attribute.
Tiers:
 T1 STRONG: same stable external/ATS ID + same company, or same normalized official application URL, or same ATS posting identifier.
 T2 HIGH-CONFIDENCE COMPOSITE: company + title + location + type (all normalized) exact match, with stable ID check (if both have IDs they must match).
 T3 DESCRIPTION: only if T2 candidate exists, use deterministic token overlap to avoid merging distinct requisitions with same T2 but materially different description.
 T4 AMBIGUOUS: do not merge.
Deterministic, no LLM, no host in primary key.
"""
from __future__ import annotations
import re
import hashlib
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse

from core.services.job_canonical_service import canonicalize_url, normalize_title, _normalize_company, _normalize_location

def _extract_stable_id(url: Optional[str], source: Optional[str] = None) -> Optional[str]:
    if not url:
        return None
    u = url.strip().lower()
    # ATS patterns
    # greenhouse: boards.greenhouse.io/.../jobs/<id> or greenhouse ATS id in path query
    m = re.search(r"greenhouse\.io/(?:.*?[?&]gh_jid=(\d+)|.*/jobs/(\d+))", u)
    if m:
        return f"gh:{m.group(1) or m.group(2)}"
    m = re.search(r"lever\.co/[^/]+/(\d+)", u) or re.search(r"jobs\.lever\.co/[^/]+/([a-f0-9\-]{36})", u)
    if m:
        return f"lever:{m.group(1)}"
    m = re.search(r"ashbyhq\.com/[^/]+/([a-f0-9\-]+)", u)
    if m:
        return f"ashby:{m.group(1)}"
    m = re.search(r"myworkdayjobs\.com/[^/]+/job/[^/]+/([A-Z0-9\-_]+)", u)
    if m:
        return f"wd:{m.group(1)}"
    # generic numeric requisition in path: /job/123 or /jobs/123 or requisition id param
    m = re.search(r"[?&](?:job[_-]?id|req[_-]?id|requisition[_-]?id)=([a-z0-9\-_]+)", u)
    if m:
        return f"req:{m.group(1)}"
    # path numeric id at end: /job/123456 or /12345
    m = re.search(r"/(?:job|jobs|careers|position|posting)/[^/]*?(\d{4,})", u)
    if m:
        return f"num:{m.group(1)}"
    # fallback: last path segment numeric
    try:
        path = urlparse(url).path.rstrip("/").split("/")[-1]
        if path.isdigit() and len(path) >= 4:
            return f"num:{path}"
    except Exception:
        pass
    return None

def _normalize_type(t: Optional[str]) -> str:
    if not t:
        return ""
    return t.strip().lower()

def _token_set(text: Optional[str]) -> set[str]:
    if not text:
        return set()
    # deterministic tokenization: lower, split on non-alnum, filter stopwords short
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    stop = {"the","and","or","a","an","to","for","with","of","in","on","that","as","is","are","be","by","at","from","you","will","we","our","your"}
    return {t for t in tokens if len(t) > 2 and t not in stop}

def _description_similarity(a: Optional[str], b: Optional[str]) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

def _official_url_canon(url: Optional[str]) -> Optional[str]:
    return canonicalize_url(url)

class CanonicalIdentityService:
    def resolve(self, observation: Dict, candidates: List[Dict]) -> Optional[int]:
        """
        observation: dict with title, company, location, type, url, jd_text, source, stable_id (optional)
        candidates: list of existing canonical jobs dicts with id, title, company, location, type, url, jd_text, canonical_id
        Returns canonical job id to merge into, or None to create new.
        Deterministic: same inputs -> same decision.
        """
        if not candidates:
            return None
        # Normalize observation
        obs_company_n = _normalize_company(observation.get("company"))
        obs_title_n = " ".join(normalize_title(observation.get("title") or "").lower().split())
        obs_loc_n = _normalize_location(observation.get("location"))
        obs_type_n = _normalize_type(observation.get("type"))
        obs_url_canon = _official_url_canon(observation.get("url"))
        obs_stable = observation.get("stable_id") or _extract_stable_id(observation.get("url"), observation.get("source"))
        obs_desc = observation.get("jd_text") or observation.get("description_snippet") or ""

        tier1_hits: List[Dict] = []
        tier2_hits: List[Dict] = []

        for cand in candidates:
            cand_company_n = _normalize_company(cand.get("company"))
            cand_title_n = " ".join(normalize_title(cand.get("title") or "").lower().split())
            cand_loc_n = _normalize_location(cand.get("location"))
            cand_type_n = _normalize_type(cand.get("type"))
            cand_url_canon = _official_url_canon(cand.get("url"))
            cand_stable = cand.get("stable_id") or _extract_stable_id(cand.get("url"), cand.get("source"))
            cand_desc = cand.get("jd_text") or ""

            # T1: stable ID + same company
            if obs_stable and cand_stable and obs_stable == cand_stable and obs_company_n and obs_company_n == cand_company_n:
                tier1_hits.append(cand)
                continue
            # T1: exact normalized official URL
            if obs_url_canon and cand_url_canon and obs_url_canon == cand_url_canon:
                tier1_hits.append(cand)
                continue
            # T2: composite high-confidence
            if obs_company_n and cand_company_n and obs_company_n == cand_company_n:
                # title must match exactly normalized (prevents I vs II merge)
                if obs_title_n and cand_title_n and obs_title_n == cand_title_n:
                    # location must match (prevents Bangalore vs New York)
                    if obs_loc_n == cand_loc_n:
                        # type must match if both present (prevents fulltime vs contract distinct)
                        if obs_type_n and cand_type_n and obs_type_n != cand_type_n:
                            continue
                        # stable ID check: if both have stable IDs and they differ -> distinct requisitions (Case E)
                        if obs_stable and cand_stable and obs_stable != cand_stable:
                            continue
                        # Passed T2 composite
                        # T3: description check if both have substantial descriptions and they differ materially
                        # Only consider description if both have >50 tokens and similarity is very low (<0.15) -> likely different requisitions
                        if obs_desc and cand_desc and len(_token_set(obs_desc)) > 20 and len(_token_set(cand_desc)) > 20:
                            sim = _description_similarity(obs_desc, cand_desc)
                            if sim < 0.12:  # materially different
                                continue
                        tier2_hits.append(cand)
                        continue

        # T1 is strong, choose if exactly one
        if len(tier1_hits) == 1:
            return int(tier1_hits[0]["id"])
        if len(tier1_hits) > 1:
            # ambiguous multiple T1 -> do not merge (T4)
            return None
        # T2
        if len(tier2_hits) == 1:
            return int(tier2_hits[0]["id"])
        if len(tier2_hits) > 1:
            # ambiguous: multiple candidates with same composite (e.g., two different requisitions with same title/company/location but no stable ID)
            # Do not merge automatically
            return None
        return None

    def find_candidates(self, observation: Dict, conn) -> List[Dict]:
        """Indexed lookup: fetch likely candidates via company (indexed) to avoid O(N^2)."""
        company = observation.get("company") or ""
        if not company.strip():
            return []
        # Use normalized company for query via lower(company) index
        # We use lower(company) = lower(%s) which can use idx_jobs_company if lower() functional? But we have idx on company, not lower, still filter in Python is okay for small N.
        # For performance, we limit to maybe 50 candidates
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, title, company, location, type, url, jd_text, canonical_id, source
                    FROM jobs WHERE is_duplicate_of IS NULL AND lower(company) = lower(%s)
                    ORDER BY id ASC LIMIT 50
                """, (company.strip(),))
                cols = ["id","title","company","location","type","url","jd_text","canonical_id","source"]
                rows = cur.fetchall()
                return [dict(zip(cols, r)) for r in rows]
        except Exception:
            return []

def get_canonical_identity_service() -> CanonicalIdentityService:
    return CanonicalIdentityService()
