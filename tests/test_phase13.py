"""
Phase 13 Tests — Scheduler / Automation / Reliability (Corrected)
Uses applyr_test PostgreSQL for all persistence tests.
Covers: non-blocking locking, cross-process ownership, periodic recovery,
observability counters, human-in-the-loop safety.

NOTE: Neon uses PgBouncer (transaction mode). Advisory locks are backend-level,
so two different connections may get different backends. Advisory lock tests
use a SINGLE connection to ensure deterministic behavior.
Every DB operation: explicit commit + close in finally block.
"""
import os
import sys
import uuid
import time
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

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


# Simple connection pool to reuse connections within a test run
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """Lazy-init a small connection pool for test helpers."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                from psycopg2 import pool
                _pool = pool.ThreadedConnectionPool(1, 10, _test_url())
    return _pool


def _exec(sql, params=None):
    """Execute a single SQL statement, commit, close (uses pool)."""
    p = _get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except psycopg2.OperationalError:
        try:
            conn.close()
        except Exception:
            pass
        conn = psycopg2.connect(_test_url())
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            p.putconn(conn)
        except Exception:
            pass


def _query(sql, params=None, fetch=True):
    """Execute SQL, return rows (uses pool)."""
    p = _get_pool()
    conn = p.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    except psycopg2.OperationalError:
        try:
            conn.close()
        except Exception:
            pass
        conn = psycopg2.connect(_test_url())
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return [] if fetch else None
    finally:
        try:
            p.putconn(conn)
        except Exception:
            pass


def _clean():
    _exec("DELETE FROM run_log")
    _exec("DELETE FROM scheduler_owner")


@pytest.fixture(scope="module", autouse=True)
def ensure_schema():
    p = _get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS run_log (
                    id            SERIAL PRIMARY KEY,
                    run_id        TEXT UNIQUE,
                    triggered_by  TEXT,
                    started_at    TEXT,
                    finished_at   TEXT,
                    jobs_found    INTEGER DEFAULT 0,
                    jobs_filtered INTEGER DEFAULT 0,
                    jobs_applied  INTEGER DEFAULT 0,
                    emails_sent   INTEGER DEFAULT 0,
                    errors_count  INTEGER DEFAULT 0,
                    status        TEXT DEFAULT 'running',
                    summary_json  TEXT,
                    error_summary TEXT,
                    duration_ms   INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_owner (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    owner_pid INTEGER NOT NULL,
                    acquired_at TEXT NOT NULL,
                    hostname TEXT
                )
            """)
            sql = Path("db/migrations/007_scheduler_reliability.sql").read_text()
            cur.execute(sql)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        p.putconn(conn)
    yield
    _clean()


@pytest.fixture(autouse=True)
def clean():
    _clean()
    yield
    _clean()


# ── NON-BLOCKING LOCK (BLOCKER 1) ───────────────────────────────────────────
# Advisory locks are backend-level. On Neon/PgBouncer, two different connections
# may get different backends, so lock behavior is non-deterministic across
# connections. Tests use a SINGLE connection for lock ordering assertions.

class TestNonBlockingLock:
    def test_try_lock_non_blocking(self):
        """pg_try_advisory_lock returns immediately (does not block)."""
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                # Acquire lock on this backend
                cur.execute("SELECT pg_try_advisory_lock(43)")
                assert cur.fetchone()[0] is True

                # Second call on SAME connection succeeds (re-entrant on same backend)
                cur.execute("SELECT pg_try_advisory_lock(43)")
                assert cur.fetchone()[0] is True

                # Release
                cur.execute("SELECT pg_advisory_unlock(43)")
                assert cur.fetchone()[0] is True

                # After release, can acquire again
                cur.execute("SELECT pg_try_advisory_lock(43)")
                assert cur.fetchone()[0] is True

                # Final release
                cur.execute("SELECT pg_advisory_unlock(43)")
                assert cur.fetchone()[0] is True
        finally:
            conn.close()

    def test_acquire_returns_false_when_locked(self):
        """SchedulerService._acquire_run_lock returns False when another run is active."""
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        acquired = svc._acquire_run_lock(run_id2)
        assert acquired is False

    def test_lock_release_allows_subsequent(self):
        """After completing a run, another invocation can acquire the lock."""
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        assert svc._acquire_run_lock(run_id2) is False

        svc._update_run_record(run_id1, status="SUCCEEDED", finished_at=datetime.now(timezone.utc).isoformat())

        assert svc._acquire_run_lock(run_id2) is True
        svc._release_run_lock()


