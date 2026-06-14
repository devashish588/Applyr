"""
DB Client — AutoApply AI
Single SQLite wrapper used by orchestrator.py, app.py, and all API routes.
Call get_db() anywhere to get a singleton instance.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logger  = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "./db/applications.db")


class DBClient:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
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
                email_body           TEXT
            );

            CREATE TABLE IF NOT EXISTS run_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
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
            );

            CREATE TABLE IF NOT EXISTS emails (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id            INTEGER,
                hr_email          TEXT,
                subject           TEXT,
                body_text         TEXT,
                status            TEXT DEFAULT 'drafted',
                resume_path       TEXT,
                cover_letter_path TEXT,
                created_at        TEXT
            );
        """)
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
        conn.commit()
        conn.close()

    def _ensure_columns(self, conn, table: str, columns: dict[str, str]):
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    # ── Jobs ──────────────────────────────────────────────────────────────────
    def insert_job(self, job: dict, app_result: dict = None,
                   email: dict = None, status: str = "found"):
        now  = datetime.now().isoformat()
        conn = self._conn()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, company, url, source, location, type, hr_email,
                 fit_score, status, scraped_at, applied_at,
                 jd_text, cover_letter_path, tailored_resume_path,
                 email_subject, email_body)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"[db] insert_job failed: {e}")
        finally:
            conn.close()

    def url_exists(self, url: str) -> bool:
        conn = self._conn()
        row  = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
        conn.close()
        return row is not None

    def job_exists(self, url: str) -> bool:
        return self.url_exists(url)

    def email_exists_for_company(self, company: str) -> bool:
        conn = self._conn()
        row = conn.execute("""
            SELECT id FROM jobs
            WHERE lower(company) = lower(?)
            AND status IN ('sent', 'draft', 'ready')
            LIMIT 1
        """, (company,)).fetchone()
        conn.close()
        return row is not None

    def get_jobs_by_company(self, company: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE lower(company) = lower(?)
            ORDER BY scraped_at DESC
        """, (company,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_jobs(self, limit: int = 100) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_unsent_emails(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE status IN ('draft','ready')
            AND email_body IS NOT NULL
            ORDER BY scraped_at DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def daily_sent_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        conn  = self._conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE applied_at LIKE ? AND status='sent'",
            (f"{today}%",)
        ).fetchone()[0]
        conn.close()
        return count

    # ── Run log ───────────────────────────────────────────────────────────────
    def start_run_log(self, run_id: str, triggered_by: str):
        conn = self._conn()
        conn.execute("""
            INSERT OR IGNORE INTO run_log (run_id, triggered_by, started_at, status)
            VALUES (?,?,?,?)
        """, (run_id, triggered_by, datetime.now().isoformat(), "running"))
        conn.commit()
        conn.close()

    def update_run_log(self, run_id: str, **kwargs):
        if not kwargs:
            return
        summary = kwargs.pop("summary", None)
        fields  = {k: v for k, v in kwargs.items()}
        if summary:
            fields["summary_json"] = json.dumps(summary)
        fields["finished_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values     = list(fields.values()) + [run_id]
        conn       = self._conn()
        conn.execute(f"UPDATE run_log SET {set_clause} WHERE run_id = ?", values)
        conn.commit()
        conn.close()

    def get_recent_run_logs(self, limit: int = 20) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM run_log ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ── Singleton ─────────────────────────────────────────────────────────────────
_db_instance = None

def get_db() -> DBClient:
    global _db_instance
    if _db_instance is None:
        _db_instance = DBClient()
    return _db_instance
