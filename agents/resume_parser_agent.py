"""
Resume Parser Agent - Extracts structured info from resume PDF/text.

Uses LangChain + Groq to parse resume into structured JSON with
contact info, skills, experience, education, and fit scoring.

Adapted from user's LangChain agent to work within Applyr pipeline.
"""
import os
import sys
import json
import re
import logging
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_client import get_llm, parse_json_response

logger = logging.getLogger(__name__)

PARSE_PROMPT = """Extract structured information from this resume and return JSON:
{
  "name": "full name",
  "email": "email or null",
  "phone": "phone or null",
  "location": "city, country or null",
  "linkedin": "URL or null",
  "github": "URL or null",
  "summary": "2-3 sentence professional summary",
  "years_experience": number,
  "current_title": "current/most recent job title",
  "skills": {
    "languages": ["Python", "JavaScript"],
    "frameworks": ["Django", "React"],
    "tools": ["Docker", "Git"],
    "soft_skills": ["leadership"]
  },
  "experience": [{"title": "...", "company": "...", "duration": "...", "highlights": ["..."]}],
  "education": [{"degree": "...", "institution": "...", "year": "..."}],
  "certifications": ["..."],
  "languages_spoken": ["English"]
}
Return only valid JSON."""

FIT_PROMPT = """Given this candidate profile and job description, return JSON:
{
  "fit_score": 0-100,
  "fit_label": "Excellent|Good|Fair|Poor",
  "strengths": ["matching point 1", "matching point 2"],
  "gaps": ["missing skill 1"],
  "recommendation": "Hire|Consider|Pass",
  "recommendation_reason": "2-3 sentence explanation"
}
Return only valid JSON."""


class ResumeParserAgent:
    """Parses resume and extracts key information.

    Pipeline interface: orchestrator calls parse_resume() and score_fit().
    """

    def __init__(self):
        self.llm = get_llm(temperature=0)

    def read_resume_text(self, path: str) -> str:
        """Read resume from PDF or text file.

        Args:
            path: Path to resume file (.pdf or .txt)

        Returns:
            Resume text content
        """
        if not os.path.exists(path):
            logger.error(f"Resume file not found: {path}")
            return ""

        if path.lower().endswith(".pdf"):
            try:
                import pypdf
                with open(path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    text = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                logger.info(f"Read {len(text)} chars from PDF resume")
                return text
            except ImportError:
                logger.error("pypdf not installed. Run: pip install pypdf")
                return ""
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read()

    def parse_resume(self, resume_path: str) -> Dict[str, Any]:
        """Parse resume file and extract structured data.

        Args:
            resume_path: Path to resume PDF/TXT

        Returns:
            Structured resume data dict
        """
        text = self.read_resume_text(resume_path)
        if not text:
            return {}

        return self.parse_resume_text(text)

    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """Parse resume text into structured data using LLM.

        Args:
            text: Raw resume text

        Returns:
            Structured resume data dict
        """
        try:
            messages = [
                SystemMessage(content=PARSE_PROMPT),
                HumanMessage(content=text[:3000])
            ]
            response = self.llm.invoke(messages)
            return parse_json_response(response.content)
        except Exception as e:
            logger.error(f"Resume parsing failed: {e}")
            return {}

    def extract_skills(self, resume_text: str) -> List[str]:
        """Extract technical skills from resume text.

        Args:
            resume_text: Raw resume text

        Returns:
            List of skills
        """
        profile = self.parse_resume_text(resume_text)
        skills = profile.get("skills", {})
        all_skills = []
        for category in ["languages", "frameworks", "tools"]:
            all_skills.extend(skills.get(category, []))
        return all_skills

    def extract_achievements(self, resume_text: str) -> List[str]:
        """Extract key achievements from resume.

        Args:
            resume_text: Raw resume text

        Returns:
            List of achievement strings
        """
        profile = self.parse_resume_text(resume_text)
        achievements = []
        for exp in profile.get("experience", []):
            achievements.extend(exp.get("highlights", []))
        return achievements

    def score_fit(self, profile: Dict[str, Any], job_desc: str) -> Dict[str, Any]:
        """Score candidate fit against a job description.

        Args:
            profile: Parsed resume profile dict
            job_desc: Job description text

        Returns:
            Fit analysis dict with score, strengths, gaps
        """
        try:
            messages = [
                SystemMessage(content=FIT_PROMPT),
                HumanMessage(content=f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\nJob description:\n{job_desc}")
            ]
            response = self.llm.invoke(messages)
            return parse_json_response(response.content)
        except Exception as e:
            logger.error(f"Fit scoring failed: {e}")
            return {"fit_score": 0, "fit_label": "Unknown", "strengths": [], "gaps": []}


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Resume Parser Agent")
    parser.add_argument("--resume", help="Path to resume file (.txt or .pdf)")
    parser.add_argument("--job-desc", help="Job description to match against")
    args = parser.parse_args()

    agent = ResumeParserAgent()

    if args.resume:
        print(f"\n📄 Parsing resume: {args.resume}")
        profile = agent.parse_resume(args.resume)
    else:
        print("\n📄 Using sample resume text")
        sample = """Jane Doe\njane@email.com | SF, CA\nSenior Python Developer, 7 years experience\nSkills: Python, FastAPI, Django, Docker, K8s, AWS\nLed team of 5, reduced latency 40%"""
        profile = agent.parse_resume_text(sample)

    print("\n" + "=" * 60)
    print("👤 PARSED RESUME")
    print("=" * 60)
    print(f"Name: {profile.get('name')}")
    print(f"Title: {profile.get('current_title')}")
    print(f"Experience: {profile.get('years_experience')} years")
    print(f"Skills: {json.dumps(profile.get('skills', {}), indent=2)}")

    if args.job_desc:
        print("\n📊 JOB FIT ANALYSIS")
        fit = agent.score_fit(profile, args.job_desc)
        print(f"Score: {fit.get('fit_score')}/100 ({fit.get('fit_label')})")
        print(f"Strengths: {', '.join(fit.get('strengths', []))}")
        print(f"Gaps: {', '.join(fit.get('gaps', []))}")


if __name__ == "__main__":
    main()
