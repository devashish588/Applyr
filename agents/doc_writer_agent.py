"""
Documentation Writer Agent - Tailors resumes and generates cover letters.

Uses Groq LLM to rewrite resume bullets for specific jobs and
generate personalized cover letters.

Adapted from user's LangChain documentation writer to work within Applyr pipeline.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_client import get_llm

logger = logging.getLogger(__name__)

TAILOR_RESUME_PROMPT = """Tailor resume to job. Return formatted text only:
Name, Contact, Summary, Experience (tailored bullets), Skills, Education.
Rules: Reorder relevant bullets first, add ATS keywords naturally, quantify only with verified evidence, concise, no greeting/filler, no "Here is...".
"""

COVER_LETTER_PROMPT = """Write cover letter. Return text only, no JSON/markdown:
Dear Hiring Manager,
...
Sincerely, [Name]
Rules: 250-300 words, mention company+role, 2-3 achievements matching requirements, authentic, no clichés, no greeting/filler like "Here is...".
"""


class DocWriterAgent:
    """Generates tailored resumes and cover letters per job.

    Pipeline interface: orchestrator calls generate methods for each job.
    """

    def __init__(self):
        self.llm = get_llm(temperature=0.2)

    def generate_tailored_resume(self, job_jd: str, profile: Dict[str, Any],
                                  master_resume_path: str = "") -> str:
        """Generate resume tailored to specific job.

        Args:
            job_jd: Job description text
            profile: User profile from profile.json
            master_resume_path: Path to master resume PDF

        Returns:
            Path to generated tailored resume file
        """
        # Read master resume if available
        master_text = ""
        if master_resume_path and os.path.exists(master_resume_path):
            try:
                import pypdf
                with open(master_resume_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    master_text = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
            except Exception:
                pass

        # Build resume text from profile if no PDF
        if not master_text:
            master_text = self._profile_to_resume_text(profile)

        try:
            messages = [
                SystemMessage(content=TAILOR_RESUME_PROMPT),
                HumanMessage(content=f"Master Resume:\n{master_text[:2500]}\n\nJob Description:\n{job_jd[:1500]}")
            ]
            response = self.llm.invoke(messages)
            tailored_text = response.content

            # Save tailored resume
            company = profile.get("_current_company", "company")
            job_id = profile.get("_current_job_id", "0")
            safe_company = "".join(c for c in company if c.isalnum() or c in "_- ")[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_dir = os.path.join("resume", "tailored")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{safe_company}_{timestamp}_resume.txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(tailored_text)

            logger.info(f"Tailored resume saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Resume tailoring failed: {e}")
            return ""

    def generate_cover_letter(self, job_data: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """Generate personalized cover letter for job.

        Args:
            job_data: Job details (title, company, jd_text)
            profile: User profile from profile.json

        Returns:
            Path to generated cover letter file
        """
        company = job_data.get("company", "the company")
        title = job_data.get("title", "the position")
        jd_text = job_data.get("jd_text", "")[:1000]

        name = profile.get("personal", {}).get("name", "Candidate")
        experience = profile.get("experience_summary", "")
        achievements = profile.get("key_achievements", [])
        skills = profile.get("skills", {})
        skill_list = ", ".join(
            skills.get("languages", []) +
            skills.get("frameworks", []) +
            skills.get("tools", [])
        )

        prompt = f"""Write a cover letter for:
Company: {company}
Role: {title}
Job Description: {jd_text}

Candidate:
Name: {name}
Experience: {experience}
Key Achievements: {json.dumps(achievements)}
Skills: {skill_list}"""

        try:
            messages = [
                SystemMessage(content=COVER_LETTER_PROMPT),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            cover_letter = response.content

            # Save cover letter
            safe_company = "".join(c for c in company if c.isalnum() or c in "_- ")[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_dir = os.path.join("resume", "cover_letters")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{safe_company}_{timestamp}_cover_letter.txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)

            logger.info(f"Cover letter saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return ""

    def reorder_resume_bullets(self, master_resume: str, job_jd: str) -> List[str]:
        """Reorder resume bullets to match job requirements.

        Args:
            master_resume: Full master resume text
            job_jd: Job description text

        Returns:
            Reordered list of resume bullets
        """
        try:
            from utils.llm_client import chat
            response = chat(
                prompt=f"Resume bullets:\n{master_resume[:1500]}\n\nJob:\n{job_jd[:500]}",
                system_prompt="Reorder these resume bullets so the most relevant ones for the job "
                              "appear first. Return as a JSON array of strings. Return ONLY a JSON array.",
                temperature=0
            )
            from utils.llm_client import parse_json_response
            result = parse_json_response(response)
            if isinstance(result, dict) and "items" in result:
                return result["items"]
            return []
        except Exception as e:
            logger.error(f"Bullet reordering failed: {e}")
            return []

    def _profile_to_resume_text(self, profile: Dict[str, Any]) -> str:
        """Convert profile.json to resume-like text."""
        personal = profile.get("personal", {})
        skills = profile.get("skills", {})
        experience = profile.get("experience_summary", "")
        achievements = profile.get("key_achievements", [])

        lines = [
            personal.get("name", "Candidate"),
            f"{personal.get('email', '')} | {personal.get('phone', '')}",
            f"LinkedIn: {personal.get('linkedin', '')}",
            f"GitHub: {personal.get('github', '')}",
            "",
            "SUMMARY",
            experience,
            "",
            "SKILLS",
            f"Languages: {', '.join(skills.get('languages', []))}",
            f"Frameworks: {', '.join(skills.get('frameworks', []))}",
            f"Tools: {', '.join(skills.get('tools', []))}",
            "",
            "KEY ACHIEVEMENTS",
        ]
        for ach in achievements:
            lines.append(f"- {ach}")

        return "\n".join(lines)


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Documentation Writer Agent")
    parser.add_argument("--job", default="Senior Python Engineer at Stripe", help="Job title")
    parser.add_argument("--jd", default="Looking for Python developer with API and distributed systems experience", help="Job description")
    args = parser.parse_args()

    agent = DocWriterAgent()

    profile = {
        "personal": {"name": "Test User", "email": "test@email.com", "phone": "+1-555-0123",
                      "linkedin": "linkedin.com/in/test", "github": "github.com/test"},
        "skills": {"languages": ["Python", "JS"], "frameworks": ["FastAPI", "Django"], "tools": ["Docker", "K8s"]},
        "experience_summary": "Senior engineer with 5 years experience building scalable APIs",
        "key_achievements": ["Built API handling 10M req/day", "Led team of 5 engineers"],
        "_current_company": "Stripe",
    }

    job = {"title": args.job, "company": "Stripe", "jd_text": args.jd}

    print("\n📝 Generating cover letter...")
    cl_path = agent.generate_cover_letter(job, profile)
    if cl_path:
        with open(cl_path) as f:
            print(f.read())


if __name__ == "__main__":
    main()
