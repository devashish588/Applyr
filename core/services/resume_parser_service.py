# -*- coding: utf-8 -*-
"""
Resume Parser Service -- 6-Level Architecture

Level 1: Text Extraction     -- Multi-engine PDF (PyMuPDF/pdfplumber/OCR) + DOCX + LaTeX
Level 2: Section Detection   -- Regex-based section splitting (before LLM)
Level 3: LLM Structuring     -- Groq/Gemini extracts structured fields per section
Level 4: Validation Layer    -- Confidence scoring per field + overall
Level 5: Role Inference      -- Map skill clusters to job roles
Level 6: Resume JSON         -- Source of truth with parser evidence
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from core.models import Resume, FieldEvidence, ParserEvidence

logger = logging.getLogger(__name__)


def _get_llm():
    """Get configured LLM (OpenRouter primary, Groq fallback)."""
    from core.services.llm_service import get_llm_client
    try:
        client = get_llm_client()
        if client.available:
            return client
    except RuntimeError:
        pass
    # Last-resort fallback: LangChain Groq
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and groq_key != "gsk_xxxxxxxxxxxxx":
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0)


SECTION_HEADERS = re.compile(
    r"(?i)^\s*(?:"
    r"education|experience|work\s*experience|employment|professional\s*experience|"
    r"skills|technical\s*skills|core\s*competencies|projects|personal\s*projects|"
    r"project\s*experience|"
    r"certifications|certificates|publications|patents|"
    r"leadership|volunteering|awards|honors|languages|interests|"
    r"summary|professional\s*summary|objective|profile|about\s*me"
    r")\s*[:.]?\s*$"
)

# Broader section match for lines that START with a known keyword but continue
# (e.g. "Leadership & Activities", "Project Experience & Portfolio")
SECTION_HEADERS_BROAD = re.compile(
    r"(?i)^\s*(?:"
    r"education|experience|work\s*experience|employment|professional\s*experience|"
    r"skills|technical\s*skills|core\s*competencies|projects|personal\s*projects|"
    r"project\s*experience|"
    r"certifications|certificates|publications|patents|"
    r"leadership|volunteering|awards|honors|languages|interests|"
    r"summary|professional\s*summary|objective|profile|about\s*me"
    r")"
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/([a-zA-Z0-9_-]+)")
GITHUB_RE = re.compile(r"github\.com/([a-zA-Z0-9_-]+)")
PORTFOLIO_RE = re.compile(r"(?:portfolio|personal\s*website|website)\s*[:.]?\s*(https?://\S+)", re.I)

COMMON_SKILLS = sorted({
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "SQL", "Java", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Bash", "Shell",
    "Objective-C", "Groovy", "Clojure", "Elixir", "Haskell", "Lisp", "Lua", "Dart",
    
    # Web Frameworks & Frontend
    "React", "Next.js", "Vue.js", "Angular", "Svelte", "Nuxt",
    "Express", "Node.js", "Django", "Flask", "FastAPI", "Spring Boot",
    "ASP.NET", "Laravel", "Ruby on Rails", "Phoenix", "Ember.js", "Backbone.js",
    
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
    "DynamoDB", "Firebase", "Firestore", "Supabase", "Neo4j", "CouchDB", "Oracle",
    "SQL Server", "MariaDB", "SQLite", "Memcached", "HBase", "Kinesis",
    
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "TravisCI",
    "Cloudflare", "Heroku", "DigitalOcean", "Linode", "AWS Lambda", "Google Cloud Functions",
    
    # AI/ML Technologies
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLM",
    "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "XGBoost", "LightGBM",
    "Pandas", "NumPy", "OpenAI", "HuggingFace", "Transformers", "BERT", "GPT",
    "LangChain", "LlamaIndex", "Pinecone", "Weaviate", "Qdrant",
    
    # Tools & Platforms
    "Git", "GitHub", "GitLab", "Jira", "Confluence", "Figma", "Slack",
    "Linux", "Mac", "Windows", "REST", "GraphQL", "gRPC", "WebSocket",
    "Unix", "Apache", "Nginx", "Vim", "VSCode", "IntelliJ", "Eclipse",
    
    # Specialized Domains
    "Spark", "Hadoop", "Kafka", "Airflow", "Databricks", "Snowflake", "BigQuery",
    "Tableau", "Power BI", "Looker", "Grafana", "Prometheus", "DataDog",
    "Excel", "Jupyter", "Jupyter Notebook", "Notebooks", "Conda", "Poetry",
    "Webpack", "Vite", "Babel", "ESLint", "Prettier", "Postman",
    
    # APIs & Protocols
    "REST API", "GraphQL", "SOAP", "OAuth", "JWT", "SSL", "TLS",
    "HTTP", "HTTPS", "WebRTC", "WebGL", "Canvas", "SVG",
    
    # Protocols & Standards
    "Scrum", "Agile", "Kanban", "Waterfall", "CI/CD", "DevOps",
    "Microservices", "Monolithic", "Serverless", "Event-Driven",
})

SKILLS_CATEGORIES = {
    "languages": {
        "Python", "JavaScript", "TypeScript", "SQL", "Java", "C++", "C#", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Bash", "Shell",
        "Objective-C", "Groovy", "Clojure", "Elixir", "Haskell", "Lisp", "Lua", "Dart",
    },
    "frameworks": {
        "React", "Next.js", "Vue.js", "Angular", "Svelte", "Nuxt", "Django", "Flask", "FastAPI",
        "Spring Boot", "Express", "Node.js", "ASP.NET", "Laravel", "Ruby on Rails", "Phoenix",
    },
    "databases": {
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch", "DynamoDB",
        "Firebase", "Firestore", "Supabase", "Neo4j", "CouchDB", "Oracle", "SQL Server",
        "MariaDB", "SQLite", "Memcached", "HBase", "Kinesis",
    },
    "ml_ai": {
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLM", "TensorFlow",
        "PyTorch", "Keras", "OpenAI", "HuggingFace", "Transformers", "LangChain",
        "Scikit-learn", "XGBoost", "LightGBM", "BERT", "GPT",
        "RAG", "RLHF", "SFT", "Embeddings", "Vector Database",
    },
    "cloud": {
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins",
        "GitHub Actions", "GitLab CI", "CircleCI", "Cloudflare", "Heroku", "DigitalOcean",
        "AWS Lambda", "Google Cloud Functions", "Serverless",
    },
    "tools": {
        "Git", "GitHub", "GitLab", "Jira", "Confluence", "Figma", "Slack",
        "Linux", "Unix", "REST", "GraphQL", "gRPC", "WebSocket",
        "Excel", "Tableau", "Power BI", "Looker", "Grafana", "Prometheus", "DataDog",
        "Spark", "Hadoop", "Kafka", "Airflow", "Databricks", "Snowflake", "BigQuery",
        "Postman", "Vim", "VSCode", "IntelliJ",
    },
}


ROLE_KEYWORDS = {
    "software engineer": ["python", "java", "javascript", "react", "node", "backend", "fullstack", "api", "rest", "microservices", "docker", "kubernetes", "aws", "system design"],
    "data scientist": ["machine learning", "deep learning", "nlp", "computer vision", "statistics", "tensorflow", "pytorch", "r", "sql", "pandas", "numpy", "data mining", "ml"],
    "data engineer": ["etl", "pipeline", "spark", "hadoop", "kafka", "airflow", "data warehouse", "sql", "big data", "databricks", "snowflake"],
    "devops engineer": ["docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd", "aws", "azure", "gcp", "monitoring", "infrastructure", "linux"],
    "product manager": ["product", "roadmap", "stakeholder", "agile", "sprint", "user story", "a/b testing", "kpi", "analytics", "strategy"],
    "frontend engineer": ["react", "angular", "vue", "typescript", "javascript", "css", "html", "ui", "ux", "responsive", "frontend", "webpack"],
    "backend engineer": ["python", "django", "flask", "fastapi", "node", "express", "spring", "java", "go", "api", "rest", "graphql", "database", "sql"],
    "ml engineer": ["machine learning", "deep learning", "mlops", "tensorflow", "pytorch", "model deployment", "feature engineering", "pipeline", "ml"],
    "full stack engineer": ["react", "node", "python", "javascript", "typescript", "frontend", "backend", "api", "database", "rest", "fullstack", "full stack"],
    "data analyst": ["sql", "excel", "tableau", "power bi", "python", "analytics", "dashboard", "reporting", "visualization", "statistics"],
}


class ResumeParseError(Exception):
    """Raised when resume parsing fails at any level."""


class ResumeParserService:
    """6-level resume parser producing a validated Resume model."""

    def __init__(self):
        self.log: List[str] = []
        self._llm = None
        self.cache_dir = Path(os.getenv("RESUME_CACHE_DIR", "resume_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_stats = {
            "engine_used": None,
            "chars_extracted": 0,
            "pages": 0,
            "confidence": 0,
        }

    @property
    def llm(self):
        if self._llm is None:
            self._llm = _get_llm()
        return self._llm

    # ------------------------------------------------------------------ #
    # Main Entry Point
    # ------------------------------------------------------------------ #

    def parse(self, path: str) -> Resume:
        """Parse a resume file through all 6 levels."""
        start = datetime.now()
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Resume not found: {path}")

        self.log = [f"Starting parse: {path}"]
        self.log.append(f"File size: {path_obj.stat().st_size} bytes")

        # Level 1: Text Extraction
        raw_text, total_pages = self._level1_extract(path_obj)
        self.extraction_stats["pages"] = total_pages
        self.extraction_stats["chars_extracted"] = len(raw_text)
        self.log.append(f"Level 1: Extracted {len(raw_text)} chars, {total_pages} page(s)")

        if not raw_text.strip():
            raise ResumeParseError("No text could be extracted from the resume")

        # Level 2: Section Detection
        sections = self._level2_detect_sections(raw_text)
        sections_detected = list(sections.keys())
        sections_missing = self._find_missing(sections)
        self.log.append(f"Level 2: Detected sections: {sections_detected}")
        if sections_missing:
            self.log.append(f"Level 2: Missing sections: {sections_missing}")

        # Level 3: LLM Structuring
        structured = self._level3_llm_structure(raw_text, sections)
        self.log.append(f"Level 3: Extracted name={structured.get('name')}, "
                        f"skills={len(structured.get('skills', []))}, "
                        f"experience={len(structured.get('experience', []))}")

        # Level 4: Validation
        evidence, confidence = self._level4_validate(structured, sections)
        self.extraction_stats["confidence"] = confidence
        self.log.append(f"Level 4: Confidence={confidence}%")

        # Level 5: Role Inference
        roles = self._level5_infer_roles(structured, sections)
        self.log.append(f"Level 5: Roles={roles}")

        # Level 6: Assemble Resume JSON
        resume = self._level6_assemble(
            structured, evidence, confidence, roles,
            sections_detected, sections_missing,
            raw_text, total_pages, str(path_obj), start
        )

        elapsed = (datetime.now() - start).total_seconds()
        self.log.append(f"Parse complete in {elapsed:.1f}s -- confidence {confidence}%")
        resume.parse_log = self.log
        
        # Cache the parsed resume
        self._save_resume_cache(resume, str(path_obj))
        
        return resume

    def parse_file(self, path: str) -> Resume:
        """Alias for parse()."""
        return self.parse(path)

    # ------------------------------------------------------------------ #
    # Level 1: Text Extraction
    # ------------------------------------------------------------------ #

    def _level1_extract(self, path: Path) -> Tuple[str, int]:
        """Extract raw text from PDF, DOCX, or LaTeX using multiple engines."""
        suffix = path.suffix.lower()
        raw_text = ""
        total_pages = 1

        if suffix == ".pdf":
            raw_text, total_pages = self._extract_pdf(path)
        elif suffix in (".docx", ".doc"):
            raw_text = self._extract_docx(path)
        elif suffix == ".tex":
            raw_text = self._extract_latex(path)
        elif suffix in (".txt", ".md", ".rtf"):
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        else:
            # Try PDF first, then text
            raw_text, total_pages = self._extract_pdf(path)

        return raw_text.strip(), total_pages

    def _extract_pdf(self, path: Path) -> Tuple[str, int]:
        """Multi-engine PDF extraction: PyMuPDF -> pdfplumber -> OCR.
        
        PRODUCTION: Every engine failure is logged at ERROR level with WHY it failed.
        This gives users exact installation instructions if needed.
        """
        text = ""
        pages = 0
        engine_errors = []

        # Engine 1: PyMuPDF (fast, good for digital PDFs)
        try:
            import fitz
            doc = fitz.open(str(path))
            pages = len(doc)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            if text.strip():
                logger.info("[resume_parser] PyMuPDF extracted %d chars from %d pages", len(text), pages)
                self.log.append(f"PDF extraction: PyMuPDF succeeded ({len(text)} chars)")
                return text, pages
            else:
                engine_errors.append("PyMuPDF: extracted 0 characters (likely scanned/image PDF)")
        except ImportError:
            engine_errors.append("PyMuPDF: NOT INSTALLED — run: pip install pymupdf")
        except Exception as e:
            engine_errors.append(f"PyMuPDF: {type(e).__name__}: {e}")
            logger.error("[resume_parser] PyMuPDF failed: %s", e, exc_info=False)

        # Engine 2: pdfplumber (better for tables, complex layouts)
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                pages = len(pdf.pages)
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                logger.info("[resume_parser] pdfplumber extracted %d chars from %d pages", len(text), pages)
                self.log.append(f"PDF extraction: pdfplumber succeeded ({len(text)} chars)")
                return text, pages
            else:
                engine_errors.append("pdfplumber: extracted 0 characters")
        except ImportError:
            engine_errors.append("pdfplumber: NOT INSTALLED — run: pip install pdfplumber")
        except Exception as e:
            engine_errors.append(f"pdfplumber: {type(e).__name__}: {e}")
            logger.error("[resume_parser] pdfplumber failed: %s", e, exc_info=False)

        # Engine 3: OCR fallback via pytesseract + pdf2image
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(str(path), dpi=300)
            pages = len(images)
            text = "\n---PAGE BREAK---\n".join(
                pytesseract.image_to_string(img) for img in images
            )
            if text.strip():
                logger.info("[resume_parser] OCR extracted %d chars from %d pages", len(text), pages)
                self.log.append(f"PDF extraction: OCR succeeded ({len(text)} chars)")
                return text, pages
            else:
                engine_errors.append("OCR: extracted 0 characters")
        except ImportError:
            engine_errors.append(
                "OCR: NOT INSTALLED — run: pip install pdf2image pytesseract "
                "AND install system binaries: poppler-utils + tesseract-ocr"
            )
        except Exception as e:
            engine_errors.append(f"OCR: {type(e).__name__}: {e}")
            logger.error("[resume_parser] OCR failed: %s", e, exc_info=False)

        # ALL THREE ENGINES FAILED — log every reason loudly before raising
        logger.error("[resume_parser] All 3 PDF extraction engines failed for %s:", path.name)
        for err in engine_errors:
            logger.error("[resume_parser]   - %s", err)
        self.log.append(f"PDF extraction FAILED: All 3 engines failed")

        raise ResumeParseError(
            f"All PDF extraction engines failed for {path.name}.\n"
            + "\n".join(f"  \u2022 {e}" for e in engine_errors)
            + "\n\nMost likely fix: Install text-extraction libraries:\n"
            + "  pip install pymupdf pdfplumber\n"
            + "For scanned PDFs, also install OCR:\n"
            + "  pip install pdf2image pytesseract\n"
            + "  (plus poppler-utils + tesseract-ocr system packages)"
        )

    def _extract_docx(self, path: Path) -> str:
        """Extract text from DOCX files."""
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed, trying textract fallback")
        try:
            import textract
            return textract.process(str(path)).decode("utf-8", errors="replace")
        except Exception as e:
            raise ResumeParseError(f"DOCX extraction failed: {e}") from e

    def _extract_latex(self, path: Path) -> str:
        """Extract text from LaTeX files, stripping commands."""
        raw = path.read_text(encoding="utf-8", errors="replace")
        # Strip LaTeX commands
        text = re.sub(r"\\(?:[a-zA-Z]+|[[\]{}])", "", raw)
        text = re.sub(r"\s+", " ", text)
        return text

    def _count_pages(self, path: Path) -> int:
        """Count pages in a PDF using PyMuPDF."""
        try:
            import fitz
            doc = fitz.open(str(path))
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 1

    # ------------------------------------------------------------------ #
    # Level 2: Section Detection
    # ------------------------------------------------------------------ #

    def _level2_detect_sections(self, text: str) -> Dict[str, str]:
        """Split resume text into sections using header regex."""
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {}
        current_section = "preamble"
        sections[current_section] = []

        for line in lines:
            stripped = line.strip()
            # First try exact match, then broad match
            if SECTION_HEADERS.match(stripped):
                header = stripped.rstrip(".:").strip().lower().replace(" ", "_")
                current_section = header
                if current_section not in sections:
                    sections[current_section] = []
            elif SECTION_HEADERS_BROAD.match(stripped):
                m = SECTION_HEADERS_BROAD.match(stripped)
                header_raw = m.group(0).rstrip(".:").strip()
                # Skip if the matched keyword is less than 60% of the line —
                # likely a content line containing a keyword (e.g. "Languages: Python, JS...")
                if len(header_raw) / max(len(stripped), 1) < 0.6:
                    sections.setdefault(current_section, []).append(stripped)
                    continue
                header = header_raw.lower().replace(" ", "_")
                current_section = header
                if current_section not in sections:
                    sections[current_section] = []
            else:
                if stripped:
                    sections.setdefault(current_section, []).append(stripped)

        # Merge common variants
        merged: Dict[str, List[str]] = {}
        section_map = {
            "work_experience": "experience",
            "employment": "experience",
            "professional_experience": "experience",
            "technical_skills": "skills",
            "core_competencies": "skills",
            "personal_projects": "projects",
            "project_experience": "projects",
            "professional_summary": "summary",
            "about_me": "summary",
        }
        for key, lines_list in sections.items():
            canon = section_map.get(key, key)
            if canon not in merged:
                merged[canon] = []
            merged[canon].extend(lines_list)

        # Remove preamble if empty
        if "preamble" in merged and not any(l.strip() for l in merged["preamble"]):
            del merged["preamble"]

        return {k: "\n".join(v) for k, v in merged.items()}

    def _find_missing(self, sections: Dict[str, str]) -> List[str]:
        """Identify expected sections that are missing from the resume."""
        expected = {"summary", "skills", "experience", "education", "projects"}
        return [s for s in expected if s not in sections]

    # ------------------------------------------------------------------ #
    # Level 3: LLM Structuring
    # ------------------------------------------------------------------ #

    def _level3_llm_structure(self, text: str, sections: Dict[str, str]) -> Dict[str, Any]:
        """Use LLM to extract structured fields from each section."""
        # First extract contact info via regex (fast path, no LLM needed)
        result: Dict[str, Any] = {}

        emails = EMAIL_RE.findall(text)
        result["email"] = emails[0] if emails else None

        phones = PHONE_RE.findall(text)
        result["phone"] = phones[0] if phones else None

        linkedin = LINKEDIN_RE.findall(text)
        result["linkedin"] = f"https://linkedin.com/in/{linkedin[0]}" if linkedin else None

        github = GITHUB_RE.findall(text)
        result["github"] = f"https://github.com/{github[0]}" if github else None

        portfolio = PORTFOLIO_RE.findall(text)
        result["portfolio"] = portfolio[0] if portfolio else None

        # Extract name (first non-empty line before any section header)
        result["name"] = self._extract_name(text)

        # Extract skills via regex (fast path)
        if "skills" in sections:
            skills_text = sections["skills"]
        elif "technical_skills" in sections:
            skills_text = sections["technical_skills"]
        else:
            skills_text = text
        result["skills"] = self._extract_skills(skills_text)

        # Use LLM for deeper extraction if available
        try:
            llm_result = self._llm_structure_sections(text, sections)
            result.update(llm_result)
        except Exception as e:
            logger.warning("LLM structuring failed: %s", e)
            # Fallback: regex extraction
            result["experience"] = self._fallback_extract_experience(sections.get("experience", ""))
            result["education"] = self._fallback_extract_education(sections.get("education", ""))
            result["projects"] = self._fallback_extract_projects(sections.get("projects", ""))
            result["certifications"] = self._fallback_extract_certifications(sections.get("certifications", ""))
            result["summary"] = sections.get("summary", "")[:500]

        return result

    def _extract_name(self, text: str) -> Optional[str]:
        """Extract candidate name from first substantive line."""
        lines = text.strip().split("\n")
        for line in lines[:15]:
            line = line.strip()
            if not line:
                continue
            # Skip if it looks like a section header, email, phone, or URL
            if SECTION_HEADERS.match(line):
                continue
            if EMAIL_RE.match(line) or PHONE_RE.match(line):
                continue
            if line.startswith("http") or "linkedin" in line.lower() or "github" in line.lower():
                continue
            if len(line.split()) in range(2, 6) and not any(
                kw in line.lower() for kw in ["resume", "cv", "curriculum"]
            ):
                return line
        return None

    def _extract_skills(self, text: str) -> List[str]:
        """Extract known skills from text using keyword matching + deduplication."""
        found = []
        text_lower = text.lower()
        seen = set()
        
        for skill in COMMON_SKILLS:
            if skill.lower() in text_lower and skill.lower() not in seen:
                found.append(skill)
                seen.add(skill.lower())
        
        # Sort by appearance order in text
        found_sorted = sorted(found, key=lambda s: text_lower.find(s.lower()))
        return found_sorted
    
    def extract_skills_categorized(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize extracted skills by type using whole-word matching."""
        import re
        categorized = {cat: [] for cat in SKILLS_CATEGORIES.keys()}
        
        for skill in skills:
            for cat, cat_skills in SKILLS_CATEGORIES.items():
                skill_lower = skill.lower()
                if any(
                    re.search(r'\b' + re.escape(skill_lower) + r'\b', cs.lower()) or
                    re.search(r'\b' + re.escape(cs.lower()) + r'\b', skill_lower)
                    for cs in cat_skills
                ):
                    categorized[cat].append(skill)
                    break
        
        return {k: v for k, v in categorized.items() if v}

    def _llm_structure_sections(self, text: str, sections: Dict[str, str]) -> Dict[str, Any]:
        """Use LLM to extract structured data from resume sections."""
        section_context = ""
        for name, content in sections.items():
            section_context += f"\n=== {name.upper()} ===\n{content[:2000]}\n"

        prompt = (
            "You are a resume parsing expert. Extract structured information from this resume.\n\n"
            "Resume text with sections:\n"
            f"{section_context[:6000]}\n\n"
            "Return ONLY a JSON object (no markdown, no code fences) with these fields:\n"
            "{\n"
            '  "name": "Full name or null",\n'
            '  "experience": [{"company": "str", "title": "str", "start_date": "str", "end_date": "str or null", "description": "str", "technologies_used": ["str"]}],\n'
            '  "education": [{"institution": "str", "degree": "str", "field": "str", "start_year": "str", "end_year": "str or null"}],\n'
            '  "projects": [{"name": "str", "description": "str", "technologies": ["str"]}],\n'
            '  "certifications": [{"name": "str", "issuer": "str", "date": "str"}],\n'
            '  "summary": "professional summary or null"\n'
            "}\n\n"
            "Use null for missing values. Be thorough -- extract ALL entries."
        )

        try:
            response = self.llm.invoke(prompt, max_tokens=1000, timeout=120)
            content = response.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]
            content = content.strip()
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            logger.warning("LLM JSON parse failed: %s", e)
            # Try to salvage partial JSON
            try:
                content = response.content.strip() if 'response' in locals() else ""
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                    content = content.rsplit("```", 1)[0]
                # Find first { and last }
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    content = content[start:end+1]
                    parsed = json.loads(content)
                    return parsed
            except Exception:
                pass
            # Re-raise to trigger fallback in _level3_llm_structure
            raise e

    def _fallback_extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract experience entries with structured data."""
        entries = []
        if not text:
            return entries
        
        # Split by date patterns or double newlines
        blocks = re.split(r"\n\s*\n|(?=\d{4})", text)
        for block in blocks[:10]:
            block = block.strip()
            if not block or len(block) < 10:
                continue
                
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            
            # Skip if doesn't look like an experience entry
            if not any(s in block.lower() for s in ["engineer", "developer", "manager", "analyst", "lead", "senior", "junior", "intern", "director", "specialist"]):
                continue
            
            entry = {
                "company": "",
                "role": "",
                "title": "",
                "start_date": "",
                "end_date": None,
                "description": "",
                "technologies_used": []
            }
            
            # Parse title and company - usually first 1-2 lines
            if len(lines) > 0:
                first_line = lines[0]
                # Try to split by common separators: | - at
                if " | " in first_line:
                    parts = first_line.split(" | ")
                    entry["title"] = parts[0].strip() if parts else ""
                    entry["company"] = parts[1].strip() if len(parts) > 1 else ""
                elif " - " in first_line:
                    parts = first_line.split(" - ")
                    entry["title"] = parts[0].strip() if parts else ""
                    entry["company"] = parts[1].strip() if len(parts) > 1 else ""
                elif " at " in first_line.lower():
                    parts = re.split(r" at ", first_line, flags=re.I)
                    entry["title"] = parts[0].strip() if parts else ""
                    entry["company"] = parts[1].strip() if len(parts) > 1 else ""
                else:
                    entry["title"] = first_line
            
            # Extract dates from all lines
            dates_found = False
            for line in lines[:3]:
                # Match patterns like "Jan 2021 - Dec 2022" or "2021 - 2022"
                date_match = re.search(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*(\d{4})\s*[-]\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Present|Current|Now)??\s*(\d{4}|Present|Current)?",
                    line, re.I
                )
                if date_match:
                    entry["start_date"] = date_match.group(2)
                    entry["end_date"] = date_match.group(4) if date_match.group(4) and date_match.group(4).lower() not in ("present", "current") else None
                    dates_found = True
                    break
            
            # Extract technologies mentioned
            entry["technologies_used"] = [s for s in COMMON_SKILLS if s.lower() in block.lower()]
            
            # Build description from remaining lines
            if len(lines) > 1:
                entry["description"] = " ".join(lines[1:])[:500]
            
            # Only add if we have meaningful data
            if entry.get("title") or entry.get("company"):
                entries.append(entry)
                
        return entries

    def _fallback_extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education entries with structured data."""
        entries = []
        if not text:
            return entries
        blocks = re.split(r"\n\s*\n", text)
        for block in blocks[:5]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            
            entry = {
                "institution": lines[0],
                "degree": "",
                "field": "",
                "cgpa": "",
                "start_year": "",
                "end_year": None
            }
            
            # Extract years
            years = re.findall(r"\b(19|20)\d{2}\b", " ".join(lines))
            if years:
                entry["start_year"] = years[0]
                entry["end_year"] = years[-1] if len(years) > 1 else None
            
            if len(lines) > 1:
                entry["degree"] = lines[1]
                # Try to extract CGPA if present
                cgpa_match = re.search(r"GPA\s*[:=]?\s*([\d.]+)", " ".join(lines), re.I)
                if cgpa_match:
                    entry["cgpa"] = cgpa_match.group(1)
            
            if len(lines) > 2:
                entry["field"] = lines[2]
            
            entries.append(entry)
        return entries

    def _fallback_extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract projects with structured data."""
        entries = []
        if not text:
            return entries
        
        # Split by double newlines or patterns that look like new entries
        blocks = re.split(r"\n\s*\n|(?=^[A-Z][A-Za-z0-9\s]*\|)", text, flags=re.MULTILINE)
        for block in blocks[:10]:
            block = block.strip()
            if not block or len(block) < 10:
                continue
            
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            
            # Extract technologies mentioned
            techs = [s for s in COMMON_SKILLS if s.lower() in block.lower()]
            
            # Skip if no technologies found (likely not a project entry)
            if not techs and not any(keyword in block.lower() for keyword in ["github", "deployed", "developed", "built", "created"]):
                continue
            
            # Extract GitHub URL if present
            github_match = re.search(r"github\.com/\S+", block, re.I)
            github_url = github_match.group(0) if github_match else ""
            
            # Extract deployment/live link if present
            deployment = ""
            deployment_match = re.search(r"(deployed|live|url|link|site)\s*[:=]?\s*(https?://\S+)", block, re.I)
            if deployment_match:
                deployment = deployment_match.group(2)
            
            project_entry = {
                "name": lines[0] if lines else "Project",
                "description": " ".join(lines[1:])[:300] if len(lines) > 1 else block[:300],
                "tech_stack": techs,
                "technologies": techs,
                "github": github_url,
                "deployment": deployment,
            }
            
            # Only add if we have meaningful data
            if project_entry.get("name") and project_entry.get("name") != "Project":
                entries.append(project_entry)
                
        return entries

    def _fallback_extract_certifications(self, text: str) -> List[Dict[str, Any]]:
        entries = []
        if not text:
            return entries
        for line in text.split("\n"):
            line = line.strip()
            if line:
                entries.append({"name": line, "issuer": "", "date": ""})
        return entries[:10]

    # ------------------------------------------------------------------ #
    # Level 4: Validation & Confidence
    # ------------------------------------------------------------------ #

    def _level4_validate(self, structured: Dict[str, Any], sections: Dict[str, str]) -> Tuple[ParserEvidence, int]:
        """Score confidence for each field and compute overall confidence.
        
        Scoring:
        - Name found = 15 points
        - Email found = 10 points  
        - Skills >= 5 = 20 points
        - Projects >= 2 = 20 points
        - Experience >= 1 = 20 points
        - Education >= 1 = 15 points
        Total = 100 max
        """
        evidence: Dict[str, FieldEvidence] = {}
        confidence_score = 0

        # Name validation (15 points)
        name = structured.get("name")
        if name and len(name.split()) >= 2:
            evidence["name"] = FieldEvidence(value=name, source="regex", confidence=95)
            confidence_score += 15
        elif name:
            evidence["name"] = FieldEvidence(value=name, source="regex", confidence=70)
            confidence_score += 7
        else:
            evidence["name"] = FieldEvidence(value=None, source="regex", confidence=0)

        # Email validation (10 points)
        email = structured.get("email")
        if email and EMAIL_RE.match(email):
            evidence["email"] = FieldEvidence(value=email, source="regex", confidence=100)
            confidence_score += 10
        elif email:
            evidence["email"] = FieldEvidence(value=email, source="regex", confidence=60)
            confidence_score += 6
        else:
            evidence["email"] = FieldEvidence(value=None, source="regex", confidence=0)

        # Phone validation (part of contact, minor weight)
        phone = structured.get("phone")
        if phone:
            digits = re.sub(r"\D", "", phone)
            phone_conf = 90 if len(digits) >= 10 else 60
            evidence["phone"] = FieldEvidence(value=phone, source="regex", confidence=phone_conf)
        else:
            evidence["phone"] = FieldEvidence(value=None, source="regex", confidence=0)

        # Skills validation (20 points for >= 5 skills)
        skills = structured.get("skills", [])
        skill_conf = 0
        if len(skills) >= 5:
            skill_conf = 95
            confidence_score += 20
        elif len(skills) >= 3:
            skill_conf = 75
            confidence_score += 12
        elif len(skills) >= 1:
            skill_conf = 60
            confidence_score += 8
        if "skills" in sections:
            skills_text = sections["skills"].lower()
            matched = sum(1 for s in skills if s.lower() in skills_text)
            if matched > 0:
                skill_conf = min(100, skill_conf + 10)
        evidence["skills"] = FieldEvidence(value=skills, source="regex+llm", confidence=skill_conf)

        # Experience validation (20 points for >= 1 entry)
        exp = structured.get("experience", [])
        exp_conf = 0
        if len(exp) >= 1:
            exp_conf = 85
            confidence_score += 20
        elif len(exp) > 0:
            exp_conf = 70
            confidence_score += 10
        if exp_conf > 0:
            evidence["experience"] = FieldEvidence(value=exp, source="llm+regex", confidence=exp_conf)

        # Education validation (15 points for >= 1 entry)
        edu = structured.get("education", [])
        edu_conf = 0
        if len(edu) >= 1:
            edu_conf = 85
            confidence_score += 15
        elif len(edu) > 0:
            edu_conf = 70
            confidence_score += 7
        if edu_conf > 0:
            evidence["education"] = FieldEvidence(value=edu, source="llm+regex", confidence=edu_conf)

        # Projects validation (20 points for >= 2 entries)
        proj = structured.get("projects", [])
        proj_conf = 0
        if len(proj) >= 2:
            proj_conf = 90
            confidence_score += 20
        elif len(proj) >= 1:
            proj_conf = 70
            confidence_score += 10
        if proj_conf > 0:
            evidence["projects"] = FieldEvidence(value=proj, source="llm+regex", confidence=proj_conf)

        # Certifications (minor)
        certs = structured.get("certifications", [])
        if certs:
            evidence["certifications"] = FieldEvidence(value=certs, source="llm+regex", confidence=75)

        # Summary
        summary = structured.get("summary", "")
        if summary and len(summary) > 20:
            evidence["summary"] = FieldEvidence(value=summary, source="llm", confidence=80)

        # Cap confidence at 100
        overall = min(100, confidence_score)
        
        # Log confidence breakdown
        self.log.append(
            f"Confidence breakdown: {confidence_score} -> {overall}% "
            f"(skills={len(skills)}, exp={len(exp)}, edu={len(edu)}, proj={len(proj)})"
        )

        return ParserEvidence(
            fields=evidence,
            overall_confidence=overall,
            sections_detected=list(sections.keys())
        ), overall

    # ------------------------------------------------------------------ #
    # Level 5: Role Inference
    # ------------------------------------------------------------------ #

    def _level5_infer_roles(self, structured: Dict[str, Any], sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """Infer candidate roles from skills, experience, and project content.
        
        Returns scored dicts: [{"role": "ML Engineer", "score": 95}, ...]
        Sorted descending, top 3-5 only.
        """
        roles_found: Dict[str, float] = {}
        all_text = ""

        # Collect all extractable text
        if "experience" in sections:
            all_text += sections["experience"] + " "
        if "skills" in sections:
            all_text += sections["skills"] + " "
        all_text += " ".join(structured.get("skills", [])) + " "
        all_text += " ".join(
            e.get("title", "") + " " + e.get("description", "")
            for e in structured.get("experience", [])
        )
        all_text += " ".join(
            p.get("name", "") + " " + p.get("description", "")
            for p in structured.get("projects", [])
        )
        all_text_lower = all_text.lower()

        # Count explicit skill matches vs. simple keyword hits
        skills_list = [s.lower() for s in structured.get("skills", [])]

        for role, keywords in ROLE_KEYWORDS.items():
            keyword_hits = 0
            skill_hits = 0
            for kw in keywords:
                if kw in all_text_lower:
                    keyword_hits += 1
                # Bonus if keyword also appears as a declared skill
                if kw in skills_list:
                    skill_hits += 1
            if keyword_hits > 0:
                raw = keyword_hits / len(keywords) * 100
                bonus = (skill_hits / len(keywords)) * 20  # up to +20 for declared skills
                roles_found[role] = min(100, raw + bonus)

        # Sort by score descending, keep roles above 25%, take top 5
        sorted_roles = sorted(roles_found.items(), key=lambda x: x[1], reverse=True)
        filtered = [r for r in sorted_roles if r[1] >= 25][:5]

        # Also return flat role names for backward compat
        self._scored_roles = [{"role": r[0], "score": round(r[1], 1)} for r in filtered]
        return [r[0] for r in filtered]

    # ------------------------------------------------------------------ #
    # Level 6: Resume JSON Assembly
    # ------------------------------------------------------------------ #

    def _compute_quality_score(self, structured: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Compute resume quality score based on completeness and depth."""
        breakdown = {}
        total = 0

        # Name (10 pts)
        name = structured.get("name")
        if name and len(name.split()) >= 2:
            breakdown["name"] = 10
            total += 10
        elif name:
            breakdown["name"] = 5
            total += 5
        else:
            breakdown["name"] = 0

        # Email (10 pts)
        if structured.get("email"):
            breakdown["email"] = 10
            total += 10
        else:
            breakdown["email"] = 0

        # Phone (5 pts)
        if structured.get("phone"):
            breakdown["phone"] = 5
            total += 5
        else:
            breakdown["phone"] = 0

        # Links (5 pts)
        links = sum(1 for k in ("linkedin", "github", "portfolio") if structured.get(k))
        breakdown["links"] = min(5, links * 2)
        total += breakdown["links"]

        # Skills (20 pts: 1 pt per skill up to 20)
        skills = structured.get("skills", [])
        skill_score = min(20, len(skills))
        breakdown["skills"] = skill_score
        total += skill_score

        # Experience (20 pts: 10 per entry up to 20)
        exp = structured.get("experience", [])
        exp_score = min(20, len(exp) * 10)
        breakdown["experience"] = exp_score
        total += exp_score

        # Education (10 pts)
        edu = structured.get("education", [])
        edu_score = 10 if len(edu) >= 1 else (5 if edu else 0)
        breakdown["education"] = edu_score
        total += edu_score

        # Projects (15 pts: 3 per project up to 15)
        proj = structured.get("projects", [])
        proj_score = min(15, len(proj) * 3)
        breakdown["projects"] = proj_score
        total += proj_score

        # Certifications (5 pts: 1 per cert up to 5)
        certs = structured.get("certifications", [])
        cert_score = min(5, len(certs))
        breakdown["certifications"] = cert_score
        total += cert_score

        return round(total, 1), breakdown

    def _level6_assemble(
        self,
        structured: Dict[str, Any],
        evidence: ParserEvidence,
        confidence: int,
        roles: List[str],
        sections_detected: List[str],
        sections_missing: List[str],
        raw_text: str,
        total_pages: int,
        source_path: str,
        start: datetime,
    ) -> Resume:
        """Assemble the final Resume model from all parsed data."""
        skills = structured.get("skills", [])
        skills_categorized = self.extract_skills_categorized(skills)
        quality_score, quality_breakdown = self._compute_quality_score(structured)
        scored_roles = getattr(self, '_scored_roles', [])

        return Resume(
            name=structured.get("name"),
            email=structured.get("email"),
            phone=structured.get("phone"),
            linkedin=structured.get("linkedin"),
            github=structured.get("github"),
            portfolio=structured.get("portfolio"),
            skills=skills,
            skills_categorized=skills_categorized,
            experience=structured.get("experience", []),
            projects=structured.get("projects", []),
            education=structured.get("education", []),
            certifications=structured.get("certifications", []),
            roles=roles,
            scored_roles=scored_roles,
            quality_score=quality_score,
            quality_breakdown=quality_breakdown,
            total_pages=total_pages,
            sections_detected=sections_detected,
            sections_missing=sections_missing,
            confidence=confidence,
            evidence=evidence,
            parse_log=[],
            raw_text=raw_text[:10000],
            source_path=source_path,
            parsed_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------ #
    # Cache & Persistence
    # ------------------------------------------------------------------ #

    def _save_resume_cache(self, resume: Resume, source_path: str) -> str:
        """Save parsed resume as JSON cache for downstream components."""
        cache_file = self.cache_dir / "resume_cache.json"
        
        cache_data = {
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "location": "",  # Not extracted, but included for completeness
            "linkedin": resume.linkedin,
            "github": resume.github,
            "portfolio": resume.portfolio or "",
            
            "skills": resume.skills,
            "skills_categorized": resume.skills_categorized or self.extract_skills_categorized(resume.skills),
            "projects": resume.projects,
            "experience": resume.experience,
            "education": resume.education,
            "certifications": resume.certifications,
            
            "target_roles": resume.roles,
            "scored_roles": resume.scored_roles,
            "quality_score": resume.quality_score,
            "quality_breakdown": resume.quality_breakdown,
            "confidence": resume.confidence,
            
            # Metadata for debugging
            "parsed_at": resume.parsed_at,
            "source_path": source_path,
            "total_pages": resume.total_pages,
            "sections_detected": resume.sections_detected,
            "sections_missing": resume.sections_missing,
            "extraction_stats": self.extraction_stats,
            "parse_log": resume.parse_log,
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info("[resume_parser] Cached resume to %s", cache_file)
        self.log.append(f"Saved cache: {cache_file}")
        return str(cache_file)

    def load_resume_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached resume if it exists."""
        cache_file = self.cache_dir / "resume_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("[resume_parser] Failed to load cache: %s", e)
        return None
