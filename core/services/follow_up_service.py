from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from core.services.application_service import _resolve_database_url, _now

ALLOWED_TYPES = {"POST_APPLICATION","POST_SCREENING","POST_INTERVIEW","POST_OFFER"}
ALLOWED_CHANNELS = {"EMAIL","LINKEDIN","OTHER"}
ALLOWED_STATUS = {"DRAFT","REVIEW","APPROVED","SENT","CANCELLED"}

def _conn():
    return psycopg2.connect(_resolve_database_url())

class FollowUpService:
    def create(self, application_id: int, follow_up_type: str="POST_APPLICATION", channel: str="EMAIL", scheduled_at: Optional[str]=None, subject: Optional[str]=None, message_preview: Optional[str]=None) -> Dict[str,Any]:
        if follow_up_type not in ALLOWED_TYPES:
            raise ValueError(f"Invalid follow_up_type {follow_up_type}")
        if channel not in ALLOWED_CHANNELS:
            raise ValueError(f"Invalid channel {channel}")
        if message_preview and len(message_preview) > 2000:
            raise ValueError("message_preview too long")
        conn=_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT id FROM applications WHERE id=%s FOR UPDATE", (application_id,))
                    if not cur.fetchone():
                        raise ValueError("Application not found")
                    cur.execute("INSERT INTO follow_ups (application_id, follow_up_type, channel, status, scheduled_at, subject, message_preview, created_at, updated_at) VALUES (%s,%s,%s,'DRAFT',%s,%s,%s,%s,%s) RETURNING *",
                                (application_id, follow_up_type, channel, scheduled_at, subject, message_preview, _now(), _now()))
                    row=cur.fetchone()
                    # No event yet — only when sent
            return dict(row)
        finally:
            conn.close()

    def review(self, follow_up_id: int) -> Dict[str,Any]:
        conn=_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT status FROM follow_ups WHERE id=%s FOR UPDATE", (follow_up_id,))
                    r=cur.fetchone()
                    if not r: raise ValueError("Follow-up not found")
                    if r["status"] != "DRAFT":
                        raise ValueError(f"Cannot review from {r['status']}")
                    cur.execute("UPDATE follow_ups SET status='REVIEW', updated_at=%s WHERE id=%s RETURNING *", (_now(), follow_up_id))
                    row=cur.fetchone()
            return dict(row)
        finally:
            conn.close()

    def approve(self, follow_up_id: int) -> Dict[str,Any]:
        conn=_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT status, application_id FROM follow_ups WHERE id=%s FOR UPDATE", (follow_up_id,))
                    r=cur.fetchone()
                    if not r: raise ValueError("Follow-up not found")
                    if r["status"] != "REVIEW":
                        raise ValueError(f"Cannot approve from {r['status']}: must be REVIEW")
                    cur.execute("UPDATE follow_ups SET status='APPROVED', updated_at=%s WHERE id=%s RETURNING *", (_now(), follow_up_id))
                    row=cur.fetchone()
            return dict(row)
        finally:
            conn.close()

    def mark_sent(self, follow_up_id: int) -> Dict[str,Any]:
        conn=_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT status, application_id FROM follow_ups WHERE id=%s FOR UPDATE", (follow_up_id,))
                    r=cur.fetchone()
                    if not r: raise ValueError("Follow-up not found")
                    if r["status"] != "APPROVED":
                        raise ValueError("Must be APPROVED before SENT")
                    cur.execute("UPDATE follow_ups SET status='SENT', sent_at=%s, updated_at=%s WHERE id=%s RETURNING *", (_now(), _now(), follow_up_id))
                    row=cur.fetchone()
                    cur.execute("INSERT INTO application_events (application_id, event_type, timestamp, actor, payload) VALUES (%s,'follow_up_sent',%s,'user',%s)",
                                (r["application_id"], _now(), json.dumps({"follow_up_id": follow_up_id})[:2000]))
                    # Link event
                    cur.execute("SELECT currval(pg_get_serial_sequence('application_events','id'))")
                    eid=cur.fetchone()["currval"]
                    cur.execute("UPDATE follow_ups SET event_id=%s WHERE id=%s", (eid, follow_up_id))
            return dict(row)
        finally:
            conn.close()

    def list_for_application(self, application_id: int) -> List[Dict[str,Any]]:
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM follow_ups WHERE application_id=%s ORDER BY created_at ASC", (application_id,))
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

_service=None
def get_follow_up_service():
    global _service
    if _service is None:
        _service=FollowUpService()
    return _service
