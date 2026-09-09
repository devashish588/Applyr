"""Phase 16 Opportunity Intelligence foundation — UNKNOWN contract, no fake data."""
import json
import os
from pathlib import Path
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def _test_url():
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        prod = os.getenv("DATABASE_URL", "")
        if "/neondb?" in prod:
            return prod.replace("/neondb?", "/applyr_test?")
        return prod.replace("/neondb", "/applyr_test") if "/neondb" in prod else prod
    return url


def _get_conn():
    return psycopg2.connect(_test_url())


def _ensure(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            cur.execute(Path("db/migrations/012_opportunity_intelligence.sql").read_text())
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY, title TEXT, company TEXT, url TEXT UNIQUE,
                    source TEXT, location TEXT, jd_text TEXT, scraped_at TEXT
                )
            """)
        conn.commit()
    finally:
        if close:
            conn.close()


def _clean(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM job_opportunity_intelligence WHERE job_id IN (SELECT id FROM jobs WHERE url LIKE 'https://opp-test%')")
            except Exception:
                pass
            try:
                cur.execute("DELETE FROM jobs WHERE url LIKE 'https://opp-test%'")
            except Exception:
                pass
        conn.commit()
    finally:
        if close:
            conn.close()


@pytest.fixture(scope="module")
def mod_conn():
    c = psycopg2.connect(_test_url())
    _ensure(c)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def clean(mod_conn):
    _clean(mod_conn)
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    yield
    _clean(mod_conn)


def _make_job(mod_conn, suffix="1"):
    import uuid
    url = f"https://opp-test.example.com/{suffix}-{uuid.uuid4().hex[:6]}"
    with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            ("Engineer", "Acme", url, "Remote", "Python required", "2026-01-01T00:00:00Z"),
        )
        jid = cur.fetchone()["id"]
    mod_conn.commit()
    return jid


# Model
def test_model_empty_unknown():
    from core.models.opportunity_intelligence import OpportunityIntelligence
    o = OpportunityIntelligence()
    assert o.competition_intensity.level.value == "UNKNOWN"
    assert o.determination_status.value == "UNDETERMINED"
    assert o.confidence is None
    assert o.evidence == []


def test_model_enum_validation():
    from core.models.opportunity_intelligence import OpportunitySignal, OpportunitySignalLevel
    import pytest as _pt
    with _pt.raises(Exception):
        OpportunitySignal(level="EXTREME")  # type: ignore


def test_model_serialization():
    from core.models.opportunity_intelligence import OpportunityIntelligence
    o = OpportunityIntelligence(job_id=5)
    d = o.to_response()
    assert d["job_id"] == 5
    assert d["competition_intensity"]["level"] == "UNKNOWN"
    assert "evidence" in d["competition_intensity"]


# UNKNOWN semantics
def test_unknown_not_low():
    from core.models.opportunity_intelligence import OpportunitySignalLevel
    assert OpportunitySignalLevel.UNKNOWN.value != OpportunitySignalLevel.LOW.value


def test_undetermined_not_determined():
    from core.models.opportunity_intelligence import OpportunityDeterminationStatus
    assert OpportunityDeterminationStatus.UNDETERMINED.value != OpportunityDeterminationStatus.DETERMINED.value


def test_null_confidence():
    from core.services.opportunity_intelligence_service import build_foundation
    o = build_foundation(job_id=1)
    assert o.confidence is None
    assert o.competition_intensity.confidence is None


# Service
def test_service_empty_foundation():
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    svc = get_opportunity_intelligence_service()
    o = svc.build_for_job({"id": 9, "title": "Engineer"})
    assert o.job_id == 9
    assert o.competition_intensity.level.value == "UNKNOWN"
    assert o.evidence == []


def test_service_deterministic():
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    svc = get_opportunity_intelligence_service()
    a = svc.build_for_job({"id": 3}).to_response()
    b = svc.build_for_job({"id": 3}).to_response()
    a.pop("computed_at", None)
    b.pop("computed_at", None)
    assert a == b


def test_service_stable_repeated():
    from core.services.opportunity_intelligence_service import build_foundation
    assert build_foundation(7).to_response()["determination_status"] == "UNDETERMINED"


# API
def test_api_existing_job(mod_conn):
    from ui.app import app
    jid = _make_job(mod_conn, "api1")
    with app.test_client() as c:
        r = c.get(f"/api/jobs/{jid}/opportunity-intelligence")
        assert r.status_code == 200
        j = r.get_json()["opportunity_intelligence"]
        # Phase 19: competition is computed (valid level), background stays UNKNOWN (no domain)
        assert j["competition_intensity"]["level"] in ("LOW", "MODERATE", "HIGH", "UNKNOWN")
        assert j["background_fit_sensitivity"]["level"] == "UNKNOWN"
        assert j["confidence"] is None


def test_api_nonexistent_job():
    from ui.app import app
    with app.test_client() as c:
        r = c.get("/api/jobs/999999999/opportunity-intelligence")
        assert r.status_code == 404
        assert "Job not found" in r.get_data(as_text=True)


def test_api_no_leakage(mod_conn):
    from ui.app import app
    jid = _make_job(mod_conn, "api2")
    with app.test_client() as c:
        r = c.get(f"/api/jobs/{jid}/opportunity-intelligence")
        txt = r.get_data(as_text=True)
        assert "Traceback" not in txt
        assert "DATABASE_URL" not in txt
        assert "npg_" not in txt


# Persistence
def test_persistence_create_read(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "p1")
    svc = get_opportunity_intelligence_service()
    saved = svc.save_for_job(jid)
    assert saved.job_id == jid
    loaded = svc.get_for_job(jid)
    assert loaded is not None and loaded.job_id == jid


def test_persistence_update(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "p2")
    svc = get_opportunity_intelligence_service()
    svc.save_for_job(jid)
    svc.save_for_job(jid)  # idempotent update, no duplicate
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM job_opportunity_intelligence WHERE job_id=%s", (jid,))
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()


def test_persistence_existing_jobs_valid(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "p3")
    # No intelligence row yet: lazy foundation still valid, no error
    assert get_opportunity_intelligence_service().get_for_job(jid) is not None


def test_migration_additive(mod_conn):
    with mod_conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='job_opportunity_intelligence'")
        cols = {r[0] for r in cur.fetchall()}
        assert {"job_id", "competition_intensity", "determination_status"} <= cols


# Regression (no behavior change)
def test_match_unchanged():
    from core.services.match_service import MatchService
    assert (MatchService.SKILL_WEIGHT, MatchService.EXPERIENCE_WEIGHT, MatchService.ROLE_WEIGHT, MatchService.LOCATION_WEIGHT, MatchService.SENIORITY_WEIGHT) == (0.40, 0.25, 0.20, 0.10, 0.05)


def test_priority_unchanged():
    import inspect
    from core.services import application_priority_service as aps
    src = inspect.getsource(aps)
    assert "Opportunity" not in src


def test_job_intelligence_unchanged():
    import inspect
    from core.services import job_intelligence_service as jis
    assert "Opportunity" not in inspect.getsource(jis)


def test_job_quality_unchanged():
    import inspect
    from core.services import job_quality_service as jqs
    assert "Opportunity" not in inspect.getsource(jqs)


def test_canonical_unchanged():
    from core.services.job_canonical_service import compute_canonical_id
    assert compute_canonical_id("A", "B", "C", "https://a.com/1") != compute_canonical_id("A", "B", "C", "https://b.com/2")


def test_master_resume_unchanged():
    import inspect
    from core.services import master_resume_service as mrs
    assert "Opportunity" not in inspect.getsource(mrs)


def test_studio_unchanged():
    import inspect
    from core.services import studio_service as st
    assert "Opportunity" not in inspect.getsource(st)


def test_lifecycle_unchanged():
    from core.services.application_service import ALLOWED_STATES
    assert {"PREPARING", "APPLIED", "CLOSED"} <= set(ALLOWED_STATES)


def test_golden_foundation():
    data = json.loads((Path(__file__).parent / "data" / "opportunity_intelligence" / "foundation_unknown.json").read_text())
    from core.services.opportunity_intelligence_service import build_foundation
    for case in data["cases"]:
        o = build_foundation(job_id=case["input"].get("job_id")).to_response()
        for k, v in case["expected"].items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    assert o[k][sk] == sv, f"{case['name']}:{k}.{sk}"
            else:
                assert o[k] == v, f"{case['name']}:{k}"


# ── Phase 17: Shortlisting Strictness ──────────────────────────────────────

def _evaluate(job_dict):
    from core.services.job_intelligence_service import get_job_intelligence_service
    from core.services.opportunity_intelligence_service import evaluate_shortlisting_strictness
    profile = get_job_intelligence_service().build_job_intelligence(job_dict)
    return evaluate_shortlisting_strictness(profile), profile


def _golden(name):
    return json.loads((Path(__file__).parent / "data" / "opportunity_intelligence" / name).read_text())


def test_shortlisting_low():
    g = _golden("shortlisting_low.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value == g["expected"]["level"]
    assert sig.status.value == g["expected"]["status"]


def test_shortlisting_moderate():
    g = _golden("shortlisting_moderate.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value == g["expected"]["level"]
    assert sig.status.value == g["expected"]["status"]


def test_shortlisting_high():
    g = _golden("shortlisting_high.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value == g["expected"]["level"]
    assert sig.status.value == "DETERMINED"
    assert len(sig.evidence) >= 3


def test_shortlisting_unknown():
    g = _golden("shortlisting_unknown.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value == "UNKNOWN"
    assert sig.status.value == "UNDETERMINED"
    assert sig.evidence == []
    assert sig.confidence is None


def test_shortlisting_determined_vs_undetermined():
    g = _golden("shortlisting_high.json")
    sig, _ = _evaluate(g["input"])
    assert sig.status.value == "DETERMINED"
    g2 = _golden("shortlisting_unknown.json")
    sig2, _ = _evaluate(g2["input"])
    assert sig2.status.value == "UNDETERMINED"


def test_shortlisting_evidence_generation():
    g = _golden("shortlisting_high.json")
    sig, _ = _evaluate(g["input"])
    assert len(sig.evidence) >= 3
    for e in sig.evidence:
        assert e.signal == "SHORTLISTING_STRICTNESS"
        assert e.reason and e.source


def test_shortlisting_evidence_source():
    g = _golden("shortlisting_moderate.json")
    sig, _ = _evaluate(g["input"])
    sources = {e.source for e in sig.evidence}
    assert sources <= {"REQUIREMENT", "EXPERIENCE_REQUIREMENT", "LOCATION_REQUIREMENT", "CERTIFICATION_REQUIREMENT", "DOMAIN_REQUIREMENT", "JOB_INTELLIGENCE"}
    assert "REQUIREMENT" in sources or "EXPERIENCE_REQUIREMENT" in sources


def test_shortlisting_required_vs_preferred():
    g = _golden("shortlisting_required_vs_preferred.json")
    sig, profile = _evaluate(g["input"])
    assert len(profile.required_skills) == 2  # only Python + SQL mandatory
    assert sig.level.value == g["expected"]["level"]  # LOW, preferred excluded


def test_shortlisting_narrow_range():
    g = _golden("shortlisting_experience_range.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value == "MODERATE"
    assert any("narrow" in e.reason for e in sig.evidence)


def test_shortlisting_certification_required():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- SQL\n- AWS Certified Solutions Architect required",
        "url": "https://example.com/cert",
    }
    sig, _ = _evaluate(job)
    assert any(e.source == "CERTIFICATION_REQUIREMENT" for e in sig.evidence)


def test_shortlisting_certification_preferred_ignored():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- SQL\nPreferred:\n- AWS Certified Solutions Architect preferred",
        "url": "https://example.com/cert-pref",
    }
    sig, _ = _evaluate(job)
    assert not any(e.source == "CERTIFICATION_REQUIREMENT" for e in sig.evidence)
    assert sig.level.value in ("LOW", "MODERATE")  # never HIGH from preferred cert alone


def test_shortlisting_education_required():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- SQL\n- Bachelor's degree required",
        "url": "https://example.com/edu",
    }
    sig, _ = _evaluate(job)
    assert sig.level.value in ("LOW", "MODERATE")


def test_shortlisting_domain_required():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- SQL\n- Finance domain experience required",
        "url": "https://example.com/domain",
    }
    sig, _ = _evaluate(job)
    assert any(e.source == "DOMAIN_REQUIREMENT" for e in sig.evidence)


def test_shortlisting_location_onsite():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- Python\n- SQL",
        "url": "https://example.com/onsite",
    }
    sig, _ = _evaluate(job)
    assert any(e.source == "LOCATION_REQUIREMENT" for e in sig.evidence)


def test_shortlisting_location_remote_not_strict():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "We are a remote team.\nRequirements:\n- Python\n- SQL",
        "url": "https://example.com/remote",
    }
    sig, _ = _evaluate(job)
    assert not any(e.source == "LOCATION_REQUIREMENT" for e in sig.evidence)


def test_shortlisting_seniority_alone_not_high():
    job = {
        "title": "Senior Software Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "We need a senior engineer.\nRequirements:\n- Python",
        "url": "https://example.com/senior",
    }
    sig, _ = _evaluate(job)
    assert sig.level.value in ("LOW", "MODERATE")  # title prestige alone never HIGH


def test_shortlisting_sparse_unknown():
    sig, _ = _evaluate({"title": "Engineer", "company": "Acme", "location": "", "jd_text": "", "url": "https://example.com/empty"})
    assert sig.level.value == "UNKNOWN"


def test_shortlisting_parser_unavailable():
    from core.services.opportunity_intelligence_service import evaluate_shortlisting_strictness
    assert evaluate_shortlisting_strictness(None).level.value == "UNKNOWN"


def test_shortlisting_deterministic():
    job = _golden("shortlisting_high.json")["input"]
    a, _ = _evaluate(dict(job))
    b, _ = _evaluate(dict(job))
    assert a.level == b.level and [e.reason for e in a.evidence] == [e.reason for e in b.evidence]


def test_shortlisting_no_mutation():
    import copy
    job = _golden("shortlisting_high.json")["input"]
    snapshot = copy.deepcopy(job)
    _evaluate(job)
    assert job == snapshot


def test_shortlisting_competition_background_remain_unknown(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "sig-unchanged")
    o = get_opportunity_intelligence_service().build_for_job({"id": jid, "title": "E", "company": "Acme", "location": "Remote", "jd_text": "Requirements:\n- Python\n- SQL", "url": "https://example.com/x"})
    assert o.competition_intensity.level.value == "UNKNOWN"
    assert o.background_fit_sensitivity.level.value == "UNKNOWN"


# False positives: must NOT become HIGH
def test_fp_many_preferred_not_high():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\nPreferred:\n- Docker\n- Kubernetes\n- AWS\n- Terraform\n- GCP\n- Azure\n- Helm\n- Istio\n- Vault",
        "url": "https://example.com/fp-pref",
    }
    sig, _ = _evaluate(job)
    assert sig.level.value != "HIGH"


def test_fp_verbose_not_high():
    job = {
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "About us: " + ("great place to work. " * 60) + "\nResponsibilities:\n" + "".join(f"- Do thing {i}\n" for i in range(20)) + "Requirements:\n- Python\n- Communication",
        "url": "https://example.com/fp-verbose",
    }
    sig, _ = _evaluate(job)
    assert sig.level.value != "HIGH"


def test_fp_senior_title_not_high():
    sig, _ = _evaluate({"title": "Principal Engineer", "company": "BigCo", "location": "Remote", "jd_text": "Join BigCo as a principal engineer.\nRequirements:\n- Python", "url": "https://example.com/fp-title"})
    assert sig.level.value != "HIGH"


def test_fp_remote_not_high():
    sig, _ = _evaluate({"title": "Engineer", "company": "Acme", "location": "Remote", "jd_text": "Fully remote role.\nRequirements:\n- Python", "url": "https://example.com/fp-remote"})
    assert sig.level.value != "HIGH"


def test_fp_missing_not_low():
    sig, _ = _evaluate({"title": "", "company": "", "location": "", "jd_text": "", "url": ""})
    assert sig.level.value == "UNKNOWN"  # never LOW from missing


def test_fp_unknown_state_not_low():
    from core.services.opportunity_intelligence_service import evaluate_shortlisting_strictness
    assert evaluate_shortlisting_strictness(None).level.value != "LOW"


# False negatives: obvious strict must not be LOW
def test_fn_obvious_strict_not_low():
    g = _golden("shortlisting_high.json")
    sig, _ = _evaluate(g["input"])
    assert sig.level.value != "LOW"
    assert sig.level.value == "HIGH"


def test_api_shortlisting_determined(mod_conn):
    from ui.app import app
    jid = _make_job(mod_conn, "api-det")
    # Give it a moderate JD via update
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET jd_text=%s WHERE id=%s", (
            "Requirements:\n- 3+ years Python experience\n- Python\n- SQL\n- Docker", jid))
    mod_conn.commit()
    with app.test_client() as c:
        r = c.get(f"/api/jobs/{jid}/opportunity-intelligence")
        assert r.status_code == 200
        j = r.get_json()["opportunity_intelligence"]
        assert j["shortlisting_strictness"]["level"] in ("LOW", "MODERATE", "HIGH")
        assert j["competition_intensity"]["level"] == "UNKNOWN"
        assert j["background_fit_sensitivity"]["level"] == "UNKNOWN"


def _evaluate_bg(job_dict):
    from core.services.job_intelligence_service import get_job_intelligence_service
    from core.services.opportunity_intelligence_service import evaluate_background_fit_sensitivity
    profile = get_job_intelligence_service().build_job_intelligence(job_dict)
    return evaluate_background_fit_sensitivity(profile), profile


def _bg_golden(name):
    return json.loads((Path(__file__).parent / "data" / "opportunity_intelligence" / name).read_text())


# ── Phase 18: Background Fit Sensitivity ───────────────────────────────────

def test_background_low_generic():
    g = _bg_golden("background_low.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "LOW"
    assert sig.status.value == "DETERMINED"


def test_background_low_transferable_tech():
    g = _bg_golden("background_low_tech.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "LOW"  # PyTorch/K8s/AWS never imply domain need


def test_background_high_banking():
    g = _bg_golden("background_high_banking.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "HIGH"
    assert sig.status.value == "DETERMINED"
    assert len(sig.evidence) >= 1


def test_background_high_platform():
    g = _bg_golden("background_high_platform.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "HIGH"


def test_background_high_healthcare():
    g = _bg_golden("background_high_healthcare.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "HIGH"


def test_background_moderate_preferred():
    g = _bg_golden("background_moderate_preferred.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "MODERATE"  # preferred alone never HIGH


def test_background_low_company_industry():
    g = _bg_golden("background_low_company.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "LOW"  # fintech employer alone means nothing


def test_background_low_seniority():
    g = _bg_golden("background_low_seniority.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "LOW"


def test_background_unknown_sparse():
    g = _bg_golden("background_unknown_sparse.json")
    sig, _ = _evaluate_bg(g["input"])
    assert sig.level.value == "UNKNOWN"
    assert sig.status.value == "UNDETERMINED"
    assert sig.evidence == []


def test_background_unknown_no_profile():
    from core.services.opportunity_intelligence_service import evaluate_background_fit_sensitivity
    sig = evaluate_background_fit_sensitivity(None)
    assert sig.level.value == "UNKNOWN"


def test_background_required_vs_preferred():
    req, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- 3 years banking domain experience required",
        "url": "https://example.com/bg-req",
    })
    pref, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\nPreferred qualifications:\n- Banking experience preferred",
        "url": "https://example.com/bg-pref",
    })
    assert req.level.value == "HIGH"
    assert pref.level.value != "HIGH"


def test_background_tech_vs_domain():
    tech, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- AWS\n- Kubernetes",
        "url": "https://example.com/bg-tech",
    })
    domain, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- Banking payments domain experience required",
        "url": "https://example.com/bg-domain",
    })
    assert tech.level.value == "LOW"
    assert domain.level.value == "HIGH"


def test_background_cert_alone_not_high():
    sig, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- AWS Certified Solutions Architect required",
        "url": "https://example.com/bg-cert",
    })
    assert sig.level.value != "HIGH"


def test_background_jira_not_high():
    sig, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- Experience with Jira required",
        "url": "https://example.com/bg-jira",
    })
    assert sig.level.value != "HIGH"


def test_background_experience_alone_not_high():
    sig, _ = _evaluate_bg({
        "title": "Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- 5 years Python experience required",
        "url": "https://example.com/bg-exp",
    })
    assert sig.level.value != "HIGH"  # years alone are shortlisting, not background


def test_background_deterministic():
    job = _bg_golden("background_high_banking.json")["input"]
    a, _ = _evaluate_bg(dict(job))
    b, _ = _evaluate_bg(dict(job))
    assert a.level == b.level and [e.reason for e in a.evidence] == [e.reason for e in b.evidence]


def test_background_no_mutation():
    import copy
    job = _bg_golden("background_high_banking.json")["input"]
    snapshot = copy.deepcopy(job)
    _evaluate_bg(job)
    assert job == snapshot


def test_background_evidence_model():
    g = _bg_golden("background_high_healthcare.json")
    sig, _ = _evaluate_bg(g["input"])
    assert len(sig.evidence) >= 1
    for e in sig.evidence:
        assert e.signal == "BACKGROUND_FIT_SENSITIVITY"
        assert e.reason and e.source == "DOMAIN_REQUIREMENT"


# False positives: never HIGH
def test_bg_fp_company_industry():
    sig, _ = _evaluate_bg({"title": "Frontend Engineer", "company": "BigBank", "location": "Remote",
                           "jd_text": "Join BigBank.\nRequirements:\n- React\n- TypeScript", "url": "https://example.com/fp-bank"})
    assert sig.level.value != "HIGH"


def test_bg_fp_role_title():
    sig, _ = _evaluate_bg({"title": "Data Scientist", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- Python\n- SQL", "url": "https://example.com/fp-title"})
    assert sig.level.value != "HIGH"


def test_bg_fp_cloud_stack():
    sig, _ = _evaluate_bg({"title": "Engineer", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- AWS\n- Terraform\n- Kafka", "url": "https://example.com/fp-cloud"})
    assert sig.level.value != "HIGH"


def test_bg_fp_generic_vocab():
    sig, _ = _evaluate_bg({"title": "Engineer", "company": "Acme", "location": "Remote",
                           "jd_text": "We are a fast-paced agile team seeking a rockstar.\nRequirements:\n- Python", "url": "https://example.com/fp-vocab"})
    assert sig.level.value != "HIGH"


# False negatives: obvious domain roles never LOW
def test_bg_fn_banking():
    sig, _ = _evaluate_bg({"title": "Engineer", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- Python\n- Mandatory banking domain experience required", "url": "https://example.com/fn-bank"})
    assert sig.level.value == "HIGH"


def test_bg_fn_healthcare():
    sig, _ = _evaluate_bg({"title": "Engineer", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- Python\n- HIPAA healthcare workflow experience required", "url": "https://example.com/fn-health"})
    assert sig.level.value == "HIGH"


def test_bg_fn_sap():
    sig, _ = _evaluate_bg({"title": "Consultant", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- SAP S/4HANA implementation experience required", "url": "https://example.com/fn-sap"})
    assert sig.level.value == "HIGH"


def test_bg_fn_credit_risk():
    sig, _ = _evaluate_bg({"title": "ML Engineer", "company": "Acme", "location": "Remote",
                           "jd_text": "Requirements:\n- Python\n- Prior credit-risk modelling experience required", "url": "https://example.com/fn-cr"})
    assert sig.level.value == "HIGH"


def test_api_background_determined(mod_conn):
    from ui.app import app
    jid = _make_job(mod_conn, "api-bg")
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET jd_text=%s WHERE id=%s", (
            "Requirements:\n- Python\n- Healthcare claims processing experience required", jid))
    mod_conn.commit()
    with app.test_client() as c:
        r = c.get(f"/api/jobs/{jid}/opportunity-intelligence")
        assert r.status_code == 200
        j = r.get_json()["opportunity_intelligence"]
        assert j["background_fit_sensitivity"]["level"] == "HIGH"
        assert j["background_fit_sensitivity"]["status"] == "DETERMINED"
        assert j["competition_intensity"]["level"] == "UNKNOWN"


def test_persistence_background_preserves_shortlisting(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "persist-bg")
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET jd_text=%s WHERE id=%s", (
            "Requirements:\n- 5-8 years experience\n- Python\n- SQL\n- AWS\n- Docker\n- Kubernetes\n- TensorFlow\n- Finance domain experience required", jid))
    mod_conn.commit()
    svc = get_opportunity_intelligence_service()
    saved = svc.save_for_job(jid)
    assert saved.background_fit_sensitivity.level.value == "HIGH"
    assert saved.shortlisting_strictness.level.value in ("MODERATE", "HIGH")
    loaded = svc.get_for_job(jid)
    assert loaded.background_fit_sensitivity.level.value == saved.background_fit_sensitivity.level.value
    assert loaded.shortlisting_strictness.level.value == saved.shortlisting_strictness.level.value
    assert loaded.competition_intensity.level.value == "UNKNOWN"


def test_shortlisting_regression_after_phase18():
    # Phase 17 goldens must produce identical results after Phase 18 changes
    for name, level in [("shortlisting_low.json", "LOW"), ("shortlisting_moderate.json", "MODERATE"),
                        ("shortlisting_high.json", "HIGH"), ("shortlisting_unknown.json", "UNKNOWN")]:
        g = json.loads((Path(__file__).parent / "data" / "opportunity_intelligence" / name).read_text())
        from core.services.job_intelligence_service import get_job_intelligence_service
        from core.services.opportunity_intelligence_service import evaluate_shortlisting_strictness
        profile = get_job_intelligence_service().build_job_intelligence(g["input"])
        assert evaluate_shortlisting_strictness(profile).level.value == level, name


def _evaluate_comp(job_dict):
    from core.services.job_intelligence_service import get_job_intelligence_service
    from core.services.opportunity_intelligence_service import evaluate_competition_intensity
    profile = get_job_intelligence_service().build_job_intelligence(job_dict)
    return evaluate_competition_intensity(profile), profile


def _comp_golden(name):
    return json.loads((Path(__file__).parent / "data" / "opportunity_intelligence" / name).read_text())


# ── Phase 19: Competition Intensity ────────────────────────────────────────

def test_competition_low():
    g = _comp_golden("competition_low.json")
    sig, _ = _evaluate_comp(g["input"])
    assert sig.level.value == "LOW"
    assert sig.status.value == "DETERMINED"


def test_competition_moderate():
    g = _comp_golden("competition_moderate.json")
    sig, _ = _evaluate_comp(g["input"])
    assert sig.level.value == "MODERATE"
    assert sig.status.value == "DETERMINED"


def test_competition_high():
    g = _comp_golden("competition_high.json")
    sig, _ = _evaluate_comp(g["input"])
    assert sig.level.value == "HIGH"
    assert sig.status.value == "DETERMINED"
    assert len(sig.evidence) >= 2


def test_competition_unknown():
    g = _comp_golden("competition_unknown.json")
    sig, _ = _evaluate_comp(g["input"])
    assert sig.level.value == "UNKNOWN"
    assert sig.status.value == "UNDETERMINED"
    assert sig.evidence == []
    assert sig.confidence is None


def test_competition_no_applicant_fields():
    import inspect
    from core.services import opportunity_intelligence_service as ois
    src = inspect.getsource(ois)
    for banned in ("applicant_count", "applications_count", "views_count", "likes_count", "saves_count", "competition_percent", "recruiter_views"):
        assert banned not in src


def test_competition_no_candidate_match_priority_inputs():
    import inspect
    from core.services.opportunity_intelligence_service import evaluate_competition_intensity
    params = set(inspect.signature(evaluate_competition_intensity).parameters)
    assert params == {"job_profile"}
    import core.services.opportunity_intelligence_service as ois
    src = inspect.getsource(ois.evaluate_competition_intensity)
    assert "CandidateAdapter" not in src and "MatchResult" not in src and "match_service" not in src


def test_competition_remote_alone_not_high():
    sig, _ = _evaluate_comp({
        "title": "Staff Security Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- 5-8 years experience\n- CISSP\n- Penetration Testing",
        "url": "https://example.com/c-remote",
    })
    assert sig.level.value != "HIGH"


def test_competition_title_alone_not_high():
    sig, _ = _evaluate_comp({
        "title": "Backend Engineer", "company": "Acme", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- Python",
        "url": "https://example.com/c-title",
    })
    assert sig.level.value != "HIGH"


def test_competition_company_alone_not_high():
    sig, _ = _evaluate_comp({
        "title": "Staff Research Scientist", "company": "Google", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- 8+ years experience\n- C++\n- Distributed Systems",
        "url": "https://example.com/c-company",
    })
    assert sig.level.value != "HIGH"  # brand prestige never counts


def test_competition_freshness_alone_not_high():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    sig, _ = _evaluate_comp({
        "title": "Staff Mainframe Engineer", "company": "Acme", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- 8+ years experience\n- COBOL\n- Mainframe",
        "url": "https://example.com/c-fresh", "scraped_at": now,
    })
    assert sig.level.value != "HIGH"


def test_competition_seniority_alone_not_high():
    sig, _ = _evaluate_comp({
        "title": "Principal Engineer", "company": "Acme", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- Python",
        "url": "https://example.com/c-senior",
    })
    assert sig.level.value != "HIGH"


def test_competition_source_count_not_used():
    # Attributions/distribution must not feed the evaluator: input contract has no such fields
    import inspect
    from core.services.opportunity_intelligence_service import evaluate_competition_intensity
    src = inspect.getsource(evaluate_competition_intensity)
    assert "attribution" not in src.lower()
    sig, _ = _evaluate_comp({
        "title": "Backend Engineer", "company": "Acme", "location": "Bangalore",
        "jd_text": "Must be onsite in Bangalore.\nRequirements:\n- 5+ years experience\n- Python",
        "url": "https://example.com/c-src",
    })
    assert sig.level.value != "HIGH"


def test_competition_specialized_not_auto_low():
    sig, _ = _evaluate_comp({
        "title": "Staff Security Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- CISSP\n- Penetration Testing",
        "url": "https://example.com/c-spec",
    })
    # Remote reach + determinable metadata: must not collapse to LOW automatically,
    # and must never claim HIGH from a single axis
    assert sig.level.value in ("MODERATE", "LOW", "UNKNOWN")
    assert sig.level.value != "HIGH"


def test_competition_fn_broad_pool_high():
    sig, _ = _evaluate_comp({
        "title": "Backend Engineer", "company": "Acme", "location": "Remote",
        "jd_text": "Requirements:\n- Python\n- SQL\n- JavaScript",
        "url": "https://example.com/c-fn",
    })
    assert sig.level.value == "HIGH"


def test_competition_candidate_independence():
    job = _comp_golden("competition_high.json")["input"]
    a, _ = _evaluate_comp(dict(job))
    # Different candidate contexts must not change a job-level signal: evaluator
    # accepts only the job profile, so rebuild candidate backgrounds and re-evaluate
    from core.services.candidate_intelligence_service import get_candidate_intelligence_service
    get_candidate_intelligence_service().build_candidate_intelligence(
        {"personal": {"name": "A"}, "skills": {"languages": ["Python"]}}, {"parsed_json": {}, "skills_json": []})
    b, _ = _evaluate_comp(dict(job))
    get_candidate_intelligence_service().build_candidate_intelligence(
        {"personal": {"name": "B"}, "skills": {"languages": ["COBOL"]}}, {"parsed_json": {}, "skills_json": []})
    c, _ = _evaluate_comp(dict(job))
    assert a.level == b.level == c.level


def test_competition_match_independence():
    from core.services.match_service import get_match_service
    job = _comp_golden("competition_high.json")["input"]
    svc = get_match_service()
    svc.analyze(job_id=1, job_title=job["title"], job_location=job["location"], jd_text=job["jd_text"], required_skills=["Python"])
    before, _ = _evaluate_comp(dict(job))
    svc.analyze(job_id=1, job_title=job["title"], job_location=job["location"], jd_text=job["jd_text"], required_skills=["COBOL", "Mainframe"])
    after, _ = _evaluate_comp(dict(job))
    assert before.level == after.level


def test_competition_priority_independence():
    import inspect
    from core.services import application_priority_service as aps
    assert "Opportunity" not in inspect.getsource(aps)
    assert "Competition" not in inspect.getsource(aps)


def test_competition_deterministic():
    job = _comp_golden("competition_high.json")["input"]
    a, _ = _evaluate_comp(dict(job))
    b, _ = _evaluate_comp(dict(job))
    assert a.level == b.level and [e.reason for e in a.evidence] == [e.reason for e in b.evidence]


def test_competition_no_mutation():
    import copy
    job = _comp_golden("competition_high.json")["input"]
    snapshot = copy.deepcopy(job)
    _evaluate_comp(job)
    assert job == snapshot


def test_competition_evidence_model():
    g = _comp_golden("competition_high.json")
    sig, _ = _evaluate_comp(g["input"])
    assert len(sig.evidence) >= 2
    for e in sig.evidence:
        assert e.signal == "COMPETITION_INTENSITY"
        assert e.reason and e.source
        assert "applicant" not in e.reason.lower()


def test_api_competition_determined(mod_conn):
    from ui.app import app
    jid = _make_job(mod_conn, "api-comp")
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET location=%s, jd_text=%s WHERE id=%s",
                    ("Remote", "Requirements:\n- Python\n- SQL\n- AWS", jid))
    mod_conn.commit()
    with app.test_client() as c:
        r = c.get(f"/api/jobs/{jid}/opportunity-intelligence")
        assert r.status_code == 200
        j = r.get_json()["opportunity_intelligence"]
        assert j["competition_intensity"]["level"] in ("LOW", "MODERATE", "HIGH")
        assert j["competition_intensity"]["status"] == "DETERMINED"
        # Why? UI input: competition evidence present with reasons, same model
        assert len(j["competition_intensity"]["evidence"]) >= 1
        assert all(e["signal"] == "COMPETITION_INTENSITY" and e["reason"] for e in j["competition_intensity"]["evidence"])


def test_persistence_competition_preserves_others(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "persist-comp")
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET location=%s, jd_text=%s WHERE id=%s", (
            "Remote",
            "Requirements:\n- 5-8 years experience\n- Python\n- SQL\n- AWS\n- Docker\n- Kubernetes\n- TensorFlow\n- Finance domain experience required",
            jid))
    mod_conn.commit()
    svc = get_opportunity_intelligence_service()
    saved = svc.save_for_job(jid)
    bg_before = saved.background_fit_sensitivity.level.value
    short_before = saved.shortlisting_strictness.level.value
    assert bg_before == "HIGH"  # mandatory finance domain
    loaded = svc.get_for_job(jid)
    assert loaded.background_fit_sensitivity.level.value == bg_before
    assert loaded.shortlisting_strictness.level.value == short_before
    # Re-save must not duplicate or reset siblings
    svc.save_for_job(jid)
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM job_opportunity_intelligence WHERE job_id=%s", (jid,))
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
    reloaded = svc.get_for_job(jid)
    assert reloaded.background_fit_sensitivity.level.value == bg_before
    assert reloaded.shortlisting_strictness.level.value == short_before


def test_persistence_shortlisting_only(mod_conn):
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    jid = _make_job(mod_conn, "persist-sig")
    with mod_conn.cursor() as cur:
        cur.execute("UPDATE jobs SET jd_text=%s WHERE id=%s", (
            "Requirements:\n- 5-8 years experience\n- Python\n- SQL\n- AWS\n- Docker\n- Kubernetes\n- TensorFlow\n- AWS Certified Solutions Architect required", jid))
    mod_conn.commit()
    svc = get_opportunity_intelligence_service()
    saved = svc.save_for_job(jid)
    assert saved.shortlisting_strictness.level.value in ("MODERATE", "HIGH")
    loaded = svc.get_for_job(jid)
    assert loaded.shortlisting_strictness.level.value == saved.shortlisting_strictness.level.value
    # Phase 19: competition is computed (valid contract); background has no domain
    # terms, so it is LOW (determined absence) or UNKNOWN — never HIGH
    assert loaded.competition_intensity.level.value in ("LOW", "MODERATE", "HIGH", "UNKNOWN")
    assert loaded.background_fit_sensitivity.level.value in ("LOW", "UNKNOWN")
    # No duplicate on re-save
    svc.save_for_job(jid)
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM job_opportunity_intelligence WHERE job_id=%s", (jid,))
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
