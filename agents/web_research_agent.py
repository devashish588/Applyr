"""
Web Research Agent - Discovers job listings using Tavily Search + Groq LLM.

Searches the web for jobs matching user profile, parses results into
structured job records for the pipeline.

Adapted from user's LangGraph agent to work within Applyr pipeline.
"""
import os
import sys
import logging
import re
from typing import Annotated, TypedDict, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from utils.llm_client import get_llm, parse_json_response

logger = logging.getLogger(__name__)


# ─── LangGraph State ────────────────────────────────────────────────
class JobSearchState(TypedDict):
    messages: Annotated[list, add_messages]
    queries: list[str]
    search_results: list[dict]
    jobs: list[dict]


# ─── Graph Nodes ────────────────────────────────────────────────────
def generate_search_queries(state: JobSearchState) -> dict:
    """Use LLM to generate targeted job search queries from user profile."""
    llm = get_llm(temperature=0)
    profile_text = state.get("profile_text", "")
    messages = [
        SystemMessage(content="""You are a job search expert. Given a candidate profile, 
generate 5 specific search queries to find relevant jobs. Return a JSON array of strings.
Focus on: role titles + locations + key skills. Example:
["Python developer remote jobs 2024", "backend engineer startup hiring"]
Return ONLY the JSON array."""),
        HumanMessage(content=f"Candidate profile:\n{profile_text}")
    ]
    response = llm.invoke(messages)
    try:
        queries = parse_json_response(response.content)
        if isinstance(queries, dict) and "items" in queries:
            queries = queries["items"]
    except Exception:
        queries = [
            "software engineer remote jobs hiring now",
            "python developer jobs 2024",
            "full stack developer internship",
            "backend engineer startup jobs",
            "software engineer entry level hiring"
        ]
    return {"queries": queries[:5]}


def search_web(state: JobSearchState) -> dict:
    """Search the web for jobs using Tavily or fallback to free APIs."""
    all_results = []

    tavily_key = os.getenv("TAVILY_API_KEY", "")

    if tavily_key:
        try:
            from langchain_tavily import TavilySearch
            tool = TavilySearch(max_results=5)
            for query in state.get("queries", [])[:3]:
                raw = tool.invoke(query)
                if isinstance(raw, list):
                    all_results.extend(raw)
                elif isinstance(raw, dict):
                    all_results.extend(raw.get("results", []))
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")

    # Fallback: Free job APIs
    if not all_results:
        all_results = _fetch_free_job_apis(state.get("queries", []))

    return {"search_results": all_results}


def _fetch_free_job_apis(queries: list) -> list:
    """Fetch jobs from free public APIs as fallback."""
    import requests
    results = []

    # RemoteOK API
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Applyr/1.0"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            for job in data[1:11]:  # Skip header, take 10
                results.append({
                    "url": job.get("url", ""),
                    "title": f"{job.get('position', '')} at {job.get('company', '')}",
                    "content": job.get("description", "")[:500],
                    "company": job.get("company", ""),
                    "position": job.get("position", ""),
                    "location": job.get("location", "Remote"),
                    "salary": job.get("salary", ""),
                    "source": "remoteok"
                })
    except Exception as e:
        logger.warning(f"RemoteOK API failed: {e}")

    # Arbeitnow API
    try:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            for job in data.get("data", [])[:10]:
                results.append({
                    "url": job.get("url", ""),
                    "title": f"{job.get('title', '')} at {job.get('company_name', '')}",
                    "content": job.get("description", "")[:500],
                    "company": job.get("company_name", ""),
                    "position": job.get("title", ""),
                    "location": job.get("location", ""),
                    "salary": "",
                    "source": "arbeitnow"
                })
    except Exception as e:
        logger.warning(f"Arbeitnow API failed: {e}")

    return results


