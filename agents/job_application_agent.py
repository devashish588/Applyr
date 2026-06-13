"""
Job Application Agent - Filters, ranks, and coordinates applications.

Uses fit scoring to rank jobs and coordinates the application process
(email, form detection, submission tracking).

Adapted from user's CrewAI agent to work within Applyr pipeline.
"""
import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import get_llm, chat

logger = logging.getLogger(__name__)


# ATS URL patterns
ATS_PATTERNS = {
    "greenhouse": r"greenhouse\.io|boards\.greenhouse",
    "lever": r"lever\.co|jobs\.lever",
    "ashby": r"ashbyhq\.com|jobs\.ashbyhq",
    "workday": r"myworkdayjobs\.com|workday\.com",
    "icims": r"icims\.com",
    "bamboohr": r"bamboohr\.com",
    "smartrecruiters": r"smartrecruiters\.com",
    "jobvite": r"jobvite\.com",
}


class JobApplicationAgent:
    """Filters jobs by fit and coordinates application submission.

    Pipeline interface: orchestrator calls filter_and_rank_jobs() and
    apply_to_job() for each qualifying job.
    """

    def __init__(self):
        self.min_score = int(os.getenv("MIN_FIT_SCORE", "50"))
        self.auto_apply = os.getenv("AUTO_APPLY", "false").lower() == "true"

    def filter_and_rank_jobs(self, jobs: List[Dict[str, Any]],
                              min_score: Optional[int] = None) -> List[Dict[str, Any]]:
        """Filter jobs by fit score and rank by best matches.

        Args:
            jobs: List of job dicts (must have 'fit_score' key)
            min_score: Minimum fit score threshold (0-100)

        Returns:
            Filtered & ranked jobs (highest score first)
        """
        threshold = min_score or self.min_score
        filtered = [j for j in jobs if j.get("fit_score", 0) >= threshold]
        ranked = sorted(filtered, key=lambda x: x.get("fit_score", 0), reverse=True)

        logger.info(f"Filtered {len(jobs)} jobs to {len(ranked)} (threshold: {threshold})")
        return ranked

    def apply_to_job(self, job_data: Dict[str, Any]) -> bool:
        """Attempt to apply to job.

        Determines the application method and coordinates the process.

        Args:
            job_data: Job details with fit_score, resume_path, etc.

        Returns:
            True if application was initiated successfully
        """
        method = self.detect_apply_method(job_data.get("url", ""))
        hr_email = job_data.get("hr_email", "")

        logger.info(f"Applying to {job_data.get('company', 'Unknown')} via {method}")

        if method == "email" and hr_email:
            # Email application is handled by the orchestrator's email step
            return True
        elif method in ("greenhouse", "lever", "ashby", "workday"):
            # ATS detected — log for manual or automated form filling
            logger.info(f"ATS detected: {method}. URL: {job_data.get('url', '')}")
            return True
        elif method == "direct_url":
            logger.info(f"Direct apply URL: {job_data.get('url', '')}")
            return True
        else:
            logger.warning(f"Unknown apply method for {job_data.get('company', 'Unknown')}")
            return False

    def detect_apply_method(self, job_url: str) -> str:
        """Detect how to apply based on URL patterns.

        Args:
            job_url: URL to job posting

        Returns:
            Application method string
        """
        if not job_url:
            return "unknown"

        url_lower = job_url.lower()

        # Check for ATS platforms
        for ats_name, pattern in ATS_PATTERNS.items():
            if re.search(pattern, url_lower):
                return ats_name

        # Check for email-based
        if "mailto:" in url_lower:
            return "email"

        # Check for common career page patterns
        if any(kw in url_lower for kw in ["career", "jobs", "apply", "hiring"]):
            return "direct_url"

        return "unknown"

    def generate_application_package(self, job_data: Dict[str, Any],
                                      profile: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to generate a complete application package.

        Args:
            job_data: Job details
            profile: Candidate profile

        Returns:
            Application package dict with cover letter highlights,
            resume bullets, and interview prep
        """
        jd_text = job_data.get("jd_text", "")[:1000]
        company = job_data.get("company", "the company")
        title = job_data.get("title", "the position")

        name = profile.get("personal", {}).get("name", "Candidate")
        experience = profile.get("experience_summary", "")
        achievements = profile.get("key_achievements", [])
        skills = profile.get("skills", {})
        skill_text = ", ".join(
            skills.get("languages", []) +
            skills.get("frameworks", []) +
            skills.get("tools", [])
        )

        try:
            response = chat(
                prompt=f"""Job: {title} at {company}
JD: {jd_text}

Candidate: {name}
Experience: {experience}
Skills: {skill_text}
Achievements: {', '.join(achievements[:3])}""",
                system_prompt="""Analyze this job and candidate match. Return JSON:
{
  "top_3_strengths": ["strength1", "strength2", "strength3"],
  "resume_bullets_to_highlight": ["bullet1", "bullet2", "bullet3", "bullet4", "bullet5"],
  "cover_letter_hook": "One compelling opening sentence",
  "keywords_to_include": ["keyword1", "keyword2", "keyword3"],
  "interview_topics": ["topic1", "topic2", "topic3"]
}
Return ONLY valid JSON.""",
                temperature=0.2
            )

            from utils.llm_client import parse_json_response
            return parse_json_response(response)
        except Exception as e:
            logger.error(f"Application package generation failed: {e}")
            return {}

    def should_auto_apply(self, job_data: Dict[str, Any]) -> bool:
        """Determine if job should be auto-applied based on safety rules.

        Args:
            job_data: Job data with fit_score

        Returns:
            True if auto-apply is safe
        """
        if not self.auto_apply:
            return False

        score = job_data.get("fit_score", 0)
        if score < 70:
            return False

        # Check for blacklisted companies (could be loaded from config)
        blacklist = os.getenv("BLACKLISTED_COMPANIES", "").split(",")
        company = job_data.get("company", "").lower()
        if any(b.strip().lower() in company for b in blacklist if b.strip()):
            return False

        return True


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Job Application Agent")
    parser.add_argument("--url", default="https://boards.greenhouse.io/stripe/jobs/123", help="Job URL to analyze")
    args = parser.parse_args()

    agent = JobApplicationAgent()

    print(f"\n🔍 Analyzing: {args.url}")
    method = agent.detect_apply_method(args.url)
    print(f"📋 Apply method: {method}")

    # Test ranking
    test_jobs = [
        {"title": "Python Dev", "company": "A", "fit_score": 85},
        {"title": "Java Dev", "company": "B", "fit_score": 30},
        {"title": "Full Stack", "company": "C", "fit_score": 72},
        {"title": "Data Eng", "company": "D", "fit_score": 55},
    ]

    ranked = agent.filter_and_rank_jobs(test_jobs, min_score=50)
    print(f"\n📊 Ranked {len(ranked)} jobs (out of {len(test_jobs)}):")
    for j in ranked:
        print(f"  {j['fit_score']}/100 - {j['title']} at {j['company']}")


if __name__ == "__main__":
    main()
