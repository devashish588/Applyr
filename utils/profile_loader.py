"""
Profile loader - reads and validates profile.json
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ProfileLoader:
    """Load and validate user profile from JSON."""
    
    def __init__(self, profile_path: str = "./profile.json"):
        self.profile_path = profile_path
        self.profile = None
        self.load()

    def load(self) -> Dict[str, Any]:
        """Load profile from JSON file."""
        if not os.path.exists(self.profile_path):
            raise FileNotFoundError(f"Profile file not found: {self.profile_path}")
        
        try:
            with open(self.profile_path, "r") as f:
                self.profile = json.load(f)
            self.validate()
            return self.profile
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in profile file: {e}")

    def validate(self) -> bool:
        """Validate profile structure."""
        required_sections = ["personal", "skills", "job_preferences"]
        
        for section in required_sections:
            if section not in self.profile:
                raise ValueError(f"Missing required section in profile: {section}")
        
        # Validate personal section
        personal_required = ["name", "email", "phone", "linkedin"]
        for field in personal_required:
            if field not in self.profile["personal"]:
                raise ValueError(f"Missing required field in personal section: {field}")
        
        # Validate skills section
        if "languages" not in self.profile["skills"]:
            raise ValueError("Missing 'languages' in skills section")
        
        # Validate job_preferences
        if "target_roles" not in self.profile["job_preferences"]:
            raise ValueError("Missing 'target_roles' in job_preferences")
        
        return True

    def get_personal_info(self) -> Dict[str, Any]:
        """Get personal information."""
        return self.profile.get("personal", {})

    def get_skills(self) -> Dict[str, Any]:
        """Get skills information."""
        return self.profile.get("skills", {})

    def get_job_preferences(self) -> Dict[str, Any]:
        """Get job preferences."""
        return self.profile.get("job_preferences", {})

    def get_target_roles(self) -> list:
        """Get target job roles."""
        return self.profile.get("job_preferences", {}).get("target_roles", [])

    def get_skills_text(self) -> str:
        """Get skills as concatenated text for matching."""
        skills = self.profile.get("skills", {})
        all_skills = []
        
        if isinstance(skills.get("languages"), list):
            all_skills.extend(skills["languages"])
        if isinstance(skills.get("frameworks"), list):
            all_skills.extend(skills["frameworks"])
        if isinstance(skills.get("tools"), list):
            all_skills.extend(skills["tools"])
        
        return ", ".join(all_skills)

    def get_experience_summary(self) -> str:
        """Get experience summary."""
        return self.profile.get("experience_summary", "")

    def get_key_achievements(self) -> list:
        """Get key achievements."""
        return self.profile.get("key_achievements", [])

    def to_dict(self) -> Dict[str, Any]:
        """Get entire profile as dictionary."""
        return self.profile.copy()

    @staticmethod
    def create_template(output_path: str = "./profile.json"):
        """Create a template profile.json file."""
        template = {
            "personal": {
                "name": "Your Full Name",
                "email": "your.email@example.com",
                "phone": "+1-XXX-XXX-XXXX",
                "linkedin": "https://linkedin.com/in/yourprofile",
                "github": "https://github.com/yourprofile",
                "portfolio": "https://yourportfolio.com",
                "city": "Your City",
                "pincode": "123456"
            },
            "skills": {
                "languages": ["Python", "JavaScript", "SQL"],
                "frameworks": ["Django", "React", "FastAPI"],
                "tools": ["Git", "Docker", "AWS"],
                "years_experience": 5,
                "certifications": []
            },
            "job_preferences": {
                "target_roles": ["Software Engineer", "Full Stack Developer"],
                "target_locations": ["Remote", "San Francisco"],
                "min_salary": 100000,
                "remote_ok": True,
                "fulltime_only": True,
                "interested_industries": ["Tech", "Finance"]
            },
            "experience_summary": "Senior software engineer with 5+ years building scalable systems",
            "key_achievements": [
                "Led migration of monolith to microservices",
                "Architected real-time data pipeline",
                "Mentored team of engineers"
            ]
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(template, f, indent=2)
        
        print(f"Template profile created at {output_path}")


# Global profile instance
_profile_instance = None


def get_profile() -> ProfileLoader:
    """Get or create global profile instance."""
    global _profile_instance
    if _profile_instance is None:
        _profile_instance = ProfileLoader()
    return _profile_instance
