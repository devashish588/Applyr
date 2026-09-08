"""
Career Copilot Service — Applyr 2.0
====================================

Contextual AI Assistant for job candidates:
- Strategy advice (resume, cover letter, positioning)
- Application review & recommendations
- Follow-up message generation & salary guidance
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

from utils.llm_client import chat, chat_json

logger = logging.getLogger(__name__)

PROSE_VERBS_REGEX = re.compile(r"\b(requires|includes|matters|contains|focuses|provides|covers|shows|is|are|was|were|be|been|have|has|had|can|should|will|would|could|for|with|about|into)\b", re.IGNORECASE)

def clean_ai_filler(text: Optional[str]) -> str:
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^(great question!|sure!|absolutely!|here is a strategic framework:?|here is the framework:?)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*(hope this helps!?|let me know if you need anything else!?)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n\s*here is a strategic framework:\s*\n", "\n\n", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def is_standalone_section_heading(line: str) -> bool:
    if not line or not line.endswith(":") or len(line) > 30:
        return False
    if re.search(r"[.,?!=]", line[:-1]):
        return False
    if PROSE_VERBS_REGEX.search(line):
        return False
    raw_title = line[:-1].strip()
    if not raw_title:
        return False
    is_all_upper = raw_title == raw_title.upper() and any(c.isalpha() for c in raw_title)
    is_title_case = all(w[0].isupper() if w else True for w in raw_title.split())
    return is_all_upper or is_title_case

def parse_inline_tokens(text: Optional[str]) -> List[Dict[str, str]]:
    if not text or not isinstance(text, str):
        return []
    parts = re.split(r"(\*\*|__)", text)
    tokens = []
    is_bold = False
    for part in parts:
        if part in ("**", "__"):
            is_bold = not is_bold
        elif part:
            tokens.append({"type": "bold" if is_bold else "text", "text": part})
    return tokens

COPILOT_SYSTEM_PROMPT = """
You are Applyr Career Intelligence — direct, concise, structured.

Output JSON only:
{
  "message": "TITLE\\n\\nSummary: 1-2 sentences.\\n\\nKey Findings:\\n- Finding\\n\\nRecommended Actions:\\n1. Action",
  "suggestions": ["Next step 1", "Next step 2"],
  "action_type": "advice"
}
Rules: No greeting (Great question!/Sure!), no restating question, no motivational filler, no closing (Hope this helps!/Let me know...), max 150 words, bullets not paragraphs, use candidate/job context when available, UNKNOWN remains UNKNOWN.
"""


class CopilotService:
    """Service providing Career Copilot AI guidance."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def ask_copilot(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        candidate_profile: Optional[Dict[str, Any]] = None,
        job_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process user query and return contextual advice."""
        if not user_message or not user_message.strip():
            return {
                "message": "Hello! I'm your Applyr Career Copilot. Ask me anything about your job search strategy, resume tailoring, networking, or interview prep!",
                "suggestions": [
                    "How can I improve my resume fit score?",
                    "What email template works best for recruiter outreach?",
                    "How should I prepare for a software engineer interview?"
                ],
                "action_type": "greeting"
            }

        # Build prompt context
        context_str = ""
        if candidate_profile:
            roles = candidate_profile.get("inferred_roles") or candidate_profile.get("job_preferences", {}).get("target_roles", [])
            skills = candidate_profile.get("skills", {})
            context_str += f"\nCandidate Target Roles: {', '.join(roles) if roles else 'General Software Engineer'}"
            if isinstance(skills, list):
                context_str += f"\nCandidate Skills: {', '.join(skills[:15])}"
            elif isinstance(skills, dict):
                all_s = []
                for v in skills.values():
                    if isinstance(v, list):
                        all_s.extend(v)
                context_str += f"\nCandidate Skills: {', '.join(all_s[:15])}"

        if job_context:
            context_str += f"\nCurrent Job Context: {job_context.get('title', '')} at {job_context.get('company', '')}"

        history_str = ""
        if history:
            history_str = "\nConversation History:\n" + "\n".join(
                f"{h.get('role', 'user').upper()}: {h.get('content', '')}" for h in history[-4:]
            )

        prompt = f"{context_str}\n{history_str}\n\nUSER QUESTION: {user_message}"

        try:
            res = chat_json(prompt=prompt, system_prompt=COPILOT_SYSTEM_PROMPT, temperature=0.7)
            if isinstance(res, dict) and "message" in res:
                return res
        except Exception as e:
            logger.warning(f"[copilot] LLM completion failed: {e}")

        # Fallback text response if JSON parsing or LLM failed
        try:
            text_resp = chat(prompt=prompt, system_prompt=COPILOT_SYSTEM_PROMPT, temperature=0.7)
            return {
                "message": text_resp,
                "suggestions": ["What skills should I highlight?", "How can I follow up on applications?"],
                "action_type": "advice"
            }
        except Exception as err:
            logger.error(f"[copilot] Fallback failed: {err}")
            return self._heuristic_fallback(user_message)

    def _heuristic_fallback(self, query: str) -> Dict[str, Any]:
        """Deterministic offline fallback when LLM is unavailable."""
        q = query.lower()
        if "resume" in q:
            msg = "**Resume Tip:** Ensure your top technical skills match the target job description keywords in your top 1/3 section. Quantify achievements with metrics (e.g. *'Improved performance by 30%'*)."
            sugg = ["How to calculate fit score?", "Tailor resume for a job"]
        elif "interview" in q:
            msg = "**Interview Prep Tip:** Practice the STAR method (Situation, Task, Action, Result) for behavioral questions. Prepare 2-3 specific project stories demonstrating leadership and problem-solving."
            sugg = ["Generate mock interview questions", "Technical interview prep tips"]
        elif "email" in q or "outreach" in q or "recruiter" in q:
            msg = "**Outreach Tip:** Keep cold emails to recruiters concise (under 150 words). Reference a specific project, state why you're a fit, and attach your tailored resume."
            sugg = ["Show email templates", "Find recruiters for a company"]
        else:
            msg = "STRATEGY GUIDANCE\n\nFocus on applying to roles where your skill match score exceeds 70%, follow up within 5 business days, and personalize outreach to recruiters."
            sugg = ["Check application status", "Discover tech startups"]

        return {
            "message": msg,
            "suggestions": sugg,
            "action_type": "fallback"
        }


# Singleton factory
_copilot_service: Optional[CopilotService] = None

def get_copilot_service() -> CopilotService:
    global _copilot_service
    if _copilot_service is None:
        _copilot_service = CopilotService()
    return _copilot_service
