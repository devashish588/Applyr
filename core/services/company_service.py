"""
Company Service for Applyr AI job application platform.

This service extracts, validates, and enriches company information
from job listings.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from core.models import Company, Job

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for managing company information."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.company_cache = {}

    def extract_company_from_job(self, job: Job) -> Tuple[Optional[str], float]:
        """
        Extract company name from a job listing.

        Args:
            job: Job object containing job listing

        Returns:
            Tuple of (company_name, confidence_score)
        """
        if not job.company:
            return None, 0.0

        company_name = job.company.strip()
        confidence = self._calculate_extraction_confidence(job)

        # Clean company name
        company_name = self._clean_company_name(company_name)

        # Check cache
        cache_key = company_name.lower()
        if cache_key in self.company_cache:
            cached_company = self.company_cache[cache_key]
            return cached_company.get("name"), cached_company.get("confidence", 0.0)

        # Store in cache
        self.company_cache[cache_key] = {
            "name": company_name,
            "confidence": confidence,
        }

        return company_name, confidence

    def _calculate_extraction_confidence(self, job: Job) -> float:
        """
        Calculate confidence score for company extraction.

        Args:
            job: Job object containing job listing

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0

        # Check if company name is valid
        if job.company and len(job.company) > 2:
            confidence += 0.3

        # Check if company name is not a placeholder
        if job.company and not self._is_placeholder_company(job.company):
            confidence += 0.4

        # Check if company name has proper format
        if job.company and self._is_valid_company_format(job.company):
            confidence += 0.3

        return min(confidence, 1.0)

    def _clean_company_name(self, company_name: str) -> str:
        """
        Clean company name by removing noise and standardizing format.

        Args:
            company_name: Raw company name

        Returns:
            Cleaned company name
        """
        if not company_name:
            return ""

        # Remove common noise
        noise_patterns = [
            r"\s*\(.*\)",  # Remove parentheses content
            r"\s*@\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # Remove email
            r"\s*\d{4}\s*\d{4}",  # Remove phone numbers
            r"\s*www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # Remove website
            r"\s*https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # Remove URLs
        ]

        cleaned = company_name
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Handle common abbreviations
        cleaned = re.sub(r"\bInc\.?\b", "Inc", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bLLC\b", "LLC", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bGmbH\b", "GmbH", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bLtd\b", "Ltd", cleaned, flags=re.IGNORECASE)

        return cleaned

    def _is_placeholder_company(self, company_name: str) -> bool:
        """
        Check if company name is a placeholder.

        Args:
            company_name: Company name to check

        Returns:
            True if company name is a placeholder
        """
        placeholder_patterns = [
            r"^none$",
            r"^null$",
            r"^n/a$",
            r"^unknown$",
            r"^not extracted$",
            r"^company not extracted$",
            r"^unknown company$",
            r"^company not found$",
            r"^no company$",
        ]

        lower_name = company_name.lower()
        for pattern in placeholder_patterns:
            if re.match(pattern, lower_name):
                return True

        return False

    def _is_valid_company_format(self, company_name: str) -> bool:
        """
        Check if company name has a valid format.

        Args:
            company_name: Company name to check

        Returns:
            True if company name has valid format
        """
        # Company name should contain at least one letter
        if not re.search(r"[a-zA-Z]", company_name):
            return False

        # Company name should not be too short
        if len(company_name) < 2:
            return False

        # Company name should not be all numbers
        if re.match(r"^\d+$", company_name):
            return False

        return True

    def enrich_company(self, company_name: str, confidence: float) -> Company:
        """
        Enrich company information.

        Args:
            company_name: Company name
            confidence: Extraction confidence score

        Returns:
            Company object with enriched information
        """
        company = Company(
            name=company_name,
            extraction_confidence=confidence,
            enriched=False,
        )

        # Try to extract domain from company name
        domain = self._extract_domain_from_company(company_name)
        if domain:
            company.domain = domain

        # Enrich company information
        self._enrich_company_data(company)

        return company

    def _extract_domain_from_company(self, company_name: str) -> Optional[str]:
        """
        Extract domain from company name.

        Args:
            company_name: Company name

        Returns:
            Extracted domain or None
        """
        # Clean company name
        cleaned = self._clean_company_name(company_name)

        # Common domains
        common_domains = {
            "google": "google.com",
            "microsoft": "microsoft.com",
            "amazon": "amazon.com",
            "apple": "apple.com",
            "facebook": "facebook.com",
            "meta": "meta.com",
            "netflix": "netflix.com",
            "tesla": "tesla.com",
            "spacex": "spacex.com",
            "uber": "uber.com",
            "lyft": "lyft.com",
            "airbnb": "airbnb.com",
            "stripe": "stripe.com",
            "square": "square.com",
            "paypal": "paypal.com",
            "adobe": "adobe.com",
            "salesforce": "salesforce.com",
            "oracle": "oracle.com",
            "ibm": "ibm.com",
            "intel": "intel.com",
            "amd": "amd.com",
            "nvidia": "nvidia.com",
            "tesla": "tesla.com",
            "spacex": "spacex.com",
            "twitter": "twitter.com",
            "x": "x.com",
            "linkedin": "linkedin.com",
            "github": "github.com",
            "gitlab": "gitlab.com",
            "bitbucket": "bitbucket.org",
            "atlassian": "atlassian.com",
            "jira": "atlassian.com",
            "confluence": "atlassian.com",
            "slack": "slack.com",
            "discord": "discord.com",
            "zoom": "zoom.us",
            "webex": "webex.com",
            "teams": "microsoft.com",
            "office": "microsoft.com",
            "outlook": "microsoft.com",
            "gmail": "google.com",
            "yahoo": "yahoo.com",
            "hotmail": "microsoft.com",
            "aol": "aol.com",
            "protonmail": "protonmail.com",
            "tutanota": "tutanota.com",
            "duckduckgo": "duckduckgo.com",
            "bing": "microsoft.com",
            "google": "google.com",
            "yandex": "yandex.com",
            "baidu": "baidu.com",
            "sina": "sina.com",
            "tencent": "tencent.com",
            "alibaba": "alibaba.com",
            "jd": "jd.com",
            "pinduoduo": "pinduoduo.com",
            "taobao": "taobao.com",
            "tmall": "tmall.com",
            "weibo": "weibo.com",
            "qq": "qq.com",
            "wechat": "wechat.com",
            "line": "line.me",
            "kakao": "kakao.com",
            "naver": "naver.com",
            "daum": "daum.net",
            "yahoo": "yahoo.com",
            "aol": "aol.com",
            "hotmail": "microsoft.com",
            "outlook": "microsoft.com",
            "gmail": "google.com",
            "icloud": "icloud.com",
            "me": "me.com",
            "mac": "apple.com",
            "windows": "microsoft.com",
            "linux": "linux.org",
            "ubuntu": "ubuntu.com",
            "debian": "debian.org",
            "fedora": "fedora.org",
            "centos": "centos.org",
            "red hat": "redhat.com",
            "suse": "suse.com",
            "oracle": "oracle.com",
            "sap": "sap.com",
            "ibm": "ibm.com",
            "hp": "hp.com",
            "dell": "dell.com",
            "lenovo": "lenovo.com",
            "asus": "asus.com",
            "acer": "acer.com",
            "msi": "msi.com",
            "razer": "razer.com",
            "logitech": "logitech.com",
            "corsair": "corsair.com",
            "steelseries": "steelseries.com",
            "hyperx": "hyperxgaming.com",
            " Kingston": "kingston.com",
            "crucial": "crucial.com",
            "seagate": "seagate.com",
            "wd": "wd.com",
            "toshiba": "toshiba.com",
            "hitachi": "hitachi.com",
            "western digital": "wd.com",
            "sandisk": "sandisk.com",
            "transcend": "transcend.com",
            "kingston": "kingston.com",
            "crucial": "crucial.com",
            "intel": "intel.com",
            "amd": "amd.com",
            "nvidia": "nvidia.com",
            "msi": "msi.com",
            "asus": "asus.com",
            "acer": "acer.com",
            "dell": "dell.com",
            "hp": "hp.com",
            "lenovo": "lenovo.com",
            "thinkpad": "lenovo.com",
            "macbook": "apple.com",
            "imac": "apple.com",
            "mac": "apple.com",
            "iphone": "apple.com",
            "ipad": "apple.com",
            "apple watch": "apple.com",
            "apple tv": "apple.com",
            "airpods": "apple.com",
            "homepod": "apple.com",
            "apple card": "apple.com",
            "apple pay": "apple.com",
            "apple id": "apple.com",
            "icloud": "icloud.com",
            "faceid": "apple.com",
            "touchid": "apple.com",
            "fingerprint": "apple.com",
            "siri": "apple.com",
            "google assistant": "google.com",
            "alexa": "amazon.com",
            "cortana": "microsoft.com",
            "bixby": "samsung.com",
            "samsung": "samsung.com",
            "oneplus": "oneplus.com",
            "xiaomi": "xiaomi.com",
            "huawei": "huawei.com",
            "oppo": "oppo.com",
            "vivo": "vivo.com",
            "realme": "realme.com",
            "motorola": "motorola.com",
            "lg": "lg.com",
            "panasonic": "panasonic.com",
            "sharp": "sharp.com",
            "toshiba": "toshiba.com",
            "hitachi": "hitachi.com",
            "fujitsu": "fujitsu.com",
            "nec": "nec.com",
            "sony": "sony.com",
            "sony ericsson": "sony.com",
            "sony pictures": "sony.com",
            "sony music": "sony.com",
            "sony tv": "sony.com",
            "sony playstation": "sony.com",
            "sony ps5": "sony.com",
            "sony ps4": "sony.com",
            "sony ps3": "sony.com",
            "sony ps2": "sony.com",
            "sony ps1": "sony.com",
            "sony vita": "sony.com",
            "sony psp": "sony.com",
            "sony ps vita": "sony.com",
            "sony playstation portable": "sony.com",
            "sony playstation 2": "sony.com",
            "sony playstation 3": "sony.com",
            "sony playstation 4": "sony.com",
            "sony playstation 5": "sony.com",
        }

        cleaned_lower = cleaned.lower()
        for company, domain in common_domains.items():
            if company in cleaned_lower:
                return domain

        # Try to guess domain from company name
        domain = self._guess_domain_from_company(cleaned)
        return domain

    def _guess_domain_from_company(self, company_name: str) -> Optional[str]:
        """
        Guess domain from company name.

        Args:
            company_name: Company name

        Returns:
            Guessed domain or None
        """
        # Remove common suffixes
        cleaned = company_name.lower()
        cleaned = re.sub(r"\s+(inc|llc|gmbh|pty|limited|corp|corporation|s.a.|ltd)", "", cleaned)
        cleaned = re.sub(r"\s+(technologies|technology|solutions|services|systems|industries|enterprises)", "", cleaned)

        # Remove common prefixes
        cleaned = re.sub(r"^(the|new|old|global|international|united|american)", "", cleaned)

        # Replace spaces with dots
        domain = re.sub(r"\s+", ".", cleaned)

        # Add common TLDs
        for tld in ["com", "net", "org", "io", "co", "ai", "tech", "app", "dev"]:
            test_domain = f"{domain}.{tld}"
            if len(test_domain) < 63 and all(c.isalnum() or c == '.' for c in test_domain):
                return test_domain

        return None

    def _enrich_company_data(self, company: Company) -> None:
        """
        Enrich company data with additional information.

        Args:
            company: Company object to enrich
        """
        # This would typically call an external API to enrich company data
        # For now, we'll just mark it as enriched
        company.enriched = True

    def validate_company(self, company: Company) -> List[str]:
        """
        Validate a company and return any errors.

        Args:
            company: Company to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not company.name:
            errors.append("Company name is required")

        if company.name and self._is_placeholder_company(company.name):
            errors.append("Company name is a placeholder")

        if company.name and len(company.name) < 2:
            errors.append("Company name is too short")

        if company.name and company.extraction_confidence < 0.5:
            errors.append("Company extraction confidence is too low")

        return errors


# Singleton instance
_company_service = None


def get_company_service() -> CompanyService:
    """Get the singleton CompanyService instance."""
    global _company_service
    if _company_service is None:
        _company_service = CompanyService()
    return _company_service