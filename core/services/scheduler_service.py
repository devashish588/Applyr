"""
Phase 13 — Scheduler Service (Corrected)
Singleton scheduler with enable/disable, non-blocking run locking,
cross-process ownership, periodic stuck-run recovery, and structured
run records. Safe for single-user local deployment.

Locking: pg_try_advisory_lock (non-blocking)
Ownership: PostgreSQL scheduler_owner table (cross-process)
Recovery: Periodic thread while scheduler is alive
"""
from __future__ import annotations

import atexit
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from core.services.application_service import _resolve_database_url

# APScheduler import at module load to avoid lazy-import hang after many DB ops
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
STUCK_RUN_TIMEOUT_MINUTES = int(os.getenv("SCHEDULER_STUCK_TIMEOUT_MINUTES", "30"))
RECOVERY_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_RECOVERY_INTERVAL_SECONDS", "300"))
MAX_RUN_HISTORY = 50
SCHEDULER_OWNERSHIP_KEY = 42  # advisory lock key for scheduler ownership
RUN_LOCK_KEY = 43             # advisory lock key for run locking


_hostaddr_cache = None
_hostaddr_cache_lock = threading.Lock()

def _resolve_hostaddr(url: str):
    """Resolve Neon pooler hostname to IPv4 to avoid 60s IPv6 fallback."""
    global _hostaddr_cache
    if _hostaddr_cache is not None:
        return _hostaddr_cache
    with _hostaddr_cache_lock:
        if _hostaddr_cache is not None:
            return _hostaddr_cache
        try:
            import socket as _sock
            from urllib.parse import urlparse as _up
            host = _up(url).hostname
            if not host:
                return None
            ipv4 = _sock.getaddrinfo(host, 5432, _sock.AF_INET, _sock.SOCK_STREAM)
            if ipv4:
                _hostaddr_cache = ipv4[0][4][0]
                return _hostaddr_cache
        except Exception:
            pass
    return None


