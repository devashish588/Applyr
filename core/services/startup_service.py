"""
Startup discovery and referral workflow for Applyr.

Ranks remote-first startups, discovers contacts, and generates concise
LinkedIn-style outreach messages.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from db.db_client import get_db
from core.models import Resume, Profile, StartupCompany, Recruiter, ApplicationTracker, SeniorityLevel

logger = logging.getLogger(__name__)


STARTUP_SOURCES = [
    {"name": "Wellfound", "url": "https://wellfound.com/jobs", "weight": 92},
    {"name": "Otta", "url": "https://otta.com/jobs", "weight": 90},
    {"name": "Remote OK", "url": "https://remoteok.com/remote-dev-jobs", "weight": 88},
    {"name": "We Work Remotely", "url": "https://weworkremotely.com/categories/remote-programming-jobs", "weight": 87},
    {"name": "Ashby Jobs", "url": "https://jobs.ashbyhq.com", "weight": 86},
    {"name": "Y Combinator Jobs", "url": "https://www.ycombinator.com/jobs", "weight": 89},
]

PRIORITY_KEYWORDS = [
    "ai",
    "machine learning",
    "data science",
    "backend",
    "python",
    "remote",
    "startup",
    "entry-level",
    "internship",
]


class StartupDiscoveryService:
    def __init__(self):
        self.db = get_db()
        self.apollo_key = os.getenv("APOLLO_API_KEY", "")
        self.profile = self._load_profile()
        self.resume = self._load_resume()

    def _load_profile(self) -> Profile:
        profile_path = os.getenv("PROFILE_PATH", "profile.json")
        if not os.path.exists(profile_path):
            return Profile()
        try:
            import json

            with open(profile_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return Profile(**data)
        except Exception as exc:
            logger.warning("[startup] failed to load profile: %s", exc)
            return Profile()

    def _load_resume(self) -> Optional[Resume]:
        try:
            resume_data = self.db.get_resume_data()
            if resume_data and resume_data.get("parsed_json"):
                return Resume(**resume_data["parsed_json"])
        except Exception as exc:
            logger.warning("[startup] failed to load resume: %s", exc)
        return None

    def discover(self, limit: int = 20) -> list[dict]:
        candidates = self._seed_startups()
        ranked = [self._score_company(company) for company in candidates]
        ranked.sort(key=lambda item: item["overall_score"], reverse=True)
        top = ranked[:limit]

        for startup in top:
            self.db.save_startup_company(startup)

        return top

    def _seed_startups(self) -> list[dict]:
        seed_names = [
            "Linear", "Supabase", "Vercel", "Ramp", "Replit", "Pinecone", "Modal",
            "Turing", "TrueFoundry", "Eden", "Gamma", "Anthropic", "Perplexity",
            "Airtable", "Notion", "Lovable", "PostHog", "Clay", "Builder", "Temporal",
            "Scale AI", "Mistral", "Cohere", "OpenAI", "Hugging Face", "Databricks",
        ]
        results: list[dict] = []
        for index, name in enumerate(seed_names):
            source = STARTUP_SOURCES[index % len(STARTUP_SOURCES)]
            results.append({
                "company": name,
                "domain": self._guess_domain(name),
                "source": source["name"],
                "source_url": source["url"],
                "location": "Remote",
                "is_remote": True,
                "job_count": 1 + (index % 3),
                "careers_page_url": self._careers_url(name),
            })
        return results

    def _score_company(self, company: dict) -> dict:
        title_terms = self._resume_terms()
        keywords = company.get("company", "").lower().split()
        role_match = self._role_match(company["company"])
        tech_stack = self._tech_stack_match(title_terms, company["company"])
        experience = self._experience_match(company["company"])
        remote = 100 if company.get("is_remote") else 70

        resume_match = min(100, int((role_match * 0.4) + (tech_stack * 0.4) + (remote * 0.2)))
        overall = round((resume_match * 0.35) + (role_match * 0.2) + (tech_stack * 0.2) + (experience * 0.15) + (remote * 0.1))

        company.update({
            "resume_match_score": resume_match,
            "role_match_score": role_match,
            "tech_stack_match": tech_stack,
            "experience_match": experience,
            "remote_compatibility": remote,
            "overall_score": overall,
            "matched_roles": self._matched_roles(company["company"]),
            "matched_skills": self._matched_skills(title_terms, company["company"]),
            "keywords": PRIORITY_KEYWORDS,
            "summary": f"{company['company']} is a remote-first startup with strong {', '.join(PRIORITY_KEYWORDS[:3])} alignment.",
            "rank_reason": self._rank_reason(company["company"], overall),
            "discovered_at": datetime.now().isoformat(),
        })
        return company

    def _resume_terms(self) -> list[str]:
        terms: list[str] = []
        if self.profile.keywords:
            terms.extend(self.profile.keywords)
        if self.profile.target_roles:
            terms.extend(self.profile.target_roles)
        if self.resume:
            terms.extend(self.resume.skills[:20])
            terms.extend(self.resume.roles[:10])
        return [term.lower() for term in terms if term]

    def _role_match(self, company_name: str) -> int:
        text = company_name.lower()
        score = 55
        if any(term in text for term in ["ai", "ml", "data", "backend", "python", "startup"]):
            score += 20
        if any(role.lower() in text for role in self.profile.target_roles):
            score += 15
        return min(100, score)

    def _tech_stack_match(self, terms: list[str], company_name: str) -> int:
        if not terms:
            return 45
        text = f"{company_name.lower()} {' '.join(terms)}"
        hits = sum(1 for kw in PRIORITY_KEYWORDS if kw in text)
        return min(100, 35 + hits * 12)

    def _experience_match(self, company_name: str) -> int:
        title = company_name.lower()
        if any(kw in title for kw in ["intern", "junior", "entry"]):
            return 95
        if any(kw in title for kw in ["startup", "ai", "data", "python", "backend"]):
            return 80
        return 65

    def _matched_roles(self, company_name: str) -> list[str]:
        matches: list[str] = []
        text = company_name.lower()
        role_map = [
            ("AI Engineer", ["ai", "ml", "machine learning"]),
            ("Data Scientist", ["data", "analytics", "science"]),
            ("Backend Engineer", ["backend", "python", "api"]),
            ("ML Intern", ["intern", "entry", "junior"]),
            ("Startup Engineer", ["startup", "product"]),
        ]
        for role, tokens in role_map:
            if any(token in text for token in tokens):
                matches.append(role)
        return matches or ["Software Engineer"]

    def _matched_skills(self, terms: list[str], company_name: str) -> list[str]:
        text = company_name.lower()
        matched = [kw for kw in PRIORITY_KEYWORDS if kw in text]
        matched.extend([term for term in terms if term in text])
        return list(dict.fromkeys(matched))[:10]

    def _rank_reason(self, company_name: str, score: int) -> str:
        return f"{company_name} ranked {score}/100 based on remote compatibility, role fit, and resume alignment."

    def _guess_domain(self, company_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
        return f"{slug}.com"

    def _careers_url(self, company_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
        return f"https://{slug}.com/careers"

    def discover_contacts(self, company: str, limit: int = 6) -> list[dict]:
        contacts = self._apollo_contacts(company)
        for contact in contacts:
            contact["company"] = company
            contact["discovered_at"] = datetime.now().isoformat()
            self.db.save_company_contact(contact)
        contacts.sort(key=lambda item: item.get("rank_score", 0), reverse=True)
        return contacts[:limit]

    def _apollo_contacts(self, company: str) -> list[dict]:
        if not self.apollo_key:
            return self._fallback_contacts(company)

        # Placeholder Apollo integration path. This can be replaced with the
        # exact Apollo endpoint your tenant uses if needed.
        base_contacts = [
            {"name": f"{company} Recruiter", "role": "Recruiter", "department": "Talent", "source": "apollo", "contact_type": "recruiter", "rank_score": 95},
            {"name": f"{company} Engineering Manager", "role": "Engineering Manager", "department": "Engineering", "source": "apollo", "contact_type": "hiring_manager", "rank_score": 90},
            {"name": f"{company} Talent Partner", "role": "Talent Acquisition", "department": "People", "source": "apollo", "contact_type": "talent", "rank_score": 88},
            {"name": f"{company} Software Engineer", "role": "Engineer", "department": "Engineering", "source": "apollo", "contact_type": "engineer", "rank_score": 72},
            {"name": f"{company} Alumni", "role": "Former Employee", "department": "Alumni", "source": "apollo", "contact_type": "alumni", "rank_score": 60},
        ]
        for contact in base_contacts:
            contact["email"] = self._guess_email(company, contact["name"])
            contact["linkedin"] = self._linkedin_url(contact["name"])
        return base_contacts

    def _fallback_contacts(self, company: str) -> list[dict]:
        return [
            {"name": f"{company} Recruiting Team", "role": "Recruiting", "department": "Talent", "email": None, "source": "fallback", "contact_type": "recruiter", "rank_score": 60, "linkedin": None},
            {"name": f"{company} Hiring Manager", "role": "Hiring Manager", "department": "Engineering", "email": None, "source": "fallback", "contact_type": "hiring_manager", "rank_score": 55, "linkedin": None},
        ]

    def _guess_email(self, company: str, contact_name: str) -> str:
        domain = self._guess_domain(company)
        slug = re.sub(r"[^a-z]", "", contact_name.lower().split()[0])
        return f"{slug}@{domain}"

    def _linkedin_url(self, contact_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "", contact_name.lower())
        return f"https://www.linkedin.com/in/{slug}"

    def generate_linkedin_message(self, company: str, contact_name: str, project_hint: Optional[str] = None) -> str:
        project = project_hint or (self.resume.projects[0].get("name") if self.resume and self.resume.projects else "a recent project")
        role = self.profile.target_roles[0] if self.profile.target_roles else "software engineer"
        msg = (
            f"Hi {contact_name.split()[0]}, I’m exploring opportunities at {company} and was especially drawn to your team’s work. "
            f"My background is in {role.lower()}, and I recently built {project}. I’d love to connect and learn more about your experience at {company}. "
            "I’ve attached my resume in case it’s helpful."
        )
        return self._trim_message(msg)

    def _trim_message(self, message: str, max_words: int = 120) -> str:
        words = message.split()
        if len(words) <= max_words:
            return message
        return " ".join(words[:max_words]).rstrip(" ,;.") + "..."

    def create_application_tracker_entry(self, item: dict) -> dict:
        follow_up = item.get("follow_up_date") or (datetime.now() + timedelta(days=6)).isoformat()
        second_follow_up = item.get("second_follow_up_date") or (datetime.now() + timedelta(days=17)).isoformat()
        payload = {
            **item,
            "follow_up_date": follow_up,
            "second_follow_up_date": second_follow_up,
            "updated_at": datetime.now().isoformat(),
        }
        self.db.upsert_application_tracker(payload)
        return payload

    def get_tracker(self) -> list[dict]:
        return self.db.get_application_tracker()

    def get_followups_due(self) -> list[dict]:
        return self.db.get_followups_due()
