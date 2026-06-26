"""
Email template loader — fills email/templates/cold_email.txt and
follow_up.txt with placeholder substitution.

Wires into email_drafting_agent.py's personalize_email() method,
or can be used standalone for the follow-up flow.
"""

import os
import re
from pathlib import Path

TEMPLATE_DIR = os.getenv("EMAIL_TEMPLATE_DIR", "./email_module/templates")


def load_template(name: str) -> str:
    """name: 'cold_email' or 'follow_up' (no .txt extension needed)"""
    path = Path(TEMPLATE_DIR) / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Template not found: {path}. "
            f"Expected files: {TEMPLATE_DIR}/cold_email.txt, {TEMPLATE_DIR}/follow_up.txt"
        )
    return path.read_text(encoding="utf-8")


def fill_template(template: str, values: dict) -> tuple:
    """
    Replace {{key}} placeholders with values.
    Any placeholder left unfilled is logged as a warning and replaced
    with empty string (rather than left as literal {{text}} in the email).
    """
    result = template
    found_placeholders = set(re.findall(r"\{\{(\w+)\}\}", template))
    missing = found_placeholders - set(values.keys())

    for key, val in values.items():
        result = result.replace(f"{{{{{key}}}}}", str(val) if val is not None else "")

    for key in missing:
        result = result.replace(f"{{{{{key}}}}}", "")

    return result, missing


def build_cold_email(job_data: dict, profile: dict, materials: dict) -> dict:
    """
    Fill cold_email.txt using job + profile + tailoring data.

    job_data:   from web_research_agent / pdf_qa_agent
    profile:    profile.json
    materials:  output of job_application_agent.process() — has
                skills_to_highlight, keywords_matched, etc.
    """
    personal = profile.get("personal", {})
    skills   = profile.get("skills", {})
    exp      = profile.get("experience", [])

    all_skills = (
        skills.get("languages", []) + skills.get("frameworks", []) + skills.get("tools", [])
    )
    main_skills = ", ".join(
        materials.get("skills_to_highlight") or all_skills[:5]
    )

    years_experience = profile.get("personal", {}).get("years_experience")
    if not years_experience and exp:
        years_experience = len(exp)

    bullets = materials.get("tailored_bullets") or []
    key_achievement_1 = bullets[0] if len(bullets) > 0 else (
        exp[0]["bullets"][0] if exp and exp[0].get("bullets") else ""
    )
    key_achievement_2 = bullets[1] if len(bullets) > 1 else (
        exp[0]["bullets"][1] if exp and exp[0].get("bullets", []) and len(exp[0]["bullets"]) > 1 else ""
    )

    values = {
        "company_hiring_manager": "Hiring Team",
        "role":           job_data.get("title", ""),
        "company":        job_data.get("company", ""),
        "main_skills":    main_skills,
        "years_experience": years_experience or "several",
        "key_achievement_1": key_achievement_1,
        "key_achievement_2": key_achievement_2,
        "name":     personal.get("name", ""),
        "phone":    personal.get("phone", ""),
        "email":    personal.get("email", ""),
        "linkedin": personal.get("linkedin", ""),
    }

    template = load_template("cold_email")
    body, missing = fill_template(template, values)

    if missing:
        import logging
        logging.getLogger(__name__).warning(
            f"[email_template] cold_email.txt has unfilled placeholders: {missing}"
        )

    subject = f"Application: {job_data.get('title', '')} — {personal.get('name', '')}"
    return {
        "subject": subject,
        "body": body,
        "to": job_data.get("hr_email"),
        "missing_placeholders": list(missing),
    }


def build_follow_up(job_data: dict, profile: dict, materials: dict) -> dict:
    """
    Fill follow_up.txt — for jobs that were applied to N days ago
    with no response. Not yet wired into the orchestrator.
    """
    personal = profile.get("personal", {})
    main_skills = ", ".join(materials.get("skills_to_highlight", [])[:4])

    values = {
        "company_hiring_manager": "Hiring Team",
        "role":         job_data.get("title", ""),
        "company":      job_data.get("company", ""),
        "main_skills":  main_skills,
        "name":         personal.get("name", ""),
    }

    template = load_template("follow_up")
    body, missing = fill_template(template, values)

    subject = f"Following up: {job_data.get('title', '')} application"
    return {
        "subject": subject,
        "body": body,
        "to": job_data.get("hr_email"),
        "missing_placeholders": list(missing),
    }
