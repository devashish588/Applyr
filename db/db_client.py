"""
Database client wrapper for SQLite.
Provides a simple interface for agents to read/write without raw SQL.
"""
import sqlite3
import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class DatabaseClient:
    def __init__(self, db_path: str = "./db/applications.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.initialize_db()

    def initialize_db(self):
        """Initialize database and create tables if they don't exist."""
        # Create db directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(self.db_path), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                schema = f.read()
            self.execute_script(schema)

    def get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local database connection."""
        conn = getattr(self._local, 'connection', None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return conn

    def execute_script(self, script: str):
        """Execute SQL script."""
        conn = self.get_connection()
        conn.executescript(script)
        conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute SELECT query and return results as list of dicts."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT query and return last row id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute UPDATE query and return rows affected."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount

    def execute_delete(self, query: str, params: tuple = ()) -> int:
        """Execute DELETE query and return rows affected."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount

    # ===================== JOB OPERATIONS =====================

    def add_job(self, title: str, company: str, url: str, source: str, 
                jd_text: str = "", fit_score: int = 0) -> int:
        """Add a new job listing."""
        query = """
            INSERT INTO jobs (title, company, url, source, jd_text, fit_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.execute_insert(query, (title, company, url, source, jd_text, fit_score))

    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job by ID."""
        query = "SELECT * FROM jobs WHERE id = ?"
        results = self.execute_query(query, (job_id,))
        return results[0] if results else None

    def get_jobs_by_status(self, status: str) -> List[Dict]:
        """Get all jobs with specific status."""
        query = "SELECT * FROM jobs WHERE status = ? ORDER BY fit_score DESC"
        return self.execute_query(query, (status,))

    def get_jobs_by_company(self, company: str) -> List[Dict]:
        """Get all jobs from a specific company."""
        query = "SELECT * FROM jobs WHERE company = ?"
        return self.execute_query(query, (company,))

    def get_jobs_by_source(self, source: str) -> List[Dict]:
        """Get all jobs from a specific source."""
        query = "SELECT * FROM jobs WHERE source = ? ORDER BY fit_score DESC"
        return self.execute_query(query, (source,))

    def get_all_jobs(self, limit: int = 100) -> List[Dict]:
        """Get all jobs, latest first."""
        query = "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?"
        return self.execute_query(query, (limit,))

    def update_job_status(self, job_id: int, status: str) -> int:
        """Update job status."""
        query = "UPDATE jobs SET status = ? WHERE id = ?"
        return self.execute_update(query, (status, job_id))

    def update_job_fit_score(self, job_id: int, fit_score: int) -> int:
        """Update job fit score."""
        query = "UPDATE jobs SET fit_score = ? WHERE id = ?"
        return self.execute_update(query, (fit_score, job_id))

    def job_exists(self, url: str) -> bool:
        """Check if job URL already exists in database."""
        query = "SELECT COUNT(*) as count FROM jobs WHERE url = ?"
        result = self.execute_query(query, (url,))
        return result[0]["count"] > 0 if result else False

    # ===================== EMAIL OPERATIONS =====================

    def add_email_log(self, job_id: int, hr_email: str, subject: str, 
                     body_text: str, resume_path: str, cover_letter_path: str = "") -> int:
        """Log an email that will be sent."""
        query = """
            INSERT INTO emails (job_id, hr_email, subject, body_text, resume_path, cover_letter_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.execute_insert(
            query, 
            (job_id, hr_email, subject, body_text, resume_path, cover_letter_path)
        )

    def update_email_status(self, email_id: int, status: str, error_message: str = "") -> int:
        """Update email status after sending."""
        query = "UPDATE emails SET status = ?, error_message = ? WHERE id = ?"
        return self.execute_update(query, (status, error_message, email_id))

    def get_emails_by_job(self, job_id: int) -> List[Dict]:
        """Get all emails for a specific job."""
        query = "SELECT * FROM emails WHERE job_id = ?"
        return self.execute_query(query, (job_id,))

    def get_unsent_emails(self) -> List[Dict]:
        """Get all emails that haven't been sent yet (pending or drafted)."""
        query = "SELECT * FROM emails WHERE status IN ('pending', 'drafted') ORDER BY id DESC"
        return self.execute_query(query)

    def email_exists_for_company(self, company: str) -> bool:
        """Check if email already sent to this company."""
        query = """
            SELECT COUNT(*) as count FROM emails e
            JOIN jobs j ON e.job_id = j.id
            WHERE j.company = ? AND e.status = 'sent'
        """
        result = self.execute_query(query, (company,))
        return result[0]["count"] > 0 if result else False

    # ===================== WEB FORM OPERATIONS =====================

    def add_web_form_submission(self, job_id: int, portal_url: str, 
                               fields_filled: Dict[str, str], screenshot_path: str = "") -> int:
        """Log a web form submission."""
        query = """
            INSERT INTO web_forms (job_id, portal_url, fields_filled, screenshot_path)
            VALUES (?, ?, ?, ?)
        """
        fields_json = json.dumps(fields_filled)
        return self.execute_insert(query, (job_id, portal_url, fields_json, screenshot_path))

    def update_web_form_status(self, form_id: int, status: str, error_message: str = "") -> int:
        """Update web form submission status."""
        query = "UPDATE web_forms SET status = ?, error_message = ? WHERE id = ?"
        return self.execute_update(query, (status, error_message, form_id))

    def get_form_submissions_by_job(self, job_id: int) -> List[Dict]:
        """Get all form submissions for a job."""
        query = "SELECT * FROM web_forms WHERE job_id = ?"
        results = self.execute_query(query, (job_id,))
        # Parse JSON fields
        for row in results:
            if row.get("fields_filled"):
                row["fields_filled"] = json.loads(row["fields_filled"])
        return results

    # ===================== RUN LOG OPERATIONS =====================

    def start_run_log(self, run_id: str, triggered_by: str = "scheduler") -> int:
        """Start a new run log."""
        query = """
            INSERT INTO run_logs (run_id, triggered_by, status)
            VALUES (?, ?, 'running')
        """
        return self.execute_insert(query, (run_id, triggered_by))

    def update_run_log(self, run_id: str, jobs_found: int = 0, jobs_filtered: int = 0,
                      jobs_applied: int = 0, emails_sent: int = 0, 
                      errors_count: int = 0, summary: Dict = None) -> int:
        """Update run log with results."""
        summary_json = json.dumps(summary) if summary else ""
        query = """
            UPDATE run_logs 
            SET jobs_found = ?, jobs_filtered = ?, jobs_applied = ?, 
                emails_sent = ?, errors_count = ?, summary_json = ?,
                completed_at = ?, status = 'completed'
            WHERE run_id = ?
        """
        return self.execute_update(
            query,
            (jobs_found, jobs_filtered, jobs_applied, emails_sent, 
             errors_count, summary_json, datetime.now().isoformat(), run_id)
        )

    def get_run_log(self, run_id: str) -> Optional[Dict]:
        """Get run log details."""
        query = "SELECT * FROM run_logs WHERE run_id = ?"
        results = self.execute_query(query, (run_id,))
        if results:
            row = results[0]
            if row.get("summary_json"):
                row["summary_json"] = json.loads(row["summary_json"])
            return row
        return None

    def get_recent_run_logs(self, limit: int = 10) -> List[Dict]:
        """Get recent run logs."""
        query = """
            SELECT * FROM run_logs 
            ORDER BY started_at DESC 
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    def close(self):
        """Close the current thread's database connection."""
        conn = getattr(self._local, 'connection', None)
        if conn:
            conn.close()
            self._local.connection = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Global database instance
_db_instance = None


def get_db() -> DatabaseClient:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseClient()
    return _db_instance
