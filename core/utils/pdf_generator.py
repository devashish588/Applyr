"""
Simple ReportLab-based PDF generator for Applyr.
Provides deterministic, Unicode-safe PDF creation for resumes and cover letters.
"""
from pathlib import Path
import os

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except Exception as e:
    raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")


def _ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _register_font():
    # Try to register DejaVuSans if available on system for better unicode support.
    # Fallback to Helvetica (built-in).
    try:
        # Common location on many systems
        dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(dejavu):
            pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu))
            return "DejaVuSans"
    except Exception:
        pass
    return "Helvetica"


def _build_story_from_text(text: str):
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=normal,
        leftIndent=12,
        bulletIndent=0,
    )

    story = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            story.append(Spacer(1, 6))
            continue
        # If block appears to be a bullet list (lines starting with • or -), convert
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if all(l.startswith("•") or l.startswith("-") or l.startswith("*") for l in lines) and len(lines) > 1:
            items = []
            for l in lines:
                t = l.lstrip("•-* ")
                items.append(ListItem(Paragraph(t, normal)))
            story.append(ListFlowable(items, bulletType='bullet', start='circle'))
            story.append(Spacer(1, 6))
            continue
        # Otherwise treat as paragraph (preserve short headings if all-caps)
        if len(block) < 80 and block.isupper():
            story.append(Paragraph(f"<b>{block}</b>", styles["Heading2"]))
        else:
            # Replace single newlines inside block with <br/>
            para_text = "<br/>".join(lines)
            story.append(Paragraph(para_text, normal))
        story.append(Spacer(1, 6))
    return story


def _validate_pdf(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "file-not-found"
    size = path.stat().st_size
    if size == 0:
        return False, "empty-file"
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            if not header.startswith(b"%PDF"):
                return False, "invalid-pdf-header"
    except Exception:
        return False, "read-error"
    return True, "ok"


def _generate_pdf_from_text(text: str, out_path: str, title: str = None):
    out = Path(out_path)
    _ensure_dir(out)
    font_name = _register_font()

    doc = SimpleDocTemplate(str(out), pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    story = []
    styles = getSampleStyleSheet()
    if title:
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 12))
    story.extend(_build_story_from_text(text))

    # Build deterministically
    doc.build(story)

    ok, reason = _validate_pdf(out)
    if not ok:
        raise RuntimeError(f"PDF generation failed: {reason}")
    return str(out)


def generate_resume_pdf(text: str, out_path: str) -> str:
    """Generate a resume PDF from plain text.

    Returns the path to the generated PDF on success.
    Raises RuntimeError or ValueError on failure.
    """
    if not text or not text.strip():
        raise ValueError("Empty resume content — refusing to generate PDF")
    return _generate_pdf_from_text(text, out_path, title="Resume")


def generate_cover_letter_pdf(text: str, out_path: str) -> str:
    """Generate a cover letter PDF from plain text."""
    if not text or not text.strip():
        raise ValueError("Empty cover letter content — refusing to generate PDF")
    return _generate_pdf_from_text(text, out_path, title="Cover Letter")
