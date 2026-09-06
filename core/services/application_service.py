"""
Application Service — Phase 7 P0
===============================

Direct PostgreSQL via DATABASE_URL (psycopg2), no DBClient._conn.
All lifecycle operations are single transactions with SELECT FOR UPDATE.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "")
# Production database that must never be used as test DB.
_PRODUCTION_DB = "neondb"


def _is_production_db(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        db = urlparse(url).path.lstrip("/").split("?")[0].split("/")[0]
        return db == _PRODUCTION_DB
    except Exception:
        return "/neondb" in url


def _resolve_database_url() -> str:
    """Resolve DB URL with TEST_DATABASE_URL override for isolated tests.

    In test mode, TEST_DATABASE_URL is checked first.  If present, it MUST be
    isolated (not contain production database).  Otherwise DATABASE_URL is used.
    """
    test_url = os.getenv("TEST_DATABASE_URL", "")
    if test_url:
        if _is_production_db(test_url):
            raise RuntimeError(
                "TEST_DATABASE_URL must be isolated — points to production database 'neondb'. "
                "Use a disposable test database (e.g. applyr_test), never production neondb."
            )
        if test_url == DATABASE_URL and DATABASE_URL:
            raise RuntimeError("TEST_DATABASE_URL must not equal DATABASE_URL (production). Use an isolated test database.")
        return test_url
    # No TEST_DATABASE_URL — caller gets production URL, but guard in tests/conftest
    # will refuse to run integration tests without explicit isolation.
    env_url = os.getenv("DATABASE_URL", "")
    return env_url or DATABASE_URL

ALLOWED_STATES = {"DISCOVERED", "PREPARING", "READY_TO_APPLY", "APPLIED", "SCREENING", "INTERVIEW", "FINAL", "OFFER", "CLOSED"}
ALLOWED_TRANSITIONS = {
    "DISCOVERED": {"PREPARING"},
    "PREPARING": {"READY_TO_APPLY", "DISCOVERED"},
    "READY_TO_APPLY": {"APPLIED", "PREPARING"},
    "APPLIED": {"SCREENING", "INTERVIEW", "CLOSED"},
    "SCREENING": {"INTERVIEW", "CLOSED"},
    "INTERVIEW": {"FINAL", "OFFER", "CLOSED"},
    "FINAL": {"OFFER", "CLOSED"},
    "OFFER": {"CLOSED"},
    "CLOSED": set(),
}
ALLOWED_OUTCOMES = {"NONE", "REJECTED", "WITHDRAWN", "EXPIRED", "ACCEPTED", "DECLINED", "UNKNOWN"}
ALLOWED_EVENT_TYPES = {
    "discovered", "opened", "shortlisted", "preparing", "resume_generated", "cover_generated",
    "application_started", "application_submitted", "application_recorded_externally",
    "autofill_started", "autofill_completed", "autofill_failed", "autofill_cancelled",
    "send_failed", "withdrawn", "expired", "closed", "note",
    "screening_started", "interview_scheduled", "interview_completed", "final_stage_reached",
    "offer_received", "application_withdrawn", "follow_up_sent", "recruiter_response",
    "screening", "interview", "final", "offer"
}
# Generic endpoint allow-list — only informational, never lifecycle transitions
GENERIC_ALLOWED_EVENTS = {"note", "recruiter_response"}

TERMINAL_OUTCOMES = {"REJECTED", "WITHDRAWN", "EXPIRED", "ACCEPTED", "DECLINED"}


def _conn():
    url = _resolve_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL not set (and TEST_DATABASE_URL not set for tests)")
    return psycopg2.connect(url)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApplicationService:
    def create_application(self, job_id: int, application_method: str = "MANUAL", candidate_id: str = "primary_candidate") -> Dict[str, Any]:
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Lock job row to prevent concurrent duplicate creation
                    cur.execute("SELECT id, title, company FROM jobs WHERE id = %s FOR UPDATE", (job_id,))
                    job = cur.fetchone()
                    if not job:
                        raise ValueError("Job not found")
                    # Check for open application
                    cur.execute("SELECT id, current_state FROM applications WHERE job_id = %s AND current_state != 'CLOSED' FOR UPDATE", (job_id,))
                    open_row = cur.fetchone()
                    if open_row:
                        raise ValueError("Open application already exists for this job (409)")

                    # Determine attempt number
                    cur.execute("SELECT COALESCE(MAX(attempt_number),0) FROM applications WHERE job_id = %s", (job_id,))
                    max_attempt = cur.fetchone()["coalesce"] or 0
                    attempt = int(max_attempt) + 1
                    # Find previous closed application for previous_application_id
                    cur.execute("SELECT id FROM applications WHERE job_id = %s ORDER BY attempt_number DESC LIMIT 1", (job_id,))
                    prev = cur.fetchone()
                    prev_id = prev["id"] if prev else None

                    cur.execute(
                        """INSERT INTO applications (job_id, attempt_number, previous_application_id, candidate_id, job_title_snapshot, company_snapshot, current_state, last_state_change_at, created_at)
                           VALUES (%s,%s,%s,%s,%s,%s,'PREPARING',%s,%s) RETURNING id""",
                        (job_id, attempt, prev_id, candidate_id, job["title"], job["company"], _now(), _now()),
                    )
                    app_id = cur.fetchone()["id"]
                    cur.execute(
                        "INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,'preparing',%s,'user',%s)",
                        (app_id, _now(), json.dumps({"job_id": job_id})),
                    )
                    cur.execute(
                        "INSERT INTO application_outcomes (application_id, outcome) VALUES (%s,'NONE') ON CONFLICT DO NOTHING",
                        (app_id,),
                    )
                    # Fetch created row within same transaction
                    cur.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
                    return cur.fetchone()
        finally:
            conn.close()

    def get_application(self, app_id: int) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
                return cur.fetchone()
        finally:
            conn.close()

    def list_applications(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM applications ORDER BY created_at DESC LIMIT %s", (limit,))
                return cur.fetchall()
        finally:
            conn.close()

    def get_timeline(self, app_id: int) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM application_events WHERE application_id = %s ORDER BY timestamp ASC", (app_id,))
                return cur.fetchall()
        finally:
            conn.close()

    def patch_state(self, app_id: int, new_state: str) -> Dict[str, Any]:
        if new_state not in ALLOWED_STATES:
            raise ValueError(f"Invalid state: {new_state}")
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT current_state FROM applications WHERE id = %s FOR UPDATE", (app_id,))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Application not found")
                    cur_state = row["current_state"]
                    if new_state == cur_state:
                        return self.get_application(app_id)  # type: ignore
                    allowed = ALLOWED_TRANSITIONS.get(cur_state, set())
                    if new_state not in allowed:
                        raise ValueError(f"Invalid transition {cur_state} -> {new_state}. Allowed: {allowed}")
                    # CLOSED requires outcome != NONE (UNKNOWN is valid per correction)
                    if new_state == "CLOSED":
                        cur.execute("SELECT outcome FROM application_outcomes WHERE application_id = %s", (app_id,))
                        out = cur.fetchone()
                        if not out or out["outcome"] == "NONE":
                            raise ValueError("CLOSED requires a valid final outcome (REJECTED/WITHDRAWN/EXPIRED/ACCEPTED/DECLINED/UNKNOWN)")
                    cur.execute("UPDATE applications SET current_state = %s, last_state_change_at = %s WHERE id = %s", (new_state, _now(), app_id))
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,%s,%s,'user')", (app_id, new_state.lower(), _now()))
            return self.get_application(app_id)  # type: ignore
        finally:
            conn.close()

    def apply_application(self, app_id: int, application_method: str = "MANUAL", match_snapshot: Optional[str] = None, priority_snapshot: Optional[str] = None, submitted_at: Optional[str] = None) -> Dict[str, Any]:
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT current_state, submitted_at FROM applications WHERE id = %s FOR UPDATE", (app_id,))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Application not found")
                    if row["current_state"] not in ("READY_TO_APPLY", "PREPARING"):
                        # Allow PREPARING -> APPLIED via direct apply for manual external?
                        # For P0, require READY_TO_APPLY, but MANUAL can bypass via dedicated method
                        raise ValueError(f"Cannot apply from state {row['current_state']}")
                    if row["submitted_at"] is not None:
                        raise ValueError("Already submitted")
                    now = submitted_at or _now()
                    # Capture snapshots immutably (only if not already set)
                    cur.execute("SELECT match_snapshot FROM applications WHERE id = %s", (app_id,))
                    existing_snap = cur.fetchone()
                    # Only set snapshots if not already set
                    if existing_snap and not existing_snap["match_snapshot"] and match_snapshot:
                        cur.execute("UPDATE applications SET match_snapshot = %s, priority_snapshot = %s WHERE id = %s", (match_snapshot, priority_snapshot, app_id))
                    cur.execute("UPDATE applications SET current_state='APPLIED', last_state_change_at=%s, submitted_at=%s WHERE id=%s", (_now(), now, app_id))
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'application_submitted',%s,'user')", (app_id, _now()))
            return self.get_application(app_id)  # type: ignore
        finally:
            conn.close()

    def record_external(self, job_id: int, submitted_at: Optional[str] = None) -> Dict[str, Any]:
        # Creates application directly as APPLIED with MANUAL method
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT id, title, company FROM jobs WHERE id = %s FOR UPDATE", (job_id,))
                    job = cur.fetchone()
                    if not job:
                        raise ValueError("Job not found")
                    cur.execute("SELECT id FROM applications WHERE job_id = %s AND current_state != 'CLOSED' FOR UPDATE", (job_id,))
                    if cur.fetchone():
                        raise ValueError("Open application already exists")
                    cur.execute("SELECT COALESCE(MAX(attempt_number),0) FROM applications WHERE job_id = %s", (job_id,))
                    attempt = int(cur.fetchone()["coalesce"] or 0) + 1
                    cur.execute("SELECT id FROM applications WHERE job_id = %s ORDER BY attempt_number DESC LIMIT 1", (job_id,))
                    prev = cur.fetchone()
                    prev_id = prev["id"] if prev else None
                    now = submitted_at or _now()
                    cur.execute(
                        """INSERT INTO applications (job_id, attempt_number, previous_application_id, candidate_id, job_title_snapshot, company_snapshot, current_state, last_state_change_at, created_at, submitted_at)
                           VALUES (%s,%s,%s,'primary_candidate',%s,%s,'APPLIED',%s,%s,%s) RETURNING id""",
                        (job_id, attempt, prev_id, job["title"], job["company"], _now(), _now(), now),
                    )
                    app_id = cur.fetchone()["id"]
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor) VALUES (%s,'application_recorded_externally',%s,'user')", (app_id, _now()))
                    cur.execute("INSERT INTO application_outcomes (application_id, outcome) VALUES (%s,'NONE') ON CONFLICT DO NOTHING", (app_id,))
            return self.get_application(app_id)  # type: ignore
        finally:
            conn.close()

    def set_outcome(self, app_id: int, outcome: str, reason: Optional[str] = None) -> Dict[str, Any]:
        if outcome not in ALLOWED_OUTCOMES:
            raise ValueError(f"Invalid outcome: {outcome}")
        if outcome in ("OFFER", "NONE"):
            raise ValueError(f"{outcome} is not a valid closing outcome")
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT current_state FROM applications WHERE id = %s FOR UPDATE", (app_id,))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Application not found")
                    if row["current_state"] == "CLOSED":
                        raise ValueError("Application already closed")
                    # Allow APPLIED -> CLOSED via outcome, also PREPARING/READY_TO_APPLY -> CLOSED via WITHDRAWN/EXPIRED
                    cur.execute("SELECT outcome FROM application_outcomes WHERE application_id = %s", (app_id,))
                    existing = cur.fetchone()
                    if existing and existing["outcome"] != "NONE":
                        raise ValueError("Outcome already set")
                    cur.execute("INSERT INTO application_outcomes (application_id, outcome, decided_at, reason) VALUES (%s,%s,%s,%s) ON CONFLICT (application_id) DO UPDATE SET outcome = EXCLUDED.outcome, decided_at = EXCLUDED.decided_at, reason = EXCLUDED.reason", (app_id, outcome, _now(), reason))
                    cur.execute("UPDATE applications SET current_state='CLOSED', last_state_change_at=%s WHERE id=%s", (_now(), app_id))
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,'closed',%s,'user',%s)", (app_id, _now(), outcome))
            return self.get_application(app_id)  # type: ignore
        finally:
            conn.close()

    def add_event(self, app_id: int, event_type: str, actor: str = "user", payload: Optional[str] = None) -> Dict[str, Any]:
        if event_type not in GENERIC_ALLOWED_EVENTS:
            raise ValueError(f"Invalid event_type for generic endpoint: {event_type}. Allowed: {GENERIC_ALLOWED_EVENTS}")
        if actor not in ("user", "system"):
            raise ValueError("Invalid actor")
        # Allow-list payload to prevent secrets
        if payload and len(payload) > 2000:
            raise ValueError("Payload too large")
        conn = _conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM applications WHERE id = %s FOR UPDATE", (app_id,))
                    if not cur.fetchone():
                        raise ValueError("Application not found")
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,%s,%s,%s,%s)", (app_id, event_type, _now(), actor, payload))
            return self.get_timeline(app_id)[-1] if self.get_timeline(app_id) else {}
        finally:
            conn.close()


def get_application_service() -> ApplicationService:
    return ApplicationService()
