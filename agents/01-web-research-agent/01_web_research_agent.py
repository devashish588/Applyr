"""
Web Research Agent — AutoApply AI
Searches for jobs/internships matching your profile and returns
structured listings ready for the next pipeline stage.

Usage:
    python 01_web_research_agent.py
    python 01_web_research_agent.py --query "Python backend developer internship Bangalore"
    python 01_web_research_agent.py --profile ./profile.json
"""

import argparse
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ── Groq (replaces OpenAI) ────────────────────────────────────────────────────

# ── Tavily ────────────────────────────────────────────────────────────────────
from langchain_tavily import TavilySearch

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

logger = logging.getLogger(__name__)

# ── Groq client (loaded once) ─────────────────────────────────────────────────
# Ensure the project root is on the import path so that ``utils`` can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.llm_client import get_llm


# ── State ─────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict):
    messages:       Annotated[list, add_messages]
    query:          str          # raw search query
    profile:        dict         # loaded from profile.json
    resume_data:    dict         # parsed resume data from DB (optional)
    search_results: list[dict]   # raw Tavily results
    job_listings:   list[dict]   # parsed, structured job objects
    report:         str          # human-readable summary
    fallback_used:  bool         # explicit provider/site fallback flag


# ── Company-name fallback helpers (Bug 2) ────────────────────────────────────
_BAD_COMPANY = {"", "none", "null", "n/a", "na", "unknown", "unknown company",
                "company not found", "company not extracted", "not extracted"}
# Major aggregators where the domain is NEVER the employer → fall back to the
# job title instead. Smaller niche boards (arc.dev, wellfound, builtin…) are left
# off so their domain label is used as a reasonable name (per the arc.dev → "Arc"
# spec) rather than being flagged for review.
_JOB_BOARDS = {"linkedin", "indeed", "glassdoor", "ziprecruiter", "dice", "monster",
               "simplyhired", "naukri", "jora", "talent", "google", "bing"}
_ATS_HOSTS = {"greenhouse", "lever", "workable", "ashbyhq", "myworkdayjobs",
              "bamboohr", "jobvite", "smartrecruiters", "breezy", "recruitee"}
_ROLE_WORDS = re.compile(
    r"(?i)\b(engineer|developer|manager|designer|analyst|intern|lead|architect|"
    r"scientist|consultant|specialist|administrator|director|officer)\b")

# Rotating pool of job sources. build_query() samples 3 each run so the Tavily
# query — and therefore the results — vary between runs (fixes the "same top-10
# every run" problem). 10+ entries as specified.
_JOB_SITE_POOL = [
    "linkedin.com/jobs", "wellfound.com", "indeed.com", "ycombinator.com",
    "weworkremotely.com", "remoteok.com", "builtin.com", "dice.com",
    "glassdoor.com", "naukri.com", "remotive.com", "arc.dev",
]


def _company_from_title(title: str):
    """Pull a company name out of a job title like 'Role at Company' or 'Company - Role'."""
    if not title:
        return None
    m = re.search(r"\bat\s+([A-Z][\w&.\-'’ ]{1,40}?)\s*$", title.strip())
    if m:
        return m.group(1).strip(" -–—")
    for sep in (" - ", " – ", " — ", " | ", " @ "):
        if sep in title:
            chunks = [c.strip() for c in title.split(sep) if c.strip()]
            # Title may be "Company - Role" or "Role - Company"; pick the side
            # that doesn't read like a role.
            for chunk in (chunks[0], chunks[-1]):
                if chunk and len(chunk) <= 40 and not _ROLE_WORDS.search(chunk):
                    return chunk
    return None


