"""
DB Client — AutoApply AI
PostgreSQL wrapper using psycopg2 with connection pooling.
Call get_db() anywhere to get a singleton instance.
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2 import pool, extras
from dotenv import load_dotenv

load_dotenv()

logger  = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "")
CACHE_DB = os.getenv("CACHE_DB_PATH", str(Path(__file__).parent.parent / "cache.db"))


class DBClient:
    _connection_pool = None
    _cache = {}
    _cache_ttl = 30  # seconds

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")
        self._init_disk_cache()
        self._init_pool()
        self._init_schema()
        self._warmup()

    # ── Local SQLite disk cache ────────────────────────────────────────────

    def _init_disk_cache(self):
        """Create the local SQLite cache database."""
        self._disk_db_path = CACHE_DB
        try:
            conn = sqlite3.connect(self._disk_db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at REAL
                )
            """)
            conn.commit()
            conn.close()
            logger.info("[db] Local disk cache ready at %s", self._disk_db_path)
        except Exception as e:
            logger.warning("[db] Failed to init disk cache (non-fatal): %s", e)
            self._disk_db_path = None

    def _disk_get(self, key: str, ttl: int = 60):
        """Read from local SQLite cache if within TTL."""
        if not self._disk_db_path:
            return None
        try:
            conn = sqlite3.connect(self._disk_db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
                (key, time.time())
            ).fetchone()
            conn.close()
            if row:
                return json.loads(row["value"])
        except Exception as e:
            logger.debug("[db] Disk cache read failed: %s", e)
        return None

    def _disk_set(self, key: str, value, ttl: int = 60):
        """Write to local SQLite cache."""
        if not self._disk_db_path:
            return
        try:
            conn = sqlite3.connect(self._disk_db_path)
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time() + ttl)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("[db] Disk cache write failed: %s", e)

    def _disk_invalidate(self, key: str = None):
        """Invalidate a cache key, or all if key is None."""
        if not self._disk_db_path:
            return
        try:
            conn = sqlite3.connect(self._disk_db_path)
            if key:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            else:
                conn.execute("DELETE FROM cache")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("[db] Disk cache invalidate failed: %s", e)

    def _warmup(self):
        """Ping the database — also starts a background keepalive thread."""
        try:
            conn = self._conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.commit()
            self._put_conn(conn)
            logger.info("[db] Connection pool warmed up")
        except Exception as e:
            logger.warning("[db] Warmup ping failed (non-fatal): %s", e)
        self._start_keepalive()

    def _start_keepalive(self):
        """Ping Neon every 120s to prevent serverless idle timeout."""
        import threading
        def _ping():
            while True:
                time.sleep(120)
                try:
                    conn = self._conn()
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    conn.commit()
                    self._put_conn(conn)
                except Exception:
                    pass
        t = threading.Thread(target=_ping, daemon=True)
        t.start()
        logger.debug("[db] Keepalive thread started (120s interval)")

    def _cache_get(self, key: str):
        """Return cached value if within TTL, else None."""
        entry = self._cache.get(key)
        if entry and (datetime.now() - entry["ts"]).seconds < self._cache_ttl:
            return entry["value"]
        return None

    def _cache_set(self, key: str, value):
        self._cache[key] = {"value": value, "ts": datetime.now()}

    def _cache_clear(self, key: str = None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def _init_pool(self):
        if DBClient._connection_pool is None:
            try:
                DBClient._connection_pool = pool.SimpleConnectionPool(
                    1, 10, dsn=self.database_url
                )
                logger.info("[db] PostgreSQL connection pool created")
            except Exception as e:
                logger.error(f"[db] Failed to create connection pool: {e}")
                raise

    def _conn(self):
        conn = DBClient._connection_pool.getconn()
        conn.autocommit = False
        return conn

    def _put_conn(self, conn):
        DBClient._connection_pool.putconn(conn)

    def _init_schema(self):
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                # Check if tables exist first — saves 7 round-trips on warm starts
                cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'jobs')")
                if cur.fetchone()[0]:
                    logger.debug("[db] Tables already exist, skipping schema init")
                    conn.commit()
                    return

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
                        summary_json  TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS emails (
                        id                SERIAL PRIMARY KEY,
                        job_id            INTEGER,
                        hr_email          TEXT,
                        subject           TEXT,
                        body_text         TEXT,
                        status            TEXT DEFAULT 'drafted',
                        resume_path       TEXT,
                        cover_letter_path TEXT,
                        created_at        TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_events (
                        id          SERIAL PRIMARY KEY,
                        run_id      TEXT NOT NULL,
                        timestamp   TEXT NOT NULL,
                        agent       TEXT,
                        step        TEXT,
                        status      TEXT DEFAULT 'running',
                        message     TEXT,
                        duration_ms INTEGER,
                        output_json TEXT,
                        error       TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS resume_data (
                        id          SERIAL PRIMARY KEY,
                        filename    TEXT,
                        file_size   INTEGER,
                        uploaded_at TEXT,
                        parsed_at   TEXT,
                        parse_status TEXT DEFAULT 'pending',
                        parsed_json TEXT,
                        skills_json TEXT,
                        roles_json  TEXT,
                        health_json TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS recruiters (
                        id          SERIAL PRIMARY KEY,
                        company     TEXT,
                        job_id      INTEGER,
                        name        TEXT,
                        role        TEXT,
                        department  TEXT,
                        email       TEXT,
                        confidence  INTEGER DEFAULT 0,
                        source      TEXT,
                        linkedin    TEXT,
                        contact_type TEXT,
                        rank_score  INTEGER DEFAULT 0,
                        discovered_at TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS startup_companies (
                        id                  SERIAL PRIMARY KEY,
                        company             TEXT,
                        domain              TEXT,
                        source              TEXT,
                        source_url          TEXT,
                        location            TEXT,
                        is_remote           BOOLEAN DEFAULT FALSE,
                        job_count           INTEGER DEFAULT 0,
                        resume_match_score  INTEGER DEFAULT 0,
                        role_match_score    INTEGER DEFAULT 0,
                        tech_stack_match    INTEGER DEFAULT 0,
                        experience_match    INTEGER DEFAULT 0,
                        remote_compatibility INTEGER DEFAULT 0,
                        overall_score       INTEGER DEFAULT 0,
                        matched_roles       TEXT,
                        matched_skills      TEXT,
                        keywords            TEXT,
                        summary             TEXT,
                        rank_reason         TEXT,
                        careers_page_url    TEXT,
                        discovered_at       TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS application_tracker (
                        id                     SERIAL PRIMARY KEY,
                        company                TEXT,
                        role                   TEXT,
                        job_url                TEXT UNIQUE,
                        source                 TEXT,
                        date_applied           TEXT,
                        referral_contact       TEXT,
                        resume_version         TEXT,
                        cover_letter_version   TEXT,
                        email_status           TEXT DEFAULT 'pending',
                        application_status     TEXT DEFAULT 'saved',
                        follow_up_date         TEXT,
                        second_follow_up_date  TEXT,
                        notes                  TEXT,
                        ats_before             INTEGER DEFAULT 0,
                        ats_after              INTEGER DEFAULT 0,
                        careers_page_url       TEXT,
                        linkedin_message       TEXT,
                        created_at             TEXT,
                        updated_at             TEXT
                    )
                """)
            conn.commit()
            self._ensure_columns(conn, "jobs", {
                "source": "TEXT",
                "location": "TEXT",
                "type": "TEXT",
                "hr_email": "TEXT",
                "jd_text": "TEXT",
                "fit_score": "INTEGER",
                "status": "TEXT DEFAULT 'found'",
                "scraped_at": "TEXT",
                "applied_at": "TEXT",
                "cover_letter_path": "TEXT",
                "tailored_resume_path": "TEXT",
                "email_subject": "TEXT",
                "email_body": "TEXT",
                "match_details_json": "TEXT",
                "resume_version": "TEXT",
                "cover_letter_version": "TEXT",
                "email_status": "TEXT",
                "follow_up_date": "TEXT",
                "second_follow_up_date": "TEXT",
                "notes": "TEXT",
                "referral_contact": "TEXT",
                "application_status": "TEXT",
                "ats_before": "INTEGER DEFAULT 0",
                "ats_after": "INTEGER DEFAULT 0",
                "linkedin_message": "TEXT",
                "careers_page_url": "TEXT",
                "needs_review": "INTEGER DEFAULT 0",
            })
            self._ensure_columns(conn, "emails", {
                "job_id": "INTEGER",
                "hr_email": "TEXT",
                "subject": "TEXT",
                "body_text": "TEXT",
                "status": "TEXT DEFAULT 'drafted'",
                "resume_path": "TEXT",
                "cover_letter_path": "TEXT",
                "created_at": "TEXT",
            })
            self._ensure_columns(conn, "run_log", {
                "run_id": "TEXT",
                "triggered_by": "TEXT",
                "started_at": "TEXT",
                "finished_at": "TEXT",
                "jobs_found": "INTEGER DEFAULT 0",
                "jobs_filtered": "INTEGER DEFAULT 0",
                "jobs_applied": "INTEGER DEFAULT 0",
                "emails_sent": "INTEGER DEFAULT 0",
                "errors_count": "INTEGER DEFAULT 0",
                "status": "TEXT DEFAULT 'running'",
                "summary_json": "TEXT",
            })
            self._ensure_columns(conn, "recruiters", {
                "company": "TEXT",
                "job_id": "INTEGER",
                "name": "TEXT",
                "role": "TEXT",
                "department": "TEXT",
                "email": "TEXT",
                "confidence": "INTEGER DEFAULT 0",
                "source": "TEXT",
                "linkedin": "TEXT",
                "contact_type": "TEXT",
                "rank_score": "INTEGER DEFAULT 0",
                "discovered_at": "TEXT",
            })
            self._ensure_columns(conn, "startup_companies", {
                "company": "TEXT",
                "domain": "TEXT",
                "source": "TEXT",
                "source_url": "TEXT",
                "location": "TEXT",
                "is_remote": "BOOLEAN DEFAULT FALSE",
                "job_count": "INTEGER DEFAULT 0",
                "resume_match_score": "INTEGER DEFAULT 0",
                "role_match_score": "INTEGER DEFAULT 0",
                "tech_stack_match": "INTEGER DEFAULT 0",
                "experience_match": "INTEGER DEFAULT 0",
                "remote_compatibility": "INTEGER DEFAULT 0",
                "overall_score": "INTEGER DEFAULT 0",
                "matched_roles": "TEXT",
                "matched_skills": "TEXT",
                "keywords": "TEXT",
                "summary": "TEXT",
                "rank_reason": "TEXT",
                "careers_page_url": "TEXT",
                "discovered_at": "TEXT",
            })
            self._ensure_columns(conn, "application_tracker", {
                "company": "TEXT",
                "role": "TEXT",
                "job_url": "TEXT UNIQUE",
                "source": "TEXT",
                "date_applied": "TEXT",
                "referral_contact": "TEXT",
                "resume_version": "TEXT",
                "cover_letter_version": "TEXT",
                "email_status": "TEXT DEFAULT 'pending'",
                "application_status": "TEXT DEFAULT 'saved'",
                "follow_up_date": "TEXT",
                "second_follow_up_date": "TEXT",
                "notes": "TEXT",
                "ats_before": "INTEGER DEFAULT 0",
                "ats_after": "INTEGER DEFAULT 0",
                "careers_page_url": "TEXT",
                "linkedin_message": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            })
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] Schema init failed: {e}")
            raise
        finally:
            self._put_conn(conn)

    def _ensure_columns(self, conn, table: str, columns: dict[str, str]):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s
            """, (table,))
            existing = {row[0] for row in cur.fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    try:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
                    except Exception as e:
                        logger.warning(f"[db] Could not add column {name} to {table}: {e}")

    # ── Jobs ──────────────────────────────────────────────────────────────────
    def insert_job(self, job: dict, app_result: dict = None,
                   email: dict = None, status: str = "found"):
        self._disk_invalidate("all_jobs")
        now  = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO jobs
                    (title, company, url, source, location, type, hr_email,
                     fit_score, status, scraped_at, applied_at,
                     jd_text, cover_letter_path, tailored_resume_path,
                     email_subject, email_body, needs_review)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (url) DO NOTHING
                """, (
                    job.get("title"),
                    job.get("company"),
                    job.get("url") or f"{job.get('company')}-{job.get('title')}-{now}",
                    job.get("source"),
                    job.get("location"),
                    job.get("type"),
                    job.get("hr_email"),
                    (app_result or {}).get("fit_score"),
                    status,
                    now,
                    now if status == "sent" else None,
                    job.get("description_snippet", job.get("jd_text", "")),
                    (app_result or {}).get("cover_letter_path"),
                    (app_result or {}).get("tailored_resume_path"),
                    (email or {}).get("subject"),
                    (email or {}).get("body"),
                    1 if job.get("needs_review") else 0,
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] insert_job failed: {e}")
        finally:
            self._put_conn(conn)

    def update_job_company(self, job_id: int, company: str) -> bool:
        """Set a corrected company name and clear the needs_review flag (Bug 2)."""
        self._disk_invalidate("all_jobs")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET company = %s, needs_review = 0 WHERE id = %s",
                    (company, job_id),
                )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] update_job_company failed: {e}")
            return False
        finally:
            self._put_conn(conn)

    def mark_job_applied(self, job_id: int, subject: str = None, body: str = None) -> bool:
        """Mark a job as sent/applied (Bug 3), persisting any edited email content."""
        self._disk_invalidate("all_jobs")
        now = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE jobs
                    SET status = 'sent',
                        applied_at = %s,
                        email_subject = COALESCE(%s, email_subject),
                        email_body = COALESCE(%s, email_body)
                    WHERE id = %s
                """, (now, subject, body, job_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] mark_job_applied failed: {e}")
            return False
        finally:
            self._put_conn(conn)

    def url_exists(self, url: str) -> bool:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM jobs WHERE url = %s", (url,))
                return cur.fetchone() is not None
        finally:
            self._put_conn(conn)

    def job_exists(self, url: str) -> bool:
        return self.url_exists(url)

    def email_exists_for_company(self, company: str) -> bool:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM jobs
                    WHERE lower(company) = lower(%s)
                    AND status IN ('sent', 'draft', 'ready')
                    LIMIT 1
                """, (company,))
                return cur.fetchone() is not None
        finally:
            self._put_conn(conn)

    def get_jobs_by_company(self, company: str) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM jobs
                    WHERE lower(company) = lower(%s)
                    ORDER BY scraped_at DESC
                """, (company,))
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def get_all_jobs(self, limit: int = 100, conn=None) -> list[dict]:
        cached = self._disk_get("all_jobs", ttl=300) if limit <= 100 else None
        if cached is not None:
            return cached[:limit] if limit < len(cached) else cached
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT %s", (limit,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if limit <= 100:
                    self._disk_set("all_jobs", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    def get_unsent_emails(self) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM jobs
                    WHERE status IN ('draft','ready')
                    AND email_body IS NOT NULL
                    AND COALESCE(needs_review, 0) = 0
                    ORDER BY scraped_at DESC
                """)
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def daily_sent_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM jobs WHERE applied_at >= %s AND status='sent'",
                    (today,)
                )
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    # ── Run log ───────────────────────────────────────────────────────────────
    def start_run_log(self, run_id: str, triggered_by: str):
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO run_log (run_id, triggered_by, started_at, status)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (run_id) DO NOTHING
                """, (run_id, triggered_by, datetime.now().isoformat(), "running"))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] start_run_log failed: {e}")
        finally:
            self._put_conn(conn)

    def update_run_log(self, run_id: str, **kwargs):
        if not kwargs:
            return
        summary = kwargs.pop("summary", None)
        fields  = {k: v for k, v in kwargs.items()}
        if summary:
            fields["summary_json"] = json.dumps(summary)
        fields["finished_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values     = list(fields.values()) + [run_id]
        conn       = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE run_log SET {set_clause} WHERE run_id = %s", values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] update_run_log failed: {e}")
        finally:
            self._put_conn(conn)

    def get_recent_run_logs(self, limit: int = 20, conn=None) -> list[dict]:
        cached = self._disk_get("recent_run_logs", ttl=300) if limit <= 50 else None
        if cached is not None:
            return cached[:limit]
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM run_log ORDER BY started_at DESC LIMIT %s", (limit,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if limit <= 50:
                    self._disk_set("recent_run_logs", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    # ── Job details ───────────────────────────────────────────────────────────
    def update_job_match(self, job_id: int, match_details_json: str, fit_score: int = None):
        self._disk_invalidate("all_jobs")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if fit_score is not None:
                    cur.execute(
                        "UPDATE jobs SET match_details_json = %s, fit_score = %s WHERE id = %s",
                        (match_details_json, fit_score, job_id)
                    )
                else:
                    cur.execute(
                        "UPDATE jobs SET match_details_json = %s WHERE id = %s",
                        (match_details_json, job_id)
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] update_job_match failed: {e}")
        finally:
            self._put_conn(conn)

    def get_job_by_id(self, job_id: int) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put_conn(conn)

    # ── Resume data ──────────────────────────────────────────────────────────
    def save_resume_data(self, data: dict):
        self._cache_clear("resume_data")
        self._disk_invalidate("resume_data")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM resume_data")
                parsed = data.get("parsed_json") or data.get("parsed", {})
                skills = data.get("skills_json") or data.get("skills", [])
                roles = data.get("roles_json") or data.get("roles", [])
                health = data.get("health")
                cur.execute("""
                    INSERT INTO resume_data
                    (filename, file_size, uploaded_at, parsed_at, parse_status,
                     parsed_json, skills_json, roles_json, health_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    data.get("filename"),
                    data.get("file_size"),
                    data.get("uploaded_at"),
                    data.get("parsed_at"),
                    data.get("parse_status", "success"),
                    json.dumps(parsed) if isinstance(parsed, (dict, list)) else parsed,
                    json.dumps(skills) if isinstance(skills, (dict, list)) else skills,
                    json.dumps(roles) if isinstance(roles, (dict, list)) else roles,
                    json.dumps(health) if isinstance(health, (dict, list)) else health,
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] save_resume_data failed: {e}")
        finally:
            self._put_conn(conn)

    def _resolve_conn(self, conn=None):
        """Return (connection, should_close). If conn is provided, don't close it."""
        if conn is not None:
            return conn, False
        return self._conn(), True

    def get_resume_data(self, conn=None) -> dict | None:
        cached = self._cache_get("resume_data")
        if cached is not None:
            return cached
        d = self._disk_get("resume_data", ttl=300)
        if d is not None:
            self._cache_set("resume_data", d)
            return d
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM resume_data ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                for key in ("parsed_json", "skills_json", "roles_json", "health_json"):
                    if d.get(key):
                        try:
                            d[key] = json.loads(d[key])
                        except (json.JSONDecodeError, TypeError):
                            pass
                self._cache_set("resume_data", d)
                self._disk_set("resume_data", d, ttl=300)
                return d
        finally:
            if close:
                self._put_conn(conn)

    # ── Pipeline events ──────────────────────────────────────────────────────
    def save_pipeline_event(self, run_id: str, event: dict):
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pipeline_events
                    (run_id, timestamp, agent, step, status, message, duration_ms, output_json, error)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    run_id,
                    event.get("timestamp"),
                    event.get("agent"),
                    event.get("step"),
                    event.get("status", "running"),
                    event.get("message"),
                    event.get("duration_ms"),
                    json.dumps(event.get("output")) if event.get("output") else None,
                    event.get("error"),
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] save_pipeline_event failed: {e}")
        finally:
            self._put_conn(conn)

    def get_pipeline_events(self, run_id: str) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM pipeline_events WHERE run_id = %s ORDER BY id ASC",
                    (run_id,)
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ── Recruiters ───────────────────────────────────────────────────────────
    def save_recruiter(self, data: dict):
        self._disk_invalidate("all_recruiters")
        self._disk_invalidate("company_contacts")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO recruiters
                    (company, job_id, name, role, department, email, confidence, source, linkedin, contact_type, rank_score, discovered_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    data.get("company"),
                    data.get("job_id"),
                    data.get("name"),
                    data.get("role"),
                    data.get("department"),
                    data.get("email"),
                    data.get("confidence", 0),
                    data.get("source"),
                    data.get("linkedin"),
                    data.get("contact_type"),
                    data.get("rank_score", 0),
                    data.get("discovered_at", datetime.now().isoformat()),
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] save_recruiter failed: {e}")
        finally:
            self._put_conn(conn)

    def get_all_recruiters(self, limit: int = 50, conn=None) -> list[dict]:
        cached = self._disk_get("all_recruiters", ttl=300) if limit <= 100 else None
        if cached is not None:
            return cached[:limit]
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM recruiters ORDER BY coalesce(confidence, 0) DESC, discovered_at DESC LIMIT %s",
                    (limit,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if limit <= 100:
                    self._disk_set("all_recruiters", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    # ── Startups ────────────────────────────────────────────────────────────
    def save_startup_company(self, company: dict):
        self._disk_invalidate("startup_companies")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM startup_companies WHERE lower(company) = lower(%s) AND coalesce(domain, '') = coalesce(%s, '')",
                    (company.get("company"), company.get("domain")),
                )
                cur.execute("""
                    INSERT INTO startup_companies
                    (company, domain, source, source_url, location, is_remote, job_count,
                     resume_match_score, role_match_score, tech_stack_match, experience_match,
                     remote_compatibility, overall_score, matched_roles, matched_skills, keywords,
                     summary, rank_reason, careers_page_url, discovered_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    company.get("company"),
                    company.get("domain"),
                    company.get("source"),
                    company.get("source_url"),
                    company.get("location"),
                    bool(company.get("is_remote", False)),
                    company.get("job_count", 0),
                    company.get("resume_match_score", 0),
                    company.get("role_match_score", 0),
                    company.get("tech_stack_match", 0),
                    company.get("experience_match", 0),
                    company.get("remote_compatibility", 0),
                    company.get("overall_score", 0),
                    json.dumps(company.get("matched_roles", [])),
                    json.dumps(company.get("matched_skills", [])),
                    json.dumps(company.get("keywords", [])),
                    company.get("summary"),
                    company.get("rank_reason"),
                    company.get("careers_page_url"),
                    company.get("discovered_at", datetime.now().isoformat()),
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] save_startup_company failed: {e}")
        finally:
            self._put_conn(conn)

    def get_startup_companies(self, limit: int = 20, conn=None) -> list[dict]:
        cached = self._disk_get("startup_companies", ttl=300) if limit <= 200 else None
        if cached is not None:
            return cached[:limit]
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM startup_companies ORDER BY overall_score DESC, discovered_at DESC LIMIT %s",
                    (limit,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                for row in rows:
                    for key in ("matched_roles", "matched_skills", "keywords"):
                        if row.get(key):
                            try:
                                row[key] = json.loads(row[key])
                            except (json.JSONDecodeError, TypeError):
                                pass
                if limit <= 200:
                    self._disk_set("startup_companies", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    # ── Contacts ───────────────────────────────────────────────────────────
    def save_company_contact(self, contact: dict):
        self._disk_invalidate("all_recruiters")
        self._disk_invalidate("company_contacts")
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM recruiters WHERE lower(company) = lower(%s) AND lower(coalesce(email, '')) = lower(%s) AND lower(coalesce(name, '')) = lower(%s)",
                    (contact.get("company"), contact.get("email", ""), contact.get("name", "")),
                )
                cur.execute("""
                    INSERT INTO recruiters
                    (company, name, role, department, email, confidence, source, linkedin, contact_type, rank_score, discovered_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    contact.get("company"),
                    contact.get("name"),
                    contact.get("role"),
                    contact.get("department"),
                    contact.get("email"),
                    contact.get("confidence", 0),
                    contact.get("source"),
                    contact.get("linkedin"),
                    contact.get("contact_type"),
                    contact.get("rank_score", 0),
                    contact.get("discovered_at", datetime.now().isoformat()),
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] save_company_contact failed: {e}")
        finally:
            self._put_conn(conn)

    def get_company_contacts(self, company: str | None = None, limit: int = 50, conn=None) -> list[dict]:
        if company is None:
            cached = self._disk_get("company_contacts", ttl=300) if limit <= 100 else None
            if cached is not None:
                return cached[:limit]
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if company:
                    cur.execute(
                        "SELECT * FROM recruiters WHERE lower(company) = lower(%s) ORDER BY coalesce(confidence, 0) DESC, discovered_at DESC LIMIT %s",
                        (company, limit),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM recruiters ORDER BY coalesce(confidence, 0) DESC, discovered_at DESC LIMIT %s",
                        (limit,),
                    )
                rows = [dict(r) for r in cur.fetchall()]
                if company is None and limit <= 100:
                    self._disk_set("company_contacts", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    # ── Application tracker ─────────────────────────────────────────────────
    def upsert_application_tracker(self, application: dict):
        self._disk_invalidate("application_tracker")
        conn = self._conn()
        now = datetime.now().isoformat()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM application_tracker WHERE job_url = %s", (application.get("job_url"),))
                existing = cur.fetchone()
                if existing:
                    cur.execute("""
                        UPDATE application_tracker SET
                            company = %s,
                            role = %s,
                            source = %s,
                            date_applied = %s,
                            referral_contact = %s,
                            resume_version = %s,
                            cover_letter_version = %s,
                            email_status = %s,
                            application_status = %s,
                            follow_up_date = %s,
                            second_follow_up_date = %s,
                            notes = %s,
                            ats_before = %s,
                            ats_after = %s,
                            careers_page_url = %s,
                            linkedin_message = %s,
                            updated_at = %s
                        WHERE job_url = %s
                    """, (
                        application.get("company"),
                        application.get("role"),
                        application.get("source"),
                        application.get("date_applied"),
                        application.get("referral_contact"),
                        application.get("resume_version"),
                        application.get("cover_letter_version"),
                        application.get("email_status", "pending"),
                        application.get("application_status", "saved"),
                        application.get("follow_up_date"),
                        application.get("second_follow_up_date"),
                        application.get("notes"),
                        application.get("ats_before", 0),
                        application.get("ats_after", 0),
                        application.get("careers_page_url"),
                        application.get("linkedin_message"),
                        now,
                        application.get("job_url"),
                    ))
                else:
                    cur.execute("""
                        INSERT INTO application_tracker
                        (company, role, job_url, source, date_applied, referral_contact,
                         resume_version, cover_letter_version, email_status, application_status,
                         follow_up_date, second_follow_up_date, notes, ats_before, ats_after,
                         careers_page_url, linkedin_message, created_at, updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        application.get("company"),
                        application.get("role"),
                        application.get("job_url"),
                        application.get("source"),
                        application.get("date_applied") or now,
                        application.get("referral_contact"),
                        application.get("resume_version"),
                        application.get("cover_letter_version"),
                        application.get("email_status", "pending"),
                        application.get("application_status", "saved"),
                        application.get("follow_up_date"),
                        application.get("second_follow_up_date"),
                        application.get("notes"),
                        application.get("ats_before", 0),
                        application.get("ats_after", 0),
                        application.get("careers_page_url"),
                        application.get("linkedin_message"),
                        now,
                        now,
                    ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[db] upsert_application_tracker failed: {e}")
        finally:
            self._put_conn(conn)

    def get_application_tracker(self, limit: int = 100, conn=None) -> list[dict]:
        cached = self._disk_get("application_tracker", ttl=300) if limit <= 200 else None
        if cached is not None:
            return cached[:limit]
        conn, close = self._resolve_conn(conn)
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM application_tracker ORDER BY coalesce(date_applied, created_at) DESC LIMIT %s",
                    (limit,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if limit <= 200:
                    self._disk_set("application_tracker", rows, ttl=300)
                return rows
        finally:
            if close:
                self._put_conn(conn)

    def get_followups_due(self) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM application_tracker
                    WHERE application_status IN ('applied', 'follow_up_due')
                      AND follow_up_date IS NOT NULL
                      AND follow_up_date <= %s
                    ORDER BY follow_up_date ASC
                """, (datetime.now().isoformat(),))
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)


# ── Singleton ─────────────────────────────────────────────────────────────────
_db_instance = None


def get_db() -> DBClient:
    global _db_instance
    if _db_instance is None:
        _db_instance = DBClient()
    return _db_instance
