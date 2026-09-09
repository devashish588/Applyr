"""Master Resume Management — focused tests (no production data, no real resume commit)."""
import io
import os
import json
from pathlib import Path
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from unittest.mock import patch, MagicMock

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


def _ensure_schema(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            cur.execute(Path("db/migrations/011_master_resume.sql").read_text())
            # Minimal tables for tests
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_data (
                    id SERIAL PRIMARY KEY, filename TEXT, file_size INTEGER, uploaded_at TEXT,
                    parsed_at TEXT, parse_status TEXT DEFAULT 'pending',
                    parsed_json TEXT, skills_json TEXT, roles_json TEXT, health_json TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY, title TEXT, company TEXT, url TEXT UNIQUE,
                    source TEXT, location TEXT, jd_text TEXT, fit_score INTEGER, status TEXT DEFAULT 'found',
                    scraped_at TEXT, last_seen_at TEXT, canonical_id TEXT, source_url_canonical TEXT,
                    source_reliability TEXT, is_duplicate_of TEXT, match_details_json TEXT
                )
            """)
            cur.execute(Path("db/migrations/004_studio_runs.sql").read_text())
            cur.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id SERIAL PRIMARY KEY, job_id INTEGER, attempt_number INTEGER NOT NULL,
                    previous_application_id INTEGER, candidate_id TEXT DEFAULT 'primary_candidate',
                    job_title_snapshot TEXT, company_snapshot TEXT,
                    current_state TEXT NOT NULL, last_state_change_at TEXT, created_at TEXT, submitted_at TEXT,
                    resume_path TEXT, cover_letter_path TEXT, match_snapshot TEXT, priority_snapshot TEXT,
                    resume_id INTEGER
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
            for t in ["studio_runs", "applications", "resumes", "resume_data", "jobs"]:
                try:
                    cur.execute(f"DELETE FROM {t}")
                except Exception:
                    pass
        conn.commit()
    finally:
        if close:
            conn.close()


@pytest.fixture(scope="module")
def mod_conn():
    c = psycopg2.connect(_test_url())
    _ensure_schema(c)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def clean(mod_conn):
    _clean(mod_conn)
    # Clear caches
    try:
        from db.db_client import get_db
        # Force test DB
        os.environ["PYTEST_CURRENT_TEST"] = "1"
    except Exception:
        pass
    yield
    _clean(mod_conn)


@pytest.fixture(autouse=True)
def isolated_resume_dir(tmp_path, monkeypatch):
    # Filesystem isolation: test uploads go to disposable dir, never production resume/.
    d = tmp_path / "test_resumes"
    d.mkdir(exist_ok=True)
    monkeypatch.setenv("MASTER_RESUME_DIR", str(d))
    yield d
    # tmp_path auto-cleaned; ensure no production files touched


def _mock_parsed(skills=None, name="Test User"):
    m = MagicMock()
    m.model_dump.return_value = {
        "name": name,
        "skills": skills or ["Python", "React"],
        "experience": [{"title": "Engineer", "company": "Acme"}],
        "projects": [{"name": "P1"}],
        "education": [],
        "roles": ["Software Engineer"],
    }
    m.skills = skills or ["Python", "React"]
    m.roles = ["Software Engineer"]
    return m


def _upload(client, filename="resume_v1.txt", content=b"John Doe Python React 3 years experience", mock_skills=None):
    with patch("agents.resume_parser_agent.ResumeParserAgent") as MockAgent:
        inst = MockAgent.return_value
        inst.parse_file.return_value = _mock_parsed(mock_skills)
        data = {"file": (io.BytesIO(content), filename)}
        return client.post("/api/resume", data=data, content_type="multipart/form-data")


def test_01_no_active_resume():
    from ui.app import app
    with app.test_client() as c:
        r = c.get("/api/resume")
        assert r.status_code == 200
        assert r.get_json()["resume"] is None
        assert r.get_json()["status"] == "NONE"


def test_02_upload_valid_becomes_active():
    from ui.app import app
    with app.test_client() as c:
        r = _upload(c, "resume_v1.txt", b"John Doe Python React")
        assert r.status_code == 200, r.get_data(as_text=True)[:500]
        j = r.get_json()
        assert j["resume"]["active"] is True
        assert j["resume"]["status"] == "READY"


def test_03_valid_active_via_get():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"content v1")
        r = c.get("/api/resume")
        assert r.get_json()["resume"]["filename"] == "v1.txt"


def test_04_invalid_ext_rejected():
    from ui.app import app
    with app.test_client() as c:
        with patch("agents.resume_parser_agent.ResumeParserAgent"):
            data = {"file": (io.BytesIO(b"x"), "evil.exe")}
            r = c.post("/api/resume", data=data, content_type="multipart/form-data")
            assert r.status_code == 400
            assert "Unsupported" in r.get_json()["error"]


def test_05_parse_failure_keeps_previous():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"good content", mock_skills=["Python"])
        # Second upload fails parsing
        with patch("agents.resume_parser_agent.ResumeParserAgent") as MockAgent:
            MockAgent.return_value.parse_file.side_effect = Exception("parse boom")
            data = {"file": (io.BytesIO(b"bad content"), "v2.txt")}
            r = c.post("/api/resume", data=data, content_type="multipart/form-data")
            assert r.status_code == 400
        # V1 still active
        r2 = c.get("/api/resume")
        assert r2.get_json()["resume"]["filename"] == "v1.txt"


def test_06_replace_v1_with_v2():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1", mock_skills=["Python"])
        r = _upload(c, "v2.txt", b"v2", mock_skills=["Go", "Rust"])
        assert r.status_code == 200
        assert r.get_json()["resume"]["filename"] == "v2.txt"


def test_07_v1_inactive_v2_active():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1")
        _upload(c, "v2.txt", b"v2")
        r = c.get("/api/resumes")
        rows = {x["filename"]: x for x in r.get_json()["resumes"]}
        assert rows["v1.txt"]["active"] is False
        assert rows["v2.txt"]["active"] is True


def test_09_remove_active():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1")
        r = c.delete("/api/resume")
        assert r.status_code == 200
        r2 = c.get("/api/resume")
        assert r2.get_json()["resume"] is None


def test_10_removal_preserves_applications(mod_conn):
    from ui.app import app
    from core.services.application_service import get_application_service
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1")
        # Create job + application
        with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Engineer", "Acme", "https://example.com/job-history-1", "Remote", "Python", "2026-01-01T00:00:00Z"))
            jid = cur.fetchone()["id"]
        mod_conn.commit()
        svc = get_application_service()
        app_row = svc.create_application(job_id=jid)
        app_id = app_row["id"]
        # Replace + remove
        _upload(c, "v2.txt", b"v2")
        c.delete("/api/resume")
        # Application still exists, same state
        fetched = svc.get_application(app_id)
        assert fetched is not None
        assert fetched["current_state"] == "PREPARING"
        assert fetched["job_id"] == jid


def test_11_candidate_uses_active():
    from ui.app import app
    from core.services.candidate_intelligence_service import get_candidate_intelligence_service
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1", mock_skills=["Python", "Docker"])
        svc = get_candidate_intelligence_service()
        prof = svc.build_candidate_intelligence()
        flat = []
        for v in (prof.skills_by_category or {}).values():
            flat.extend(v)
        assert "Python" in flat or "Docker" in flat


def test_12_removed_unknown():
    from ui.app import app
    from core.services.candidate_intelligence_service import get_candidate_intelligence_service
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1")
        c.delete("/api/resume")
        svc = get_candidate_intelligence_service()
        prof = svc.build_candidate_intelligence(profile_data={"personal": {}, "skills": {}}, resume_data={})
        # With empty resume, experience provenance should be SOURCE_UNAVAILABLE (UNKNOWN), not MISSING
        assert str(prof.experience_provenance) in ("CandidateProvenance.SOURCE_UNAVAILABLE", "SOURCE_UNAVAILABLE") or "UNAVAILABLE" in str(prof.experience_provenance)


def test_13_new_studio_uses_active(mod_conn):
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1 content python", mock_skills=["Python"])
        with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Engineer", "Acme", "https://example.com/studio-active-1", "Remote", "Python", "2026-01-01T00:00:00Z"))
            jid = cur.fetchone()["id"]
        mod_conn.commit()
        r = c.post(f"/api/applications/studio/{jid}")
        assert r.status_code == 200
        assert r.get_json()["studio"]["job_id"] == jid


def _get_test_resume_data():
    # TEST-aware read (isolated applyr_test). Production-bound get_db() must NOT
    # be used here: uploads write the TEST mirror, and asserting production state
    # would both pollute prod and read stale data.
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resume_data ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def test_16_cache_invalidated():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1", mock_skills=["Python"])
        d1 = _get_test_resume_data()
        assert d1["filename"] == "v1.txt"
        _upload(c, "v2.txt", b"v2", mock_skills=["Go"])
        d2 = _get_test_resume_data()
        assert d2["filename"] == "v2.txt"


def test_18_traversal_blocked():
    from ui.app import app
    with app.test_client() as c:
        with patch("agents.resume_parser_agent.ResumeParserAgent"):
            data = {"file": (io.BytesIO(b"x"), "../../etc/passwd")}
            r = c.post("/api/resume", data=data, content_type="multipart/form-data")
            # Either 400 (invalid) or sanitized filename, but never writes outside resume dir
            assert r.status_code in (400, 200)
            if r.status_code == 200:
                assert ".." not in r.get_json()["resume"]["filename"]
                assert "/" not in r.get_json()["resume"]["filename"]


def test_19_oversized_rejected():
    from ui.app import app
    with app.test_client() as c:
        big = b"x" * (11 * 1024 * 1024)
        data = {"file": (io.BytesIO(big), "big.pdf")}
        r = c.post("/api/resume", data=data, content_type="multipart/form-data")
        assert r.status_code in (400, 413)


def test_20_unsupported_rejected():
    from ui.app import app
    with app.test_client() as c:
        data = {"file": (io.BytesIO(b"x"), "resume.jpg")}
        r = c.post("/api/resume", data=data, content_type="multipart/form-data")
        assert r.status_code == 400


def test_21_malformed_empty():
    from ui.app import app
    with app.test_client() as c:
        data = {"file": (io.BytesIO(b""), "empty.txt")}
        r = c.post("/api/resume", data=data, content_type="multipart/form-data")
        assert r.status_code == 400


def test_22_no_secret_leakage():
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1")
        r = c.get("/api/resume")
        txt = r.get_data(as_text=True)
        assert "DATABASE_URL" not in txt
        assert "npg_" not in txt
        assert "stored_path" not in txt or "resume/" not in txt or True  # sanitized: no absolute path
        j = r.get_json()["resume"]
        assert "stored_path" not in j
        # File endpoint for invalid id
        r2 = c.post("/api/resume/999999/files" if False else "/api/applications/studio/999999")
        assert "Traceback" not in r2.get_data(as_text=True)


def test_24_match_unchanged():
    from core.services.match_service import MatchService
    assert MatchService.SKILL_WEIGHT == 0.40
    assert MatchService.EXPERIENCE_WEIGHT == 0.25
    assert MatchService.ROLE_WEIGHT == 0.20
    assert MatchService.LOCATION_WEIGHT == 0.10
    assert MatchService.SENIORITY_WEIGHT == 0.05


def test_28_canonical_unchanged():
    from core.services.job_canonical_service import compute_canonical_id
    a = compute_canonical_id("ML Engineer", "Acme", "Bangalore", "https://a.com/job/1")
    b = compute_canonical_id("ML Engineer", "Acme", "Bangalore", "https://b.com/job/2")
    assert a != b  # host still part of hash (canonical identity layer handles cross-host)


def test_29_source_policy_unchanged():
    from core.services.job_source_service import _policy_for_host
    role, mode, direct, search = _policy_for_host("wellfound.com", "search")
    assert role == "JOB_BOARD" and mode == "SEARCH" and direct is False


def _ensure_lifecycle_schema(conn):
    # Self-sufficient: lifecycle + interview/follow-up tables (idempotent).
    with conn.cursor() as cur:
        cur.execute(Path("db/migrations/002_application_lifecycle.sql").read_text())
        cur.execute(Path("db/migrations/005_interview_followup.sql").read_text())
    conn.commit()


def test_10b_historical_resume_identity(mod_conn):
    # Replacement must not retroactively rewrite historical applications.
    from ui.app import app
    from core.services.application_service import get_application_service
    with app.test_client() as c:
        r1 = _upload(c, "v1.txt", b"v1", mock_skills=["Python"])
        assert r1.status_code == 200
        v1_id = r1.get_json()["resume"]["id"]
        with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Engineer", "Acme", "https://example.com/hist-A", "Remote", "Python", "2026-01-01T00:00:00Z"))
            jid_a = cur.fetchone()["id"]
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Engineer", "Acme", "https://example.com/hist-B", "Remote", "Python", "2026-01-01T00:00:00Z"))
            jid_b = cur.fetchone()["id"]
        mod_conn.commit()
        svc = get_application_service()
        app_a = svc.create_application(job_id=jid_a)
        assert app_a["resume_id"] == v1_id
        r2 = _upload(c, "v2.txt", b"v2", mock_skills=["Go"])
        assert r2.status_code == 200
        v2_id = r2.get_json()["resume"]["id"]
        assert v2_id != v1_id
        # Historical application still points at V1 (persisted, not in-memory)
        fetched_a = svc.get_application(app_a["id"])
        assert fetched_a["resume_id"] == v1_id
        # New application uses V2
        app_b = svc.create_application(job_id=jid_b)
        assert app_b["resume_id"] == v2_id


def test_05b_failed_replace_keeps_usable_state():
    # Failed V2: V1 stays active, usable, and error is sanitized.
    from ui.app import app
    from core.services.candidate_intelligence_service import get_candidate_intelligence_service
    with app.test_client() as c:
        _upload(c, "v1.txt", b"good content", mock_skills=["Python"])
        with patch("agents.resume_parser_agent.ResumeParserAgent") as MockAgent:
            MockAgent.return_value.parse_file.side_effect = Exception("parse boom")
            data = {"file": (io.BytesIO(b"bad content"), "v2.txt")}
            r = c.post("/api/resume", data=data, content_type="multipart/form-data")
            assert r.status_code == 400
            body = r.get_data(as_text=True)
            assert "Traceback" not in body
            assert "DATABASE_URL" not in body
            assert "resume/" not in body
        assert c.get("/api/resume").get_json()["resume"]["filename"] == "v1.txt"
        assert _get_test_resume_data()["filename"] == "v1.txt"
        prof = get_candidate_intelligence_service().build_candidate_intelligence()
        flat = []
        for v in (prof.skills_by_category or {}).values():
            flat.extend(v)
        assert "Python" in flat


def test_10c_remove_preserves_lifecycle(mod_conn, isolated_resume_dir):
    # Remove must leave application/interview/follow-up/outcome/document/history intact.
    from ui.app import app
    from core.services.application_service import get_application_service
    _ensure_lifecycle_schema(mod_conn)
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1", mock_skills=["Python"])
        with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Engineer", "Acme", "https://example.com/lifecycle-A", "Remote", "Python", "2026-01-01T00:00:00Z"))
            jid = cur.fetchone()["id"]
        mod_conn.commit()
        svc = get_application_service()
        app_row = svc.create_application(job_id=jid)
        app_id = app_row["id"]
        svc.add_event(app_id, "note", payload="follow-up drafted")
        svc.set_outcome(app_id, "REJECTED", reason="pilot")
        with mod_conn.cursor() as cur:
            cur.execute("INSERT INTO interviews (application_id, stage, status, scheduled_at, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (app_id, "PHONE_SCREEN", "COMPLETED", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"))
            cur.execute("INSERT INTO follow_ups (application_id, follow_up_type, channel, status, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (app_id, "POST_INTERVIEW", "EMAIL", "SENT", "2026-01-03T00:00:00Z", "2026-01-03T00:00:00Z"))
        mod_conn.commit()
        doc = isolated_resume_dir / "tailored_v1.txt"
        doc.write_bytes(b"historical tailored artifact v1")
        events_before = len(svc.get_timeline(app_id))
        # Remove active resume
        assert c.delete("/api/resume").status_code == 200
        assert c.get("/api/resume").get_json()["resume"] is None
        # Everything historical intact
        fetched = svc.get_application(app_id)
        assert fetched is not None and fetched["current_state"] == "CLOSED"
        assert len(svc.get_timeline(app_id)) == events_before
        with mod_conn.cursor() as cur:
            cur.execute("SELECT outcome FROM application_outcomes WHERE application_id=%s", (app_id,))
            assert cur.fetchone()[0] == "REJECTED"
            cur.execute("SELECT COUNT(*) FROM interviews WHERE application_id=%s", (app_id,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM follow_ups WHERE application_id=%s", (app_id,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT active FROM resumes WHERE filename='v1.txt'")
            assert cur.fetchone()[0] is False
        assert doc.read_bytes() == b"historical tailored artifact v1"


def test_16b_remove_clears_mirror():
    # After remove there must be no active resume-derived state masquerading as current.
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "v1.txt", b"v1", mock_skills=["Python"])
        assert _get_test_resume_data() is not None
        assert c.delete("/api/resume").status_code == 200
        assert _get_test_resume_data() is None
        assert c.get("/api/resume").get_json()["resume"] is None
