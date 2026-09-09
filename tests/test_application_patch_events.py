"""P1 regression: PATCH state transitions must record valid event_type values.

Root cause fixed: patch_state() inserted new_state.lower() directly as
event_type, so READY_TO_APPLY/APPLIED violated the application_events
CHECK constraint (HTTP 500). States now map to the existing event
vocabulary (READY_TO_APPLY -> application_started, APPLIED ->
application_submitted); the DB constraint is unchanged.

All DB access uses the disposable TEST database. No production writes.
"""
import os
import uuid
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


def _ensure_schema(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    try:
        with conn.cursor() as cur:
            cur.execute(Path("db/migrations/002_application_lifecycle.sql").read_text())
            cur.execute(Path("db/migrations/005_interview_followup.sql").read_text())
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
            cur.execute("DELETE FROM application_events WHERE application_id IN (SELECT id FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE url LIKE 'https://patch-ev%'))")
            cur.execute("DELETE FROM application_outcomes WHERE application_id IN (SELECT id FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE url LIKE 'https://patch-ev%'))")
            cur.execute("DELETE FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE url LIKE 'https://patch-ev%')")
            cur.execute("DELETE FROM jobs WHERE url LIKE 'https://patch-ev%'")
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
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    yield
    _clean(mod_conn)


def _make_job(mod_conn, suffix=None):
    url = f"https://patch-ev.example.com/{suffix or uuid.uuid4().hex[:8]}"
    with mod_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("INSERT INTO jobs (title, company, url, location, jd_text, scraped_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                    ("Engineer", "Acme", url, "Remote", "Python", "2026-01-01T00:00:00Z"))
        jid = cur.fetchone()["id"]
    mod_conn.commit()
    return jid


def _constraint_allows(mod_conn, event_type):
    with mod_conn.cursor() as cur:
        cur.execute("""SELECT pg_get_constraintdef(oid) FROM pg_constraint
                       WHERE conrelid='application_events'::regclass AND conname='application_events_event_type_check'""")
        row = cur.fetchone()
        assert row, "event_type CHECK constraint must exist (integrity must not be weakened)"
        return f"'{event_type}'" in row[0]


def test_01_patch_preparing_to_ready_returns_success(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    out = svc.patch_state(app_row["id"], "READY_TO_APPLY")
    assert out["current_state"] == "READY_TO_APPLY"


def test_02_state_is_ready_to_apply(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    fetched = svc.patch_state(app_row["id"], "READY_TO_APPLY")
    reread = svc.get_application(app_row["id"])
    assert reread["current_state"] == "READY_TO_APPLY"
    assert fetched["current_state"] == "READY_TO_APPLY"


def test_03_ready_event_exists(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    types = [e["event_type"] for e in svc.get_timeline(app_row["id"])]
    assert "application_started" in types
    assert "ready_to_apply" not in types


def test_04_ready_event_satisfies_check(mod_conn):
    from core.services.application_service import ALLOWED_EVENT_TYPES, get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    assert "application_started" in ALLOWED_EVENT_TYPES
    assert _constraint_allows(mod_conn, "application_started")


def test_05_patch_ready_to_applied_returns_success(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    out = svc.patch_state(app_row["id"], "APPLIED")
    assert out["current_state"] == "APPLIED"


def test_06_state_is_applied(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    svc.patch_state(app_row["id"], "APPLIED")
    assert svc.get_application(app_row["id"])["current_state"] == "APPLIED"


def test_07_applied_event_is_valid(mod_conn):
    from core.services.application_service import ALLOWED_EVENT_TYPES, get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    svc.patch_state(app_row["id"], "APPLIED")
    types = [e["event_type"] for e in svc.get_timeline(app_row["id"])]
    assert "application_submitted" in types
    assert "applied" not in types
    assert "application_submitted" in ALLOWED_EVENT_TYPES
    assert _constraint_allows(mod_conn, "application_submitted")


def test_08_no_check_violation(mod_conn):
    from core.services.application_service import get_application_service
    import psycopg2.errors
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    try:
        svc.patch_state(app_row["id"], "READY_TO_APPLY")
        svc.patch_state(app_row["id"], "APPLIED")
    except psycopg2.errors.CheckViolation:
        pytest.fail("CHECK violation: lifecycle event mapping still invalid")


def test_09_rollback_on_failure(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    before_state = svc.get_application(app_row["id"])["current_state"]
    before_events = len(svc.get_timeline(app_row["id"]))
    with pytest.raises(ValueError):
        svc.patch_state(app_row["id"], "INTERVIEW")  # invalid from PREPARING
    assert svc.get_application(app_row["id"])["current_state"] == before_state
    assert len(svc.get_timeline(app_row["id"])) == before_events


def test_10_invalid_transition_rejected(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    with pytest.raises(ValueError):
        svc.patch_state(app_row["id"], "OFFER")  # PREPARING -> OFFER not allowed
    with pytest.raises(ValueError):
        svc.patch_state(app_row["id"], "NOT_A_STATE")


def test_11_repeat_patch_follows_contract(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    svc.patch_state(app_row["id"], "READY_TO_APPLY")
    n_events = len(svc.get_timeline(app_row["id"]))
    # Repeating the same state returns current row without appending a duplicate event
    out = svc.patch_state(app_row["id"], "READY_TO_APPLY")
    assert out["current_state"] == "READY_TO_APPLY"
    assert len(svc.get_timeline(app_row["id"])) == n_events


def test_12_duplicate_application_unchanged(mod_conn):
    from core.services.application_service import get_application_service
    svc = get_application_service()
    jid = _make_job(mod_conn)
    svc.create_application(job_id=jid)
    with pytest.raises(ValueError, match="already exists"):
        svc.create_application(job_id=jid)


def test_13_no_production_writes():
    from urllib.parse import urlparse
    from core.services.application_service import _resolve_database_url
    url = _resolve_database_url()
    # Database name is the URL path ("/neondb" also appears in the username
    # "neondb_owner", so compare the parsed path exactly like _is_production_db).
    db = urlparse(url).path.lstrip("/").split("?")[0].split("/")[0]
    assert db == "applyr_test", f"tests must run against the isolated DB, got: {db}"


def test_14_api_patch_contract(mod_conn):
    from ui.app import app
    from core.services.application_service import get_application_service
    svc = get_application_service()
    app_row = svc.create_application(job_id=_make_job(mod_conn))
    with app.test_client() as c:
        r = c.patch(f"/api/applications/{app_row['id']}", json={"state": "READY_TO_APPLY"})
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        body = r.get_json()
        assert body["success"] is True
        assert body["application"]["current_state"] == "READY_TO_APPLY"
        r2 = c.patch(f"/api/applications/{app_row['id']}", json={"state": "READY_TO_APPLY"})
        assert r2.status_code == 200
        # Sanitized failure contract: invalid state -> 400 without internals
        r3 = c.patch(f"/api/applications/{app_row['id']}", json={"state": "BOGUS"})
        assert r3.status_code == 400
        txt = r3.get_data(as_text=True)
        assert "Traceback" not in txt and "DATABASE_URL" not in txt and "npg_" not in txt
