"""
Resume parser agent - extracts usable resume facts without requiring an LLM.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "SQL", "Java", "C++", "C#",
    "Django", "Flask", "FastAPI", "React", "Next.js", "Node.js", "Express",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
    "AWS", "Azure", "GCP", "Git", "Linux", "REST", "GraphQL",
    "Machine Learning", "LangChain", "LLM", "Pandas", "NumPy",
]


class ResumeParserAgent:
    """Parses resume and extracts key information."""
    
    def __init__(self):
        pass
    
    def parse_file(self, resume_path: str) -> dict:
        """Parse resume file (orchestrator compatibility alias)."""
        return self.parse_resume(resume_path)
    
    def parse_resume(self, resume_path: str) -> dict:
        """
        Parse resume file and extract structured data.
        
        Args:
            resume_path: Path to resume PDF/DOCX
        
        Returns:
            {
                "name": "John Doe",
                "email": "john@example.com",
                "skills": ["Python", "JavaScript", "React"],
                "experience": [
                    {
                        "title": "Senior Developer",
                        "company": "Acme",
                        "duration": "2020-2024",
                        "description": "..."
                    }
                ],
                "achievements": ["Led X project", "Improved Y by 40%"],
                "education": [{"degree": "BS CS", "school": "MIT"}]
            }
        """
        text = self._extract_text(resume_path)
        skills = self.extract_skills(text)
        achievements = self.extract_achievements(text)

        return {
            "name": self._extract_name(text),
            "email": self._extract_email(text),
            "phone": self._extract_phone(text),
            "skills": skills,
            "experience": self._extract_experience(text, achievements),
            "achievements": achievements,
            "education": self._extract_education(text),
            "raw_text": text[:8000],
            "source_path": str(resume_path),
        }

    def _extract_text(self, resume_path: str) -> str:
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf_text(path)
        if ext == ".docx":
            return self._extract_docx_text(path)
        if ext in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="ignore")

        raise ValueError(f"Unsupported resume format: {ext or 'unknown'}")

    def _extract_pdf_text(self, path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("pypdf is required to parse PDF resumes") from exc

        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    def _extract_docx_text(self, path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise ImportError("python-docx is required to parse DOCX resumes") from exc

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    
    def extract_skills(self, resume_text: str) -> list:
        """Extract technical skills from resume."""
        text = resume_text.lower()
        found = []
        for skill in COMMON_SKILLS:
            pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, text):
                found.append(skill)
        return found
    
    def extract_achievements(self, resume_text: str) -> list:
        """Extract key achievements from resume."""
        achievements = []
        for raw_line in resume_text.splitlines():
            line = raw_line.strip(" \t-*•")
            if len(line) < 25:
                continue
            lower = line.lower()
            has_signal = any(word in lower for word in [
                "built", "created", "led", "owned", "improved", "reduced",
                "increased", "designed", "implemented", "migrated",
                "optimized", "launched", "architected", "mentored",
            ])
            has_metric = bool(re.search(r"\b\d+[%+x]?\b", line))
            if has_signal or has_metric:
                achievements.append(line)
            if len(achievements) >= 8:
                break
        return achievements

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        return re.sub(r"\s+", " ", match.group(0)).strip() if match else None

    def _extract_name(self, text: str) -> str | None:
        for raw_line in text.splitlines()[:12]:
            line = raw_line.strip()
            if not line or "@" in line or re.search(r"\d", line):
                continue
            if len(line.split()) <= 5:
                return line
        return None

    def _extract_experience(self, text: str, achievements: list[str]) -> list[dict]:
        if achievements:
            return [{
                "title": "Resume Highlights",
                "company": "",
                "duration": "",
                "bullets": achievements[:6],
            }]
        return []

    def _extract_education(self, text: str) -> list[dict]:
        education = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            lower = line.lower()
            if any(term in lower for term in ["bachelor", "master", "degree", "university", "college"]):
                education.append({"summary": line})
            if len(education) >= 3:
                break
        return education