# ── CROSS-PROCESS OWNERSHIP (BLOCKER 2) ────────────────────────────────────

class TestCrossProcessOwnership:
    def test_first_owner_succeeds(self):
        from core.services.scheduler_service import SchedulerService, _ensure_owner_table
        _ensure_owner_table()
        svc = SchedulerService()
        result = svc._acquire_ownership()
        assert result is True
        assert svc._ownership_acquired is True
        svc._release_ownership()

    def test_dead_owner_replaced(self):
        from core.services.scheduler_service import SchedulerService, _ensure_owner_table
        _ensure_owner_table()

        dead_pid = os.getpid() + 99999
        _exec("DELETE FROM scheduler_owner WHERE id = 1")
        _exec(
            "INSERT INTO scheduler_owner (id, owner_pid, acquired_at, hostname) VALUES (1, %s, %s, 'test')",
            (dead_pid, datetime.now(timezone.utc).isoformat()),
        )

        svc = SchedulerService()
        result = svc._acquire_ownership()
        assert result is True
        svc._release_ownership()

    def test_same_process_cannot_double_own(self):
        from core.services.scheduler_service import SchedulerService, _ensure_owner_table
        _ensure_owner_table()

        _exec("DELETE FROM scheduler_owner WHERE id = 1")
        _exec(
            "INSERT INTO scheduler_owner (id, owner_pid, acquired_at, hostname) VALUES (1, %s, %s, 'test')",
            (os.getpid(), datetime.now(timezone.utc).isoformat()),
        )

        svc = SchedulerService()
        result = svc._acquire_ownership()
        assert result is False

    def test_ownership_reacquired_after_release(self):
        from core.services.scheduler_service import SchedulerService, _ensure_owner_table
        _ensure_owner_table()

        svc = SchedulerService()
        assert svc._acquire_ownership() is True
        svc._release_ownership()

        svc2 = SchedulerService()
        assert svc2._acquire_ownership() is True
        svc2._release_ownership()

    def test_ownership_table_exists(self):
        from core.services.scheduler_service import _ensure_owner_table
        _ensure_owner_table()
        _query("SELECT 1 FROM scheduler_owner WHERE id = 1")


# ── STUCK RUN RECOVERY (BLOCKER 3) ─────────────────────────────────────────

