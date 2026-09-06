from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from core.services.application_service import _resolve_database_url, _now

ALLOWED_SIGNALS = {"RECOMMENDATION_USEFUL","RECOMMENDATION_NOT_USEFUL","PREP_USEFUL","PREP_NOT_USEFUL","APPLICATION_WORTHWHILE","APPLICATION_NOT_WORTHWHILE"}

def _conn():
    return psycopg2.connect(_resolve_database_url())

class FeedbackService:
    def create(self, application_id: Optional[int]=None, job_id: Optional[int]=None, signal_type: str="", value: Optional[str]=None) -> Dict[str,Any]:
        if signal_type not in ALLOWED_SIGNALS:
            raise ValueError(f"Invalid signal_type {signal_type}")
        if value and len(value) > 500:
            raise ValueError("value too long (max 500)")
        conn=_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Validate application/job exists if provided
                    if application_id is not None:
                        cur.execute("SELECT id FROM applications WHERE id=%s", (application_id,))
                        if not cur.fetchone():
                            raise ValueError("Application not found")
                    if job_id is not None:
                        cur.execute("SELECT id FROM jobs WHERE id=%s", (job_id,))
                        if not cur.fetchone():
                            raise ValueError("Job not found")
                    cur.execute("INSERT INTO feedback (application_id, job_id, signal_type, value, created_at) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                                (application_id, job_id, signal_type, value, _now()))
                    row=cur.fetchone()
            return dict(row)
        finally:
            conn.close()
    def list(self, application_id: Optional[int]=None) -> List[Dict[str,Any]]:
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if application_id:
                    cur.execute("SELECT * FROM feedback WHERE application_id=%s ORDER BY created_at ASC", (application_id,))
                else:
                    cur.execute("SELECT * FROM feedback ORDER BY created_at ASC LIMIT 100")
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

_service=None
def get_feedback_service():
    global _service
    if _service is None:
        _service=FeedbackService()
    return _service
