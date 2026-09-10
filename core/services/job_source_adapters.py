"""
Job Source Adapters — minimal per-source fetch+normalize with common contract.
Each adapter returns (jobs: list[dict], failure_category, error) without DB writes.
Respects robots via simple check (robots.txt disallow for path), rate limit, User-Agent.
No fabricated jobs. No stealth/CAPTCHA bypass.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import requests
from requests.exceptions import Timeout, RequestException

logger = logging.getLogger(__name__)

UA = "Applyr/2.0 (+https://applyr.local) Mozilla/5.0"
TIMEOUT = 12

FAIL = {
    "SUCCESS", "NO_RESULTS", "TIMEOUT", "HTTP_ERROR", "BLOCKED",
    "ROBOTS_DISALLOWED", "AUTH_REQUIRED", "AUTH", "PARSER_ERROR", "SCHEMA_CHANGED",
    "RATE_LIMITED", "UNSUPPORTED", "NETWORK", "PROVIDER_ERROR", "FILTERED", "UNKNOWN",
}

def _robots_allowed(url: str) -> bool:
    try:
        p = urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True  # fail-open for availability, but we still respect explicit disallow

def _http_get(url: str) -> Tuple[int, str, str | None]:
    """GET url, return (status, text, error_category)."""
    if not _robots_allowed(url):
        return 0, "", "ROBOTS_DISALLOWED"
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                         timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 429:
            return r.status_code, "", "RATE_LIMITED"
        if r.status_code == 401 or r.status_code == 403:
            # Check for explicit block vs auth
            body = r.text[:2000].lower()
            if "captcha" in body or "access denied" in body or "blocked" in body:
                return r.status_code, "", "BLOCKED"
            return r.status_code, "", "AUTH_REQUIRED"
        if r.status_code >= 400:
            return r.status_code, "", "HTTP_ERROR"
        return r.status_code, r.text, None
    except Timeout:
        return 0, "", "TIMEOUT"
    except RequestException as e:
        msg = str(e).lower()
        if "timeout" in msg:
            return 0, "", "TIMEOUT"
        if "connection" in msg or "name resolution" in msg or "dns" in msg:
            return 0, "", "NETWORK"
        return 0, "", "NETWORK"

def _to_job(title: str, company: str, url: str, source: str, snippet: str = "", location: str = "Remote", jd_text: str = "") -> dict:
    return {
        "title": (title or "Unknown Role").strip()[:200],
        "company": (company or "Company unknown").strip()[:200],
        "url": url,
        "source": source,
        "location": location,
        "type": "fulltime",
        "hr_email": None,
        "description_snippet": (snippet or jd_text or "")[:1200],
        "jd_text": jd_text or snippet or "",
        "required_skills": [],
    }

def generic_html_adapter(source) -> Tuple[list[dict], str, str | None, int]:
    url = source.url
    status, html, cat = _http_get(url)
    if cat:
        return [], cat, f"HTTP {status} {cat}" if status else cat, 0
    if not html or len(html.strip()) < 80:
        return [], "NO_RESULTS", "Empty HTML", 0
    # Minimal parse: use BeautifulSoup if available else regex
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        # collect anchors that look like jobs
        jobs = []
        for a in soup.find_all("a", href=True)[:200]:
            href = a["href"].strip()
            t = a.get_text(" ", strip=True)
            if not t or len(t) < 8 or len(t) > 120:
                continue
            # need job-ish title and link
            if not any(k in t.lower() for k in ("engineer", "developer", "manager", "analyst", "intern", "designer", "scientist", "lead", "specialist")):
                # still allow if href looks like greenhouse/lever/job
                if not any(k in href.lower() for k in ("/jobs", "/careers", "greenhouse", "lever", "workable", "ashby")):
                    continue
            abs_url = urljoin(url, href)
            # host must be same or ATS
            try:
                uh = urlparse(abs_url).netloc.lower()
                sh = urlparse(url).netloc.lower()
                if uh and sh and uh != sh and "greenhouse" not in uh and "lever" not in uh and "workable" not in uh:
                    continue
            except Exception:
                pass
            jobs.append(_to_job(t, source.name, abs_url, source.host, snippet=t, jd_text=t))
            if len(jobs) >= 20:
                break
        if jobs:
            return jobs, "SUCCESS", None, len(jobs)
        # fallback: treat page as single listing if it looks like a JD
        if len(text) > 800 and any(k in text.lower() for k in ("responsibilities", "requirements", "qualifications", "about us")):
            title = soup.title.string.strip() if soup.title and soup.title.string else source.name
            return [_to_job(title, source.name, url, source.host, snippet=text[:1200], jd_text=text[:4000])], "SUCCESS", None, 1
        return [], "NO_RESULTS", "No job links found", 0
    except ImportError:
        # regex fallback
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{8,120})</a>', html, re.I)
        jobs = []
        for href, t in links[:80]:
            if len(t.strip()) < 8:
                continue
            abs_url = urljoin(url, href)
            jobs.append(_to_job(t.strip(), source.name, abs_url, source.host, snippet=t.strip()))
            if len(jobs) >= 15:
                break
        if jobs:
            return jobs, "SUCCESS", None, len(jobs)
        return [], "NO_RESULTS", "No job links (no bs4)", 0
    except Exception as e:
        return [], "PARSER_ERROR", str(e)[:500], 0

def rss_adapter(source) -> Tuple[list[dict], str, str | None, int]:
    url = source.url
    status, text, cat = _http_get(url)
    if cat:
        return [], cat, f"HTTP {status} {cat}" if status else cat, 0
    try:
        import feedparser
        feed = feedparser.parse(text)
        if feed.bozo and not feed.entries:
            return [], "PARSER_ERROR", str(feed.bozo_exception)[:500], 0
        jobs = []
        for e in feed.entries[:25]:
            title = getattr(e, "title", "") or ""
            link = getattr(e, "link", url) or url
            desc = getattr(e, "description", getattr(e, "summary", "")) or ""
            # strip html
            desc = re.sub(r"<[^>]+>", " ", desc)[:1200]
            jobs.append(_to_job(title, source.name, link, source.host, snippet=desc, jd_text=desc))
        if not jobs:
            return [], "NO_RESULTS", "Empty feed", 0
        # provider_raw is raw entry count before normalization
        return jobs, "SUCCESS", None, len(feed.entries[:25])
    except ImportError:
        # minimal xml regex fallback
        items = re.findall(r"<item[^>]*>(.*?)</item>", text, re.S | re.I)
        jobs = []
        for it in items[:25]:
            t = re.search(r"<title[^>]*>(.*?)</title>", it, re.S | re.I)
            l = re.search(r"<link[^>]*>(.*?)</link>", it, re.S | re.I)
            d = re.search(r"<description[^>]*>(.*?)</description>", it, re.S | re.I)
            title = re.sub(r"<[^>]+>", "", t.group(1)).strip() if t else "Unknown Role"
            link = re.sub(r"<[^>]+>", "", l.group(1)).strip() if l else url
            desc = re.sub(r"<[^>]+>", "", d.group(1)).strip()[:1200] if d else ""
            jobs.append(_to_job(title, source.name, link, source.host, snippet=desc, jd_text=desc))
        if not jobs:
            return [], "PARSER_ERROR", "feedparser not installed and regex found 0 items", 0
        return jobs, "SUCCESS", None, len(items[:25])
    except Exception as e:
        return [], "PARSER_ERROR", str(e)[:500], 0

def json_adapter(source) -> Tuple[list[dict], str, str | None, int]:
    url = source.url
    status, text, cat = _http_get(url)
    if cat:
        return [], cat, f"HTTP {status} {cat}" if status else cat, 0
    try:
        data = json.loads(text)
        # common shapes: list, {jobs: [...]}, {results: [...]}, Greenhouse {jobs: [...]}
        candidates = None
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            for k in ("jobs", "results", "data", "items", "listings", "positions"):
                if k in data and isinstance(data[k], list):
                    candidates = data[k]
                    break
            if candidates is None:
                # single job object
                if "title" in data and "company" in data or "title" in data:
                    candidates = [data]
        if not candidates:
            return [], "NO_RESULTS", "No job array in JSON", 0
        jobs = []
        for j in candidates[:25]:
            if not isinstance(j, dict):
                continue
            title = j.get("title") or j.get("name") or j.get("position") or "Unknown Role"
            company = j.get("company") or j.get("company_name") or j.get("organization") or source.name
            link = j.get("url") or j.get("absolute_url") or j.get("link") or j.get("apply_url") or url
            loc = j.get("location") or j.get("city") or "Remote"
            desc = j.get("description") or j.get("content") or j.get("snippet") or j.get("jd_text") or ""
            if isinstance(desc, str):
                desc = re.sub(r"<[^>]+>", " ", desc)[:1200]
            else:
                desc = ""
            jobs.append(_to_job(str(title), str(company), str(link), source.host, snippet=str(desc)[:1200], location=str(loc), jd_text=str(desc)))
        if not jobs:
            return [], "NO_RESULTS", "JSON array contained 0 mappable jobs", 0
        return jobs, "SUCCESS", None, len(candidates[:25])
    except json.JSONDecodeError as e:
        return [], "PARSER_ERROR", f"JSON decode: {e}", 0
    except Exception as e:
        return [], "PARSER_ERROR", str(e)[:500], 0

def ats_adapter(source) -> Tuple[list[dict], str, str | None, int]:
    url = source.url
    # Greenhouse: https://boards.greenhouse.io/embed/job_board?for=company  or https://boards-api.greenhouse.io/v1/board/company/jobs
    # Lever: https://api.lever.co/v0/postings/company?mode=json
    low = url.lower()
    try:
        if "greenhouse.io" in low:
            # extract company slug
            m = re.search(r"greenhouse\.io/(?:embed/job_board\?for=|boards/|v1/board/)([^/?&#]+)", low)
            company = m.group(1) if m else None
            # try company from source name or host subdomain
            if not company:
                # board.company.greenhouse.io -> company
                hm = re.match(r"([^.]+)\.greenhouse\.io", urlparse(url).netloc.lower())
                if hm:
                    company = hm.group(1)
            if not company:
                return [], "UNSUPPORTED", "Could not extract Greenhouse company slug from URL", 0
            api = f"https://boards-api.greenhouse.io/v1/board/{company}/jobs"
            status, text, cat = _http_get(api)
            if cat:
                return [], cat, f"Greenhouse API {status} {cat}" if status else cat, 0
            data = json.loads(text)
            jobs_raw = data.get("jobs", []) if isinstance(data, dict) else []
            jobs = []
            for j in jobs_raw[:25]:
                title = j.get("title") or "Unknown Role"
                loc = (j.get("location") or {}).get("name") if isinstance(j.get("location"), dict) else j.get("location") or "Remote"
                link = j.get("absolute_url") or url
                desc = j.get("content") or ""
                desc = re.sub(r"<[^>]+>", " ", desc)[:1200]
                jobs.append(_to_job(title, source.name, link, source.host, snippet=desc, location=str(loc), jd_text=desc))
            if not jobs:
                return [], "NO_RESULTS", "Greenhouse returned 0 jobs", 0
            return jobs, "SUCCESS", None, len(jobs_raw[:25])
        if "lever.co" in low:
            m = re.search(r"lever\.co/([^/?&#]+)", low)
            company = m.group(1) if m else None
            if not company:
                # jobs.lever.co/company -> path is /company
                path_parts = [p for p in urlparse(url).path.split("/") if p]
                if path_parts:
                    company = path_parts[0]
            if not company:
                return [], "UNSUPPORTED", "Could not extract Lever company slug", 0
            api = f"https://api.lever.co/v0/postings/{company}?mode=json&limit=25"
            status, text, cat = _http_get(api)
            if cat:
                return [], cat, f"Lever API {status} {cat}" if status else cat, 0
            data = json.loads(text)
            # Lever returns list
            lst = data if isinstance(data, list) else data.get("data") if isinstance(data, dict) else []
            jobs = []
            for j in (lst or [])[:25]:
                title = j.get("text") or j.get("title") or "Unknown Role"
                loc = j.get("categories", {}).get("location") or j.get("location") or "Remote"
                link = j.get("hostedUrl") or j.get("applyUrl") or j.get("url") or url
                desc = j.get("description") or j.get("descriptionPlain") or ""
                desc = re.sub(r"<[^>]+>", " ", desc)[:1200]
                jobs.append(_to_job(title, source.name, link, source.host, snippet=desc, location=str(loc), jd_text=desc))
            if not jobs:
                return [], "NO_RESULTS", "Lever returned 0 jobs", 0
            return jobs, "SUCCESS", None, len((lst or [])[:25])
        # generic ATS fallback: treat as JSON
        return json_adapter(source)
    except Exception as e:
        return [], "PARSER_ERROR", str(e)[:500], 0

# SearchAdapter wraps existing web_research_agent per-source site-filtered Tavily call
def search_adapter(source, profile: dict, resume_data: dict | None) -> Tuple[list[dict], str, str | None, int]:
    # For built-in search sources, we run a site-specific Tavily query (one host only)
    # Reuse _run_tavily + LLM extraction via agents pipeline but scoped to single host
    host = source.host
    # Build minimal query from resume/profile
    prefs = (profile or {}).get("job_preferences", {})
    roles = []
    skills: list[str] = []
    if resume_data:
        roles = resume_data.get("roles_json") or resume_data.get("roles") or []
        skills = resume_data.get("skills_json") or resume_data.get("skills") or []
        if not roles:
            parsed = resume_data.get("parsed_json") or {}
            roles = parsed.get("roles", [])
        if not skills:
            parsed = resume_data.get("parsed_json") or {}
            skills = parsed.get("skills", [])
    if not roles:
        roles = prefs.get("target_roles", ["Software Engineer"])
    if not skills:
        sd = (profile or {}).get("skills", {})
        skills = (sd.get("languages", []) + sd.get("frameworks", []) + sd.get("tools", []))[:10]
    def _role_name(r): return r.get("role", "") if isinstance(r, dict) else r
    role_str = " OR ".join(f'"{_role_name(r)}"' for r in roles[:3] if _role_name(r))
    skill_str = " ".join(skills[:6])
    loc = (prefs.get("target_locations") or ["Remote"])[0]
    query = f"({role_str}) {skill_str} {loc} jobs hiring now (site:{host})"
    try:
        from agents.web_research_agent import _run_tavily
        from utils.llm_client import get_llm
        import json as _json
        import re as _re
        import ast as _ast
        def _local_parse(text: str):
            t = text.strip()
            if "```" in t:
                m = _re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
                if m:
                    t = m.group(1).strip()
            # try JSON
            try:
                data = _json.loads(t)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, list):
                            return v
                    return [data]
            except Exception:
                pass
            # try array extract
            m = _re.search(r"\[\s*\{[\s\S]*\}\s*\]", t)
            if m:
                try:
                    return _json.loads(m.group(0))
                except Exception:
                    pass
            # try ast literal_eval for Python repr (tests)
            try:
                data = _ast.literal_eval(t)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except Exception:
                pass
            return []
        # Respect missing key -> UNSUPPORTED
        import os
        if not os.getenv("TAVILY_API_KEY"):
            return [], "AUTH", "TAVILY_API_KEY not configured", 0, []
        results = _run_tavily(query)
        provider_raw = len(results) if isinstance(results, list) else 0
        if not results:
            return [], "NO_RESULTS", "Tavily returned 0 results", provider_raw, []
        llm = get_llm()
        # Build LLM extraction like _extract_job_listings but capture provider_attempts
        # Replicate _extract_job_listings to keep observability
        results_text = "\n\n".join(
            f"[{i+1}] URL: {r.get('url', 'N/A')}\n"
            f"Title: {r.get('title', 'N/A')}\n"
            f"Snippet: {r.get('content', r.get('snippet', ''))[:400]}"
            for i, r in enumerate(results[:8])
        )
        system_prompt = """You are a job listing extractor.
