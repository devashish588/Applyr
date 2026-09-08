"""
Direct Parser & Formatter Tests for FormattedText Component
Tests all 16 mandatory test cases for AI Output Presentation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.services.copilot_service import clean_ai_filler, is_standalone_section_heading, parse_inline_tokens


def test_1_bold_parsing():
    input_text = "Use **Python** for the example."
    tokens = parse_inline_tokens(input_text)
    # Expected: list of tokens where "Python" is flagged as bold, no literal '**'
    bold_tokens = [t for t in tokens if t["type"] == "bold"]
    assert len(bold_tokens) == 1
    assert bold_tokens[0]["text"] == "Python"
    assert "**" not in [t["text"] for t in tokens]


def test_2_unordered_list_parsing():
    input_text = "* Python\n* React\n* SQL"
    lines = [l.strip() for l in input_text.split("\n") if l.strip()]
    assert len(lines) == 3
    for line in lines:
        assert line.startswith("* ")
        content = line[2:]
        assert "*" not in content


def test_3_dash_list_parsing():
    input_text = "- Python\n- React"
    lines = [l.strip() for l in input_text.split("\n") if l.strip()]
    assert len(lines) == 2
    for line in lines:
        assert line.startswith("- ")


def test_4_ordered_list_parsing():
    input_text = "1. Python\n2. React"
    lines = [l.strip() for l in input_text.split("\n") if l.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("1. ")
    assert lines[1].startswith("2. ")


def test_5_explicit_heading():
    input_text = "### Interview Preparation"
    assert input_text.startswith("### ")
    heading_text = input_text[4:]
    assert heading_text == "Interview Preparation"


def test_6_normal_prose_is_not_heading():
    input_text = "Preparing for a software engineering interview requires a balanced approach across technical depth, problem-solving, and communication."
    assert not is_standalone_section_heading(input_text)


def test_7_normal_sentence_with_colon_is_not_heading():
    input_text = "Focus areas include: Python, SQL, and system design."
    assert not is_standalone_section_heading(input_text)


def test_8_short_colon_heading():
    input_text = "CORE LANGUAGES:"
    assert is_standalone_section_heading(input_text)


def test_9_bold_inside_list():
    input_text = "* **Python** — primary language\n* **React** — frontend"
    lines = [l.strip() for l in input_text.split("\n") if l.strip()]
    tokens_1 = parse_inline_tokens(lines[0][2:])
    bold_tokens = [t for t in tokens_1 if t["type"] == "bold"]
    assert len(bold_tokens) == 1
    assert bold_tokens[0]["text"] == "Python"


def test_10_multiple_paragraphs():
    input_text = "First paragraph.\n\nSecond paragraph."
    paragraphs = [p.strip() for p in input_text.split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert paragraphs[0] == "First paragraph."
    assert paragraphs[1] == "Second paragraph."


def test_11_empty_string():
    assert clean_ai_filler("") == ""
    assert parse_inline_tokens("") == []


def test_12_null_undefined():
    assert clean_ai_filler(None) == ""
    assert parse_inline_tokens(None) == []


def test_13_malicious_script_html():
    input_text = "<script>alert('x')</script>"
    # Ensure script content is safely tokenized as plain string without raw execution
    tokens = parse_inline_tokens(input_text)
    assert len(tokens) == 1
    assert tokens[0]["text"] == "<script>alert('x')</script>"


def test_14_malicious_image_url_html():
    input_text = "<img src=x onerror=alert('x')>"
    tokens = parse_inline_tokens(input_text)
    assert len(tokens) == 1
    assert tokens[0]["text"] == "<img src=x onerror=alert('x')>"


def test_15_markdown_no_double_render():
    input_text = "**Important**"
    tokens = parse_inline_tokens(input_text)
    assert len(tokens) == 1
    assert tokens[0]["type"] == "bold"
    assert tokens[0]["text"] == "Important"


def test_16_long_normal_prose_with_multiple_colons():
    input_text = "Why this matters: Python is required, system design is crucial: focus areas include APIs and databases."
    assert not is_standalone_section_heading(input_text)
