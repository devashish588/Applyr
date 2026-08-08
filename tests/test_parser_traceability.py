import pytest
from pathlib import Path
from core.services.resume_parser_service import ResumeParserService

RESUME_PATH = Path("resume/master_resume.pdf")

@pytest.mark.skipif(not RESUME_PATH.exists(), reason="master_resume.pdf not present")
def test_master_resume_experience_traceability():
    svc = ResumeParserService()
    resume = svc.parse(str(RESUME_PATH))
    canon = svc.to_canonical(resume)
    raw = resume.raw_text or ""

    # For each experience entry, ensure at least one string field is present in raw_text
    for entry in canon.experience:
        # entry should be a dict-like object
        assert isinstance(entry, dict)
        found = False
        for k, v in entry.items():
            if isinstance(v, str) and v.strip():
                if v.strip() in raw:
                    found = True
                    break
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item.strip() and item.strip() in raw:
                        found = True
                        break
                if found:
                    break
        assert found, f"Experience entry missing traceable evidence for field keys: {list(entry.keys())}"


def test_confidence_reduces_when_no_evidence():
    svc = ResumeParserService()
    # Structured with fabricated experience entries that won't match any section text
    structured = {
        "name": "Test User",
        "email": "test@example.com",
        "skills": ["Python", "SQL"],
        "experience": [
            {"company": "MadeUpCo", "title": "Imaginary Role", "description": "No match here"}
        ],
        "education": [],
        "projects": [],
        "certifications": []
    }
    sections = {}  # empty sections -> no evidence
    evidence, confidence = svc._level4_validate(structured, sections)
    # Confidence should be low (not 100)
    assert confidence < 100
    # Experience evidence confidence should be low (<50) because no textual evidence
    exp_evidence = evidence.fields.get("experience")
    assert exp_evidence is not None
    assert exp_evidence.confidence < 50
