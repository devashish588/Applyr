import os
import tempfile
from core.utils.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf


def _read_header(path):
    with open(path, "rb") as f:
        return f.read(4)


def test_generate_resume_pdf_basic(tmp_path):
    text = "John Doe\n\nExperienced Software Engineer.\n\n- Built APIs\n- Led team\n"
    out = tmp_path / "resume_test.pdf"
    path = generate_resume_pdf(text, str(out))
    assert os.path.exists(path)
    header = _read_header(path)
    assert header.startswith(b"%PDF")
    assert out.stat().st_size > 0


def test_generate_cover_letter_pdf_basic(tmp_path):
    text = "Dear Hiring Team,\n\nI am writing to apply...\n\nSincerely,\nJohn"
    out = tmp_path / "cover_test.pdf"
    path = generate_cover_letter_pdf(text, str(out))
    assert os.path.exists(path)
    header = _read_header(path)
    assert header.startswith(b"%PDF")
    assert out.stat().st_size > 0


def test_generate_pdf_empty_rejected(tmp_path):
    out = tmp_path / "empty.pdf"
    try:
        generate_resume_pdf("   ", str(out))
        assert False, "Expected ValueError for empty input"
    except ValueError:
        pass
    try:
        generate_cover_letter_pdf("", str(out))
        assert False, "Expected ValueError for empty input"
    except ValueError:
        pass


def test_multi_page_resume(tmp_path):
    # Create a long text to force multiple pages
    text = "\n\n".join([f"Section {i}\n\n" + "Line\n" * 80 for i in range(6)])
    out = tmp_path / "multi.pdf"
    path = generate_resume_pdf(text, str(out))
    assert os.path.exists(path)
    assert out.stat().st_size > 1000
    header = _read_header(path)
    assert header.startswith(b"%PDF")
