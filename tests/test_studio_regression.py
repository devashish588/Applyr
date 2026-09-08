import os, uuid, json, sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))

def _test_url():
    url = os.getenv("TEST_DATABASE_URL","")
    if not url:
        prod = os.getenv("DATABASE_URL","")
        if "/neondb?" in prod:
            return prod.replace("/neondb?","/applyr_test?")
        return prod.replace("/neondb","/applyr_test") if "/neondb" in prod else prod
    return url

def _get_conn():
    return psycopg2.connect(_test_url())

def _ensure():
    conn=_get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY, title TEXT, company TEXT, url TEXT UNIQUE,
                    source TEXT, location TEXT, jd_text TEXT, fit_score INTEGER, status TEXT DEFAULT 'found',
                    scraped_at TEXT, last_seen_at TEXT, canonical_id TEXT, source_url_canonical TEXT, source_reliability TEXT, is_duplicate_of TEXT,
                    match_details_json TEXT, hr_email TEXT
                )
            """)
            cur.execute(Path("db/migrations/004_studio_runs.sql").read_text())
            cur.execute("CREATE TABLE IF NOT EXISTS recruiters (id SERIAL PRIMARY KEY, company TEXT, job_id INTEGER, name TEXT, email TEXT, confidence INTEGER, source TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS job_source_attributions (id SERIAL PRIMARY KEY, canonical_job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE, source_id TEXT, source_name TEXT, host TEXT, mode TEXT, adapter TEXT, source_url TEXT, first_seen_at TEXT, last_seen_at TEXT, UNIQUE(canonical_job_id, source_id, source_url))")
            # Ensure job_sources for FK (008/009)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS job_sources (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, host TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE, source_type TEXT DEFAULT 'search', adapter TEXT DEFAULT 'SearchAdapter',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    last_run_at TEXT, last_success_at TEXT, last_failure_at TEXT,
                    last_job_count INTEGER DEFAULT 0, last_duration_ms INTEGER DEFAULT 0,
                    failure_category TEXT, last_error TEXT, priority INTEGER DEFAULT 100, is_builtin BOOLEAN DEFAULT FALSE
                )
            """)
        conn.commit()
    finally:
        conn.close()

def _clean():
    conn=_get_conn()
    try:
        with conn.cursor() as cur:
            for t in ["job_source_attributions","studio_runs","recruiters","jobs"]:
                try:
                    cur.execute(f"DELETE FROM {t}")
                except:
                    pass
        conn.commit()
    finally:
        conn.close()

def _create_job(title="Regression Job", company="RegressionCorp", url=None, jd_text="Python required"):
    conn=_get_conn()
    try:
        if url is None:
            url=f"https://example.com/regression/{uuid.uuid4()}"
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at, source, hr_email) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                        (title, company, url, "Bangalore", jd_text, "2026-09-08T00:00:00Z", "test", "hr@example.com"))
            jid=cur.fetchone()["id"]
        conn.commit()
        return jid
    finally:
        conn.close()

def test_studio_with_recruiter_outreach_dict():
    """Regression: outreach_text is dict from build_cold_email, slicing must not fail (HTTP 500)."""
    _ensure()
    _clean()
    jid=_create_job(company="StudioRecruitCo")
    # Insert recruiter for this company to trigger outreach preview
    conn=_get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO recruiters (company, job_id, name, email, confidence, source) VALUES (%s,%s,%s,%s,%s,%s)",
                        ("StudioRecruitCo", jid, "Jane Recruiter", "jane@studiorecruitco.com", 95, "test"))
        conn.commit()
    finally:
        conn.close()
    from ui.app import app
    with app.test_client() as c:
        r=c.post(f"/api/applications/studio/{jid}")
        assert r.status_code==200, f"expected 200, got {r.status_code} body {r.get_data(as_text=True)[:500]}"
        studio=r.get_json()["studio"]
        assert studio["recruiter"]["status"]=="FOUND"
        # outreach_preview should be string, not error
        assert studio["outreach_preview"]["status"]=="READY"
        assert isinstance(studio["outreach_preview"]["text"], str)
        assert len(studio["outreach_preview"]["text"]) > 10
        assert "Traceback" not in r.get_data(as_text=True)

def test_studio_with_multiple_attributions():
    """Job with 2 source attributions must still load Studio HTTP 200."""
    _ensure()
    _clean()
    jid=_create_job(company="MultiAttribCo", url="https://example.com/multi/1")
    conn=_get_conn()
    try:
        with conn.cursor() as cur:
            # Ensure job_sources exist for FK
            cur.execute("INSERT INTO job_sources (id, name, url, host, enabled, source_type, adapter, created_at, updated_at, is_builtin, priority) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                        ("test-src-a","Company","https://example.com/careers","example.com",True,"html","GenericHTMLAdapter","2026-01-01T00:00:00","2026-01-01T00:00:00",False,100))
            cur.execute("INSERT INTO job_sources (id, name, url, host, enabled, source_type, adapter, created_at, updated_at, is_builtin, priority) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                        ("test-src-b","Wellfound","https://wellfound.com/jobs","wellfound.com",True,"search","SearchAdapter","2026-01-01T00:00:00","2026-01-01T00:00:00",False,100))
            cur.execute("INSERT INTO job_source_attributions (canonical_job_id, source_id, source_name, host, mode, adapter, source_url, first_seen_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (jid,"test-src-a","Company","example.com","HTML","GenericHTMLAdapter","https://example.com/multi/1","2026-09-08T00:00:00","2026-09-08T00:00:00"))
            cur.execute("INSERT INTO job_source_attributions (canonical_job_id, source_id, source_name, host, mode, adapter, source_url, first_seen_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (jid,"test-src-b","Wellfound","wellfound.com","SEARCH","SearchAdapter","https://wellfound.com/multi/1","2026-09-08T00:00:00","2026-09-08T00:00:00"))
        conn.commit()
    finally:
        conn.close()
    from ui.app import app
    with app.test_client() as c:
        r=c.post(f"/api/applications/studio/{jid}")
        assert r.status_code==200
        assert r.get_json()["studio"]["job_id"]==jid

def test_studio_with_missing_optional_fields():
    """Job with NULL optional fields must not 500."""
    _ensure()
    _clean()
    conn=_get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        ("Sparse Job", "SparseCo", f"https://example.com/sparse/{uuid.uuid4()}", None, None, "2026-09-08T00:00:00Z"))
            jid=cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    from ui.app import app
    with app.test_client() as c:
        r=c.post(f"/api/applications/studio/{jid}")
        assert r.status_code==200
        assert "error" not in r.get_json() or r.get_json().get("success") is True

def test_studio_sanitized_error():
    """Invalid job_id must not leak secrets."""
    from ui.app import app
    with app.test_client() as c:
        r=c.post("/api/applications/studio/999999")
        assert r.status_code==400 or r.status_code==404 or r.status_code==500
        txt=r.get_data(as_text=True)
        assert "Traceback" not in txt
        assert "npg_" not in txt
        assert "gsk_" not in txt
        assert "DATABASE_URL" not in txt