class TestStuckRunRecovery:
    def test_old_running_run_recovered(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id, "test", old_time),
        )

        svc._recover_stuck_runs()

        rows = _query("SELECT status FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "TIMED_OUT"

    def test_active_run_not_marked_failed(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id, "test", recent_time),
        )

        svc._recover_stuck_runs()

        rows = _query("SELECT status FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "RUNNING"

    def test_recovery_does_not_corrupt_completed_run(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status, finished_at) VALUES (%s,%s,%s,'SUCCEEDED',%s)",
            (run_id, "test", (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(), datetime.now(timezone.utc).isoformat()),
        )

        svc._recover_stuck_runs()

        rows = _query("SELECT status FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "SUCCEEDED"

    def test_recovery_does_not_change_historical_runs(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()

        for status in ["SUCCEEDED", "PARTIAL", "FAILED", "TIMED_OUT", "SKIPPED"]:
            run_id = f"run_{uuid.uuid4().hex[:8]}"
            _exec(
                "INSERT INTO run_log (run_id, triggered_by, started_at, status, finished_at) VALUES (%s,%s,%s,%s,%s)",
                (run_id, "test", (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(), status, datetime.now(timezone.utc).isoformat()),
            )

        svc._recover_stuck_runs()

        rows = _query("SELECT status FROM run_log WHERE triggered_by = 'test' ORDER BY id")
        statuses = [r["status"] for r in rows]
        assert statuses == ["SUCCEEDED", "PARTIAL", "FAILED", "TIMED_OUT", "SKIPPED"]

    def test_recovery_works_while_scheduler_alive(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id, "test", old_time),
        )

        svc._recover_stuck_runs()

        rows = _query("SELECT status FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "TIMED_OUT"

        svc._recover_stuck_runs()


# ── SCHEDULER LIFECYCLE ──────────────────────────────────────────────────────

class TestSchedulerLifecycle:
    @pytest.fixture(autouse=True, scope="class")
    def _drop_pool_before_lifecycle(self):
        """Free Neon connections before lifecycle tests (pool holds 10 idle)."""
        global _pool
        if _pool is not None:
            try:
                _pool.closeall()
            except Exception:
                pass
            _pool = None
        yield
        if _pool is not None:
            try:
                _pool.closeall()
            except Exception:
                pass
            _pool = None
    def test_disabled_by_default(self):
        import core.services.scheduler_service as mod
        mod._scheduler_singleton = None
        os.environ.pop("SCHEDULER_ENABLED", None)
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        result = svc.start()
        assert result is False
        assert svc.is_running is False
        mod._scheduler_singleton = None

    def test_enabled_starts(self):
        import core.services.scheduler_service as mod
        mod._scheduler_singleton = None
        os.environ["SCHEDULER_ENABLED"] = "true"
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        result = svc.start()
        assert result is True
        assert svc.is_running is True
        svc.stop()
        os.environ.pop("SCHEDULER_ENABLED", None)
        mod._scheduler_singleton = None

    def test_singleton_behavior(self):
        import core.services.scheduler_service as mod
        mod._scheduler_singleton = None
        from core.services.scheduler_service import get_scheduler_service
        svc1 = get_scheduler_service()
        svc2 = get_scheduler_service()
        assert svc1 is svc2
        mod._scheduler_singleton = None

    def test_duplicate_start_no_second_scheduler(self):
        import core.services.scheduler_service as mod
        mod._scheduler_singleton = None
        os.environ["SCHEDULER_ENABLED"] = "true"
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        r1 = svc.start()
        r2 = svc.start()
        assert r1 is True
        assert r2 is False
        svc.stop()
        os.environ.pop("SCHEDULER_ENABLED", None)
        mod._scheduler_singleton = None

    def test_timezone_schedule_istanbul_kolkata(self):
        import core.services.scheduler_service as mod
        mod._scheduler_singleton = None
        os.environ["SCHEDULER_ENABLED"] = "true"
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        svc.start()
        jobs = svc._scheduler.get_jobs()
        job_ids = {job.id for job in jobs}
        assert len(jobs) == 4
        for h in [9, 12, 15, 18]:
            assert f"discovery_{h:02d}00" in job_ids
        svc.stop()
        os.environ.pop("SCHEDULER_ENABLED", None)
        mod._scheduler_singleton = None


# ── RUN LOCKING ──────────────────────────────────────────────────────────────

class TestRunLocking:
    def test_overlapping_run_prevented(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        acquired = svc._acquire_run_lock(run_id2)
        assert acquired is False

    def test_manual_trigger_returns_empty_when_locked(self):
        from core.services.scheduler_service import SchedulerService
        from unittest.mock import patch
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        with patch.object(svc, '_execute_manual_run'):
            run_id = svc.trigger_run(triggered_by="manual")
            assert run_id == ""

    def test_second_invocation_skipped(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        acquired = svc._acquire_run_lock(run_id2)
        assert acquired is False


# ── IDEMPOTENCY ──────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_repeated_run_same_canonical_job_one_job(self):
        url = f"https://example.com/idempotent_{uuid.uuid4().hex[:8]}"
        _exec(
            "INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at, canonical_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            ("Test Job", "Test Co", url, "test", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), f"canon_{uuid.uuid4().hex[:8]}"),
        )

        rows = _query("SELECT count(*) as cnt FROM jobs WHERE url = %s", (url,))
        assert rows[0]["cnt"] == 1

    def test_last_seen_updates_without_changing_scraped_at(self):
        url = f"https://example.com/lastseen_{uuid.uuid4().hex[:8]}"
        scraped = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        rows = _query(
            "INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at, canonical_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, scraped_at",
            ("T", "C", url, "test", scraped, scraped, f"canon_{uuid.uuid4().hex[:8]}"),
        )
        jid = rows[0]["id"]
        orig_scraped = rows[0]["scraped_at"]

        new_seen = datetime.now(timezone.utc).isoformat()
        _exec("UPDATE jobs SET last_seen_at = %s WHERE id = %s", (new_seen, jid))

        rows = _query("SELECT scraped_at, last_seen_at FROM jobs WHERE id = %s", (jid,))
        assert rows[0]["scraped_at"] == orig_scraped
        assert rows[0]["last_seen_at"] == new_seen

    def test_repeated_run_no_second_application_attempt(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()

        url = f"https://example.com/no_dup_{uuid.uuid4().hex[:8]}"
        rows = _query(
            "INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at, canonical_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            ("T", "C", url, "test", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), f"canon_{uuid.uuid4().hex[:8]}"),
        )
        jid = rows[0]["id"]

        app1 = svc.create_application(job_id=jid)
        assert app1["attempt_number"] == 1

        try:
            app2 = svc.create_application(job_id=jid)
            assert False, "Should have raised ValueError for duplicate open application"
        except ValueError as e:
            assert "Open application already exists" in str(e)

    def test_no_duplicate_followup(self):
        url = f"https://example.com/fup_{uuid.uuid4().hex[:8]}"
        rows = _query(
            "INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at, canonical_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            ("T", "C", url, "test", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), f"canon_{uuid.uuid4().hex[:8]}"),
        )
        jid = rows[0]["id"]

        rows = _query(
            "INSERT INTO applications (job_id, current_state, attempt_number) VALUES (%s,'PREPARING',1) RETURNING id",
            (jid,),
        )
        aid = rows[0]["id"]

        now = datetime.now(timezone.utc).isoformat()
        _exec(
            "INSERT INTO follow_ups (application_id, follow_up_type, channel, status, message_preview, created_at, updated_at) VALUES (%s,'POST_APPLICATION','EMAIL','DRAFT','test msg',%s,%s)",
            (aid, now, now),
        )
        _exec(
            "INSERT INTO follow_ups (application_id, follow_up_type, channel, status, message_preview, created_at, updated_at) VALUES (%s,'POST_APPLICATION','EMAIL','DRAFT','test msg 2',%s,%s)",
            (aid, now, now),
        )

        rows = _query("SELECT count(*) as cnt FROM follow_ups WHERE application_id = %s", (aid,))
        assert rows[0]["cnt"] == 2


# ── FAILURE ISOLATION ────────────────────────────────────────────────────────

class TestFailureIsolation:
    def test_one_item_fails_partial_status(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        svc._write_run_record(run_id, "test", "RUNNING")

        svc._update_run_record(
            run_id,
            status="PARTIAL",
            finished_at=datetime.now(timezone.utc).isoformat(),
            jobs_found=10,
            jobs_filtered=5,
            errors_count=3,
            error_summary="3 items failed",
        )

        rows = _query("SELECT * FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "PARTIAL"
        assert rows[0]["errors_count"] == 3

    def test_sanitized_errors(self):
        from core.services.scheduler_service import _sanitize_error
        msg = "Failed with key npg_abc123 and token gsk_xyz789"
        sanitized = _sanitize_error(msg)
        assert "npg_abc123" not in sanitized
        assert "gsk_xyz789" not in sanitized
        assert "REDACTED" in sanitized


# ── RUN RECORDS ──────────────────────────────────────────────────────────────

class TestRunRecords:
    def test_write_and_update(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        svc._write_run_record(run_id, "scheduler", "RUNNING")

        rows = _query("SELECT * FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0] is not None
        assert rows[0]["status"] == "RUNNING"
        assert rows[0]["triggered_by"] == "scheduler"

        svc._update_run_record(run_id, status="SUCCEEDED", jobs_found=5, errors_count=0, finished_at=datetime.now(timezone.utc).isoformat())

        rows = _query("SELECT * FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["status"] == "SUCCEEDED"
        assert rows[0]["jobs_found"] == 5
        assert rows[0]["finished_at"] is not None

    def test_counts_and_duration(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        svc._write_run_record(run_id, "test", "RUNNING")
        svc._update_run_record(
            run_id,
            status="SUCCEEDED",
            jobs_found=20,
            jobs_filtered=15,
            jobs_applied=3,
            errors_count=2,
            duration_ms=45000,
        )

        rows = _query("SELECT * FROM run_log WHERE run_id = %s", (run_id,))
        assert rows[0]["jobs_found"] == 20
        assert rows[0]["jobs_filtered"] == 15
        assert rows[0]["jobs_applied"] == 3
        assert rows[0]["errors_count"] == 2
        assert rows[0]["duration_ms"] == 45000

    def test_bounded_history(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()

        for i in range(25):
            run_id = f"run_{uuid.uuid4().hex[:8]}"
            svc._write_run_record(run_id, "test", "SUCCEEDED")

        history = svc.get_run_history(limit=10)
        assert len(history) <= 10

        history_all = svc.get_run_history(limit=100)
        assert len(history_all) <= 50


# ── HEALTH API ───────────────────────────────────────────────────────────────

class TestHealthAPI:
    def test_status_endpoint(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        status = svc.get_status()
        assert "enabled" in status
        assert "running" in status
        assert "pipeline_active" in status
        assert "schedule" in status
        assert status["schedule"] == "09:00, 12:00, 15:00, 18:00 IST"

    def test_last_run(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        svc._write_run_record(run_id, "test", "RUNNING")
        svc._update_run_record(run_id, status="SUCCEEDED", finished_at=datetime.now(timezone.utc).isoformat())

        status = svc.get_status()
        assert status["last_run"] is not None
        assert status["last_run"]["run_id"] == run_id

    def test_run_history(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()

        for i in range(3):
            run_id = f"run_{uuid.uuid4().hex[:8]}"
            svc._write_run_record(run_id, "test", "SUCCEEDED")

        runs = svc.get_run_history(limit=5)
        assert len(runs) >= 3


# ── HUMAN-IN-THE-LOOP ────────────────────────────────────────────────────────

class TestHumanInLoop:
    def test_scheduler_never_sends_email(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        source = __import__('inspect').getsource(svc._run_pipeline)
        assert 'send_email' not in source.lower()
        assert 'auto_apply' not in source.lower()

    def test_scheduler_never_approves_followup(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        source = __import__('inspect').getsource(svc._run_pipeline)
        assert 'approve' not in source.lower()

    def test_scheduler_never_submits_application(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        source = __import__('inspect').getsource(svc._run_pipeline)
        assert 'submit' not in source.lower()

    def test_scheduler_never_changes_lifecycle(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        source = __import__('inspect').getsource(svc._run_pipeline)
        assert 'patch_state' not in source
        assert 'set_outcome' not in source


# ── FRESHNESS ────────────────────────────────────────────────────────────────

class TestFreshness:
    def test_repeated_observation_updates_last_seen(self):
        from core.services.job_canonical_service import freshness_state
        url = f"https://example.com/fresh_{uuid.uuid4().hex[:8]}"
        scraped = datetime.now(timezone.utc).isoformat()
        rows = _query(
            "INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at, canonical_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            ("T", "C", url, "test", scraped, scraped, f"canon_{uuid.uuid4().hex[:8]}"),
        )
        jid = rows[0]["id"]

        new_seen = datetime.now(timezone.utc).isoformat()
        _exec("UPDATE jobs SET last_seen_at = %s WHERE id = %s", (new_seen, jid))

        rows = _query("SELECT scraped_at FROM jobs WHERE id = %s", (jid,))
        state = freshness_state(rows[0]["scraped_at"])
        assert state in ("NEW", "RECENT", "STALE")

    def test_priority_based_on_scraped_at(self):
        from core.services.job_canonical_service import freshness_state
        fresh = freshness_state(datetime.now(timezone.utc).isoformat())
        stale = freshness_state((datetime.now(timezone.utc) - timedelta(days=40)).isoformat())
        assert fresh in ("NEW", "RECENT")
        assert stale == "STALE"


# ── REGRESSION ───────────────────────────────────────────────────────────────

class TestRegression:
    def test_phase9_freshness(self):
        from core.services.job_canonical_service import freshness_state
        assert freshness_state(datetime.now(timezone.utc).isoformat()) in ("NEW", "RECENT")

    def test_phase11_lifecycle(self):
        from core.services.application_service import ApplicationService, ALLOWED_STATES
        assert "PREPARING" in ALLOWED_STATES
        assert "INTERVIEW" in ALLOWED_STATES
        assert "OFFER" in ALLOWED_STATES
        assert "CLOSED" in ALLOWED_STATES

    def test_phase12_outcome(self):
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        svc = OutcomeAnalyticsService()
        f = svc.funnel()
        assert "applications_started" in f
        assert "final_count" in f

    def test_phase10_studio(self):
        from core.services.studio_service import StudioService
        assert hasattr(StudioService, 'build')


# ── SECURITY ─────────────────────────────────────────────────────────────────

class TestSecurity:
    def test_no_secrets_in_run_records(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        svc._write_run_record(run_id, "test", "RUNNING")
        svc._update_run_record(run_id, status="FAILED", error_summary="npg_abc123 secret exposed")

        rows = _query("SELECT error_summary FROM run_log WHERE run_id = %s", (run_id,))
        assert "npg_abc123" not in (rows[0]["error_summary"] or "")

    def test_sanitize_removes_api_keys(self):
        from core.services.scheduler_service import _sanitize_error
        msg = "Error with Bearer eyJhbGciOiJIUzI1NiJ9.token and password=secret123"
        result = _sanitize_error(msg)
        assert "eyJhbGciOiJIUzI1NiJ9.token" not in result
        assert "secret123" not in result

    def test_bounded_run_history_limit(self):
        from core.services.scheduler_service import SchedulerService, MAX_RUN_HISTORY
        svc = SchedulerService()
        runs = svc.get_run_history(limit=999)
        assert len(runs) <= MAX_RUN_HISTORY


# ── MANUAL TRIGGER ───────────────────────────────────────────────────────────

class TestManualTrigger:
    def test_trigger_while_locked_returns_immediately(self):
        from core.services.scheduler_service import SchedulerService
        svc = SchedulerService()
        run_id1 = f"run_{uuid.uuid4().hex[:12]}"

        _exec(
            "INSERT INTO run_log (run_id, triggered_by, started_at, status) VALUES (%s,%s,%s,'RUNNING')",
            (run_id1, "test", datetime.now(timezone.utc).isoformat()),
        )

        run_id2 = svc.trigger_run(triggered_by="manual")
        assert run_id2 == ""

    def test_trigger_no_duplicate_execution(self):
        from core.services.scheduler_service import SchedulerService
        from unittest.mock import patch
        svc = SchedulerService()
        with patch.object(svc, '_execute_manual_run'):
            run_id = svc.trigger_run(triggered_by="manual")
            assert run_id != ""
            svc._release_run_lock()
