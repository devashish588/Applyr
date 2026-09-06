from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from core.services.application_service import _resolve_database_url, _now

ALLOWED_STAGES = {"PHONE_SCREEN","TECHNICAL","BEHAVIORAL","MANAGER","PANEL","FINAL","OTHER"}
ALLOWED_INTERVIEW_STATUS = {"SCHEDULED","COMPLETED","CANCELLED"}

def _conn():
    url = _resolve_database_url()
    return psycopg2.connect(url)

class InterviewStoreService:
    def create(self, application_id: int, stage: str = "OTHER", scheduled_at: Optional[str]=None, notes: Optional[str]=None) -> Dict[str, Any]:
        if stage not in ALLOWED_STAGES:
            raise ValueError(f"Invalid stage {stage}")
        if notes and len(notes) > 2000:
            raise ValueError("Notes too long")
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT current_state FROM applications WHERE id=%s FOR UPDATE", (application_id,))
                    if not cur.fetchone():
                        raise ValueError("Application not found")
                    cur.execute("INSERT INTO interviews (application_id, stage, status, scheduled_at, notes, created_at, updated_at) VALUES (%s,%s,'SCHEDULED',%s,%s,%s,%s) RETURNING *",
                                (application_id, stage, scheduled_at, notes, _now(), _now()))
                    row = cur.fetchone()
                    # event
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,'interview_scheduled',%s,'user',%s)",
                                (application_id, _now(), json.dumps({"stage": stage, "scheduled_at": scheduled_at})[:2000]))
            return self.get(row["id"])
        finally:
            conn.close()

    def complete(self, interview_id: int, notes: Optional[str]=None) -> Dict[str, Any]:
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT application_id, status FROM interviews WHERE id=%s FOR UPDATE", (interview_id,))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Interview not found")
                    if row["status"] != "SCHEDULED":
                        raise ValueError(f"Cannot complete interview in status {row['status']}")
                    cur.execute("UPDATE interviews SET status='COMPLETED', completed_at=%s, notes=COALESCE(%s, notes), updated_at=%s WHERE id=%s RETURNING *",
                                (_now(), notes, _now(), interview_id))
                    updated = cur.fetchone()
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,'interview_completed',%s,'user',%s)",
                                (row["application_id"], _now(), json.dumps({"interview_id": interview_id})[:2000]))
            return dict(updated)
        finally:
            conn.close()

    def cancel(self, interview_id: int) -> Dict[str, Any]:
        conn = _conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT application_id, status FROM interviews WHERE id=%s FOR UPDATE", (interview_id,))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Interview not found")
                    if row["status"] != "SCHEDULED":
                        raise ValueError(f"Cannot cancel interview in status {row['status']}")
                    cur.execute("UPDATE interviews SET status='CANCELLED', updated_at=%s WHERE id=%s RETURNING *",
                                (_now(), interview_id))
                    updated = cur.fetchone()
            return dict(updated)
        finally:
            conn.close()

    def list_for_application(self, application_id: int) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM interviews WHERE application_id=%s ORDER BY created_at ASC", (application_id,))
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get(self, interview_id: int) -> Optional[Dict[str,Any]]:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM interviews WHERE id=%s", (interview_id,))
                r = cur.fetchone()
                return dict(r) if r else None
        finally:
            conn.close()

_service=None
def get_interview_store_service():
    global _service
    if _service is None:
        _service=InterviewStoreService()
    return _service