def _company_from_url(url: str, title: str = ""):
    """Derive a company name from the job URL's domain, falling back to the title."""
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).netloc or "").lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        parts = [p for p in host.split(".") if p]
        if not parts:
            return _company_from_title(title)
        # ATS sub-domains: company.greenhouse.io, company.lever.co, company.workable.com
        if len(parts) >= 3 and parts[-2] in _ATS_HOSTS:
            sub = parts[0]
            if sub not in ("jobs", "boards", "apply", "careers", "www", "app"):
                return sub.replace("-", " ").title()
        label = parts[-2] if len(parts) >= 2 else parts[0]
        if label in _JOB_BOARDS or label in _ATS_HOSTS:
            return _company_from_title(title)
        # Direct company domain, e.g. stripe.com/jobs → Stripe
        return label.replace("-", " ").title()
    except Exception:
        return _company_from_title(title)


# ── Node 1: build a smart query from profile + resume ────────────────────────
def build_query(state: ResearchState) -> ResearchState:
    """
    Build search query from resume-extracted roles and skills.
    Falls back to profile.json ONLY if no resume data is available.
    """
    if state.get("query"):
        return state

    profile = state.get("profile", {})
    resume_data = state.get("resume_data") or {}
    prefs = profile.get("job_preferences", {})

    # Priority 1: resume-extracted roles
    roles = resume_data.get("roles_json", []) or resume_data.get("roles", [])
    # Priority 2: inferred roles from resume
    if not roles:
        parsed = resume_data.get("parsed_json", {}) or resume_data.get("parsed", {})
        roles = parsed.get("roles", [])
    # Priority 3: profile target_roles (no resume parsed yet)
    if not roles:
        roles = prefs.get("target_roles", ["Software Engineer"])

    # Priority 1: resume-extracted skills
    skills = resume_data.get("skills_json", []) or resume_data.get("skills", [])
    if not skills:
        parsed = resume_data.get("parsed_json", {}) or resume_data.get("parsed", {})
        skills = parsed.get("skills", [])
    if not skills:
        skill_dict = profile.get("skills", {})
        skills = (skill_dict.get("languages", []) + skill_dict.get("frameworks", []) + skill_dict.get("tools", []))[:10]

    locs = prefs.get("target_locations", ["Remote"])

    # Resume-extracted roles arrive as dicts like {"role": "backend engineer", "score": 98.6};
    # profile/target_roles arrive as plain strings. Normalize to the role name either way.
    def _role_name(r):
        return r.get("role", "") if isinstance(r, dict) else r

    role_str = " OR ".join(f'"{_role_name(r)}"' for r in roles[:4] if _role_name(r))
    skill_str = " ".join(skills[:8])
    loc_str = locs[0] if locs else "Remote"

    # Bug 2 (+ hardening): vary the query each run so Tavily doesn't return an
    # identical top-10.
    #   (a) sample 3 source sites from a rotating pool,
    #   (b) append a rotating time phrase (current month-year or "hiring now"),
    #   (c) drop the stale hardcoded year.
    # If this site-filtered query extracts 0 jobs, parse_jobs retries once
    # without the site: filter (see parse_jobs).
    sites = random.sample(_JOB_SITE_POOL, 3)
    site_filter = " OR ".join(f"site:{s}" for s in sites)

    now = datetime.now()
    time_phrases = [
        "hiring now",
        now.strftime("%B %Y"),     # e.g. "June 2026"
        f"jobs {now.year}",
        "actively hiring",
        "new openings",
        "urgent hiring",
    ]
    time_phrase = random.choice(time_phrases)

    query = f"({role_str}) {skill_str} {loc_str} jobs {time_phrase} ({site_filter})"

    print(f"[web_research] Resume-driven query: {query}")
    print(f"[web_research] Roles: {roles[:4]} | Skills: {skills[:8]} | "
          f"Sites: {sites} | Phrase: {time_phrase!r}")
    return {"query": query}


