import os
import tempfile
import pytest
from core.services.resume_parser_service import ResumeParserService, ResumeParseError
from core.models import Resume


def write_temp_file(contents: str, suffix: str = ".txt") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)
    return path


def test_preserve_raw_text_txt_and_sections():
    svc = ResumeParserService()
    text = """
    Alice Example
    Email: alice@example.com

    Summary:
    Experienced engineer.

    Skills:
    Python, SQL, Docker

    Experience:
    Software Engineer | Acme Corp | 2019 - 2022
    - Built X\n

    Education:
    B.Sc. Computer Science, 2018
    """
    path = write_temp_file(text, suffix=".txt")
    try:
        resume = svc.parse(path)
        # raw_text preserved
        assert resume.raw_text is not None
        assert "Alice Example" in resume.raw_text
        # sections detected should include 'experience' and 'skills'
        assert any(s.lower().startswith("experience") or s == "experience" for s in resume.sections_detected)
        assert isinstance(resume.experience, list)
    finally:
        os.remove(path)


def test_llm_partial_result_triggers_fallback():
    svc = ResumeParserService()
    # Prepare a simple resume text with an experience block
    text = """
    Alice Example

    Experience:
    Senior Engineer - Beta Inc - 2020 - Present
    - Led team

    Skills:
    Python, AWS
    """
    path = write_temp_file(text, suffix=".txt")
    # Monkeypatch the LLM structurer to return partial data (no experience)
    original = svc._llm_structure_sections
    def partial_llm(text_arg, sections_arg):
        return {"name": "Alice Example", "skills": ["Python"]}
    svc._llm_structure_sections = partial_llm
    try:
        resume = svc.parse(path)
        # Because LLM returned no experience, fallback extractor should populate it
        assert isinstance(resume.experience, list)
        assert len(resume.experience) >= 1
    finally:
        svc._llm_structure_sections = original
        os.remove(path)


def test_multpage_pdf_extraction_preserves_pages_and_content():
    # This test uses PyMuPDF to create and then extract a simple multi-page PDF.
    fitz = pytest.importorskip("fitz")
    svc = ResumeParserService()
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Alice Example\nPage 1 Content\nExperience:\nCompany A - 2018-2020")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Page 2 Content\nProjects:\nProject X - github.com/example/project")
    tmpdir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmpdir, "test_multi.pdf")
    doc.save(pdf_path)
    doc.close()

    try:
        resume = svc.parse(pdf_path)
        # Total pages should be 2
        assert resume.total_pages == 2 or resume.total_pages >= 2
        # raw_text should contain content from both pages
        assert "Page 1 Content" in resume.raw_text
        assert "Page 2 Content" in resume.raw_text
        # The enforced page marker should be present
        assert "---PAGE_BREAK---" in resume.raw_text
    finally:
        try:
            os.remove(pdf_path)
            os.rmdir(tmpdir)
        except Exception:
            pass
