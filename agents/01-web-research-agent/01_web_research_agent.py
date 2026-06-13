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
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ── Groq (replaces OpenAI) ────────────────────────────────────────────────────
from langchain_groq import ChatGroq

# ── Tavily ────────────────────────────────────────────────────────────────────
from langchain_tavily import TavilySearch

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

# ── Groq client (loaded once) ─────────────────────────────────────────────────
def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    model   = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found in .env — "
            "get yours free at https://console.groq.com"
        )

    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0,
    )


# ── State ─────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict):
    messages:       Annotated[list, add_messages]
    query:          str          # raw search query
    profile:        dict         # loaded from profile.json
    search_results: list[dict]   # raw Tavily results
    job_listings:   list[dict]   # parsed, structured job objects
    report:         str          # human-readable summary


# ── Node 1: build a smart query from profile ──────────────────────────────────
def build_query(state: ResearchState) -> ResearchState:
    """
    If a manual query was passed in, use it.
    Otherwise build one from profile.json target_roles + skills.
    """
    if state.get("query"):
        return state  # manual query takes priority

    profile = state.get("profile", {})
    prefs   = profile.get("job_preferences", {})
    roles   = prefs.get("target_roles", ["software developer"])
    skills  = profile.get("skills", {}).get("languages", [])[:3]
    locs    = prefs.get("locations", ["remote"])

    role_str  = " OR ".join(f'"{r}"' for r in roles[:2])
    skill_str = " ".join(skills)
    loc_str   = locs[0] if locs else "remote"

    query = f"({role_str}) {skill_str} jobs internships {loc_str} 2024 site:linkedin.com OR site:internshala.com OR site:naukri.com"

    print(f"[web_research] Auto-built query: {query}")
    return {"query": query}


# ── Node 2: search the web ────────────────────────────────────────────────────
def search_web(state: ResearchState) -> ResearchState:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        raise EnvironmentError(
            "TAVILY_API_KEY not found in .env — "
            "get yours free at https://app.tavily.com"
        )

    tool        = TavilySearch(max_results=10)
    raw_results = tool.invoke(state["query"])

    # Tavily can return dict or list depending on version
    if isinstance(raw_results, dict):
        results = raw_results.get("results", [])
    elif isinstance(raw_results, list):
        results = raw_results
    else:
        results = []

    print(f"[web_research] Found {len(results)} raw results")
    return {"search_results": results}


# ── Node 3: parse results into job objects ────────────────────────────────────
def parse_jobs(state: ResearchState) -> ResearchState:
    """
    Use LLM to extract structured job listings from raw search snippets.
    Returns a list of dicts ready to insert into applications.db.
    """
    llm = get_llm()

    results_text = "\n\n".join(
        f"[{i+1}] URL: {r.get('url', 'N/A')}\n"
        f"Title: {r.get('title', 'N/A')}\n"
        f"Snippet: {r.get('content', r.get('snippet', ''))[:600]}"
        for i, r in enumerate(state["search_results"])
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
  "hr_email": "HR email if found, else null",
  "description_snippet": "2-3 sentence summary of the role",
  "required_skills": ["skill1", "skill2"]
}
If you cannot extract a real job listing from a result, skip it.
Return ONLY the JSON array, no other text."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Extract job listings from these results:\n\n{results_text}"),
    ]

    response  = llm.invoke(messages)
    raw_json  = response.content.strip()

    # Strip markdown fences if LLM wraps in ```json
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]
    raw_json = raw_json.strip()

    try:
        job_listings = json.loads(raw_json)
        if not isinstance(job_listings, list):
            job_listings = []
    except json.JSONDecodeError as e:
        print(f"[web_research] JSON parse error: {e}")
        job_listings = []

    print(f"[web_research] Extracted {len(job_listings)} structured job listings")
    return {"job_listings": job_listings, "messages": [response]}


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
    return {"report": response.content, "messages": [response]}


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