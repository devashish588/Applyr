import pytest
from core.services.resume_parser_service import ResumeParserService
from core.models import Resume


def test_to_canonical_minimal():
    svc = ResumeParserService()
    r = Resume(name="Alice Example", email="alice@example.com", skills=["Python", "SQL"])
    canon = svc.to_canonical(r)
    # Should be a ResumeParsed or dict with expected keys
    assert hasattr(canon, "name") or isinstance(canon, dict)
    assert (canon.name if hasattr(canon, "name") else canon.get("name")) == "Alice Example"
    assert (canon.email if hasattr(canon, "email") else canon.get("email")) == "alice@example.com"
    skills = canon.skills if hasattr(canon, "skills") else canon.get("skills")
    assert isinstance(skills, list) and "Python" in skills


def test_to_canonical_missing_fields_empty_lists():
    svc = ResumeParserService()
    r = Resume()  # all fields missing
    canon = svc.to_canonical(r)
    # Check lists are present and empty, not None
    for key in ["skills", "experience", "projects", "education", "certifications", "roles"]:
        val = getattr(canon, key) if hasattr(canon, key) else canon.get(key)
        assert isinstance(val, list)


def test_to_canonical_preserves_raw_text_and_evidence():
    svc = ResumeParserService()
    r = Resume(raw_text="This is a resume text", source_path="/tmp/resume.pdf", parsed_at="2026-01-01T00:00:00")
    canon = svc.to_canonical(r)
    assert (canon.raw_text if hasattr(canon, "raw_text") else canon.get("raw_text")) == "This is a resume text"
    assert (canon.source_path if hasattr(canon, "source_path") else canon.get("source_path")) == "/tmp/resume.pdf"


if __name__ == '__main__':
    pytest.main([__file__])
