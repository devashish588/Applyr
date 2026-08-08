import json
import pytest
from core import schemas


def test_valid_resume_parsed_minimal():
    r = schemas.ResumeParsed(name="Alice", email="a@example.com")
    assert r.name == "Alice"
    assert r.email == "a@example.com"
    # optional lists default
    assert isinstance(r.skills, list) and r.skills == []


def test_valid_match_analysis_and_serialization():
    m = schemas.MatchAnalysis(final_score=85, recommendation="Apply", explanation="Matches skills")
    s = m.model_dump()
    assert s["final_score"] == 85
    j = json.dumps(s)
    loaded = schemas.MatchAnalysis.model_validate_json(j)
    assert loaded.final_score == 85


def test_valid_tailored_material():
    t = schemas.TailoredMaterial(
        tailored_bullets=["Built X"],
        cover_letter="Short cover",
        skills_to_highlight=["Python"],
        tailored_resume_path="./resume/tailored/alice.txt",
    )
    assert t.tailored_bullets[0] == "Built X"
    assert t.cover_letter == "Short cover"


def test_asset_paths_optional():
    a = schemas.AssetPaths()
    assert a.tailored_resume_path is None
    assert a.cover_letter_pdf_path is None


def test_template_validation():
    tpl = schemas.Template(name="default", kind="resume", content="%NAME%")
    assert tpl.kind == "resume"

    with pytest.raises(Exception):
        schemas.Template(name="bad", kind="invalid", content="x")


def test_match_analysis_required_field():
    # missing required final_score should raise
    with pytest.raises(Exception):
        schemas.MatchAnalysis()


def test_resume_parsed_from_dict_and_serialization():
    payload = {"name": "Bob", "skills": ["python", "sql"], "raw_text": "..."}
    r = schemas.ResumeParsed(**payload)
    assert r.name == "Bob"
    j = r.model_dump()
    assert j["skills"] == ["python", "sql"]


if __name__ == '__main__':
    pytest.main([__file__])
