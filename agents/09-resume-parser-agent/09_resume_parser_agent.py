"""
Resume parser agent — Multi-engine extraction (PyMuPDF + pdfplumber + fallback).
Produces structured Resume JSON with validation and confidence scoring.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

COMMON_SKILLS = sorted({
    "Python", "JavaScript", "TypeScript", "SQL", "Java", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl",
    "Django", "Flask", "FastAPI", "React", "Next.js", "Vue.js", "Angular",
    "Svelte", "Node.js", "Express", "Spring Boot", "ASP.NET", "Laravel",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
    "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitHub Actions",
    "AWS", "Azure", "GCP", "Firebase", "Cloudflare",
    "Git", "Linux", "REST", "GraphQL", "gRPC", "WebSocket",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "LangChain", "LLM", "OpenAI", "HuggingFace", "Transformers",
    "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
    "XGBoost", "LightGBM", "Spark", "Hadoop", "Kafka", "Airflow",
    "Tableau", "Power BI", "Excel", "Jira", "Confluence", "Figma",
})

SECTION_HEADERS = re.compile(
    r"(?i)^\s*(education|experience|work\s*experience|employment|professional\s*experience|"
    r"skills|technical\s*skills|core\s*competencies|projects|personal\s*projects|"
    r"certifications|certificates|publications|patents|"
    r"leadership|volunteering|awards|honors|languages|interests|"
    r"summary|professional\s*summary|objective|profile|about\s*me)\s*[:.]?\s*$"
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
URL_RE = re.compile(r"(https?://[^\s]+)")
LINKEDIN_RE = re.compile(r"(?:linkedin\.com/in/|linkedin\.com/)([a-zA-Z0-9_-]+)")
GITHUB_RE = re.compile(r"(?:github\.com/)([a-zA-Z0-9_-]+)")


class ResumeParseError(Exception):
    pass


class ResumeParserAgent:
    """Multi-engine resume parser producing structured JSON output."""

    def __init__(self):
        self.parse_log: list[str] = []
        self.confidence: float = 0.0

    def parse_file(self, resume_path: str) -> dict:
        return self.parse_resume(resume_path)

    def parse_resume(self, resume_path: str) -> dict:
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

        raw_text = self._extract_text_multi(path)
        self.parse_log.append(f"Extracted {len(raw_text)} chars from {path.suffix}")

        sections = self._detect_sections(raw_text)
        self.parse_log.append(f"Detected sections: {list(sections.keys())}")

        structured = {
            "name": self._extract_name(raw_text, sections),
            "email": self._extract_email(raw_text),
            "phone": self._extract_phone(raw_text),
            "linkedin": self._extract_linkedin(raw_text),
            "github": self._extract_github(raw_text),
            "skills": self._extract_skills(raw_text, sections),
            "experience": self._extract_experience(sections, raw_text),
            "projects": self._extract_projects(sections, raw_text),
            "education": self._extract_education(sections, raw_text),
            "certifications": self._extract_certifications(sections, raw_text),
            "roles": self._infer_roles(sections, raw_text),
            "total_pages": self._count_pages(path),
            "sections_detected": list(sections.keys()),
            "sections_missing": self._find_missing_sections(sections),
            "parse_log": self.parse_log,
            "raw_text": raw_text[:12000],
            "source_path": str(resume_path),
            "parsed_at": datetime.now().isoformat(),
        }
        structured["confidence"] = self._compute_confidence(structured)
        return structured

    # ── Multi-engine text extraction ───────────────────────────────────────

    def _extract_text_multi(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(path)
        if ext == ".docx":
            return self._extract_docx(path)
        if ext in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="ignore")
        raise ValueError(f"Unsupported format: {ext}")

    def _extract_pdf(self, path: Path) -> str:
        texts = []

        # Engine 1: PyMuPDF (fitz) — best layout preservation
        try:
            import fitz
            doc = fitz.open(str(path))
            for page in doc:
                texts.append(page.get_text("text"))
            self.parse_log.append(f"PyMuPDF: {len(texts)} pages")
        except Exception as e:
            self.parse_log.append(f"PyMuPDF failed: {e}")

        # Engine 2: pdfplumber — better for tables, multi-column
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                plumber_texts = [page.extract_text() or "" for page in pdf.pages]
                if len("".join(plumber_texts)) > len("".join(texts)):
                    texts = plumber_texts
                    self.parse_log.append(f"pdfplumber preferred: {len(plumber_texts)} pages")
                else:
                    self.parse_log.append(f"pdfplumber: {len(plumber_texts)} pages (secondary)")
        except Exception as e:
            self.parse_log.append(f"pdfplumber failed: {e}")

        # Engine 3: pypdf fallback
        if not texts or len("".join(texts)) < 50:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                texts = [page.extract_text() or "" for page in reader.pages]
                self.parse_log.append(f"pypdf fallback: {len(texts)} pages")
            except Exception as e:
                self.parse_log.append(f"pypdf fallback failed: {e}")

        if not texts:
            raise ResumeParseError("All PDF extractors failed")

        return "\n\n=== PAGE BREAK ===\n\n".join(texts)

    def _extract_docx(self, path: Path) -> str:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _count_pages(self, path: Path) -> int:
        try:
            import fitz
            doc = fitz.open(str(path))
            return len(doc)
        except Exception:
            pass
        try:
            from pypdf import PdfReader
            return len(PdfReader(str(path)).pages)
        except Exception:
            return 0

    # ── Section detection ─────────────────────────────────────────────────

    def _detect_sections(self, text: str) -> dict[str, str]:
        lines = text.splitlines()
        sections: dict[str, str] = {}
        current_section = "header"
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            match = SECTION_HEADERS.match(stripped)
            if match:
                sections[current_section] = "\n".join(current_lines).strip()
                current_section = match.group(1).lower().strip()
                current_lines = []
            else:
                current_lines.append(line)

        sections[current_section] = "\n".join(current_lines).strip()
        return sections

    def _find_missing_sections(self, sections: dict[str, str]) -> list[str]:
        required = ["skills", "experience", "education"]
        present = set(sections.keys())
        return [s for s in required if s not in present]

    # ── Field extraction ──────────────────────────────────────────────────

    def _extract_name(self, text: str, sections: dict) -> str | None:
        candidates = []
        for line in text.splitlines()[:15]:
            line = line.strip()
            if not line or len(line) > 60:
                continue
            if "@" in line or re.search(r"\d{4}", line):
                continue
            words = line.split()
            if 1 < len(words) <= 5 and all(w[0].isupper() for w in words if w):
                candidates.append(line)
        return candidates[0] if candidates else None

    def _extract_email(self, text: str) -> str | None:
        m = EMAIL_RE.search(text)
        return m.group(0) if m else None

    def _extract_phone(self, text: str) -> str | None:
        m = PHONE_RE.search(text)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else None

    def _extract_linkedin(self, text: str) -> str | None:
        m = LINKEDIN_RE.search(text)
        return m.group(0) if m else None

    def _extract_github(self, text: str) -> str | None:
        m = GITHUB_RE.search(text)
        return m.group(0) if m else None

    def _extract_skills(self, text: str, sections: dict) -> list[str]:
        # Priority: explicit skills section
        skill_text = sections.get("skills", "") or sections.get("technical skills", "") or sections.get("core competencies", "") or text
        found: list[str] = []
        text_lower = skill_text.lower()

        for skill in COMMON_SKILLS:
            pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, text_lower):
                found.append(skill)

        # Deduplicate preserving order
        seen: set[str] = set()
        unique = []
        for s in found:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique.append(s)
        return unique

    def _extract_experience(self, sections: dict, text: str) -> list[dict]:
        exp_text = sections.get("experience", "") or sections.get("work experience", "") or sections.get("professional experience", "") or sections.get("employment", "") or ""
        if not exp_text:
            return []

        entries: list[dict] = []
        blocks = re.split(r"\n\s*\n", exp_text)
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) < 2:
                continue
            title = lines[0] if len(lines) > 0 else ""
            company = lines[1] if len(lines) > 1 else ""
            duration = ""
            bullets = []
            date_match = re.search(r"(\d{4})\s*[-–]+\s*(\d{4}|present|current)", block, re.IGNORECASE)
            if date_match:
                duration = f"{date_match.group(1)} - {date_match.group(2)}"
            for line in lines[2:]:
                if re.match(r"^[•\-\*]\s", line) or re.match(r"^\d+\.\s", line):
                    bullets.append(re.sub(r"^[•\-\*\d\.]\s*", "", line).strip())
                elif line and len(line) > 20:
                    bullets.append(line)
            if title:
                entries.append({
                    "title": title,
                    "company": company,
                    "duration": duration,
                    "bullets": bullets[:8],
                })
        return entries

    def _extract_projects(self, sections: dict, text: str) -> list[dict]:
        proj_text = sections.get("projects", "") or sections.get("personal projects", "") or ""
        if not proj_text:
            return []

        projects: list[dict] = []
        blocks = re.split(r"\n\s*\n", proj_text)
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue
            desc_lines = [l for l in lines[1:] if len(l) > 15]
            projects.append({
                "name": lines[0],
                "description": " ".join(desc_lines[:3]) if desc_lines else "",
                "technologies": self._extract_skills(block, {}),
            })
        return projects

    def _extract_education(self, sections: dict, text: str) -> list[dict]:
        edu_text = sections.get("education", "") or ""
        if not edu_text:
            return []

        entries: list[dict] = []
        lines = [l.strip() for l in edu_text.splitlines() if l.strip()]
        for line in lines:
            lower = line.lower()
            if any(t in lower for t in ["bachelor", "master", "phd", "ph.d", "b.tech", "m.tech", "b.e", "m.e", "b.s", "m.s", "degree", "university", "college", "institute", "school"]):
                entries.append({"summary": line})
        return entries

    def _extract_certifications(self, sections: dict, text: str) -> list[str]:
        cert_text = sections.get("certifications", "") or sections.get("certificates", "") or sections.get("licenses", "") or ""
        if not cert_text:
            return []
        lines = [l.strip().lstrip("•-*123456789.").strip() for l in cert_text.splitlines() if l.strip()]
        return [l for l in lines if len(l) > 5][:10]

    def _infer_roles(self, sections: dict, text: str) -> list[str]:
        skills = self._extract_skills(text, sections)
        skill_lower = {s.lower() for s in skills}
        roles = []

        ml_set = {"machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch", "scikit-learn", "keras", "xgboost"}
        data_set = {"pandas", "numpy", "sql", "tableau", "power bi", "spark", "hadoop"}
        ai_set = {"langchain", "llm", "openai", "huggingface", "transformers", "rag", "vector database"}
        web_set = {"react", "next.js", "vue.js", "angular", "node.js", "express", "django", "flask", "fastapi", "html", "css", "javascript", "typescript"}
        backend_set = {"docker", "kubernetes", "aws", "azure", "gcp", "postgresql", "redis", "kafka", "grpc"}

        if skill_lower & ml_set:
            roles.extend(["Machine Learning Engineer", "ML Intern"])
        if skill_lower & data_set:
            roles.extend(["Data Scientist", "Data Analyst"])
        if skill_lower & ai_set:
            roles.extend(["AI Engineer", "GenAI Engineer"])
        if skill_lower & web_set:
            roles.extend(["Full Stack Developer", "Frontend Developer"])
        if skill_lower & backend_set:
            roles.extend(["Backend Engineer", "Software Engineer"])
        if {"docker", "kubernetes", "terraform", "jenkins", "github actions"} & skill_lower:
            roles.append("DevOps Engineer")

        seen: set[str] = set()
        unique = []
        for r in roles:
            if r not in seen:
                seen.add(r)
                unique.append(r)

        # Fallback: check experience titles for role hints
        if not unique:
            exp = self._extract_experience(sections, text)
            for e in exp:
                t = (e.get("title", "") or "").lower()
                if "engineer" in t:
                    unique.append("Software Engineer")
                    break
                if "developer" in t:
                    unique.append("Software Developer")
                    break
                if "scientist" in t:
                    unique.append("Data Scientist")
                    break
                if "intern" in t:
                    unique.append("Intern")
                    break

        return unique or ["Software Engineer"]

    def _compute_confidence(self, structured: dict) -> float:
        score = 0.0
        checks = 0

        if structured.get("name"): score += 1
        checks += 1
        if structured.get("email"): score += 1
        checks += 1
        if structured.get("phone"): score += 1
        checks += 1

        skill_count = len(structured.get("skills", []))
        if skill_count >= 10: score += 1
        elif skill_count >= 5: score += 0.5
        checks += 1

        exp_count = len(structured.get("experience", []))
        if exp_count >= 2: score += 1
        elif exp_count >= 1: score += 0.5
        checks += 1

        edu_count = len(structured.get("education", []))
        if edu_count >= 1: score += 1
        checks += 1

        sections_detected = structured.get("sections_detected", [])
        if len(sections_detected) >= 4: score += 1
        elif len(sections_detected) >= 2: score += 0.5
        checks += 1

        total = score / checks if checks > 0 else 0
        return round(total * 100, 1)


# ── Standalone CLI ───────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Resume Parser Agent")
    parser.add_argument("resume_path", help="Path to resume PDF/DOCX/TXT")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    agent = ResumeParserAgent()
    try:
        result = agent.parse_resume(args.resume_path)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n{'='*60}")
            print(f"RESUME PARSE RESULT")
            print(f"{'='*60}")
            print(f"Name:         {result.get('name', 'N/A')}")
            print(f"Email:        {result.get('email', 'N/A')}")
            print(f"Phone:        {result.get('phone', 'N/A')}")
            print(f"Pages:        {result.get('total_pages', 'N/A')}")
            print(f"Confidence:   {result.get('confidence', 0)}%")
            print(f"\nSections:     {', '.join(result.get('sections_detected', []))}")
            print(f"Missing:      {', '.join(result.get('sections_missing', [])) or 'None'}")
            print(f"\nSkills ({len(result.get('skills', []))}): {', '.join(result.get('skills', [])[:12])}")
            print(f"Roles ({len(result.get('roles', []))}): {', '.join(result.get('roles', []))}")
            print(f"Experience ({len(result.get('experience', []))} entries)")
            for exp in result.get("experience", [])[:3]:
                print(f"  - {exp.get('title')} @ {exp.get('company')} ({exp.get('duration', '')})")
            print(f"Education ({len(result.get('education', []))} entries)")
            for edu in result.get("education", [])[:2]:
                print(f"  - {edu.get('summary', '')}")
            print(f"Projects ({len(result.get('projects', []))})")
            print(f"Certifications ({len(result.get('certifications', []))})")

            print(f"\nParse Log:")
            for entry in result.get("parse_log", []):
                print(f"  • {entry}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
