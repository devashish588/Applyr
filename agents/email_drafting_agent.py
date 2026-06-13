"""
Email Drafting Agent - Generates personalized cold emails.

Uses Groq LLM to draft compelling application emails with
context analysis and professional writing.

Adapted from user's CrewAI agent to work within Applyr pipeline.
"""
import os
import sys
import logging
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_client import get_llm, chat

logger = logging.getLogger(__name__)

COLD_EMAIL_PROMPT = """You are an expert career coach who writes compelling cold application emails.

Write a professional cold email for a job application with these rules:
- Subject line: compelling, not generic
- Opening: personalized hook mentioning the company/role
- Body: 2-3 sentences connecting candidate skills to job requirements
- Close: clear call to action
- Total: under 150 words for the body
- Tone: confident, professional, not desperate
- DO NOT use generic phrases like "I am writing to express my interest"

Return JSON:
{
  "subject": "Email subject line",
  "body": "Full email body text"
}
Return ONLY valid JSON."""

FOLLOW_UP_PROMPT = """Write a brief, professional follow-up email for a job application.
Keep it under 100 words. Be polite but direct.

Return JSON:
{
  "subject": "Follow-up subject line",
  "body": "Follow-up email body"
}
Return ONLY valid JSON."""


class EmailDraftingAgent:
    """Drafts personalized cold emails for job applications.

    Pipeline interface: orchestrator calls draft_email() for each job.
    """

    def __init__(self):
        self.llm = get_llm(temperature=0.3)

    def draft_email(self, job_data: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, str]:
        """Draft personalized cold email for a specific job.

        Args:
            job_data: Job details (title, company, jd_text, etc.)
            profile: User profile dict from profile.json

        Returns:
            {"subject": "...", "body": "..."}
        """
        company = job_data.get("company", "the company")
        title = job_data.get("title", "the position")
        jd_text = job_data.get("jd_text", "")[:500]

        # Build candidate summary
        name = profile.get("personal", {}).get("name", "Candidate")
        skills = profile.get("skills", {})
        skill_list = ", ".join(
            skills.get("languages", [])[:3] +
            skills.get("frameworks", [])[:2] +
            skills.get("tools", [])[:2]
        )
        experience = profile.get("experience_summary", "experienced software engineer")
        achievements = profile.get("key_achievements", [])
        top_achievement = achievements[0] if achievements else "significant technical contributions"

        prompt = f"""Draft a cold application email for:
Company: {company}
Role: {title}
Job Description: {jd_text}

Candidate:
Name: {name}
Skills: {skill_list}
Experience: {experience}
Top Achievement: {top_achievement}"""

        try:
            messages = [
                SystemMessage(content=COLD_EMAIL_PROMPT),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)

            from utils.llm_client import parse_json_response
            result = parse_json_response(response.content)

            return {
                "subject": result.get("subject", f"Application: {title} at {company}"),
                "body": result.get("body", "")
            }
        except Exception as e:
            logger.error(f"Email drafting failed: {e}")
            # Fallback template
            return {
                "subject": f"Application: {title} at {company}",
                "body": f"Dear Hiring Team,\n\nI'm {name}, {experience}. "
                        f"I'm excited about the {title} role at {company}. "
                        f"My skills in {skill_list} align well with your requirements. "
                        f"{top_achievement}.\n\n"
                        f"I'd welcome the opportunity to discuss how I can contribute to your team.\n\n"
                        f"Best regards,\n{name}"
            }

    def draft_follow_up(self, job_data: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, str]:
        """Draft a follow-up email for a previously applied job.

        Args:
            job_data: Job details
            profile: User profile dict

        Returns:
            {"subject": "...", "body": "..."}
        """
        company = job_data.get("company", "the company")
        title = job_data.get("title", "the position")
        name = profile.get("personal", {}).get("name", "Candidate")

        try:
            prompt = f"Follow up on application for {title} at {company}. Candidate: {name}"
            messages = [
                SystemMessage(content=FOLLOW_UP_PROMPT),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)

            from utils.llm_client import parse_json_response
            return parse_json_response(response.content)
        except Exception as e:
            logger.error(f"Follow-up drafting failed: {e}")
            return {
                "subject": f"Following up: {title} at {company}",
                "body": f"Dear Hiring Team,\n\nI wanted to follow up on my application for the {title} "
                        f"position. I remain very interested and would love to discuss my qualifications.\n\n"
                        f"Best regards,\n{name}"
            }

    def personalize_email(self, template: str, replacements: Dict[str, str]) -> str:
        """Fill email template with personalized data.

        Args:
            template: Email template with {{placeholders}}
            replacements: Key-value pairs for replacement

        Returns:
            Personalized email text
        """
        result = template
        for key, value in replacements.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Email Drafting Agent")
    parser.add_argument("--company", default="Stripe", help="Company name")
    parser.add_argument("--role", default="Senior Python Engineer", help="Job title")
    args = parser.parse_args()

    agent = EmailDraftingAgent()

    job = {"title": args.role, "company": args.company, "jd_text": "Looking for experienced Python developer with API experience"}
    profile = {
        "personal": {"name": "Test User"},
        "skills": {"languages": ["Python", "JS"], "frameworks": ["FastAPI"], "tools": ["Docker"]},
        "experience_summary": "Senior engineer with 5 years experience",
        "key_achievements": ["Built API handling 10M requests/day"]
    }

    email = agent.draft_email(job, profile)

    print("=" * 60)
    print("📧 DRAFTED EMAIL")
    print("=" * 60)
    print(f"Subject: {email['subject']}")
    print(f"\n{email['body']}")


if __name__ == "__main__":
    main()
