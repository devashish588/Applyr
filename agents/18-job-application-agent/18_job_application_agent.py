"""
Job Application Agent — AutoApply AI
Analyzes a job description against your profile, scores fit,
tailors your resume bullets, writes a cover letter, and saves
both as files ready to attach to the email.

Fixes vs original:
  - langchain_openai.ChatOpenAI → langchain_groq.ChatGroq
  - CrewAI removed — replaced with structured single-LLM pipeline
  - Now produces actual files: tailored resume (.txt) + cover letter (.txt)
  - Returns structured dict for orchestrator (not raw string)
  - Reads from profile.json + fit score from resume parser agent
  - Respects MIN_FIT_SCORE from .env (skips weak matches)

Usage:
    # CLI — test against a job
    python 18_job_application_agent.py --job '{"title":"SDE","company":"Stripe",...}'
    python 18_job_application_agent.py --job-file ./uploads/jd_pdfs/stripe.json

    # Pipeline (used by orchestrator)
    from agents.18_job_application_agent import JobApplicationAgent
    agent = JobApplicationAgent()
    result = agent.process(job_data, profile, parsed_resume)

Install:
    pip install langchain-groq python-dotenv
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_client import get_llm

load_dotenv()


# ── Prompts ───────────────────────────────────────────────────────────────────
TAILOR_PROMPT = """Analyze candidate vs job. Return JSON only, no markdown:
{
  "fit_score": 0-100,
  "fit_label": "Excellent|Good|Fair|Poor",
  "apply_recommendation": "Apply|Consider|Skip",
  "tailored_bullets": ["Rewritten bullet - quantified, JD keywords"],
  "skills_to_highlight": ["skill"],
  "keywords_matched": ["JD keyword in profile"],
  "keywords_missing": ["JD keyword not in profile"],
  "cover_letter": "3 paragraphs, <220 words, company+role specific",
  "interview_questions": [{"q": "Question", "framework": "STAR: ..."}],
  "salary_estimate": "range or null"
}
Rules: No greeting/filler ("Great question!"), direct, concise, use profile/JD evidence, UNKNOWN remains UNKNOWN.
Cover letter: Paragraph1 hook, Paragraph2 2-3 achievements matching JD, Paragraph3 company why + CTA, sign name, <220 words, no generic phrases.
"""


# ── Agent class ───────────────────────────────────────────────────────────────
class JobApplicationAgent:
    """
    Analyzes job fit, tailors resume bullets, writes cover letter,
    and saves output files ready for email attachment.
    """

    def __init__(self):
        self.llm_error        = None
        try:
            self.llm          = get_llm(temperature=0.3)
        except Exception as e:
            self.llm          = None
            self.llm_error    = str(e)
            print(f"[job_agent] LLM unavailable, using local fallback: {e}")
        self.min_fit_score    = int(os.getenv("MIN_FIT_SCORE", "50"))
        self.tailored_dir     = os.getenv("TAILORED_RESUME_DIR",  "./resume/tailored/")
        self.cover_letter_dir = os.getenv("COVER_LETTER_DIR",     "./resume/cover_letters/")
        self.dry_run          = os.getenv("DRY_RUN", "true").lower() == "true"

        Path(self.tailored_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cover_letter_dir).mkdir(parents=True, exist_ok=True)

    # ── Main pipeline entry point ──────────────────────────────────────────────
    def process(self, job_data: dict, profile: dict,
                parsed_resume: dict | None = None) -> dict:
        """
        Full pipeline for one job:
          1. Score fit
          2. If above MIN_FIT_SCORE → tailor resume + write cover letter
          3. Save files
          4. Return structured result for orchestrator

        Args:
            job_data:       from web_research_agent or pdf_qa_agent
            profile:        loaded from profile.json
            parsed_resume:  output of resume_parser_agent.parse() — optional

        Returns:
            {
              "job": job_data,
              "fit_score": 75,
              "fit_label": "Good",
              "should_apply": True,
              "cover_letter_path": "./resume/cover_letters/stripe_sde_2024-06-13.txt",
              "tailored_resume_path": "./resume/tailored/stripe_sde_2024-06-13.txt",
              "email_data": { subject, body hint, to },
              "materials": { full LLM output }
            }
        """
        company = self._slugify(job_data.get("company", "company"))
        title   = self._slugify(job_data.get("title", "role"))
        slug    = f"{company}_{title}_{datetime.now().strftime('%Y-%m-%d')}"

        print(f"\n[job_agent] Processing: {job_data.get('title')} at {job_data.get('company')}")

        # ── Step 1: analyse + tailor ───────────────────────────────────────────
        materials = self._analyse_and_tailor(job_data, profile, parsed_resume)

        try:
            fit_score = int(materials.get("fit_score", 0))
        except (TypeError, ValueError):
            fit_score = 0
        materials["fit_score"] = fit_score
        fit_label = materials.get("fit_label", "Unknown")
        recommendation = str(materials.get("apply_recommendation", "")).lower()
        should_apply = (
            fit_score >= self.min_fit_score and
            recommendation != "skip"
        )

        print(f"[job_agent] Fit: {fit_score}/100 ({fit_label}) -> {'[APPLY] Apply' if should_apply else '[SKIP] Skip'}")

        if not should_apply:
            return {
                "job":        job_data,
                "fit_score":  fit_score,
                "fit_label":  fit_label,
                "should_apply": False,
                "reason":     f"Score {fit_score} below threshold {self.min_fit_score}",
                "materials":  materials,
            }

        # ── Step 2: save cover letter ──────────────────────────────────────────
        cover_letter_path = os.path.join(self.cover_letter_dir, f"{slug}.txt")
        # Preserve original txt path in case PDF generation fails — returned as *_txt_path
        cover_letter_txt_path = cover_letter_path
        cover_letter_text = self._format_cover_letter(
            materials.get("cover_letter", ""),
            job_data,
            profile,
        )
        if not self.dry_run:
            with open(cover_letter_path, "w") as f:
                f.write(cover_letter_text)
            print(f"[job_agent] Cover letter saved: {cover_letter_path}")
            # Attempt to generate PDF version and prefer it when available
            try:
                from core.utils.pdf_generator import generate_cover_letter_pdf
                cover_pdf_path = os.path.splitext(cover_letter_path)[0] + ".pdf"
                pdf_path = generate_cover_letter_pdf(cover_letter_text, cover_pdf_path)
                cover_letter_path = pdf_path
                print(f"[job_agent] Cover letter PDF generated: {cover_letter_path}")
            except Exception as e:
                print(f"[job_agent] Cover letter PDF generation failed: {e}")
        else:
            print(f"[job_agent] DRY RUN — cover letter not saved (would be: {cover_letter_path})")

        # ── Step 3: save tailored resume bullets ──────────────────────────────
        tailored_resume_path = os.path.join(self.tailored_dir, f"{slug}.txt")
        # Preserve original txt path in case PDF generation fails — returned as *_txt_path
        tailored_resume_txt_path = tailored_resume_path
        tailored_resume_text = self._format_tailored_resume(
            materials, job_data, profile
        )
        if not self.dry_run:
            with open(tailored_resume_path, "w") as f:
                f.write(tailored_resume_text)
            print(f"[job_agent] Tailored resume saved: {tailored_resume_path}")
            # Attempt to generate PDF version and prefer it when available
            try:
                from core.utils.pdf_generator import generate_resume_pdf
                tailored_pdf_path = os.path.splitext(tailored_resume_path)[0] + ".pdf"
                pdf_path = generate_resume_pdf(tailored_resume_text, tailored_pdf_path)
                tailored_resume_path = pdf_path
                print(f"[job_agent] Tailored resume PDF generated: {tailored_resume_path}")
            except Exception as e:
                print(f"[job_agent] Tailored resume PDF generation failed: {e}")
        else:
            print(f"[job_agent] DRY RUN — tailored resume not saved (would be: {tailored_resume_path})")

        return {
            "job":                  job_data,
            "fit_score":            fit_score,
            "fit_label":            fit_label,
            "should_apply":         True,
            "cover_letter_path":    cover_letter_path,
            "tailored_resume_path": tailored_resume_path,
            "cover_letter_txt_path": cover_letter_txt_path,
            "tailored_resume_txt_path": tailored_resume_txt_path,
            "cover_letter_text":    cover_letter_text,
            "skills_to_highlight":  materials.get("skills_to_highlight", []),
            "keywords_matched":     materials.get("keywords_matched", []),
            "keywords_missing":     materials.get("keywords_missing", []),
            "interview_questions":  materials.get("interview_questions", []),
            "email_data": {
                "to":      job_data.get("hr_email"),
                "subject": f"Application: {job_data.get('title')} — "
                           f"{profile.get('personal', {}).get('name', '')}",
            },
            "materials": materials,
        }

    # ── Internal: call LLM ────────────────────────────────────────────────────
    def _analyse_and_tailor(self, job_data: dict, profile: dict,
                             parsed_resume: dict | None) -> dict:
        if self.llm is None:
            return self._fallback_materials(job_data, profile, parsed_resume)

        personal   = profile.get("personal", {})
        skills     = profile.get("skills", {})
        experience = profile.get("experience", [])

        # Build experience text from profile
        exp_lines = []
        for exp in experience[:3]:
            exp_lines.append(
                f"Role: {exp.get('role')} at {exp.get('company')} ({exp.get('duration', '')})"
            )
            for b in exp.get("bullets", [])[:3]:
                exp_lines.append(f"  • {b}")

        # Also pull parsed resume highlights if available
        parsed_bullets = []
        if parsed_resume:
            for exp in parsed_resume.get("experience", [])[:2]:
                parsed_bullets += exp.get("bullets", [])[:2]

        all_skills = (
            skills.get("languages", []) +
            skills.get("frameworks", []) +
            skills.get("tools", [])
        )

        candidate_block = f"""
