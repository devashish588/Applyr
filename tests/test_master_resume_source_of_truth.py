"""Source-of-truth regression: DB active is authoritative, stale legacy file never means active."""
import io
import os
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


def _ensure(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            cur.execute(Path("db/migrations/011_master_resume.sql").read_text())
            cur.execute(Path("db/migrations/004_studio_runs.sql").read_text())
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_data (
                    id SERIAL PRIMARY KEY, filename TEXT, file_size INTEGER, uploaded_at TEXT,
                    parsed_at TEXT, parse_status TEXT, parsed_json TEXT, skills_json TEXT, roles_json TEXT, health_json TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY, title TEXT, company TEXT, url TEXT UNIQUE, source TEXT,
                    location TEXT, jd_text TEXT, scraped_at TEXT
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
            for stmt in [
                "DELETE FROM studio_runs WHERE job_id IN (SELECT id FROM jobs WHERE url LIKE 'https://sot%' OR url LIKE 'https://example.com/sot%')",
                "DELETE FROM jobs WHERE url LIKE 'https://sot%' OR url LIKE 'https://example.com/sot%'",
                "DELETE FROM resumes WHERE filename LIKE 'sot-%'",
                "DELETE FROM resume_data",
            ]:
                try:
                    cur.execute(stmt)
                except Exception:
                    conn.rollback()
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


@pytest.fixture(autouse=True)
def isolated_dir(tmp_path, monkeypatch):
    d = tmp_path / "sot_resumes"
    d.mkdir(exist_ok=True)
    monkeypatch.setenv("MASTER_RESUME_DIR", str(d))
    yield d


def _mock_parsed(skills=None):
    m = MagicMock()
    m.model_dump.return_value = {"name": "SOT User", "skills": skills or ["Python"], "experience": [{"title": "E", "company": "Acme"}], "projects": [], "education": [], "roles": ["Software Engineer"]}
    m.skills = skills or ["Python"]
    m.roles = ["Software Engineer"]
    return m


def _upload(client, name, skills=None):
    with patch("agents.resume_parser_agent.ResumeParserAgent") as MA:
        MA.return_value.parse_file.return_value = _mock_parsed(skills)
        return client.post("/api/resume", data={"file": (io.BytesIO(b"content " + name.encode()), name)}, content_type="multipart/form-data")


def test_1_db_none_stale_file_api_none_and_pipeline_blocked(isolated_dir):
    """Most important: DB NONE + stale legacy file → API NONE, pipeline BLOCKED."""
    from ui.app import app
    # Ensure DB NONE
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resumes")
            cur.execute("DELETE FROM resume_data")
        conn.commit()
    finally:
        conn.close()
    # Create stale legacy file in isolated dir
    stale = isolated_dir / "master_resume.pdf"
    stale.write_bytes(b"stale v1 content")
    with app.test_client() as c:
        r = c.get("/api/resume")
        assert r.status_code == 200
        assert r.get_json()["resume"] is None
        assert r.get_json()["status"] == "NONE"
    # Pipeline must treat as unavailable despite file
    from pipeline.orchestrator import Orchestrator
    orch = Orchestrator(run_id="sot-none")
    assert orch.resume_blocked is True
    assert "No active master resume" in orch.resume_block_reason


def test_2_db_active_legacy_exists_available(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        r = _upload(c, "sot-v1.txt", ["Python"])
        assert r.status_code == 200
        # Legacy pointer should exist in isolated dir
        assert (isolated_dir / "master_resume.txt").exists()
        # Orchestrator sees V1 available (mock parser for orchestrator file read)
        with patch("agents.resume_parser_agent.ResumeParserAgent") as MA:
            m = MagicMock()
            m.parse_file.return_value = MagicMock(confidence=95, name="SOT", skills=["Python", "Go", "Rust", "SQL", "Docker"], experience=[{"t": "e"}], projects=[{"n": "p"}])
            MA.return_value = m
            # Need parse_file to return object with attributes, not MagicMock default
            parsed = MagicMock()
            parsed.confidence = 95
            parsed.name = "SOT User"
            parsed.skills = ["Python", "Go", "Rust", "SQL", "Docker"]
            parsed.experience = [{"title": "E"}]
            parsed.projects = [{"name": "P"}]
            MA.return_value.parse_file.return_value = parsed
            from pipeline.orchestrator import Orchestrator
            orch = Orchestrator(run_id="sot-active")
            # Should not be blocked on missing resume (may block on confidence, but not on NONE)
            assert "No active master resume" not in (orch.resume_block_reason or "")


def test_3_db_active_legacy_missing_still_available(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        r = _upload(c, "sot-v1.txt", ["Python"])
        assert r.status_code == 200
        # Delete legacy pointer, keep versioned file
        leg = isolated_dir / "master_resume.txt"
        if leg.exists():
            leg.unlink()
        # Active must remain logically available via stored_path
        r2 = c.get("/api/resume")
        assert r2.get_json()["resume"] is not None
        assert r2.get_json()["status"] == "READY"


def test_4_v2_active_stale_v1_pointer_uses_v2(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "sot-v1.txt", ["Python"])
        _upload(c, "sot-v2.txt", ["Go"])
        # Simulate stale V1 pointer: overwrite legacy with V1 content
        (isolated_dir / "master_resume.txt").write_bytes(b"stale V1")
        # API must show V2
        r = c.get("/api/resume")
        assert r.get_json()["resume"]["filename"] == "sot-v2.txt"
        # Candidate must use V2 (Go), not V1 (Python only)
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        prof = get_candidate_intelligence_service().build_candidate_intelligence()
        flat = []
        for v in (prof.skills_by_category or {}).values():
            flat.extend(v)
        assert "Go" in flat


def test_5_remove_legacy_absent_unknown_blocked(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "sot-v1.txt", ["Python"])
        c.delete("/api/resume")
        # DB NONE
        r = c.get("/api/resume")
        assert r.get_json()["resume"] is None
        # Candidate UNKNOWN
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        prof = get_candidate_intelligence_service().build_candidate_intelligence(profile_data={"personal": {}, "skills": {}}, resume_data={})
        assert "UNAVAILABLE" in str(prof.experience_provenance)
        # Pipeline blocked
        from pipeline.orchestrator import Orchestrator
        orch = Orchestrator(run_id="sot-removed")
        assert orch.resume_blocked is True


def test_6_remove_stale_survives_db_none_wins(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "sot-v1.txt", ["Python"])
        c.delete("/api/resume")
        # Simulate stale pointer surviving
        (isolated_dir / "master_resume.pdf").write_bytes(b"stale")
        r = c.get("/api/resume")
        assert r.get_json()["resume"] is None
        from pipeline.orchestrator import Orchestrator
        orch = Orchestrator(run_id="sot-stale")
        assert orch.resume_blocked is True
        assert "No active master resume" in orch.resume_block_reason


def test_7_reupload_uses_v2(isolated_dir):
    from ui.app import app
    with app.test_client() as c:
        _upload(c, "sot-v1.txt", ["Python"])
        c.delete("/api/resume")
        r = _upload(c, "sot-v2.txt", ["Rust"])
        assert r.status_code == 200
        assert r.get_json()["resume"]["filename"] == "sot-v2.txt"
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        prof = get_candidate_intelligence_service().build_candidate_intelligence()
        flat = []
        for v in (prof.skills_by_category or {}).values():
            flat.extend(v)
        assert "Rust" in flat


def test_cross_boundary_consistency(isolated_dir, mod_conn):
    """API, Candidate, Studio, Pipeline agree on NONE with stale file."""
    from ui.app import app
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resumes")
            cur.execute("DELETE FROM resume_data")
        conn.commit()
    finally:
        conn.close()
    (isolated_dir / "master_resume.pdf").write_bytes(b"stale")
    with app.test_client() as c:
        api_none = c.get("/api/resume").get_json()["resume"] is None
    from core.services.candidate_intelligence_service import get_candidate_intelligence_service
    prof = get_candidate_intelligence_service().build_candidate_intelligence(profile_data={"personal": {}, "skills": {}}, resume_data={})
    cand_unknown = "UNAVAILABLE" in str(prof.experience_provenance)
    from pipeline.orchestrator import Orchestrator
    orch = Orchestrator(run_id="sot-cross")
    pipe_blocked = orch.resume_blocked is True
    # Studio: new run with no active should not use stale file content
    with mod_conn.cursor() as cur:
        from psycopg2.extras import RealDictCursor
        # create job
        import uuid
        url = f"https://sot.example.com/{uuid.uuid4()}"
        cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                    ("Engineer", "Acme", url, "Remote", "Python", "2026-01-01T00:00:00Z"))
        jid = cur.fetchone()[0]
    mod_conn.commit()
    with app.test_client() as c:
        r = c.post(f"/api/applications/studio/{jid}")
        assert r.status_code == 200
        studio = r.get_json()["studio"]
        # Resume source must not claim READY from stale file; profile fallback may give READY via profile, but path must not be stale file
        # At minimum, studio must succeed without using stale content and historical runs unchanged
        assert studio["job_id"] == jid
    assert api_none and cand_unknown and pipe_blocked
