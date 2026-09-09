"""
Job Listing Gate — deterministic pre-storage filter for clear non-job pages.

Search/HTML adapters can return listing indexes, tag pages, team pages, or
editorial articles as "jobs" (e.g. builtin.com "View All Jobs at Built In").
This gate classifies each normalized job dict BEFORE canonical ID / DB insert:

    JOB          — eligible for downstream handling as a posting
    NON_JOB      — clearly not an individual posting; excluded, reason recorded
    UNDETERMINED — weak evidence either way; stays eligible, existing Job
                   Quality / Intelligence handles it downstream

Conservative by design: sparse descriptions, missing locations, unknown
companies, unusual titles, or unfamiliar URLs never produce NON_JOB on
their own. Deterministic stdlib only — no candidate data, no Match /
Priority imports, no LLM, no network.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qsl

JOB = "JOB"
NON_JOB = "NON_JOB"
UNDETERMINED = "UNDETERMINED"

# Title shapes of listing-index / editorial pages. These are page-type
# signals, not one-off strings: real posting titles are noun phrases and
# essentially never take these forms.
_INDEX_TITLE_PREFIXES = (
    "view all",
    "browse all",
    "see all",
    "all jobs",
    "job search results",
    "search results",
    "job results",
    "find jobs",
)

# Bare site sections that list, describe, or market — never a single posting.
# Applied to the first URL path segment of any host (generic CMS/board
# vocabulary); a posting identifier anywhere in the URL always rescues first.
# "careers" is intentionally NOT a section: bare /careers roots are handled
# by _LISTING_ROOTS with a substantive-text carve-out, because the HTML
# adapter itself may emit a JD-like careers page as a single listing.
_LISTING_ROOTS = {
    "/jobs", "/job", "/careers", "/positions", "/openings",
    "/vacancies", "/search", "/jobs/search", "/careers/jobs",
}
_SECTION_SEGMENTS = {
    "company", "companies", "team", "teams", "tag", "tags",
    "article", "articles", "blog", "blogs", "news", "press",
    "about", "stories", "perspectives", "insights", "resources",
    "events", "podcast",
}

# Query params that carry a concrete posting identity.
_JOB_ID_PARAMS = {
    "job_id", "jobid", "posting", "postingid", "posting_id",
    "requisition", "requisition_id", "req_id", "gh_jid",
    "vacancy", "vacancy_id", "jobkey", "jk",
}

# Role-like words (same concept as the HTML adapter's job-ish anchor check).
_ROLE_WORDS = {
    "engineer", "developer", "manager", "analyst", "intern",
    "designer", "scientist", "lead", "specialist", "nurse",
    "teacher", "accountant", "marketer", "sales", "support",
    "technician", "assistant", "associate", "director",
    "consultant", "architect", "writer", "editor", "cook", "driver",
}

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _has_posting_identifier(url: str) -> bool:
    """True when the URL itself carries a concrete posting identity.

    Numeric path segments (>=4 digits, avoids year-like false rescues only in
    combination — a bare year still needs a posting-shaped context, but an
    identifier always rescues from URL-based NON_JOB signals), UUID segments
    (Lever-style), or known job-id query params. Absence proves nothing.
    """
    try:
        parts = urlparse(url or "")
    except Exception:
        return False
    try:
        for seg in (parts.path or "").split("/"):
            s = seg.strip()
            if not s:
                continue
            if s.isdigit() and len(s) >= 4:
                return True
            if _UUID_RE.match(s):
                return True
            # Slug-embedded posting ids ("frontend-engineer-1842", "job-10533632").
            # Threshold 3+ digits avoids matching years inside article slugs alone
            # (those still face the title rules); absence proves nothing.
            if re.search(r"-(\d{3,})$", s):
                return True
        try:
            for k, v in parse_qsl(parts.query or "", keep_blank_values=True):
                if k.lower() in _JOB_ID_PARAMS and (v or "").strip():
                    if k.lower() == "id":
                        if v.strip().isdigit() and len(v.strip()) >= 4:
                            return True
                    else:
                        return True
        except Exception:
            pass
    except Exception:
        return False
    return False


def classify_listing(job: dict) -> tuple[str, str]:
    """Classify a normalized job dict. Returns (verdict, reason)."""
    title = str(job.get("title") or "").strip()
    tl = title.lower()
    url = str(job.get("url") or "").strip()
    text = str(job.get("jd_text") or job.get("description_snippet") or "")

    # 1) Title page-type signals — near-certain, decisive on their own.
    # Real posting titles are noun phrases; a question mark only occurs in
    # article/editorial headlines.
    if "?" in tl:
        return NON_JOB, "NON_JOB_PAGE:title contains a question mark (headline, not a posting)"
    for prefix in _INDEX_TITLE_PREFIXES:
        if tl.startswith(prefix):
            return NON_JOB, f"NON_JOB_PAGE:listing-index title ({prefix!r})"

    # 2) URL structural signals — only when no posting identifier rescues, and
    # only for non-substantive pages. The HTML adapter itself treats a page as
    # a single listing when its text is long and JD-like, so a section/root
    # page with substantive text stays eligible for downstream Job Quality
    # instead of being rejected here. Short text + structural URL = clear page.
    if url and not _has_posting_identifier(url) and len(text.strip()) < 800:
        try:
            path = (urlparse(url).path or "").lower()
            norm = path.rstrip("/") or "/"
            if norm in _LISTING_ROOTS:
                return NON_JOB, f"NON_JOB_PAGE:bare listing root ({norm}) with no posting identifier"
            segs = [s for s in path.split("/") if s]
            if segs and segs[0] in _SECTION_SEGMENTS:
                return NON_JOB, f"NON_JOB_PAGE:non-posting site section (/{segs[0]})"
        except Exception:
            pass

    # 3) Positive posting evidence — anything below keeps the item eligible.
    if _has_posting_identifier(url):
        return JOB, "JOB:posting identifier present in URL"
    if len(text.strip()) >= 40:
        return JOB, "JOB:substantive description present"
    words = set(re.findall(r"[a-z]+", tl))
    if words & _ROLE_WORDS:
        return JOB, "JOB:role-like title with clean URL"

    return UNDETERMINED, "UNDETERMINED:insufficient posting evidence either way"


def filter_listings(jobs: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Split raw adapter output into (passing, [(non_job, reason), ...]).

    Passing = JOB + UNDETERMINED. Only NON_JOB is excluded, with reason.
    """
    passing: list[dict] = []
    filtered: list[tuple[dict, str]] = []
    for job in jobs or []:
        try:
            verdict, reason = classify_listing(job if isinstance(job, dict) else {})
        except Exception:
            verdict, reason = UNDETERMINED, "UNDETERMINED:classifier error, fail open"
        if verdict == NON_JOB:
            filtered.append((job, reason))
        else:
            passing.append(job)
    return passing, filtered