CANDIDATE: {personal.get('name')}
Email: {personal.get('email')}
Skills: {', '.join(all_skills[:15])}

Experience:
{chr(10).join(exp_lines)}

{'Parsed resume highlights: ' + chr(10).join(f'  • {b}' for b in parsed_bullets) if parsed_bullets else ''}
"""

        jd_block = f"""
ROLE:    {job_data.get('title')}
COMPANY: {job_data.get('company')}
LOCATION: {job_data.get('location', 'N/A')}
TYPE:    {job_data.get('type', 'N/A')}

Required skills: {', '.join(job_data.get('required_skills', []))}

Description:
{job_data.get('description_snippet', '')[:800]}
"""

        messages = [
            SystemMessage(content=TAILOR_PROMPT),
            HumanMessage(content=(
                f"CANDIDATE PROFILE:\n{candidate_block}\n\n"
                f"JOB DESCRIPTION:\n{jd_block}"
            )),
        ]

        try:
            response = self.llm.invoke(messages)
            parsed = self._parse_json(response.content)
            if parsed.get("fit_score") is None:
                return self._fallback_materials(job_data, profile, parsed_resume)
            try:
                parsed_score = int(parsed.get("fit_score", 0))
            except (TypeError, ValueError):
                return self._fallback_materials(job_data, profile, parsed_resume)

            parse_failed = parsed_score == 0 and parsed.get("fit_label") == "Unknown"
            if parse_failed:
                return self._fallback_materials(job_data, profile, parsed_resume)

            if parsed_score < self.min_fit_score:
                fallback = self._fallback_materials(job_data, profile, parsed_resume)
                if fallback.get("fit_score", 0) >= self.min_fit_score:
                    fallback["llm_score_overridden"] = parsed_score
                    return fallback
            return parsed
        except Exception as e:
            print(f"[job_agent] LLM tailoring failed, using local fallback: {e}")
            return self._fallback_materials(job_data, profile, parsed_resume)

    def _parse_json(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"[job_agent] Warning: could not parse JSON response")
            return {"fit_score": 0, "fit_label": "Unknown", "cover_letter": raw}

    def _fallback_materials(self, job_data: dict, profile: dict,
                            parsed_resume: dict | None) -> dict:
        personal = profile.get("personal", {})
        skills = profile.get("skills", {})
        all_skills = (
            skills.get("languages", []) +
            skills.get("frameworks", []) +
            skills.get("tools", [])
        )
        jd_text = self._job_text(job_data)
        jd_lower = jd_text.lower()

        required = job_data.get("required_skills") or []
        matched = []
        for skill in all_skills:
            pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, jd_lower):
                matched.append(skill)

        matched_lower = {m.lower() for m in matched}
        missing = [
            skill for skill in required
            if skill and skill.lower() not in matched_lower
        ][:8]

        role_score = self._score_role(job_data, profile)
        skill_denominator = max(len(required), min(len(all_skills), 8), 1)
        skill_score = min(45, int(45 * len(matched) / skill_denominator))
        location_score = self._score_location(job_data, profile)
        achievement_score = 10 if profile.get("key_achievements") else 5
        fit_score = max(0, min(100, role_score + skill_score + location_score + achievement_score))

        fit_label = (
            "Excellent" if fit_score >= 80 else
            "Good" if fit_score >= 65 else
            "Fair" if fit_score >= 50 else
            "Poor"
        )
        recommendation = "Apply" if fit_score >= self.min_fit_score else "Skip"

        highlights = profile.get("key_achievements", [])[:5]
        parsed_highlights = []
        if parsed_resume:
            parsed_highlights = parsed_resume.get("achievements", [])[:3]
        source_bullets = highlights or parsed_highlights or [
            profile.get("experience_summary", "Built and shipped production software systems.")
        ]

        title = job_data.get("title") or "this role"
        company = job_data.get("company") or "your company"
        skill_phrase = ", ".join(matched[:3]) or "strong engineering fundamentals"
        tailored_bullets = [
            f"{bullet} Relevant to {title} through {skill_phrase}."
            for bullet in source_bullets[:5]
        ]

        cover_letter = self._fallback_cover_letter(
            name=personal.get("name", ""),
            company=company,
            title=title,
            matched=matched,
            achievements=source_bullets,
        )

        return {
            "fit_score": fit_score,
            "fit_label": fit_label,
            "apply_recommendation": recommendation,
            "tailored_bullets": tailored_bullets,
            "skills_to_highlight": matched[:8] or all_skills[:5],
            "keywords_matched": matched[:10],
            "keywords_missing": missing,
            "cover_letter": cover_letter,
            "interview_questions": [
                {
                    "q": f"How would your experience help you succeed as {title}?",
                    "framework": "Use STAR and anchor the answer in a shipped project.",
                },
                {
                    "q": f"Which technical strengths are most relevant for {company}?",
                    "framework": f"Lead with {skill_phrase}.",
                },
            ],
            "salary_estimate": job_data.get("salary"),
            "fallback_used": True,
            "fallback_reason": self.llm_error,
        }

    def _score_role(self, job_data: dict, profile: dict) -> int:
        target_roles = profile.get("job_preferences", {}).get("target_roles", [])
        role_text = (job_data.get("title") or "").lower()
        role_tokens = set(re.split(r"\W+", role_text))
        score = 0
        for role in target_roles:
            role_lower = role.lower()
            role_words = {w for w in re.split(r"\W+", role_lower) if len(w) > 2}
            if role_lower in role_text:
                score = max(score, 30)
            elif role_words.intersection(role_tokens):
                score = max(score, 25)
        return score

    def _score_location(self, job_data: dict, profile: dict) -> int:
        prefs = profile.get("job_preferences", {})
        location = (job_data.get("location") or "").lower()
        if not location:
            return 10
        if "remote" in location and prefs.get("remote_ok", True):
            return 15
        for target in prefs.get("target_locations", []):
            target_lower = target.lower()
            if target_lower in location or location in target_lower:
                return 15
        return 5

    def _fallback_cover_letter(self, *, name: str, company: str, title: str,
                               matched: list[str], achievements: list[str]) -> str:
        skills_text = ", ".join(matched[:5]) if matched else "the required engineering stack"
        achievement_text = " ".join(achievements[:2]) if achievements else (
            "I have built reliable software systems and worked across the delivery lifecycle."
        )
        return (
            f"{company}'s {title} opening stood out because it calls for hands-on impact "
            f"with {skills_text}.\n\n"
            f"My background lines up with that need: {achievement_text}\n\n"
            f"I would welcome the chance to discuss how I can contribute to {company}'s team.\n\n"
            f"{name}"
        )

    def _job_text(self, job_data: dict) -> str:
        return " ".join([
            str(job_data.get("title", "")),
            str(job_data.get("description_snippet", "")),
            str(job_data.get("jd_text", "")),
            " ".join(job_data.get("required_skills", [])),
        ])

    def _slugify(self, value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        return cleaned or "item"

    def _format_cover_letter(self, body: str, job_data: dict, profile: dict) -> str:
        personal = profile.get("personal", {})
        header   = (
            f"{personal.get('name', '')}\n"
            f"{personal.get('email', '')} | {personal.get('phone', '')}\n"
            f"{personal.get('linkedin', '')}\n"
            f"{datetime.now().strftime('%B %d, %Y')}\n\n"
            f"Hiring Team\n"
            f"{job_data.get('company', '')}\n\n"
        )
        return header + body

    def _format_tailored_resume(self, materials: dict,
                                 job_data: dict, profile: dict) -> str:
        personal = profile.get("personal", {})
        lines    = [
            f"TAILORED RESUME — {job_data.get('title')} at {job_data.get('company')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Fit Score: {materials.get('fit_score')}/100 ({materials.get('fit_label')})",
            "=" * 60,
            "",
            f"{personal.get('name', '')}",
            f"{personal.get('email', '')} | {personal.get('phone', '')}",
            f"{personal.get('linkedin', '')} | {personal.get('github', '')}",
            "",
            "SKILLS TO HIGHLIGHT FOR THIS ROLE",
            "-" * 40,
        ]
        for skill in materials.get("skills_to_highlight", []):
            lines.append(f"  • {skill}")

        lines += [
            "",
            "TAILORED EXPERIENCE BULLETS",
            "-" * 40,
        ]
        for bullet in materials.get("tailored_bullets", []):
            lines.append(f"  • {bullet}")

        lines += [
            "",
            "KEYWORDS MATCHED",
            "-" * 40,
            "  " + ", ".join(materials.get("keywords_matched", [])),
            "",
            "KEYWORDS MISSING (consider addressing in cover letter)",
            "-" * 40,
            "  " + ", ".join(materials.get("keywords_missing", [])),
        ]

        if materials.get("interview_questions"):
            lines += ["", "INTERVIEW PREP", "-" * 40]
            for item in materials.get("interview_questions", [])[:5]:
                lines.append(f"Q: {item.get('q', '')}")
                lines.append(f"   → {item.get('framework', '')}")
                lines.append("")

        return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AutoApply — Job Application Agent")
    parser.add_argument("--job",      default=None, help="Job data as JSON string")
    parser.add_argument("--job-file", default=None, help="Path to job JSON file")
    parser.add_argument("--profile",  default="./profile.json", help="Path to profile.json")
    args = parser.parse_args()

    # Load profile
    if os.path.exists(args.profile):
        with open(args.profile) as f:
            profile = json.load(f)
    else:
        print(f"[job_agent] profile.json not found at {args.profile} — using sample")
        profile = {
            "personal": {
                "name": "Alex Kumar", "email": "alex@example.com",
                "phone": "+91-9876543210",
                "linkedin": "https://linkedin.com/in/alexkumar",
                "github":   "https://github.com/alexkumar",
            },
            "skills": {
                "languages":  ["Python", "JavaScript", "SQL"],
                "frameworks": ["FastAPI", "Django", "React"],
                "tools":      ["Docker", "Kubernetes", "Redis", "PostgreSQL"],
            },
            "experience": [{
                "role": "Backend Engineer", "company": "TechCorp",
                "duration": "2022-Present",
                "bullets": [
                    "Built REST APIs with FastAPI serving 50k daily users",
                    "Reduced API response time 40% with Redis caching",
                    "Deployed microservices on AWS using Docker + Kubernetes",
                ],
            }],
        }

    # Load job data
    if args.job_file and os.path.exists(args.job_file):
        with open(args.job_file) as f:
            job_data = json.load(f)
    elif args.job:
        job_data = json.loads(args.job)
    else:
        job_data = {
            "title":   "Senior Python Engineer",
            "company": "Stripe",
            "location": "Remote",
            "type":    "fulltime",
            "hr_email": "jobs@stripe.com",
            "description_snippet": (
                "Join Stripe's API Platform team to build high-performance APIs "
                "handling millions of requests per day. You'll work with Python, "
                "distributed systems, PostgreSQL, Redis, and Kubernetes. "
                "5+ years Python required. Strong REST API design skills essential."
            ),
            "required_skills": [
                "Python", "distributed systems", "REST APIs",
                "PostgreSQL", "Redis", "Kubernetes",
            ],
        }

    agent  = JobApplicationAgent()
    result = agent.process(job_data, profile)

    print("\n" + "=" * 60)
    print("JOB APPLICATION PACKAGE")
    print("=" * 60)
    print(f"Role:       {result['job'].get('title')} at {result['job'].get('company')}")
    print(f"Fit Score:  {result['fit_score']}/100 ({result['fit_label']})")
    print(f"Decision:   {'[APPLY] Apply' if result['should_apply'] else '[SKIP] Skip - ' + result.get('reason','')}")

    if result["should_apply"]:
        print(f"\nCover letter: {result['cover_letter_path']}")
        print(f"Tailored resume: {result['tailored_resume_path']}")
        print(f"\nSkills to highlight: {', '.join(result['skills_to_highlight'])}")
        print(f"Keywords matched:    {', '.join(result['keywords_matched'][:5])}")
        print(f"Keywords missing:   {', '.join(result['keywords_missing'][:5])}")
        print(f"\n--- COVER LETTER PREVIEW ---")
        print(result["cover_letter_text"][:600] + "...")

    return result


if __name__ == "__main__":
    main()
