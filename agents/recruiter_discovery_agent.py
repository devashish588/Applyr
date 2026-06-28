"""
Recruiter Discovery Agent — AutoApply AI

Multi-provider recruiter discovery:
  1. Apollo.io (primary) — company contact discovery
  2. Clearbit (secondary) — company enrichment
  3. Naive guess (fallback)

Stores recruiter records with confidence scores.
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)


class RecruiterDiscoveryAgent:
    """Discover recruiter contact information with confidence scoring."""

    def __init__(self):
        self.apollo_key = os.getenv("APOLLO_API_KEY", "")
        self.hunter_key = os.getenv("HUNTER_API_KEY", "")
        self.clearbit_key = os.getenv("CLEARBIT_API_KEY", "")
        if self.apollo_key:
            logger.info("[recruiter] Apollo.io API key loaded")
        if self.hunter_key:
            logger.info("[recruiter] Hunter API key loaded")
        if self.clearbit_key:
            logger.info("[recruiter] Clearbit API key loaded")

    def find_email(self, job_data: dict) -> str | None:
        """Public entry point — returns best email or None."""
        # Already have one?
        existing = job_data.get("hr_email")
        if existing:
            return existing

        company = job_data.get("company")
        if not company:
            return None

        result = self.discover(job_data)
        return result.get("email") if result else None

    def discover(self, job_data: dict) -> dict | None:
        """
        Full discovery pipeline.

        Returns:
            {
                "name": "Jane Recruiter",
                "title": "HR Manager",
                "email": "jane@company.com",
                "confidence": 90,
                "source": "hunter",
                "company": "Acme Inc",
            } or None
        """
        company = job_data.get("company", "")
        domain = self._extract_domain(company, job_data.get("url", ""))
        # If the URL points at a job board / aggregator (linkedin, indeed…), its
        # domain is NOT the employer — guess from the company name instead, so we
        # don't surface the job board's own staff as the recruiter.
        if not domain or self._is_job_board(domain):
            domain = self._guess_domain(company)

        # 1. Apollo.io (best, but people search needs a paid plan)
        # 2. Hunter.io (domain email search — works on free tier)
        # 3. Clearbit (enrichment)
        # 4. Pattern fallback (generic application inbox) so outreach is always possible
        for provider, fn in (
            ("apollo",   lambda: self._apollo_lookup(domain, company) if self.apollo_key else None),
            ("hunter",   lambda: self._hunter_lookup(domain) if self.hunter_key else None),
            ("clearbit", lambda: self._clearbit_lookup(domain) if self.clearbit_key else None),
            ("pattern",  lambda: self._pattern_contact(domain, company)),
        ):
            result = fn()
            if result and result.get("email"):
                result["company"] = company
                result["discovered_at"] = datetime.now().isoformat()
                self._log_recruiter(result)
                return result

        return None

    def _pattern_contact(self, domain: str, company: str) -> dict | None:
        """Last-resort guess: a generic application inbox at the company domain.

        Low confidence and clearly labelled so the user knows it's inferred, but
        it keeps the Networking page populated and gives the Review & Send flow a
        recipient when no specific recruiter can be found.
        """
        if not domain:
            return None
        return {
            "name": "Hiring Team",
            "title": "Recruiting / Talent",
            "email": f"careers@{domain}",
            "confidence": 25,
            "source": "pattern",
            "company": company,
        }

    def _apollo_lookup(self, domain: str, company: str) -> dict | None:
        """Apollo.io people search.

        Auth is via the ``X-Api-Key`` header (NOT ``Authorization: Bearer``), and
        people search lives at ``/api/v1/mixed_people/search``. People search +
        email reveal require a PAID plan — free keys get HTTP 403
        (API_INACCESSIBLE), which we handle gracefully and fall through to the
        pattern fallback in ``discover()``.
        """
        try:
            url = "https://api.apollo.io/api/v1/mixed_people/search"
            payload = {
                "q_organization_domains": domain,
                "person_titles": ["Recruiter", "Talent Acquisition", "Technical Recruiter",
                                   "HR Manager", "People Operations"],
                "per_page": 1,
            }
            headers = {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": self.apollo_key,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                response_data = json.loads(resp.read())

            people = response_data.get("people", []) or response_data.get("contacts", [])
            if people:
                p = people[0]
                email = (p.get("email") or "").strip()
                # Apollo masks locked emails as "email_not_unlocked@domain.com".
                if "not_unlocked" in email:
                    email = ""
                name = p.get("name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
                if email:
                    logger.info(f"[recruiter] Apollo found {name or 'a contact'} <{email}> for {domain}")
                    return {
                        "name": name, "title": p.get("title", ""), "email": email,
                        "confidence": 85, "source": "apollo.io",
                    }
                logger.debug(f"[recruiter] Apollo person had no unlocked email for {domain}")
            else:
                logger.debug(f"[recruiter] Apollo: no people for {domain}")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                logger.info(f"[recruiter] Apollo not accessible (HTTP {e.code} — plan/auth); using fallback")
            else:
                logger.debug(f"[recruiter] Apollo HTTP {e.code} for {domain}")
        except Exception as e:
            logger.debug(f"[recruiter] Apollo lookup failed for {domain}: {e}")

        return None

    def _hunter_lookup(self, domain: str) -> dict | None:
        """Hunter API — email finder (deprecated, kept for backwards compatibility)."""
        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={urllib.parse.quote(domain)}&api_key={self.hunter_key}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            email_data = data.get("data", {})
            emails = email_data.get("emails", [])

            # Filter to likely recruiter/HR titles and sort by confidence
            hr_keywords = ["hr", "recruit", "talent", "people", "hiring", "personnel"]
            scored = []
            for e in emails:
                title = (e.get("position", "") or "").lower()
                confidence = e.get("confidence", 50)

                # Boost HR/recruiter titles
                if any(kw in title for kw in hr_keywords):
                    confidence = min(99, confidence + 20)

                scored.append({
                    "name": e.get("first_name", "") + " " + e.get("last_name", ""),
                    "title": e.get("position", ""),
                    "email": e.get("value", ""),
                    "confidence": confidence,
                    "source": "hunter",
                })

            if scored:
                scored.sort(key=lambda x: x["confidence"], reverse=True)
                best = scored[0]
                logger.info(f"[recruiter] Hunter found: {best['email']} ({best['confidence']}%) for {domain}")
                return best

        except Exception as e:
            logger.debug(f"[recruiter] Hunter lookup failed for {domain}: {e}")

        return None

    def _clearbit_lookup(self, domain: str) -> dict | None:
        """Clearbit Enrichment API — fallback."""
        if not self.clearbit_key:
            return None
        try:
            url = f"https://company.clearbit.com/v2/companies/find?domain={urllib.parse.quote(domain)}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {self.clearbit_key}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            email = data.get("email")
            if email:
                return {
                    "name": data.get("name", ""),
                    "title": "Contact",
                    "email": email,
                    "confidence": 60,
                    "source": "clearbit",
                }

            contacts = data.get("contacts", [])
            for contact in contacts:
                title = (contact.get("title") or "").lower()
                if "hr" in title or "recruit" in title:
                    return {
                        "name": contact.get("name", {}).get("fullName", ""),
                        "title": contact.get("title", ""),
                        "email": contact.get("email"),
                        "confidence": 50,
                        "source": "clearbit",
                    }
        except Exception as e:
            logger.debug(f"[recruiter] Clearbit lookup failed for {domain}: {e}")

        return None

    def _extract_domain(self, company: str, url: str | None) -> str | None:
        """Extract domain from job URL or company name."""
        if url:
            match = re.search(r"https?://(?:www\.)?([^/]+)", url)
            if match:
                return match.group(1)
        return None

    def _guess_domain(self, company_name: str) -> str:
        cleaned = company_name.lower().replace(" ", "").replace(",", "").replace(".", "")
        cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
        return f"{cleaned}.com"

    def _log_recruiter(self, result: dict):
        """Persist recruiter record to DB."""
        try:
            from db.db_client import get_db
            get_db().save_recruiter({
                "company": result.get("company", ""),
                "name": result.get("name", ""),
                "role": result.get("title", ""),
                "email": result.get("email", ""),
                "confidence": result.get("confidence", 0),
                "source": result.get("source", ""),
                "discovered_at": result.get("discovered_at", datetime.now().isoformat()),
            })
        except Exception as e:
            logger.warning(f"[recruiter] Failed to persist: {e}")
