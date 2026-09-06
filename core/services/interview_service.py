"""
Interview Prep Service — Applyr 2.0
=====================================

Generates customized interview preparation kits and evaluates practice answers:
- Behavioral questions with STAR (Situation, Task, Action, Result) guidance
- Technical drill-down questions tailored to job skills
- Talking points linking candidate resume to job description
- Interactive practice answer evaluator & feedback engine
"""

import json
import logging
from typing import Dict, List, Any, Optional

from utils.llm_client import chat, chat_json

logger = logging.getLogger(__name__)

INTERVIEW_PREP_PROMPT = """
You are an expert technical interviewer and executive talent coach.
Generate a structured Interview Preparation Kit for the following job opportunity.

Return ONLY a JSON object with this exact structure:
{
  "behavioral_questions": [
    {
      "question": "Describe a time when you resolved a critical production issue under pressure.",
      "category": "Problem Solving / Resilience",
      "star_guidance": "S: Mention system outage. T: Restore service. A: Isolated root cause using logs. R: Reduced MTTR by 40%."
    }
  ],
  "technical_questions": [
    {
      "question": "How do you optimize a slow database query in PostgreSQL?",
      "topic": "Databases & Performance",
      "expected_answer_outline": "Explain EXPLAIN ANALYZE, indexing strategies (B-Tree, GIN), connection pooling, and query restructuring."
    }
  ],
  "talking_points": [
    "Highlight experience with Python REST APIs and PostgreSQL optimization",
    "Emphasize experience collaborating in Agile teams and continuous delivery"
  ],
  "company_insights": "Focus on high-scale system reliability, clear communication, and ownership mindset."
}
"""

EVALUATE_ANSWER_PROMPT = """
You are a senior tech interviewer evaluating a candidate's practice interview answer.
Be constructive, encouraging, and specific.

Return ONLY a JSON object:
{
  "score": 85, // 0-100 integer
  "feedback": "Strong structure following the STAR method. Clear metric given for final impact.",
  "strengths": ["Clear situation context", "Quantified results"],
  "areas_for_improvement": ["Elaborate more on specific tools used during the action phase"],
  "sample_improved_answer": "An optimized version of the candidate's answer incorporating missing details."
}
"""


class InterviewService:
    """Service providing interview preparation kits and answer evaluations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_prep_kit(
        self,
        job_title: str,
        company: str,
        jd_text: str = "",
        candidate_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete interview prep kit for a job."""
        skills_str = ", ".join(candidate_skills[:10]) if candidate_skills else "Python, SQL, System Architecture"
        prompt = (
            f"Job Title: {job_title}\n"
            f"Company: {company}\n"
            f"Candidate Skills: {skills_str}\n"
            f"Job Description Snippet:\n{jd_text[:1500] if jd_text else 'Standard Software Engineer position'}"
        )

        try:
            res = chat_json(prompt=prompt, system_prompt=INTERVIEW_PREP_PROMPT, temperature=0.5)
            if isinstance(res, dict) and "behavioral_questions" in res:
                return res
        except Exception as e:
            logger.warning(f"[interview] LLM prep kit generation failed: {e}")

        return self._heuristic_prep_kit(job_title, company, candidate_skills or [])

    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        expected_topic: str = "",
    ) -> Dict[str, Any]:
        """Evaluate candidate's practice answer."""
        if not user_answer or len(user_answer.strip()) < 10:
            return {
                "score": 30,
                "feedback": "Answer is too brief. Try elaborating using the STAR method (Situation, Task, Action, Result).",
                "strengths": ["Attempted response"],
                "areas_for_improvement": ["Add specific context, action steps taken, and measurable results"],
                "sample_improved_answer": "In my previous role, when faced with [Situation], I was responsible for [Task]. I executed [Action using specific technologies], which resulted in [Measurable Result]."
            }

        prompt = (
            f"Question: {question}\n"
            f"Topic/Category: {expected_topic}\n"
            f"Candidate Answer:\n{user_answer}"
        )

        try:
            res = chat_json(prompt=prompt, system_prompt=EVALUATE_ANSWER_PROMPT, temperature=0.3)
            if isinstance(res, dict) and "score" in res:
                return res
        except Exception as e:
            logger.warning(f"[interview] LLM answer evaluation failed: {e}")

        # Fallback heuristic evaluation
        word_count = len(user_answer.split())
        score = min(90, max(50, 40 + (word_count // 3)))
        return {
            "score": score,
            "feedback": f"Good effort! Your response covers key points ({word_count} words). To elevate it further, ensure you highlight exact technical tools and measurable outcomes.",
            "strengths": ["Demonstrates relevant experience", "Directly addresses the question"],
            "areas_for_improvement": ["Include specific metric/result metrics", "Highlight personal ownership"],
            "sample_improved_answer": f"{user_answer} This enabled our team to deliver on schedule with enhanced system stability."
        }

    def _heuristic_prep_kit(
        self,
        job_title: str,
        company: str,
        skills: List[str],
    ) -> Dict[str, Any]:
        """Fallback interview prep kit when LLM is offline."""
        top_skills = ", ".join(skills[:3]) if skills else "software engineering"
        return {
            "behavioral_questions": [
                {
                    "question": f"Tell me about a challenging project you built using {skills[0] if skills else 'modern tech'} and how you overcame technical hurdles.",
                    "category": "Technical Execution",
                    "star_guidance": "S: Project scope. T: Key technical bottleneck. A: Design decision & code implementation. R: Successful launch and metric impact."
                },
                {
                    "question": f"Why do you want to join {company} as a {job_title}?",
                    "category": "Company Alignment",
                    "star_guidance": "Connect company's core product / mission with your personal career goals and engineering background."
                }
            ],
            "technical_questions": [
                {
                    "question": f"What are best practices for designing scalable REST APIs and handling error responses?",
                    "topic": "System Design & API Architecture",
                    "expected_answer_outline": "Discuss HTTP status codes, idempotent operations, pagination, rate limiting, and structured JSON error payloads."
                },
                {
                    "question": f"How do you approach writing clean, testable code in {skills[0] if skills else 'Python'}?",
                    "topic": "Code Quality & Testing",
                    "expected_answer_outline": "Discuss SOLID principles, dependency injection, unit testing with mocks, and linting/formatting standards."
                }
            ],
            "talking_points": [
                f"Hands-on experience in {top_skills}",
                "Proven track record of delivering clean, tested code on schedule",
                "Strong problem-solving and cross-functional communication"
            ],
            "company_insights": f"Research {company}'s recent engineering blogs, public tech stack, and core values prior to the interview."
        }


# Singleton factory
_interview_service: Optional[InterviewService] = None

def get_interview_service() -> InterviewService:
    global _interview_service
    if _interview_service is None:
        _interview_service = InterviewService()
    return _interview_service
