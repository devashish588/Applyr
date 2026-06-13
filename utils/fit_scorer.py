"""
Fit scorer - scores job fit against user profile (0-100)
"""
from utils.profile_loader import get_profile
from typing import Dict, Any, List
import re


class FitScorer:
    """Score job fit based on skills and preferences match."""
    
    def __init__(self):
        self.profile = get_profile()
        self.target_roles = self.profile.get_target_roles()
        self.target_locations = self.profile.get_job_preferences().get("target_locations", [])
        self.skills = self.profile.get_skills()
        self.job_prefs = self.profile.get_job_preferences()
    
    def score_job(self, job_data: Dict[str, Any]) -> int:
        """
        Score a job 0-100 based on fit.
        
        Scoring breakdown:
        - Role match: 30 points
        - Skills match: 40 points
        - Location match: 20 points
        - Salary match: 10 points (if available)
        """
        score = 0
        
        # Role match (30 points)
        role_score = self._score_role(job_data.get("title", ""))
        score += role_score
        
        # Skills match (40 points)
        skills_score = self._score_skills(job_data.get("jd_text", ""))
        score += skills_score
        
        # Location match (20 points)
        location_score = self._score_location(job_data.get("location", ""))
        score += location_score
        
        # Salary match (10 points)
        salary_score = self._score_salary(job_data.get("salary", ""))
        score += salary_score
        
        return min(100, max(0, score))
    
    def _score_role(self, job_title: str) -> int:
        """Score based on role match (0-30)."""
        if not job_title:
            return 0
        
        title_lower = job_title.lower()
        score = 0
        
        for target_role in self.target_roles:
            target_lower = target_role.lower()
            # Exact or substring match
            if target_lower in title_lower or title_lower in target_lower:
                score = 30
                break
            # Partial match
            if any(word in title_lower for word in target_lower.split()):
                score = max(score, 20)
        
        return score
    
    def _score_skills(self, jd_text: str) -> int:
        """Score based on skills match (0-40)."""
        if not jd_text:
            return 0
        
        jd_lower = jd_text.lower()
        matched_skills = []
        
        # Check languages
        for lang in self.skills.get("languages", []):
            if lang.lower() in jd_lower:
                matched_skills.append(lang)
        
        # Check frameworks
        for fw in self.skills.get("frameworks", []):
            if fw.lower() in jd_lower:
                matched_skills.append(fw)
        
        # Check tools
        for tool in self.skills.get("tools", []):
            if tool.lower() in jd_lower:
                matched_skills.append(tool)
        
        total_skills = len(self.skills.get("languages", [])) + \
                      len(self.skills.get("frameworks", [])) + \
                      len(self.skills.get("tools", []))
        
        if total_skills == 0:
            return 0
        
        match_percentage = len(matched_skills) / total_skills
        return int(40 * match_percentage)
    
    def _score_location(self, job_location: str) -> int:
        """Score based on location match (0-20)."""
        if not job_location or not self.target_locations:
            # Assume remote-friendly if not specified
            return 10
        
        location_lower = job_location.lower()
        
        # Check for remote
        if "remote" in location_lower:
            if self.job_prefs.get("remote_ok", True):
                return 20
            else:
                return 0
        
        # Check specific locations
        for target_loc in self.target_locations:
            target_lower = target_loc.lower()
            if target_lower in location_lower or location_lower in target_lower:
                return 20
        
        return 5  # Partial credit for unspecified location
    
    def _score_salary(self, salary_str: str) -> int:
        """Score based on salary match (0-10)."""
        if not salary_str:
            return 5  # Neutral if not specified
        
        min_salary = self.job_prefs.get("min_salary", 0)
        if min_salary == 0:
            return 5  # No preference specified
        
        # Try to extract salary numbers
        numbers = re.findall(r'\d+', salary_str)
        if not numbers:
            return 5
        
        max_salary_in_range = max(int(n) for n in numbers)
        
        if max_salary_in_range >= min_salary:
            return 10
        else:
            # Partial credit if below but close
            percentage = max_salary_in_range / min_salary
            return int(10 * percentage)
    
    def get_score_breakdown(self, job_data: Dict[str, Any]) -> Dict[str, int]:
        """Get detailed score breakdown."""
        return {
            "role_match": self._score_role(job_data.get("title", "")),
            "skills_match": self._score_skills(job_data.get("jd_text", "")),
            "location_match": self._score_location(job_data.get("location", "")),
            "salary_match": self._score_salary(job_data.get("salary", "")),
            "total": self.score_job(job_data)
        }
    
    def filter_by_score(self, jobs: List[Dict[str, Any]], min_score: int = 50) -> List[Dict[str, Any]]:
        """Filter jobs by minimum fit score."""
        scored_jobs = []
        for job in jobs:
            score = self.score_job(job)
            job["fit_score"] = score
            if score >= min_score:
                scored_jobs.append(job)
        
        # Sort by score descending
        return sorted(scored_jobs, key=lambda x: x["fit_score"], reverse=True)
