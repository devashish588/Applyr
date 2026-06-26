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
import urllib.parse
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)


class RecruiterDiscoveryAgent:
    """Discover recruiter contact information with confidence scoring."""

    def __init__(self):
        self.apollo_key = os.getenv("APOLLO_API_KEY", "")
        self.clearbit_key = os.getenv("CLEARBIT_API_KEY", "")
        if self.apollo_key:
            logger.info("[recruiter] Apollo.io API key loaded")
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
        if not domain:
            domain = self._guess_domain(company)

        # 1. Apollo.io
        if self.apollo_key:
            result = self._apollo_lookup(domain, company)
            if result:
                result["company"] = company
                result["discovered_at"] = datetime.now().isoformat()
                self._log_recruiter(result)
                return result

        # 2. Clearbit
        if self.clearbit_key:
            result = self._clearbit_lookup(domain)
            if result:
                result["company"] = company
                result["discovered_at"] = datetime.now().isoformat()
                self._log_recruiter(result)
                return result

        return None

    def _apollo_lookup(self, domain: str, company: str) -> dict | None:
        """Apollo.io API — company contact discovery."""
        try:
            url = "https://api.apollo.io/v1/contacts/search"
            
            # Search by domain and HR/Recruiter keywords
            payload = {
                "domain": domain,
                "titles": ["Recruiter", "HR Manager", "Talent Acquisition", "People Operations", "HR Lead"],
                "per_page": 1,
                "page": 1,
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.apollo_key}",
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                response_data = json.loads(resp.read())
            
            contacts = response_data.get("contacts", [])
            if contacts:
                contact = contacts[0]
                result = {
                    "name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                    "title": contact.get("title", ""),
                    "email": contact.get("email", ""),
                    "confidence": 85,  # Apollo.io is highly reliable
                    "source": "apollo.io",
                }
                logger.info(f"[recruiter] Apollo.io found: {result['email']} for {domain}")
                return result
            else:
                logger.debug(f"[recruiter] Apollo.io: No contacts found for {domain}")
        
        except Exception as e:
            logger.debug(f"[recruiter] Apollo.io lookup failed for {domain}: {e}")
        
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
                "name": result.get("name", ""),
                "role": result.get("title", ""),
                "email": result.get("email", ""),
                "confidence": result.get("confidence", 0),
                "source": result.get("source", ""),
                "discovered_at": result.get("discovered_at", datetime.now().isoformat()),
            })
        except Exception as e:
            logger.warning(f"[recruiter] Failed to persist: {e}")
