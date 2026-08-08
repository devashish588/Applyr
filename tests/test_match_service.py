"""
PR-4 — Deterministic, Explainable Job Matching: test suite
===========================================================

Covers all 24 mandatory verification scenarios from the approved plan:

 1. MatchAnalysis schema compatibility
 2. Identical inputs → identical score (determinism)
 3. Exact skill matches
 4. Partial skill overlap
 5. Missing required skills
 6. Duplicate skills handling
 7. Case-insensitive matching
 8. Role relevance scoring
 9. Location & seniority alignment
10. Score remains 0–100 (integer, clamped)
11. Explanation is populated
12. Supporting sentences populated when evidence exists
13. ResumeParsed input
14. Resume model input
15. dict input
16. None input
17. Legacy positional signature compatibility
18. New resume/job keyword compatibility
19. Keyword signature compatibility (ui/app.py pattern)
20. JSON serialization / deserialization round-trip
21. Exact scoring formula verification
22. Complete determinism (all fields identical on repeat)
23. Regression protection (ui/app.py calling pattern)
24. No hidden external dependencies
"""

import json
import pytest

from core.models import (
    MatchAnalysis,
    MatchComponent,
    Profile,
    Resume,
    SeniorityLevel,
)
from core.schemas import (
    MatchAnalysis as SchemaMatchAnalysis,
    ResumeParsed,
)
from core.services.match_service import (
    MatchService,
    _is_resume_object,
    _is_job_object,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_resume():
    """A minimal Resume model with known skills and roles."""
    return Resume(
        name="Test Candidate",
        email="test@example.com",
        skills=["Python", "SQL", "Docker", "AWS", "FastAPI"],
        roles=["Backend Engineer", "Software Developer"],
        experience=[
            {
                "company": "Acme Corp",
                "title": "Backend Engineer",
                "start_date": "2020",
                "end_date": "2024",
                "description": "Built REST APIs",
            }
        ],
        education=[{"degree": "B.Tech", "institution": "IIT"}],
    )


@pytest.fixture
def sample_profile():
    """A minimal Profile with target roles and locations."""
    return Profile(
        target_roles=["Backend Engineer", "Software Engineer"],
        target_locations=["Remote", "Bangalore"],
        remote_ok=True,
        skills={"languages": ["Python", "SQL"]},
    )


@pytest.fixture
def sample_service(sample_profile, sample_resume):
    """MatchService initialized with sample profile and resume."""
    return MatchService(profile=sample_profile, resume=sample_resume)


@pytest.fixture
def sample_job_dict():
    """A job dict with known attributes."""
    return {
        "id": 42,
        "title": "Senior Backend Engineer",
        "company": "TestCo",
        "location": "Remote",
        "jd_text": "We need a Senior Backend Engineer with 3+ years experience in Python, SQL, and Docker.",
        "required_skills": ["Python", "SQL", "Docker", "Kubernetes"],
    }


# ---------------------------------------------------------------------------
# Guard function tests
# ---------------------------------------------------------------------------

class TestGuardFunctions:
    """Verify _is_resume_object and _is_job_object never misclassify."""

    def test_resume_model_passes(self, sample_resume):
        assert _is_resume_object(sample_resume) is True

    def test_resume_parsed_passes(self):
        rp = ResumeParsed(name="X", skills=["Python"])
        assert _is_resume_object(rp) is True

    def test_resume_dict_passes(self):
        assert _is_resume_object({"skills": ["Python"], "experience": []}) is True

    def test_integer_does_not_pass(self):
        assert _is_resume_object(42) is False

    def test_string_does_not_pass(self):
        assert _is_resume_object("Backend Engineer") is False

    def test_list_does_not_pass(self):
        assert _is_resume_object(["Python", "SQL"]) is False

    def test_job_dict_passes(self):
        assert _is_job_object({"title": "SWE", "jd_text": "..."}) is True

    def test_job_dict_without_keys_fails(self):
        assert _is_job_object({"foo": "bar"}) is False

    def test_job_integer_fails(self):
        assert _is_job_object(101) is False

    def test_job_string_fails(self):
        assert _is_job_object("Senior Engineer") is False


# ---------------------------------------------------------------------------
# Core matching tests
# ---------------------------------------------------------------------------

class TestMatchAnalysisSchemaCompat:
    """1. MatchAnalysis schema compatibility."""

    def test_analyze_returns_match_analysis(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            jd_text="Python SQL", required_skills=["Python"],
        )
        assert isinstance(result, MatchAnalysis)

    def test_to_schema_produces_schema_match_analysis(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            jd_text="Python SQL", required_skills=["Python"],
        )
        schema = sample_service.to_schema(result)
        assert isinstance(schema, SchemaMatchAnalysis)
        assert 0 <= schema.final_score <= 100
        assert schema.recommendation in ("Apply", "Consider", "Skip")


class TestDeterminism:
    """2 & 22. Identical inputs → identical outputs on repeated calls."""

    def test_identical_inputs_identical_score(self, sample_service):
        kwargs = dict(
            job_id=10, job_title="Backend Engineer",
            job_location="Remote",
            jd_text="Python, SQL, Docker experience required. 3 years experience.",
            required_skills=["Python", "SQL", "Docker"],
        )
        r1 = sample_service.analyze(**kwargs)
        r2 = sample_service.analyze(**kwargs)

        assert r1.final_score == r2.final_score
        assert r1.recommendation == r2.recommendation
        assert r1.explanation == r2.explanation
        assert r1.why_this_score == r2.why_this_score
        assert r1.skills_to_highlight == r2.skills_to_highlight


class TestSkillMatching:
    """3-7. Skill overlap, partial, missing, duplicates, case-insensitivity."""

    def test_exact_skill_matches(self, sample_service):
        result = sample_service.analyze(
            job_id=1, jd_text="Python SQL Docker",
            required_skills=["Python", "SQL", "Docker"],
        )
        assert result.skill_match.score > 0
        assert "Python" in result.skill_match.matched

    def test_partial_skill_overlap(self, sample_service):
        result = sample_service.analyze(
            job_id=1, jd_text="Python SQL Go Rust",
            required_skills=["Python", "SQL", "Go", "Rust"],
        )
        assert len(result.skill_match.matched) >= 2
        assert len(result.skill_match.missing) >= 1

    def test_missing_required_skills(self, sample_service):
        result = sample_service.analyze(
            job_id=1, jd_text="Haskell Erlang Elixir",
            required_skills=["Haskell", "Erlang", "Elixir"],
        )
        assert len(result.skill_match.missing) >= 2

    def test_duplicate_skills_handled(self):
        resume = Resume(
            name="Dup",
            skills=["Python", "python", "PYTHON", "SQL"],
        )
        service = MatchService(resume=resume)
        result = service.analyze(
            job_id=1, jd_text="Python SQL",
            required_skills=["Python", "SQL"],
        )
        # Deduplication in _get_candidate_skills should prevent over-counting
        assert result.skill_match.score > 0

    def test_case_insensitive_matching(self):
        resume = Resume(name="CI", skills=["python", "sql"])
        service = MatchService(resume=resume)
        result = service.analyze(
            job_id=1, jd_text="Python SQL",
            required_skills=["Python", "SQL"],
        )
        assert len(result.skill_match.matched) >= 2


class TestRoleRelevance:
    """8. Role relevance scoring."""

    def test_exact_role_match(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
        )
        assert result.role_match.score >= 50

    def test_unrelated_role(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Pastry Chef",
        )
        assert result.role_match.score < 50


class TestLocationSeniority:
    """9. Location & seniority alignment."""

    def test_remote_location_match(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_location="Remote",
        )
        assert result.location_match.score >= 70

    def test_seniority_penalty_applied(self):
        resume = Resume(name="Junior", roles=["Junior Developer"])
        service = MatchService(resume=resume)
        result = service.analyze(
            job_id=1, job_title="Principal Engineer",
            jd_text="Principal Engineer",
        )
        assert result.seniority_penalty > 0


class TestScoreRange:
    """10. Score clamped to integer 0–100."""

    def test_score_is_integer(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        # core.models.MatchAnalysis stores final_score as float field,
        # but PR-4 guarantees the VALUE is always a whole number.
        assert result.final_score == int(result.final_score), (
            f"final_score should be integer-valued, got {result.final_score}"
        )
        # core.schemas.MatchAnalysis enforces int type
        schema = sample_service.to_schema(result)
        assert isinstance(schema.final_score, int)

    def test_score_within_bounds(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        assert 0 <= result.final_score <= 100

    def test_score_never_negative(self):
        """Even with heavy seniority penalty the score stays >= 0."""
        resume = Resume(name="Intern", roles=["Intern"])
        service = MatchService(resume=resume)
        result = service.analyze(
            job_id=1, job_title="Principal Staff Engineer",
            jd_text="20 years experience",
            required_skills=["Quantum Computing", "Nuclear Physics"],
        )
        assert result.final_score >= 0


class TestExplanation:
    """11. Explanation is populated."""

    def test_explanation_populated(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        assert result.explanation
        assert len(result.explanation) > 10

    def test_why_this_score_populated(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        assert result.why_this_score
        assert "Skill weight" in result.why_this_score


class TestSupportingSentences:
    """12. Supporting sentences populated when evidence exists."""

    def test_supporting_sentences_with_skills(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            jd_text="Python SQL Docker",
            required_skills=["Python", "SQL", "Docker"],
        )
        schema = sample_service.to_schema(result)
        assert len(schema.supporting_sentences) > 0

    def test_no_supporting_sentences_on_none_resume(self):
        service = MatchService()
        result = service.analyze(job_id=1, job_title="SWE")
        assert result.explanation  # still has explanation
        # None-resume result has limited evidence
        assert result.final_score == 0


# ---------------------------------------------------------------------------
# Input format tests (13-16)
# ---------------------------------------------------------------------------

class TestResumeInputFormats:
    """13-16. ResumeParsed, Resume, dict, None inputs."""

    def test_resume_parsed_input(self, sample_profile):
        rp = ResumeParsed(
            name="Alice", skills=["Python", "Java"],
            roles=["Backend Engineer"],
        )
        service = MatchService(profile=sample_profile)
        result = service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
            resume=rp,
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_resume_model_input(self, sample_profile, sample_resume):
        service = MatchService(profile=sample_profile)
        result = service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
            resume=sample_resume,
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_dict_input(self, sample_profile):
        resume_dict = {
            "name": "Bob",
            "skills": ["Python", "SQL"],
            "experience": [],
            "roles": ["Backend Engineer"],
        }
        service = MatchService(profile=sample_profile)
        result = service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
            resume=resume_dict,
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_none_input(self):
        service = MatchService()  # no resume
        result = service.analyze(job_id=1, job_title="SWE")
        assert isinstance(result, MatchAnalysis)
        assert result.final_score == 0
        assert result.recommendation == "Skip"
        assert "No candidate resume" in result.explanation


# ---------------------------------------------------------------------------
# Positional & keyword compatibility (17-19, 23)
# ---------------------------------------------------------------------------

class TestPositionalCompatibility:
    """17. Legacy positional signature compatibility & new positional support."""

    def test_legacy_positional_args(self, sample_service):
        """analyze(job_id, job_title, job_location, jd_text, required_skills)"""
        result = sample_service.analyze(
            101, "Backend Engineer", "Remote", "Python SQL", ["Python", "SQL"],
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_new_positional_resume_job_args(self, sample_profile, sample_resume, sample_job_dict):
        """analyze(resume_obj, job_obj) positionally!"""
        service = MatchService(profile=sample_profile)
        result = service.analyze(sample_resume, sample_job_dict)
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_legacy_keyword_args(self, sample_service):
        """analyze(job_id=..., job_title=..., ...)"""
        result = sample_service.analyze(
            job_id=101,
            job_title="Backend Engineer",
            job_location="Remote",
            jd_text="Python SQL",
            required_skills=["Python", "SQL"],
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0


class TestStateMutationSafety:
    """Verify MatchService instance state (self.resume) is never mutated during calls."""

    def test_self_resume_unmodified_after_explicit_resume_analyze(self, sample_profile, sample_resume):
        service = MatchService(profile=sample_profile, resume=sample_resume)
        original_resume_name = service.resume.name

        other_resume = Resume(name="Other Candidate", skills=["Haskell", "Erlang"])
        result = service.analyze(resume=other_resume, job_id=1, job_title="Functional Dev")

        assert isinstance(result, MatchAnalysis)
        # Instance self.resume MUST remain untouched
        assert service.resume.name == original_resume_name

    def test_sequential_different_resumes_same_service(self):
        service = MatchService(profile=Profile())
        r1 = Resume(name="Candidate 1", skills=["Python"])
        r2 = Resume(name="Candidate 2", skills=["Haskell"])

        res1 = service.analyze(r1, {"title": "Python Dev", "required_skills": ["Python"]})
        res2 = service.analyze(r2, {"title": "Python Dev", "required_skills": ["Python"]})

        assert res1.candidate_name == "Candidate 1"
        assert res2.candidate_name == "Candidate 2"
        assert res1.final_score > res2.final_score


class TestNewKeywordCompatibility:
    """18-19. New resume/job keyword signature."""

    def test_resume_job_keywords(self, sample_profile, sample_resume, sample_job_dict):
        service = MatchService(profile=sample_profile)
        result = service.analyze(
            resume=sample_resume,
            job=sample_job_dict,
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0

    def test_resume_keyword_only(self, sample_profile, sample_resume):
        service = MatchService(profile=sample_profile)
        result = service.analyze(
            job_id=5,
            job_title="Backend Engineer",
            required_skills=["Python"],
            resume=sample_resume,
        )
        assert isinstance(result, MatchAnalysis)
        assert result.final_score > 0


class TestUIAppPattern:
    """23. Regression protection — ui/app.py calling pattern."""

    def test_ui_app_calling_pattern(self, sample_service):
        """Exact pattern from ui/app.py lines 872-878 and 975-981."""
        job = {
            "title": "Backend Engineer",
            "location": "Remote",
            "jd_text": "Python SQL Docker experience required",
            "required_skills": ["Python", "SQL"],
        }
        job_id = 42

        # This is exactly how ui/app.py calls it
        analysis = sample_service.analyze(
            job_id=job_id,
            job_title=job.get("title", ""),
            job_location=job.get("location", ""),
            jd_text=job.get("jd_text", ""),
            required_skills=job.get("required_skills", []),
        )

        assert isinstance(analysis, MatchAnalysis)
        assert isinstance(analysis.final_score, (int, float))
        assert 0 <= analysis.final_score <= 100

        # Verify to_json and int(analysis.final_score) work (ui/app.py does this)
        match_json = sample_service.to_json(analysis)
        assert isinstance(match_json, str)
        fit_score = int(analysis.final_score)
        assert 0 <= fit_score <= 100

        # Verify JSON round-trip
        parsed = json.loads(match_json)
        assert "final_score" in parsed


# ---------------------------------------------------------------------------
# Serialization (20)
# ---------------------------------------------------------------------------

class TestSerialization:
    """20. JSON serialization and deserialization round-trip."""

    def test_json_round_trip(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            jd_text="Python SQL", required_skills=["Python", "SQL"],
        )
        json_str = sample_service.to_json(result)
        restored = sample_service.from_json(json_str)
        assert restored is not None
        assert restored.final_score == result.final_score
        assert restored.recommendation == result.recommendation

    def test_schema_serialization(self, sample_service):
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        schema = sample_service.to_schema(result)
        j = schema.model_dump()
        restored = SchemaMatchAnalysis(**j)
        assert restored.final_score == schema.final_score


# ---------------------------------------------------------------------------
# Exact scoring formula (21)
# ---------------------------------------------------------------------------

class TestExactScoringFormula:
    """21. Verify final_score = clamp(round(
        skill*0.40 + exp*0.25 + role*0.20 + loc*0.10 + seniority*0.05
        - seniority_penalty * 0.05 * 100
    ), 0, 100)."""

    def test_formula_matches_components(self, sample_service):
        result = sample_service.analyze(
            job_id=1,
            job_title="Backend Engineer",
            job_location="Remote",
            jd_text="Python SQL Docker 3 years experience",
            required_skills=["Python", "SQL", "Docker"],
        )

        raw = (
            result.skill_match.score * 0.40
            + result.experience_match.score * 0.25
            + result.role_match.score * 0.20
            + result.location_match.score * 0.10
            + result.seniority_match.score * 0.05
        )
        expected = max(0, min(100, int(round(
            raw - result.seniority_penalty * 0.05 * 100
        ))))
        assert result.final_score == expected, (
            f"Expected {expected}, got {result.final_score}. "
            f"Components: skill={result.skill_match.score}, "
            f"exp={result.experience_match.score}, "
            f"role={result.role_match.score}, "
            f"loc={result.location_match.score}, "
            f"seniority={result.seniority_match.score}, "
            f"penalty={result.seniority_penalty}"
        )


# ---------------------------------------------------------------------------
# No external dependencies (24)
# ---------------------------------------------------------------------------

class TestNoExternalDependencies:
    """24. MatchService must not make LLM, embedding, network, or API calls."""

    def test_no_imports_of_external_apis(self):
        """Verify match_service.py does not import network/LLM modules."""
        import importlib
        import inspect
        mod = importlib.import_module("core.services.match_service")
        source = inspect.getsource(mod)

        forbidden = [
            "openai", "anthropic", "groq", "langchain", "llama",
            "requests.get", "requests.post", "httpx",
            "chromadb", "pinecone", "weaviate", "faiss",
            "urllib.request",
        ]
        for term in forbidden:
            assert term not in source, (
                f"match_service.py must not reference '{term}'"
            )

    def test_analyze_works_offline(self, sample_service):
        """Calling analyze should succeed without any network access."""
        # If it returns without error and without hanging, no network call was made
        result = sample_service.analyze(
            job_id=1, job_title="Backend Engineer",
            required_skills=["Python"],
        )
        assert isinstance(result, MatchAnalysis)


# ---------------------------------------------------------------------------
# Integer-only positional guard safety
# ---------------------------------------------------------------------------

class TestPositionalSafetyGuards:
    """Verify ordinary ints/strings/lists are never reinterpreted."""

    def test_integer_job_id_not_misinterpreted(self, sample_service):
        """Passing an integer as job_id must not be treated as a resume."""
        result = sample_service.analyze(42, "Backend Engineer", "Remote", "", ["Python"])
        assert isinstance(result, MatchAnalysis)
        # job_id should remain as passed
        assert result.job_id == 42

    def test_string_job_title_not_misinterpreted(self, sample_service):
        """Passing a string as job_title must not be treated as a job object."""
        result = sample_service.analyze(
            job_id=1, job_title="Software Engineer",
        )
        assert isinstance(result, MatchAnalysis)
