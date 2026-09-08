"""
Job Attribution — cross-source additive layer (33.1)
Canonical job retains multiple source observations without duplicating canonical identity.
Uses job_source_attributions table (009). Fail-open if table missing (migration not yet applied).
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

def _now():
    return datetime.now().isoformat()

class JobAttributionService:
    def _db(self):
        try:
            from db.db_client import get_db
            return get_db()
        except Exception:
            return None

    def _table_exists(self, conn) -> bool:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM job_source_attributions LIMIT 1")
            return True
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def _resolve_canonical_id(self, job_url: str, canonical_id: str | None, title: str | None = None, company: str | None = None, location: str | None = None) -> Optional[int]:
        """Resolve canonical job id via existing dedup semantics, plus cross-host fallback for same title/company."""
        db = self._db()
        if not db:
            return None
        conn = None
        try:
            conn = db._conn()
            if job_url:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, canonical_id, is_duplicate_of FROM jobs WHERE url=%s LIMIT 1", (job_url,))
                    row = cur.fetchone()
                    if row:
                        dup_of = row[2] if len(row)>2 else None
                        cid = int(dup_of) if dup_of else int(row[0])
                        return cid
            if canonical_id:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM jobs WHERE canonical_id=%s AND is_duplicate_of IS NULL ORDER BY id ASC LIMIT 1", (canonical_id,))
                    row = cur.fetchone()
                    if row:
                        return int(row[0])
                # 33.1 Cross-host fallback: same title/company/location but different host should still be same underlying job
                # Try host-agnostic match via normalized title/company/location
                if title and company:
                    try:
                        from core.services.job_canonical_service import normalize_title, _normalize_company, _normalize_location
                        nt = " ".join(normalize_title(title).lower().split())
                        nc = _normalize_company(company)
                        nl = _normalize_location(location or "")
                        # Search for canonical with same normalized components (host-agnostic)
                        # Use Python-level filtering to avoid SQL normalizer mismatch
                        with conn.cursor() as cur2:
                            cur2.execute("SELECT id, title, company, location FROM jobs WHERE is_duplicate_of IS NULL")
                            for rid, rt, rc, rl in cur2.fetchall():
                                if _normalize_company(rc) == nc and " ".join(normalize_title(rt or "").lower().split()) == nt and _normalize_location(rl or "") == nl:
                                    return int(rid)
                    except Exception:
                        pass
            return None
        except Exception as e:
            logger.debug("[attribution] resolve canonical failed: %s", e)
            return None
        finally:
            if conn:
                try:
                    db._put_conn(conn)
                except Exception:
                    pass

    def record_observation(self, *, source_id: str, source_name: str, host: str, mode: str, adapter: str, source_url: str, canonical_job_id: Optional[int] = None, job_url: Optional[str] = None, canonical_id: Optional[str] = None, title: str | None = None, company: str | None = None, location: str | None = None):
        """Additive: record that canonical job was observed via source. No duplicate canonical creation."""
        # Resolve canonical if not given (with cross-host title/company fallback)
        if canonical_job_id is None:
            canonical_job_id = self._resolve_canonical_id(job_url or source_url, canonical_id, title=title, company=company, location=location)
        if not canonical_job_id:
            logger.debug("[attribution] no canonical for %s", source_url)
            return
        db = self._db()
        if not db:
            return
        conn = None
        try:
            conn = db._conn()
            if not self._table_exists(conn):
                # Table missing -> migration not applied, fail-open without DDL
                try:
                    db._put_conn(conn)
                except Exception:
                    pass
                logger.warning("[attribution] job_source_attributions missing (run 009 migration)")
                return
            now = _now()
            with conn.cursor() as cur:
                # Insert or update last_seen
                cur.execute("""
                    INSERT INTO job_source_attributions (canonical_job_id, source_id, source_name, host, mode, adapter, source_url, first_seen_at, last_seen_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (canonical_job_id, source_id, source_url) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at
                """, (canonical_job_id, source_id, source_name, host, mode.upper(), adapter, source_url, now, now))
            conn.commit()
            db._put_conn(conn)
        except Exception as e:
            logger.warning("[attribution] record failed: %s", e)
            if conn:
                try:
                    conn.rollback()
                    db._put_conn(conn)
                except Exception:
                    pass

    def get_for_job(self, canonical_job_id: int) -> list[dict]:
        db = self._db()
        if not db:
            return []
        conn = None
        try:
            conn = db._conn()
            if not self._table_exists(conn):
                db._put_conn(conn)
                return []
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM job_source_attributions WHERE canonical_job_id=%s ORDER BY first_seen_at ASC", (canonical_job_id,))
                rows = [dict(r) for r in cur.fetchall()]
            db._put_conn(conn)
            return rows
        except Exception as e:
            logger.warning("[attribution] get failed: %s", e)
            if conn:
                try:
                    conn.rollback()
                    db._put_conn(conn)
                except Exception:
                    pass
            return []

    def get_for_canonical_or_duplicate(self, job_id: int) -> list[dict]:
        """If job is duplicate, resolve to canonical first."""
        db = self._db()
        if not db:
            return []
        conn = None
        try:
            conn = db._conn()
            with conn.cursor() as cur:
                cur.execute("SELECT id, is_duplicate_of FROM jobs WHERE id=%s", (job_id,))
                row = cur.fetchone()
                if not row:
                    db._put_conn(conn)
                    return []
                canonical = int(row[1]) if row[1] else int(row[0])
            db._put_conn(conn)
            return self.get_for_job(canonical)
        except Exception:
            if conn:
                try:
                    db._put_conn(conn)
                except Exception:
                    pass
            return []

_attribution_singleton = None
def get_attribution_service() -> JobAttributionService:
    global _attribution_singleton
    if _attribution_singleton is None:
        _attribution_singleton = JobAttributionService()
    return _attribution_singleton