# ── Tavily search (shared helper) ─────────────────────────────────────────────
def _run_tavily(query: str) -> list[dict]:
    """Run a single Tavily search and normalize the result shape to a list."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        raise EnvironmentError(
            "TAVILY_API_KEY not found in .env — "
            "get yours free at https://app.tavily.com"
        )

    # "advanced" depth returns a richer, less repetitive result set than "basic".
    tool        = TavilySearch(max_results=10, search_depth="advanced")
    raw_results = tool.invoke(query)

    # Tavily can return dict or list depending on version
    if isinstance(raw_results, dict):
        return raw_results.get("results", [])
    if isinstance(raw_results, list):
        return raw_results
    return []


# ── Node 2: search the web ────────────────────────────────────────────────────
def search_web(state: ResearchState) -> ResearchState:
    results = _run_tavily(state["query"])
    print(f"[web_research] Found {len(results)} raw results")
    return {"search_results": results}


def _parse_json_safely(raw_text: str) -> list[dict]:
    """Robustly parse JSON array from LLM response, even if wrapped in markdown or partially truncated."""
    if not raw_text:
        return []
    
    text = raw_text.strip()
    
    # Strip markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        else:
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()

    # 1. Direct json load
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
            return [data]
    except Exception:
        pass

    # 2. Extract array string [...]
    array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    # 3. Truncated JSON repair: find all completed job objects {...}
    objects = []
    obj_matches = re.findall(r"\{\s*\"title\"[\s\S]*?\n\s*\}", text)
    for obj_str in obj_matches:
        try:
            obj = json.loads(obj_str)
            if isinstance(obj, dict) and "title" in obj:
                objects.append(obj)
        except Exception:
            continue
            
    if objects:
        return objects

    # 4. Truncated array repair: truncate at last complete object
    last_brace = text.rfind("}")
    if last_brace != -1:
        repaired = text[:last_brace+1] + "]"
        first_bracket = repaired.find("[")
        if first_bracket != -1:
            repaired = repaired[first_bracket:]
        else:
            repaired = "[" + repaired[repaired.find("{"):]
        try:
            data = json.loads(repaired)
            if isinstance(data, list):
                return data
        except Exception:
            pass

    return []


# ── LLM extraction (shared helper) ────────────────────────────────────────────
def _extract_job_listings(results: list[dict], llm) -> list[dict]:
    """LLM-extract structured job listings from raw Tavily results."""
    if not results:
        return []

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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Extract job listings from these results:\n\n{results_text}"),
    ]

    try:
        response = llm.invoke(messages, max_tokens=4000)
    except Exception:
        response = llm.invoke(messages)

    raw_json = response.content.strip()
    job_listings = _parse_json_safely(raw_json)
    
    if not job_listings:
        print(f"[web_research] Could not parse JSON array, raw text preview: {raw_json[:200]!r}")

    return job_listings


# ── Node 3: parse results into job objects ────────────────────────────────────
def parse_jobs(state: ResearchState) -> ResearchState:
    """
    Use LLM to extract structured job listings from raw search snippets.
    Returns a list of dicts ready to insert into applications.db.
    """
    llm = get_llm()
    query = state.get("query", "")
    job_listings = _extract_job_listings(state.get("search_results", []), llm)
    fallback_used = False

    # Bug 2 hardening: if a site-filtered query produced nothing extractable
    # (e.g. the sampled sites only returned category/search pages), retry ONCE
    # with the site: filter stripped — a broader query that reliably yields
    # postings. Prevents 0-job runs.
    if not job_listings and "site:" in query:
        broad_query = re.sub(r"\s*\(site:[^)]*\)", "", query).strip()
        logger.warning(
            "[web_research] 0 jobs extracted from site-filtered query — "
            "retrying once without the site: filter"
        )
        print(f"[web_research] Retry (broadened) query: {broad_query}")
        broad_results = _run_tavily(broad_query)
        print(f"[web_research] Found {len(broad_results)} raw results (retry)")
        job_listings = _extract_job_listings(broad_results, llm)
        fallback_used = True

    # Post-process (Bug 5): never insert a literal "Unknown Company".
    # 3-step fallback when the LLM didn't return a usable company name:
    #   (a) domain from the job URL, minus known job-board domains,
    #   (b) "at <Company>" / "<Company> - Role" parsed from the title,
    #   (c) else "Company unknown" + needs_review=True for human follow-up.
    # Steps (a) and (b) are both handled inside _company_from_url(url, title).
    for job in job_listings:
        company = str(
            job.get("company") or job.get("organization") or job.get("employer") or ""
        ).strip()

        if not company or company.lower() in _BAD_COMPANY:
            company = str(_company_from_url(job.get("url", ""), job.get("title", "")) or "").strip()

        if not company or company.lower() in _BAD_COMPANY:
            company = "Company unknown"
            job["needs_review"] = True

        job["company"] = company

    print(f"[web_research] Extracted {len(job_listings)} structured job listings (fallback={fallback_used})")
    return {
        "job_listings": job_listings,
        "fallback_used": fallback_used,
        "messages": [AIMessage(content=f"Extracted {len(job_listings)} job listings")],
    }


# ── Node 4: generate human-readable report ────────────────────────────────────
def generate_report(state: ResearchState) -> ResearchState:
    llm      = get_llm()
    listings = state.get("job_listings", [])

    if not listings:
        report = "No job listings found for this query. Try broadening your search."
        return {"report": report}

    listings_text = "\n\n".join(
        f"{i+1}. {j.get('title')} at {j.get('company')} "
        f"({j.get('location')}) — {j.get('type')}\n"
        f"   Skills: {', '.join(j.get('required_skills', []))}\n"
        f"   URL: {j.get('url')}"
        for i, j in enumerate(listings)
    )

    profile  = state.get("profile", {})
    my_skills = profile.get("skills", {}).get("languages", []) + \
                profile.get("skills", {}).get("frameworks", [])

    messages = [
        SystemMessage(content=(
            "You are a career advisor. Given a list of job listings and the "
            "candidate's skills, write a brief summary: how many listings found, "
            "which look like the best fits and why, and any notable companies."
        )),
        HumanMessage(content=(
            f"My skills: {', '.join(my_skills[:8])}\n\n"
            f"Job listings found:\n{listings_text}"
        )),
    ]

    response = llm.invoke(messages)
    return {"report": response.content, "messages": [AIMessage(content=response.content)]}


# ── Graph ─────────────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("build_query",     build_query)
    graph.add_node("search",          search_web)
    graph.add_node("parse_jobs",      parse_jobs)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("build_query")
    graph.add_edge("build_query",     "search")
    graph.add_edge("search",          "parse_jobs")
    graph.add_edge("parse_jobs",      "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AutoApply — Web Research Agent")
    parser.add_argument("--query",   default="",             help="Manual search query (optional)")
    parser.add_argument("--profile", default="./profile.json", help="Path to profile.json")
    args = parser.parse_args()

    # Load profile
    profile = {}
    if os.path.exists(args.profile):
        with open(args.profile) as f:
            profile = json.load(f)
        print(f"[web_research] Loaded profile: {profile.get('personal', {}).get('name', 'Unknown')}")
    else:
        print(f"[web_research] Warning: profile not found at {args.profile}")

    print(f"\n🔍 Starting job search...\n")

    agent  = build_graph()
    result = agent.invoke({
        "query":          args.query,
        "profile":        profile,
        "messages":       [],
        "search_results": [],
        "job_listings":   [],
        "report":         "",
    })

    # ── Print report ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📄 JOB SEARCH REPORT")
    print("=" * 60)
    print(result["report"])

    # ── Print structured listings ─────────────────────────────────────────────
    listings = result.get("job_listings", [])
    if listings:
        print(f"\n{'=' * 60}")
        print(f"📋 {len(listings)} STRUCTURED LISTINGS (ready for pipeline)")
        print("=" * 60)
        for i, job in enumerate(listings, 1):
            print(f"\n{i}. {job.get('title')} — {job.get('company')}")
            print(f"   📍 {job.get('location')}  |  {job.get('type')}")
            print(f"   🔗 {job.get('url')}")
            print(f"   🛠  {', '.join(job.get('required_skills', []))}")
            if job.get("hr_email"):
                print(f"   📧 {job.get('hr_email')}")

    return result  # pipeline: next agent receives result["job_listings"]


if __name__ == "__main__":
    main()
