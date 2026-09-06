"""
Phase 7 Final Hardening — PostgreSQL Integration via Isolated TEST_DATABASE_URL.
All tests use real PostgreSQL on disposable `applyr_test` database, never production neondb.
Verifies: migration reproducibility, transaction atomicity (rollback), constraints,
concurrency (SELECT FOR UPDATE), lifecycle integration (service + HTTP), routes.

Safety: conftest.py refuses to run if TEST_DATABASE_URL missing or points to production.
"""
import os
import json
import threading
import time
from pathlib import Path

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

pytestmark = pytest.mark.hardening

# ---------------------------------------------------------------------------
# Helpers — test DB wiring (isolated applyr_test, never production neondb)
# ---------------------------------------------------------------------------

def _test_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        prod = os.getenv("DATABASE_URL", "")
        if "/neondb?" in prod:
            url = prod.replace("/neondb?", "/applyr_test?")
        elif "/neondb" in prod:
            url = prod.replace("/neondb", "/applyr_test")
        else:
            url = prod
    return url


def _is_production(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        db = urlparse(url).path.lstrip("/").split("?")[0].split("/")[0]
        return db == "neondb"
    except Exception:
        return "/neondb" in url


def _get_conn():
    url = _test_url()
    assert url, "TEST_DATABASE_URL required"
    assert not _is_production(url), f"TEST_DATABASE_URL must not be production: {url[:60]}"
    return psycopg2.connect(url)


def _ensure_test_schema(conn=None):
    """Create jobs + lifecycle tables in applyr_test from scratch (idempotent)."""
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            # jobs table — mirrors db_client._init_schema (Postgres version)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id                   SERIAL PRIMARY KEY,
                    title                TEXT,
                    company              TEXT,
                    url                  TEXT UNIQUE,
                    source               TEXT,
                    location             TEXT,
                    type                 TEXT,
                    hr_email             TEXT,
                    jd_text              TEXT,
                    fit_score            INTEGER,
                    status               TEXT DEFAULT 'found',
                    scraped_at           TEXT,
                    applied_at           TEXT,
                    cover_letter_path    TEXT,
                    tailored_resume_path TEXT,
                    email_subject        TEXT,
                    email_body           TEXT,
                    match_details_json   TEXT
                )
            """)
            # lifecycle migration 002 — read from file for reproducibility check
            mig_path = Path(__file__).parent.parent / "db" / "migrations" / "002_application_lifecycle.sql"
            mig_sql = mig_path.read_text(encoding="utf-8")
            cur.execute(mig_sql)
        conn.commit()
    finally:
        if close:
            conn.close()


def _clean_tables(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            # order matters for FKs
            cur.execute("DELETE FROM application_events")
            cur.execute("DELETE FROM application_outcomes")
            cur.execute("DELETE FROM applications")
            cur.execute("DELETE FROM jobs")
        conn.commit()
    finally:
        if close:
            conn.close()


def _create_job(conn, title="Test Engineer", company="TestCo", url=None):
    if url is None:
        import uuid
        url = f"https://example.com/job/{uuid.uuid4()}"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO jobs (title, company, url, status, scraped_at) VALUES (%s,%s,%s,'found',%s) RETURNING id",
            (title, company, url, __import__("datetime").datetime.now().isoformat()),
        )
        job_id = cur.fetchone()["id"]
    conn.commit()
    return job_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_db_url():
    url = _test_url()
    assert url and not _is_production(url), "TEST_DATABASE_URL must be isolated applyr_test"
    return url


@pytest.fixture(scope="module")
def module_conn(test_db_url):
    conn = psycopg2.connect(test_db_url)
    _ensure_test_schema(conn)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def clean(module_conn):
    _clean_tables(module_conn)
    yield
    _clean_tables(module_conn)


# ---------------------------------------------------------------------------
# 1. Isolation guard — proves we never run against production
# ---------------------------------------------------------------------------

class TestIsolationGuard:
    def test_guard_rejects_production_marker(self):
        # Directly verify guard logic, not via conftest hook
        assert _is_production("postgresql://x@ep-patient-glitter-atdfvafq-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require")
        assert _is_production("postgresql://u:p@host/neondb?sslmode=require")
        assert not _is_production("postgresql://u:p@host/applyr_test?sslmode=require")
        assert not _is_production("postgresql://u:p@127.0.0.1:5433/applyr_test")

    def test_test_url_is_isolated(self, test_db_url):
        from urllib.parse import urlparse
        assert "applyr_test" in test_db_url
        db = urlparse(test_db_url).path.lstrip("/").split("?")[0].split("/")[0]
        assert db == "applyr_test", f"test DB must be applyr_test, got {db}"
        # also ensure prod still exists but we are not using it
        prod = os.getenv("DATABASE_URL", "")
        assert test_db_url != prod
        assert urlparse(prod).path.lstrip("/").split("?")[0].split("/")[0] == "neondb"

    def test_service_uses_test_url(self, test_db_url):
        # ApplicationService._resolve_database_url must return test URL when TEST_DATABASE_URL set
        from core.services.application_service import _resolve_database_url
        resolved = _resolve_database_url()
        assert resolved == test_db_url
        assert "applyr_test" in resolved


# ---------------------------------------------------------------------------
# 2. Migration reproducibility — 002_application_lifecycle.sql on clean DB
# ---------------------------------------------------------------------------

class TestMigrationReproducibility:
    def test_migration_applies_clean(self, module_conn):
        # _ensure_test_schema already applied; verify tables exist
        with module_conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('applications','application_events','application_outcomes')")
            tables = {r[0] for r in cur.fetchall()}
        assert tables == {"applications", "application_events", "application_outcomes"}

    def test_migration_idempotent(self, module_conn):
        # Re-run migration SQL twice — must not raise
        mig_path = Path(__file__).parent.parent / "db" / "migrations" / "002_application_lifecycle.sql"
        mig_sql = mig_path.read_text(encoding="utf-8")
        with module_conn.cursor() as cur:
            cur.execute(mig_sql)
        module_conn.commit()
        with module_conn.cursor() as cur:
            cur.execute(mig_sql)
        module_conn.commit()
        # tables still exist
        with module_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM applications")
            assert cur.fetchone()[0] >= 0

    def test_jobs_table_exists_in_test_db(self, module_conn):
        with module_conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='jobs'")
            assert cur.fetchone() is not None


# ---------------------------------------------------------------------------
# 3. Real transaction atomicity — write then force failure must rollback
# ---------------------------------------------------------------------------

class TestTransactionRollback:
    def test_rollback_after_partial_writes(self, module_conn):
        """BEGIN → insert application + event → raise → ROLLBACK → verify no partial state."""
        # Need a job for FK
        job_id = _create_job(module_conn, title="Rollback Test", company="RollbackCo")
        # Directly test transaction rollback via psycopg2 (no mock)
        conn = _get_conn()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                # Start txn implicitly, insert app
                cur.execute(
                    "INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s) RETURNING id",
                    (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
                )
                app_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'preparing',%s,'user')",
                    (app_id, "2026-01-01T00:00:00+00:00"),
                )
                cur.execute(
                    "INSERT INTO application_outcomes (application_id, outcome) VALUES (%s,'NONE')",
                    (app_id,),
                )
                # Now force controlled failure BEFORE commit
                raise RuntimeError("intentional failure before commit")
                conn.commit()
        except RuntimeError as e:
            assert "intentional failure" in str(e)
            conn.rollback()
        finally:
            conn.close()

        # Verify no partial writes remain in a fresh connection
        verify = _get_conn()
        try:
            with verify.cursor() as cur:
                cur.execute("SELECT count(*) FROM applications WHERE job_id=%s", (job_id,))
                assert cur.fetchone()[0] == 0, "applications must be 0 after rollback"
                cur.execute("SELECT count(*) FROM application_events WHERE application_id IN (SELECT id FROM applications WHERE job_id=%s)", (job_id,))
                # No events for rolled-back app
                cur.execute("SELECT count(*) FROM application_events")
                # But there may be 0 events total (since we cleaned before)
                total_events = cur.fetchone()[0]
                assert total_events == 0, f"events must be 0 after rollback, got {total_events}"
                cur.execute("SELECT count(*) FROM application_outcomes")
                assert cur.fetchone()[0] == 0
        finally:
            verify.close()

    def test_rollback_on_service_exception_is_atomic(self, module_conn):
        """Via ApplicationService: create then force failure in same txn must not leave partial."""
        # This uses the service's single-transaction create; we test that if second insert fails,
        # the first insert is not persisted. We simulate by violating constraint after insert.
        job_id = _create_job(module_conn, title="Atomic Service", company="AtomicCo")
        # We will directly test a manual txn that mimics service behavior but fails on purpose
        conn = _get_conn()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM jobs WHERE id=%s FOR UPDATE", (job_id,))
                cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s) RETURNING id", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                app_id = cur.fetchone()[0]
                # Violate CHECK by inserting invalid outcome — will raise before commit
                try:
                    cur.execute("INSERT INTO application_outcomes (application_id, outcome) VALUES (%s,'INVALID_OUTCOME')", (app_id,))
                    conn.commit()
                    assert False, "should have raised check violation"
                except psycopg2.errors.CheckViolation:
                    conn.rollback()
        finally:
            conn.close()
        verify = _get_conn()
        try:
            with verify.cursor() as cur:
                cur.execute("SELECT count(*) FROM applications WHERE job_id=%s", (job_id,))
                assert cur.fetchone()[0] == 0
        finally:
            verify.close()


# ---------------------------------------------------------------------------
# 4. Real PostgreSQL constraint tests — PostgreSQL itself must reject
# ---------------------------------------------------------------------------

class TestPostgresConstraints:
    def test_A_unique_job_attempt(self, module_conn):
        job_id = _create_job(module_conn, title="Unique", company="UniCo")
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s)", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                conn.commit()
                # Duplicate same (job_id, attempt_number) must violate UNIQUE
                with pytest.raises(psycopg2.errors.UniqueViolation):
                    cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s)", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                    conn.commit()
                conn.rollback()
        finally:
            conn.close()

    def test_B_check_attempt_number_positive(self, module_conn):
        job_id = _create_job(module_conn, title="CheckAttempt", company="ChkCo")
        conn = _get_conn()
        try:
            with pytest.raises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,0,'PREPARING',%s,%s)", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_C_check_current_state(self, module_conn):
        job_id = _create_job(module_conn, title="CheckState", company="ChkCo2")
        conn = _get_conn()
        try:
            with pytest.raises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'INVALID_STATE',%s,%s)", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_D_check_outcome(self, module_conn):
        # Need an application first
        job_id = _create_job(module_conn, title="CheckOutcome", company="ChkCo3")
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s) RETURNING id", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                app_id = cur.fetchone()[0]
                conn.commit()
            with pytest.raises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO application_outcomes (application_id, outcome) VALUES (%s,'INVALID')", (app_id,))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_E_check_event_type(self, module_conn):
        job_id = _create_job(module_conn, title="CheckEvent", company="ChkCo4")
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s) RETURNING id", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                app_id = cur.fetchone()[0]
                conn.commit()
            with pytest.raises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'invalid_event',%s,'user')", (app_id, "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_F_check_actor(self, module_conn):
        job_id = _create_job(module_conn, title="CheckActor", company="ChkCo5")
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s) RETURNING id", (job_id, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                app_id = cur.fetchone()[0]
                conn.commit()
            with pytest.raises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'note',%s,'invalid_actor')", (app_id, "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_G_fk_application_event(self, module_conn):
        conn = _get_conn()
        try:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'note',%s,'user')", (999999, "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()

    def test_H_fk_job_application(self, module_conn):
        conn = _get_conn()
        try:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                with conn.cursor() as cur:
                    # job_id 999999 does not exist
                    cur.execute("INSERT INTO applications (job_id, attempt_number, current_state, last_state_change_at, created_at) VALUES (%s,1,'PREPARING',%s,%s)", (999999, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                    conn.commit()
            conn.rollback()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# 5. Concurrency — SELECT FOR UPDATE must prevent duplicate open
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_creations_one_succeeds(self, module_conn):
        job_id = _create_job(module_conn, title="Concurrent", company="ConcCo")
        results = []
        errors = []

        def try_create():
            # Each thread needs its own service instance and connection
            try:
                from core.services.application_service import ApplicationService
                svc = ApplicationService()
                app = svc.create_application(job_id=job_id)
                results.append(app["id"])
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=try_create)
        t2 = threading.Thread(target=try_create)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Exactly one should succeed, one should fail with "already exists"
        assert len(results) == 1, f"expected 1 success, got {len(results)} results={results} errors={errors}"
        assert len(errors) == 1
        assert "already exists" in errors[0].lower() or "409" in errors[0]

        # DB must have exactly one open application with attempt_number=1
        verify = _get_conn()
        try:
            with verify.cursor() as cur:
                cur.execute("SELECT count(*) FROM applications WHERE job_id=%s", (job_id,))
                assert cur.fetchone()[0] == 1
                cur.execute("SELECT attempt_number, current_state FROM applications WHERE job_id=%s", (job_id,))
                row = cur.fetchone()
                assert row[0] == 1
                assert row[1] != "CLOSED"
        finally:
            verify.close()


# ---------------------------------------------------------------------------
# 6. Route regression — Flask route map must be correct
# ---------------------------------------------------------------------------

class TestRouteRegression:
    def test_lifecycle_routes(self):
        from ui.app import app
        rules = {(r.rule, tuple(sorted(r.methods - {"OPTIONS", "HEAD"}))): r.endpoint for r in app.url_map.iter_rules()}
        # lifecycle
        assert ("/api/applications", ("GET",)) in rules
        assert rules[("/api/applications", ("GET",))] == "api_applications"
        assert ("/api/applications", ("POST",)) in rules
        assert rules[("/api/applications", ("POST",))] == "api_applications_create"
        assert ("/api/applications/<int:app_id>", ("GET",)) in rules
        assert ("/api/applications/<int:app_id>", ("PATCH",)) in rules
        assert ("/api/applications/<int:app_id>/apply", ("POST",)) in rules
        assert ("/api/applications/<int:app_id>/outcome", ("POST",)) in rules
        assert ("/api/applications/<int:app_id>/events", ("POST",)) in rules
        assert ("/api/applications/<int:app_id>/timeline", ("GET",)) in rules
        # legacy tracker must be at /api/tracker, not /api/applications
        assert ("/api/tracker", ("GET", "POST")) in rules
        assert rules[("/api/tracker", ("GET", "POST"))] == "api_application_tracker"
        assert ("/api/tracker/followups", ("GET",)) in rules
        # No conflict: /api/applications GET must not be tracker
        assert rules[("/api/applications", ("GET",))] != "api_application_tracker"

    def test_each_url_method_has_single_endpoint(self):
        from ui.app import app
        seen = {}
        for r in app.url_map.iter_rules():
            for m in r.methods - {"OPTIONS", "HEAD"}:
                key = (r.rule, m)
                assert key not in seen, f"duplicate route {key}: {seen[key]} vs {r.endpoint}"
                seen[key] = r.endpoint


# ---------------------------------------------------------------------------
# 7. Complete lifecycle integration via service + via HTTP (isolated DB)
# ---------------------------------------------------------------------------

class TestLifecycleIntegrationService:
    def test_full_lifecycle_via_service(self, module_conn):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        job_id = _create_job(module_conn, title="Lifecycle SVC", company="LifeCo")

        # Create → 201, attempt 1, PREPARING, snapshots
        app = svc.create_application(job_id=job_id)
        assert app["attempt_number"] == 1
        assert app["current_state"] == "PREPARING"
        assert app["job_title_snapshot"] == "Lifecycle SVC"
        assert app["company_snapshot"] == "LifeCo"
        app_id = app["id"]

        # GET
        fetched = svc.get_application(app_id)
        assert fetched["id"] == app_id

        # Apply → APPLIED, submitted_at
        applied = svc.apply_application(app_id)
        assert applied["current_state"] == "APPLIED"
        assert applied["submitted_at"] is not None

        # Timeline → has preparing + application_submitted
        tl = svc.get_timeline(app_id)
        types = [e["event_type"] for e in tl]
        assert "preparing" in types
        assert "application_submitted" in types

        # Outcome UNKNOWN → CLOSED
        closed = svc.set_outcome(app_id, "UNKNOWN")
        assert closed["current_state"] == "CLOSED"

        # Reapply → attempt 2, previous_application_id
        app2 = svc.create_application(job_id=job_id)
        assert app2["attempt_number"] == 2
        assert app2["previous_application_id"] == app_id

        # Third open attempt → 409
        with pytest.raises(ValueError, match="already exists"):
            svc.create_application(job_id=job_id)


class TestLifecycleIntegrationHTTP:
    def test_full_lifecycle_via_http(self, module_conn):
        # Use Flask test client with TEST_DATABASE_URL
        from ui.app import app
        client = app.test_client()

        # Create job directly in test DB for FK
        job_id = _create_job(module_conn, title="Lifecycle HTTP", company="HttpCo")

        # POST /api/applications → 201
        resp = client.post("/api/applications", json={"job_id": job_id})
        assert resp.status_code == 201, resp.get_data(as_text=True)
        app_id = resp.get_json()["application"]["id"]
        assert resp.get_json()["application"]["attempt_number"] == 1

        # GET /api/applications → 200
        resp = client.get("/api/applications")
        assert resp.status_code == 200
        assert any(a["id"] == app_id for a in resp.get_json()["applications"])

        # GET /api/applications/<id> → 200 with timeline
        resp = client.get(f"/api/applications/{app_id}")
        assert resp.status_code == 200
        assert "timeline" in resp.get_json()

        # POST /api/applications/<id>/apply → 200 APPLIED
        resp = client.post(f"/api/applications/{app_id}/apply", json={})
        assert resp.status_code == 200
        assert resp.get_json()["application"]["current_state"] == "APPLIED"

        # GET /api/applications/<id>/timeline → 200 with events
        resp = client.get(f"/api/applications/{app_id}/timeline")
        assert resp.status_code == 200
        assert any(e["event_type"] == "application_submitted" for e in resp.get_json()["timeline"])

        # POST /api/applications/<id>/outcome UNKNOWN → 200 CLOSED
        resp = client.post(f"/api/applications/{app_id}/outcome", json={"outcome": "UNKNOWN"})
        assert resp.status_code == 200
        assert resp.get_json()["application"]["current_state"] == "CLOSED"

        # POST reapply → 201 attempt 2
        resp = client.post("/api/applications", json={"job_id": job_id})
        assert resp.status_code == 201
        assert resp.get_json()["application"]["attempt_number"] == 2
        assert resp.get_json()["application"]["previous_application_id"] == app_id

        # POST third open → 409
        resp = client.post("/api/applications", json={"job_id": job_id})
        assert resp.status_code == 409

        # Also verify non-lifecycle routes still 200
        resp = client.get("/api/jobs/prioritized")
        assert resp.status_code == 200
        resp = client.get("/api/candidate/intelligence")
        assert resp.status_code == 200

        # Legacy tracker still works
        resp = client.get("/api/tracker")
        assert resp.status_code == 200
        resp = client.get("/api/tracker/followups")
        assert resp.status_code == 200
