"""
Profile Service for Applyr AI job application platform.

This service generates user profiles from resume data and manages
profile-related operations.
"""

import logging
from typing import List, Dict, Any, Optional
from core.models import Resume, Profile

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing user profiles."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_profile_from_resume(self, resume: Resume) -> Profile:
        """
        Create a profile from resume data.

        Args:
            resume: Resume object containing parsed resume data

        Returns:
            Profile object generated from resume data
        """
        self.logger.info(f"Creating profile from resume with {len(resume.skills)} skills")

        # Extract roles from resume
        roles = resume.roles or self._infer_roles_from_skills(resume.skills)

        # Extract keywords from skills
        keywords = self._extract_keywords_from_skills(resume.skills)

        # Create profile
        profile = Profile(
            inferred_roles=roles,
            preferred_locations=["Remote"],  # Default to remote
            seniority=self._infer_seniority_from_experience(resume.experience),
            keywords=keywords,
            target_roles=roles,
            target_locations=["Remote"],
            remote_ok=True,
            personal={
                "name": resume.name,
                "email": resume.email,
                "phone": resume.phone,
                "linkedin": resume.linkedin,
                "github": resume.github,
            },
            skills={
                "languages": self._categorize_skills(resume.skills, "programming"),
                "frameworks": self._categorize_skills(resume.skills, "framework"),
                "tools": self._categorize_skills(resume.skills, "tool"),
            }
        )

        self.logger.info(f"Profile created with {len(roles)} inferred roles")
        return profile

    def _infer_roles_from_skills(self, skills: List[str]) -> List[str]:
        """
        Infer job roles from skills.

        Args:
            skills: List of skills

        Returns:
            List of inferred roles
        """
        ml_keywords = {
            "machine learning", "scikit-learn", "tensorflow", "pytorch",
            "keras", "xgboost", "deep learning", "nlp", "computer vision"
        }
        data_keywords = {
            "pandas", "numpy", "sql", "power bi", "tableau", "excel",
            "data analysis", "statistics", "r", "spark"
        }
        ai_keywords = {
            "langchain", "llm", "openai", "gpt", "transformers",
            "huggingface", "rag", "vector database"
        }
        web_keywords = {
            "react", "next.js", "node.js", "express", "django", "flask",
            "fastapi", "html", "css", "javascript", "typescript"
        }
        backend_keywords = {
            "python", "java", "go", "rust", "c++", "docker",
            "kubernetes", "aws", "gcp", "azure", "postgresql", "redis"
        }
        devops_keywords = {
            "docker", "kubernetes", "terraform", "ci/cd", "jenkins",
            "github actions", "aws", "gcp"
        }

        skill_lower = {s.lower() for s in skills}
        roles = []

        if skill_lower & ml_keywords:
            roles.extend(["Machine Learning Engineer", "ML Intern"])
        if skill_lower & data_keywords:
            roles.extend(["Data Scientist", "Data Analyst"])
        if skill_lower & ai_keywords:
            roles.extend(["AI Engineer", "GenAI Engineer"])
        if skill_lower & web_keywords:
            roles.extend(["Full Stack Developer", "Frontend Developer"])
        if skill_lower & backend_keywords:
            roles.extend(["Backend Engineer", "Software Engineer"])
        if skill_lower & devops_keywords:
            roles.append("DevOps Engineer")

        # Deduplicate preserving order
        seen = set()
        unique_roles = []
        for role in roles:
            if role not in seen:
                seen.add(role)
                unique_roles.append(role)

        return unique_roles or ["Software Engineer"]

    def _extract_keywords_from_skills(self, skills: List[str]) -> List[str]:
        """
        Extract keywords from skills for search.

        Args:
            skills: List of skills

        Returns:
            List of keywords
        """
        # Prioritize technical skills
        technical_skills = [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
            "Django", "Flask", "FastAPI", "React", "Next.js", "Vue.js", "Angular",
            "Node.js", "Express", "Spring Boot", "ASP.NET", "Laravel",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "Firebase", "Cloudflare",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "LangChain", "LLM", "OpenAI", "HuggingFace", "Transformers",
            "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
        ]

        keywords = []
        for skill in skills:
            if skill in technical_skills:
                keywords.append(skill)

        # Add a few more for diversity
        if len(keywords) < 5:
            keywords.extend(["AI", "ML", "Data Science", "Web Development", "Software Engineering"])

        return keywords[:10]

    def _infer_seniority_from_experience(self, experience: List[Dict[str, Any]]) -> Optional[str]:
        """
        Infer seniority level from experience.

        Args:
            experience: List of experience entries

        Returns:
            Seniority level (Junior, Mid-level, Senior, Lead, Principal)
        """
        if not experience:
            return None

        # Calculate total years of experience
        total_years = 0
        for exp in experience:
            duration = exp.get("duration", "")
            if " - " in duration:
                start, end = duration.split(" - ")
                if end.lower() == "present" or end.lower() == "current":
                    # Calculate years from start
                    try:
                        start_year = int(start.split("-")[0])
                        total_years += 2026 - start_year
                    except:
                        pass
                else:
                    try:
                        start_year = int(start.split("-")[0])
                        end_year = int(end.split("-")[0])
                        total_years += end_year - start_year
                    except:
                        pass

        if total_years < 2:
            return "Junior"
        elif total_years < 5:
            return "Mid-level"
        elif total_years < 10:
            return "Senior"
        elif total_years < 15:
            return "Lead"
        else:
            return "Principal"

    def _categorize_skills(self, skills: List[str], category: str) -> List[str]:
        """
        Categorize skills into groups.

        Args:
            skills: List of skills
            category: Category to filter by

        Returns:
            List of skills in the specified category
        """
        # Define skill categories
        programming_skills = {
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
            "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl"
        }

        framework_skills = {
            "Django", "Flask", "FastAPI", "React", "Next.js", "Vue.js", "Angular",
            "Svelte", "Node.js", "Express", "Spring Boot", "ASP.NET", "Laravel"
        }

        tool_skills = {
            "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitHub Actions",
            "AWS", "Azure", "GCP", "Firebase", "Cloudflare", "Linux", "Git"
        }

        ml_skills = {
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "LangChain", "LLM", "OpenAI", "HuggingFace", "Transformers",
            "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
            "XGBoost", "LightGBM", "Spark", "Hadoop", "Kafka", "Airflow"
        }

        data_skills = {
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
            "Pandas", "NumPy", "Scikit-learn", "Spark", "Hadoop", "Kafka", "Airflow",
            "Tableau", "Power BI", "Excel"
        }

        target_set = {
            "programming": programming_skills,
            "framework": framework_skills,
            "tool": tool_skills,
            "ml": ml_skills,
            "data": data_skills,
        }.get(category, set())

        return [skill for skill in skills if skill in target_set]

    def validate_profile(self, profile: Profile) -> List[str]:
        """
        Validate a profile and return any errors.

        Args:
            profile: Profile to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not profile.inferred_roles:
            errors.append("No inferred roles found")

        if not profile.target_roles:
            errors.append("No target roles found")

        if not profile.keywords:
            errors.append("No keywords found")

        if not profile.skills.get("languages") and not profile.skills.get("frameworks") and not profile.skills.get("tools"):
            errors.append("No technical skills found")

        return errors


# Singleton instance
_profile_service = None


def get_profile_service() -> ProfileService:
    """Get the singleton ProfileService instance."""
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService()
    return _profile_service