def _conn():
    url = _resolve_database_url()
    ha = _resolve_hostaddr(url)
    kwargs = dict(connect_timeout=10, keepalives=1, keepalives_idle=10, keepalives_interval=5, keepalives_count=3)
    if ha:
        kwargs["hostaddr"] = ha
    return psycopg2.connect(url, **kwargs)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sanitize_error(msg: str) -> str:
    """Remove secrets and sensitive data from error messages."""
    import re
    msg = re.sub(r"npg_[A-Za-z0-9]+", "[REDACTED]", msg)
    msg = re.sub(r"gsk_[A-Za-z0-9]+", "[REDACTED]", msg)
    msg = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", msg)
    msg = re.sub(r"password=[^\s&]+", "password=[REDACTED]", msg)
    msg = re.sub(r"DATABASE_URL=[^\s]+", "DATABASE_URL=[REDACTED]", msg)
    return msg[:500]


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _ensure_owner_table(_conn_obj=None):
    """Create scheduler_owner table if not exists. Reuses _conn_obj if provided (startup optimization)."""
    should_close = _conn_obj is None
    conn = _conn_obj if _conn_obj is not None else _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_owner (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    owner_pid INTEGER NOT NULL,
                    acquired_at TEXT NOT NULL,
                    hostname TEXT
                )
            """)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        if should_close:
            try:
                conn.close()
            except Exception:
                pass


class SchedulerService:
    """
    Singleton scheduler service.

    - Cross-process ownership via PostgreSQL (scheduler_owner table)
    - Non-blocking run locking via pg_try_advisory_lock
    - Periodic stuck-run recovery while scheduler is alive
    - Respects SCHEDULER_ENABLED env var
    - Uses Asia/Kolkata timezone (09:00, 12:00, 15:00, 18:00)
    """

    def __init__(self):
        self._scheduler = None
        self._started = False
        self._running = False
        self._last_run_id: Optional[str] = None
        self._recovery_thread: Optional[threading.Thread] = None
        self._stop_recovery = threading.Event()
        self._ownership_acquired = False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the scheduler. Returns True if started, False if disabled or already running."""
        if self._started:
            logger.info("Scheduler already started, skipping")
            return False

        enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
        if not enabled:
            logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
            return False

        if not _APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not installed, scheduler disabled")
            return False

        try:
            # Startup optimization: single DB connection for ensure+acquire+recover
            startup_conn = _conn()
            try:
                _ensure_owner_table(startup_conn)
                if not self._acquire_ownership(startup_conn):
                    logger.info("Another scheduler process already owns scheduling — skipping")
                    return False
                self._recover_stuck_runs(startup_conn)
            finally:
                try:
                    startup_conn.close()
                except Exception:
                    pass


            self._scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
            self._scheduler.configure(
                jobstores={"default": {"type": "memory"}},
                executors={"default": {"type": "threadpool", "max_workers": 1}},
                job_defaults={"coalesce": True, "max_instances": 1},
            )

            for hour in [9, 12, 15, 18]:
                self._scheduler.add_job(
                    self._run_pipeline,
                    trigger=CronTrigger(hour=hour, minute=0, timezone="Asia/Kolkata"),
                    id=f"discovery_{hour:02d}00",
                    name=f"Discovery {hour:02d}:00 IST",
                    replace_existing=True,
                )

            self._scheduler.start()
            self._started = True

            self._start_recovery_thread()
            atexit.register(self.stop)

            logger.info("Scheduler started with 4 daily runs: 09:00, 12:00, 15:00, 18:00 IST")
            return True

        except ImportError:
            logger.warning("APScheduler not installed, scheduler disabled")
            return False
        except Exception as e:
            logger.error("Scheduler start failed: %s", _sanitize_error(str(e)))
            return False

    def stop(self):
        """Stop the scheduler gracefully."""
        self._stop_recovery.set()
        if self._recovery_thread and self._recovery_thread.is_alive():
            self._recovery_thread.join(timeout=5)
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        self._release_ownership()
        self._started = False
        logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._started and self._scheduler is not None and self._scheduler.running

    @property
    def is_active(self) -> bool:
        return self._running

    # ── Cross-process ownership ──────────────────────────────────────────────

    def _acquire_ownership(self, _conn_obj=None) -> bool:
        """Try to become the scheduler owner. Non-blocking, cross-process safe."""
        import socket
        should_close = _conn_obj is None
        conn = _conn_obj if _conn_obj is not None else _conn()
        try:
            with conn.cursor() as cur:
                # Try advisory lock for ownership (non-blocking)
                cur.execute("SELECT pg_try_advisory_lock(%s)", (SCHEDULER_OWNERSHIP_KEY,))
                result = cur.fetchone()
                if not result or not result[0]:
                    return False

                # Check if existing owner is alive
                cur.execute("SELECT owner_pid, hostname FROM scheduler_owner WHERE id = 1")
                row = cur.fetchone()
                if row:
                    old_pid = row[0]
                    # Check if old process is still alive (best-effort on same host)
                    try:
                        os.kill(old_pid, 0)
                        # Process still alive — we cannot take ownership
                        cur.execute("SELECT pg_advisory_unlock(%s)", (SCHEDULER_OWNERSHIP_KEY,))
                        conn.commit()
                        return False
                    except (OSError, ProcessLookupError):
                        # Old process dead — take ownership
                        pass

                cur.execute(
                    """INSERT INTO scheduler_owner (id, owner_pid, acquired_at, hostname)
                       VALUES (1, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE
                       SET owner_pid = EXCLUDED.owner_pid,
                           acquired_at = EXCLUDED.acquired_at,
                           hostname = EXCLUDED.hostname""",
                    (os.getpid(), _now(), socket.gethostname()),
                )
            conn.commit()
            self._ownership_acquired = True
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.error("Ownership acquire failed: %s", _sanitize_error(str(e)))
            return False
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    def _release_ownership(self):
        """Release scheduler ownership."""
        if not self._ownership_acquired:
            return
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM scheduler_owner WHERE id = 1 AND owner_pid = %s", (os.getpid(),))
                cur.execute("SELECT pg_advisory_unlock(%s)", (SCHEDULER_OWNERSHIP_KEY,))
            conn.commit()
            self._ownership_acquired = False
        except Exception:
            conn.rollback()
        finally:
            conn.close()

    # ── Pipeline execution ───────────────────────────────────────────────────

    def _run_pipeline(self):
        """Execute the discovery pipeline with non-blocking run locking."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        logger.info("Pipeline triggered: %s", run_id)

        lock_acquired = self._acquire_run_lock(run_id)
        if not lock_acquired:
            logger.info("Run skipped — another run is active: %s", run_id)
            self._write_run_record(run_id, "scheduler", "SKIPPED")
            return

        self._running = True
        self._last_run_id = run_id
        started_at = _now()
        self._write_run_record(run_id, "scheduler", "RUNNING", started_at=started_at)

        try:
            from pipeline.orchestrator import Orchestrator

            orchestrator = Orchestrator()
            results = orchestrator.run_full_pipeline(triggered_by="scheduler")

            items_found = results.get("jobs_found", 0)
            items_filtered = results.get("jobs_filtered", 0)
            items_applied = results.get("jobs_applied", 0)
            errors = results.get("errors", [])
            errors_count = len(errors)
            error_summary = _sanitize_error("; ".join(str(e) for e in errors[:5])) if errors else None

            status = "SUCCEEDED" if errors_count == 0 else "PARTIAL"

            self._update_run_record(
                run_id,
                status=status,
                finished_at=_now(),
                jobs_found=items_found,
                jobs_filtered=items_filtered,
                jobs_applied=items_applied,
                errors_count=errors_count,
                error_summary=error_summary,
            )

            logger.info(
                "Run %s completed: status=%s found=%d filtered=%d applied=%d errors=%d",
                run_id, status, items_found, items_filtered, items_applied, errors_count,
            )

        except Exception as e:
            self._update_run_record(
                run_id,
                status="FAILED",
                finished_at=_now(),
                error_summary=_sanitize_error(str(e)),
            )
            logger.error("Run %s failed: %s", run_id, _sanitize_error(str(e)))

        finally:
            self._running = False
            self._release_run_lock()

    # ── Run locking (non-blocking) ──────────────────────────────────────────

    def _acquire_run_lock(self, run_id: str) -> bool:
        """Non-blocking try to acquire run lock via pg_try_advisory_lock."""
        conn = _conn()
        try:
            with conn.cursor() as cur:
                # Check for existing RUNNING runs first
                cur.execute(
                    "SELECT id FROM run_log WHERE status = 'RUNNING' AND run_id != %s LIMIT 1",
                    (run_id,),
                )
                if cur.fetchone():
                    return False

                # Non-blocking advisory lock
                cur.execute("SELECT pg_try_advisory_lock(%s)", (RUN_LOCK_KEY,))
                result = cur.fetchone()
                if result and result[0]:
                    return True
                return False
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.error("Run lock acquire failed: %s", _sanitize_error(str(e)))
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _release_run_lock(self):
        """Release run advisory lock."""
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (RUN_LOCK_KEY,))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

    # ── Periodic stuck-run recovery ──────────────────────────────────────────

    def _start_recovery_thread(self):
        """Start background thread for periodic stuck-run recovery."""
        self._stop_recovery.clear()
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True,
            name="scheduler-recovery",
        )
        self._recovery_thread.start()

    def _recovery_loop(self):
        """Periodic recovery loop — runs while scheduler is alive."""
        while not self._stop_recovery.is_set():
            try:
                self._recover_stuck_runs()
            except Exception as e:
                logger.error("Recovery loop error: %s", _sanitize_error(str(e)))
            self._stop_recovery.wait(timeout=RECOVERY_INTERVAL_SECONDS)

    def _recover_stuck_runs(self, _conn_obj=None):
        """Mark old RUNNING runs as TIMED_OUT."""
        should_close = _conn_obj is None
        conn = _conn_obj if _conn_obj is not None else _conn()
        try:
            with conn.cursor() as cur:
                threshold = (datetime.now(timezone.utc) - timedelta(minutes=STUCK_RUN_TIMEOUT_MINUTES)).isoformat()
                cur.execute(
                    """UPDATE run_log
                       SET status = 'TIMED_OUT', finished_at = %s,
                           error_summary = 'Run exceeded timeout and was recovered'
                        WHERE status = 'RUNNING' AND started_at < %s""",
                    (_now(), threshold),
                )
                count = cur.rowcount
                conn.commit()
                if count > 0:
                    logger.info("Recovered %d stuck run(s)", count)
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.error("Stuck run recovery failed: %s", _sanitize_error(str(e)))
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    # ── Run records ──────────────────────────────────────────────────────────

    def _write_run_record(
        self,
        run_id: str,
        triggered_by: str,
        status: str,
        started_at: Optional[str] = None,
    ):
        """Create a run record."""
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO run_log (run_id, triggered_by, started_at, status)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (run_id) DO NOTHING""",
                    (run_id, triggered_by, started_at or _now(), status),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Write run record failed: %s", _sanitize_error(str(e)))
        finally:
            conn.close()

    def _update_run_record(self, run_id: str, **kwargs):
        """Update an existing run record."""
        if not kwargs:
            return
        if "error_summary" in kwargs and kwargs["error_summary"]:
            kwargs["error_summary"] = _sanitize_error(kwargs["error_summary"])
        fields = {k: v for k, v in kwargs.items()}
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [run_id]
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE run_log SET {set_clause} WHERE run_id = %s", values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Update run record failed: %s", _sanitize_error(str(e)))
        finally:
            conn.close()

    # ── Status / history ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        last_run = self._get_last_run()
        enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
        return {
            "enabled": enabled,
            "running": self.is_running,
            "pipeline_active": self._running,
            "last_run": last_run,
            "schedule": "09:00, 12:00, 15:00, 18:00 IST",
            "timezone": "Asia/Kolkata",
            "stuck_timeout_minutes": STUCK_RUN_TIMEOUT_MINUTES,
        }

    def get_run_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get bounded run history."""
        limit = min(max(1, limit), MAX_RUN_HISTORY)
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM run_log ORDER BY started_at DESC LIMIT %s",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error("Get run history failed: %s", _sanitize_error(str(e)))
            return []
        finally:
            conn.close()

    def _get_last_run(self) -> Optional[Dict[str, Any]]:
        """Get the most recent completed run."""
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM run_log
                       WHERE status IN ('SUCCEEDED','PARTIAL','FAILED','TIMED_OUT')
                       ORDER BY started_at DESC LIMIT 1"""
                )
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception:
            return None
        finally:
            conn.close()

    # ── Manual trigger ───────────────────────────────────────────────────────

    def trigger_run(self, triggered_by: str = "manual") -> str:
        """Manually trigger a pipeline run. Returns run_id, or empty if locked."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        lock_acquired = self._acquire_run_lock(run_id)
        if not lock_acquired:
            return ""

        self._running = True
        self._last_run_id = run_id
        started_at = _now()
        self._write_run_record(run_id, triggered_by, "RUNNING", started_at=started_at)

        thread = threading.Thread(
            target=self._execute_manual_run,
            args=(run_id, triggered_by),
            daemon=True,
        )
        thread.start()
        return run_id

    def _execute_manual_run(self, run_id: str, triggered_by: str):
        """Execute a manual pipeline run in background thread."""
        try:
            from pipeline.orchestrator import Orchestrator

            orchestrator = Orchestrator()
            results = orchestrator.run_full_pipeline(triggered_by=triggered_by)

            items_found = results.get("jobs_found", 0)
            items_filtered = results.get("jobs_filtered", 0)
            items_applied = results.get("jobs_applied", 0)
            errors = results.get("errors", [])
            errors_count = len(errors)
            error_summary = _sanitize_error("; ".join(str(e) for e in errors[:5])) if errors else None

            status = "SUCCEEDED" if errors_count == 0 else "PARTIAL"

            self._update_run_record(
                run_id,
                status=status,
                finished_at=_now(),
                jobs_found=items_found,
                jobs_filtered=items_filtered,
                jobs_applied=items_applied,
                errors_count=errors_count,
                error_summary=error_summary,
            )

        except Exception as e:
            self._update_run_record(
                run_id,
                status="FAILED",
                finished_at=_now(),
                error_summary=_sanitize_error(str(e)),
            )
        finally:
            self._running = False
            self._release_run_lock()


# ── Module-level singleton ───────────────────────────────────────────────────

_scheduler_singleton: Optional[SchedulerService] = None
_scheduler_lock = threading.Lock()


def get_scheduler_service() -> SchedulerService:
    """Get or create the singleton scheduler service (in-process guard)."""
    global _scheduler_singleton
    if _scheduler_singleton is None:
        with _scheduler_lock:
            if _scheduler_singleton is None:
                _scheduler_singleton = SchedulerService()
    return _scheduler_singleton


def init_scheduler() -> bool:
    """Initialize and start the scheduler singleton. Called from Flask startup."""
    svc = get_scheduler_service()
    return svc.start()
