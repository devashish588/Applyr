"""
Deduplicator - checks if job has already been applied to
"""
from db.db_client import get_db
from typing import Optional, Dict, Any


class Deduplicator:
    """Prevent duplicate applications to the same company."""
    
    def __init__(self):
        self.db = get_db()
    
    def has_applied_to_company(self, company: str) -> bool:
        """Check if we've already applied to this company."""
        return self.db.email_exists_for_company(company)
    
    def has_applied_to_url(self, url: str) -> bool:
        """Check if we've already applied to this specific job URL."""
        return self.db.job_exists(url)
    
    def get_company_applications(self, company: str) -> list:
        """Get all applications to a specific company."""
        return self.db.get_jobs_by_company(company)
    
    def should_skip_job(self, job_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Determine if job should be skipped.
        
        Returns:
            tuple: (should_skip, reason)
        """
        company = job_data.get("company", "").strip()
        url = job_data.get("url", "").strip()
        
        if not company or not url:
            return True, "Missing company or URL"
        
        # Check if URL already in database
        if self.has_applied_to_url(url):
            return True, "Job URL already processed"
        
        # Check if already applied to this company
        if self.has_applied_to_company(company):
            # Allow multiple applications to same company but different roles
            # This is more lenient - comment out if strict one-per-company policy needed
            return False, None
        
        return False, None
    
    def log_duplicate_check(self, company: str, url: str) -> Dict[str, Any]:
        """Get detailed deduplication info."""
        applied_to_company = self.has_applied_to_company(company)
        url_exists = self.has_applied_to_url(url)
        company_apps = self.get_company_applications(company)
        
        return {
            "company": company,
            "url": url,
            "applied_to_company_before": applied_to_company,
            "url_exists_in_db": url_exists,
            "previous_applications": len(company_apps),
            "should_skip": url_exists
        }