def parse_jobs_from_results(state: JobSearchState) -> dict:
    """Use LLM to parse search results into structured job records."""
    llm = get_llm(temperature=0)

    results_text = "\n\n---\n\n".join(
        f"URL: {r.get('url', 'N/A')}\nTitle: {r.get('title', 'N/A')}\n"
        f"Content: {r.get('content', '')[:400]}"
        for r in state.get("search_results", [])[:15]
    )

    if not results_text.strip():
        return {"jobs": []}

    messages = [
        SystemMessage(content="""You are a job listing parser. Extract job listings from search results.
Return a JSON array of job objects. Each job must have:
{
  "title": "Job Title",
  "company": "Company Name",
  "url": "https://...",
  "source": "remoteok|arbeitnow|tavily",
  "jd_text": "Brief job description (2-3 sentences)",
  "location": "City, Country or Remote",
  "salary": "salary range or empty string",
  "hr_email": "email if found or empty string"
}
Extract as many distinct jobs as possible. Return ONLY a JSON array."""),
        HumanMessage(content=f"Parse these search results into job listings:\n\n{results_text}")
    ]

    response = llm.invoke(messages)
    try:
        parsed = parse_json_response(response.content)
        if isinstance(parsed, dict) and "items" in parsed:
            jobs = parsed["items"]
        elif isinstance(parsed, list):
            jobs = parsed
        else:
            jobs = []
    except Exception as e:
        logger.error(f"Failed to parse jobs from LLM: {e}")
        # Fallback: use raw results directly
        jobs = []
        for r in state.get("search_results", []):
            if r.get("position") or r.get("title"):
                jobs.append({
                    "title": r.get("position", r.get("title", "")),
                    "company": r.get("company", "Unknown"),
                    "url": r.get("url", ""),
                    "source": r.get("source", "web"),
                    "jd_text": r.get("content", "")[:500],
                    "location": r.get("location", ""),
                    "salary": r.get("salary", ""),
                    "hr_email": ""
                })

    return {"jobs": jobs}


# ─── Graph Builder ──────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(JobSearchState)
    graph.add_node("generate_queries", generate_search_queries)
    graph.add_node("search", search_web)
    graph.add_node("parse", parse_jobs_from_results)
    graph.set_entry_point("generate_queries")
    graph.add_edge("generate_queries", "search")
    graph.add_edge("search", "parse")
    graph.add_edge("parse", END)
    return graph.compile()


# ─── Pipeline Interface ─────────────────────────────────────────────
class WebResearchAgent:
    """Discovers job listings from multiple sources.

    Pipeline interface: orchestrator calls scrape_jobs() to get job list.
    """

    def __init__(self):
        self.graph = build_graph()

    def scrape_jobs(self, profile_text: str = "") -> List[Dict[str, Any]]:
        """Search the web for jobs matching the user profile.

        Args:
            profile_text: User profile summary for search query generation

        Returns:
            List of job dicts with title, company, url, source, jd_text, etc.
        """
        if not profile_text:
            profile_text = "Software Engineer, Python, JavaScript, Full Stack, Remote"

        logger.info(f"Starting web job search...")

        try:
            result = self.graph.invoke({
                "profile_text": profile_text,
                "queries": [],
                "messages": [],
                "search_results": [],
                "jobs": []
            })
            jobs = result.get("jobs", [])
            logger.info(f"Found {len(jobs)} jobs from web search")
            return jobs
        except Exception as e:
            logger.error(f"Web research agent failed: {e}")
            return []


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("--query", default="Python developer remote jobs", help="Search focus")
    args = parser.parse_args()

    print(f"\n🔍 Searching for jobs: {args.query}\n")

    agent = WebResearchAgent()
    jobs = agent.scrape_jobs(profile_text=args.query)

    print("=" * 60)
    print(f"📋 FOUND {len(jobs)} JOBS")
    print("=" * 60)
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job.get('title', 'N/A')}")
        print(f"   Company: {job.get('company', 'N/A')}")
        print(f"   Location: {job.get('location', 'N/A')}")
        print(f"   URL: {job.get('url', 'N/A')}")


if __name__ == "__main__":
    main()