Given raw search results, extract ONLY actual job postings (not articles or blogs).
Return a JSON array. Each object must have these exact keys:
{
  "title": "Job title",
  "company": "Company name",
  "location": "City or Remote",
  "url": "Direct job URL",
  "source": "linkedin|internshala|naukri|wellfound|other",
  "type": "fulltime|internship|contract",
  "hr_email": null,
  "description_snippet": "1-2 sentence summary of the role",
  "required_skills": ["skill1", "skill2"]
}
If you cannot extract a real job listing from a result, skip it.
Return ONLY the JSON array, no other text."""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Extract job listings from these results:\n\n{results_text}")]
        except Exception:
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Extract job listings from these results:\n\n{results_text}"}]
        try:
            response = llm.invoke(messages, max_tokens=4000)
        except Exception:
            response = llm.invoke(messages)
        raw_json = getattr(response, "content", str(response)).strip() if hasattr(response, "content") else str(response).strip()
        provider_attempts = getattr(response, "provider_attempts", [])
        listings = _local_parse(raw_json)
        if not listings:
            return [], "NO_RESULTS", "LLM extracted 0 jobs", provider_raw, provider_attempts
        # normalize to standard shape
        out = []
        for j in listings[:15]:
            out.append(_to_job(j.get("title","Unknown Role"), j.get("company","Company unknown"),
                               j.get("url", f"https://{host}"), host,
                               snippet=j.get("description_snippet","")[:1200],
                               location=j.get("location","Remote"),
                               jd_text=j.get("description_snippet","") ))
            out[-1]["required_skills"] = j.get("required_skills", [])
            out[-1]["type"] = j.get("type", "fulltime")
        return out, "SUCCESS", None, provider_raw, provider_attempts
    except Exception as e:
        # Preserve highest-confidence failure taxonomy without exposing secrets
        # Use gateway exception hierarchy when available, else fallback to message heuristics
        # Capture per-provider attempts if available
        _pa = getattr(e, "provider_attempts", [])
        if not isinstance(_pa, list):
            _pa = []
        try:
            from core.ai.errors import (
                RateLimitError as _RL, TimeoutError as _TO, AuthenticationError as _AE,
                PaymentRequiredError as _PAY, ProviderUnavailableError as _PU, sanitize_exception_message as _san,
            )
            safe = _san(str(e))[:500]
            if isinstance(e, _RL):
                return [], "RATE_LIMITED", safe, 0, _pa
            if isinstance(e, _TO):
                return [], "TIMEOUT", safe, 0, _pa
            if isinstance(e, _AE):
                return [], "AUTH", safe, 0, _pa
            if isinstance(e, _PAY):
                return [], "PAYMENT_REQUIRED", safe, 0, _pa
            if isinstance(e, _PU):
                # Distinguish rate-limit wrapped as ProviderUnavailable with 429 hint
                low = str(e).lower()
                if "429" in low or "rate" in low or "quota" in low:
                    return [], "RATE_LIMITED", safe, 0, _pa
                if "timeout" in low:
                    return [], "TIMEOUT", safe, 0, _pa
                if "402" in low or "payment" in low:
                    return [], "PAYMENT_REQUIRED", safe, 0, _pa
                return [], "PROVIDER_ERROR", safe, 0, _pa
        except Exception:
            pass
        # Fallback heuristics (do NOT infer RATE_LIMITED merely from multi-provider failure)
        try:
            from core.ai.errors import sanitize_exception_message as _san2
            safe2 = _san2(str(e))[:500]
        except Exception:
            safe2 = str(e)[:500]
        msg = str(e).lower()
        if "tavily" in msg and "api key" in msg:
            return [], "AUTH", safe2, 0, _pa
        if "timeout" in msg:
            return [], "TIMEOUT", safe2, 0, _pa
        if "rate" in msg and ("429" in msg or "quota" in msg or "rate limit" in msg):
            return [], "RATE_LIMITED", safe2, 0, _pa
        if "402" in msg or "payment" in msg:
            return [], "PAYMENT_REQUIRED", safe2, 0, _pa
        if "auth" in msg or "401" in msg or "403" in msg:
            return [], "AUTH", safe2, 0, _pa
        # Generic provider/availability without stronger evidence
        if "connection" in msg or "provider" in msg or "unavailable" in msg or "5" in msg:
            # If insufficient evidence for RATE_LIMITED/TIMEOUT/AUTH, use PROVIDER_ERROR
            if "all ai providers unavailable" in msg:
                # Ambiguous multi-provider exhaustion — keep as PROVIDER_ERROR (not RATE_LIMITED) per spec
                return [], "PROVIDER_ERROR", safe2, 0, _pa
            return [], "PROVIDER_ERROR", safe2, 0, _pa
        return [], "UNKNOWN", safe2, 0, _pa

def dispatch(source, profile: dict | None = None, resume_data: dict | None = None) -> Tuple[list[dict], str, str | None, int, list]:
    """Dispatch to correct adapter based on source.adapter / source_type. Returns (jobs, cat, err, provider_raw, provider_attempts)."""
    def _norm(res):
        # Normalize adapter result to 5-tuple (jobs, cat, err, provider_raw, provider_attempts) for backward compat with mocks returning 3/4-tuple
        if isinstance(res, tuple):
            if len(res) == 5:
                return res  # type: ignore
            if len(res) == 4:
                jobs, cat, err, pr = res  # type: ignore
                return (jobs, cat, err, pr, [])
            if len(res) == 3:
                jobs, cat, err = res  # type: ignore
                # provider_raw best effort: len(jobs) if success else 0
                try:
                    pr = len(jobs) if isinstance(jobs, list) and cat in ("SUCCESS", "NO_RESULTS") else 0
                except Exception:
                    pr = 0
                return (jobs, cat, err, pr, [])
        # fallback
        return ([], "UNKNOWN", "Invalid adapter result", 0, [])
    adapter = (source.adapter or "").lower()
    if "search" in adapter:
        return _norm(search_adapter(source, profile or {}, resume_data))
    if "rss" in adapter:
        return _norm(rss_adapter(source))
    if "json" in adapter:
        return _norm(json_adapter(source))
    if "ats" in adapter:
        return _norm(ats_adapter(source))
    if "generic" in adapter or "html" in adapter:
        return _norm(generic_html_adapter(source))
    # fallback by source_type
    st = (source.source_type or "").lower()
    if st == "rss":
        return _norm(rss_adapter(source))
    if st == "json":
        return _norm(json_adapter(source))
    if st == "ats":
        return _norm(ats_adapter(source))
    if st == "search":
        return _norm(search_adapter(source, profile or {}, resume_data))
    return _norm(generic_html_adapter(source))

def _mode_to_adapter(mode: str) -> str:
    m = (mode or "AUTO").upper()
    if m == "HTML":
        return "GenericHTMLAdapter"
    if m == "RSS":
        return "RSSAdapter"
    if m == "JSON":
        return "JSONAdapter"
    if m == "ATS":
        return "ATSAdapter"
    if m == "SEARCH":
        return "SearchAdapter"
    if m == "PLAYWRIGHT":
        return "PlaywrightAdapter"
    return "GenericHTMLAdapter"

def dispatch_with_policy(source, profile: dict | None = None, resume_data: dict | None = None) -> tuple[list[dict], str, str | None, str, bool, str | None, int, list]:
    """
    Source-aware dispatch (010): uses source_role/primary_mode/direct_fetch_allowed/search_discovery_allowed.
    Returns (jobs, failure_category, error, actual_mode, fallback_used, primary_failure, provider_raw_count, provider_attempts)
    Truthful mode, no hidden fallback. provider_raw_count is raw Tavily count for SEARCH, or raw feed count for others.
    provider_attempts is list of {provider, attempts, final_category} for observability.
    """
    # Determine policy (fallback to derived if DB columns missing)
    try:
        role = getattr(source, "source_role", "UNKNOWN") or "UNKNOWN"
        primary = getattr(source, "primary_mode", "AUTO") or "AUTO"
        direct_allowed = bool(getattr(source, "direct_fetch_allowed", True))
        search_allowed = bool(getattr(source, "search_discovery_allowed", True))
    except Exception:
        role, primary, direct_allowed, search_allowed = "UNKNOWN", "AUTO", True, True

    # Normalize primary
    primary = primary.upper() if isinstance(primary, str) else "AUTO"
    if primary == "AUTO":
        # Auto: infer from role/source_type
        if role == "JOB_BOARD":
            primary = "SEARCH"
        elif role == "ATS":
            primary = "ATS"
        elif role == "FEED":
            # FEED could be RSS or JSON, keep original adapter's mode
            primary = (getattr(source, "source_type", "") or "RSS").upper()
            if primary not in ("RSS","JSON"):
                primary = "RSS"
        elif role == "EMPLOYER":
            primary = "HTML"
        else:
            # CUSTOM/UNKNOWN: try HTML if direct allowed, else SEARCH
            primary = "HTML" if direct_allowed else "SEARCH"

    # If direct disallowed and primary is direct mode, switch to SEARCH if allowed
    if not direct_allowed and primary in ("HTML","PLAYWRIGHT"):
        if search_allowed:
            primary = "SEARCH"
        else:
            return [], "ROBOTS_DISALLOWED", "Direct fetch disabled by policy", primary, False, None, 0, []

    # If search disallowed and primary is SEARCH, and direct not allowed -> UNSUPPORTED
    if not search_allowed and primary == "SEARCH" and not direct_allowed:
        return [], "UNSUPPORTED", "Search discovery disabled by policy", primary, False, None, 0, []

    # Choose adapter for primary
    primary_adapter = _mode_to_adapter(primary)
    # Build a temporary source-like object with overridden adapter for dispatch
    class _Tmp:
        pass
    tmp = _Tmp()
    tmp.url = source.url
    tmp.host = getattr(source, "host", "")
    tmp.name = getattr(source, "name", "")
    tmp.adapter = primary_adapter
    tmp.source_type = primary.lower()
    # Execute primary — dispatch now returns (jobs, cat, err, provider_raw, provider_attempts)
    _r = dispatch(tmp, profile, resume_data)  # type: ignore
    if isinstance(_r, tuple) and len(_r) == 5:
        jobs, cat, err, provider_raw, provider_attempts = _r  # type: ignore
    elif isinstance(_r, tuple) and len(_r) == 4:
        jobs, cat, err, provider_raw = _r  # type: ignore
        provider_attempts = []
    elif isinstance(_r, tuple) and len(_r) == 3:
        jobs, cat, err = _r  # type: ignore
        provider_raw = len(jobs) if isinstance(jobs, list) and cat in ("SUCCESS", "NO_RESULTS") else 0
        provider_attempts = []
    else:
        jobs, cat, err, provider_raw, provider_attempts = [], "UNKNOWN", "Invalid dispatch result", 0, []
    actual_mode = primary
    fallback_used = False
    primary_failure = None

    # Fallback only if primary failed and search fallback explicitly allowed and primary was direct/structured
    if cat not in ("SUCCESS","NO_RESULTS") or not jobs:
        # Consider fallback only for meaningful failures, not for NO_RESULTS (which is not failure)
        should_fallback = False
        if cat in ("PARSER_ERROR","HTTP_ERROR","BLOCKED","ROBOTS_DISALLOWED","TIMEOUT","NETWORK","UNKNOWN","UNSUPPORTED","AUTH","PAYMENT_REQUIRED","PROVIDER_ERROR"):
            should_fallback = True
        # Also fallback if SUCCESS but 0 jobs and primary was HTML with search allowed? But NO_RESULTS is not failure, don't fallback
        if should_fallback and search_allowed and primary in ("HTML","RSS","JSON","ATS","PLAYWRIGHT") and cat != "NO_RESULTS":
            # Wellfound direct false already handled, so here direct was allowed but failed
            # Try SEARCH as fallback
            primary_failure = cat
            fallback_mode = "SEARCH"
            fallback_adapter = "SearchAdapter"
            tmp2 = _Tmp()
            tmp2.url = source.url
            tmp2.host = getattr(source, "host", "")
            tmp2.name = getattr(source, "name", "")
            tmp2.adapter = fallback_adapter
            tmp2.source_type = "search"
            _r2 = dispatch(tmp2, profile, resume_data)  # type: ignore
            if isinstance(_r2, tuple) and len(_r2) == 5:
                jobs2, cat2, err2, provider_raw2, provider_attempts2 = _r2  # type: ignore
            elif isinstance(_r2, tuple) and len(_r2) == 4:
                jobs2, cat2, err2, provider_raw2 = _r2  # type: ignore
                provider_attempts2 = []
            elif isinstance(_r2, tuple) and len(_r2) == 3:
                jobs2, cat2, err2 = _r2  # type: ignore
                provider_raw2 = len(jobs2) if isinstance(jobs2, list) and cat2 in ("SUCCESS", "NO_RESULTS") else 0
                provider_attempts2 = []
            else:
                jobs2, cat2, err2, provider_raw2, provider_attempts2 = [], "UNKNOWN", "Invalid dispatch result", 0, []
            # Record fallback truthfully
            actual_mode = fallback_mode
            fallback_used = True
            provider_raw = provider_raw2
            provider_attempts = provider_attempts2
            # If fallback succeeded, return its result with fallback flag
            if cat2 in ("SUCCESS","NO_RESULTS"):
                return jobs2, cat2, err2, actual_mode, fallback_used, primary_failure, provider_raw, provider_attempts
            # If fallback also failed, return fallback result but preserve primary_failure
            return jobs2, cat2, err2, actual_mode, fallback_used, primary_failure, provider_raw, provider_attempts

    # No fallback, return primary result
    return jobs, cat, err, actual_mode, fallback_used, primary_failure, provider_raw, provider_attempts
