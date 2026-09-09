"""
Master Resume Service — single active resume with history preservation.
Active resume is authoritative for Candidate Intelligence / Studio new runs.
Historical applications retain their own tailored artifacts and snapshots.
No runtime DDL: tables come from db/migrations/011_master_resume.sql.
"""
from __future__ import annotations
import os
import uuid
import json
import logging
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

ALLOWED_EXTS = {"pdf", "docx", "doc", "txt"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB
ROOT = Path(__file__).parent.parent.parent
RESUME_DIR = ROOT / "resume"


def _resume_dir() -> Path:
    # Test isolation: MASTER_RESUME_DIR overrides production resume/ dir.
    # Production default remains resume/<uuid>_<safe>. No behavior change unless env set.
    override = os.getenv("MASTER_RESUME_DIR", "").strip()
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        return p
    return RESUME_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    base = os.path.basename(name or "")
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in base).strip()
    if not safe:
        safe = "resume.pdf"
    safe = safe.replace("..", "_")
    return safe[:120]


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _resolve_db_url() -> str:
    from core.services.application_service import _resolve_database_url
    return _resolve_database_url()


def _conn():
    url = _resolve_db_url()
    if not url:
        raise RuntimeError("DATABASE_URL not set (run migration 011_master_resume.sql)")
    return psycopg2.connect(url)


def _has_resumes_table(conn) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM resumes LIMIT 1")
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _parse_json_field(v):
    if not v:
        return v
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return v


class MasterResumeService:
    """Single-active resume registry. History rows retained with active=FALSE."""

    def get_active(self) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            if not _has_resumes_table(conn):
                logger.warning("[master_resume] resumes table missing (run migration 011_master_resume.sql); falling back to legacy resume_data")
                return self._legacy_fallback(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resumes WHERE active=TRUE ORDER BY uploaded_at DESC LIMIT 1")
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    for k in ("parsed_json", "skills_json", "roles_json", "health_json"):
                        d[k] = _parse_json_field(d.get(k))
                    return d
                # No active: distinguish never-used (fallback legacy) vs removed (return None)
                cur.execute("SELECT COUNT(*) AS c FROM resumes")
                cnt = cur.fetchone()["c"] if cur.description else 0
                if cnt == 0:
                    return self._legacy_fallback(conn)
                return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _legacy_fallback(self, conn) -> Optional[Dict[str, Any]]:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resume_data ORDER BY id DESC LIMIT 1")
                rd = cur.fetchone()
                if not rd:
                    return None
                rd = dict(rd)
                if rd.get("parse_status") != "success":
                    return None
                return {
                    "id": rd.get("id"),
                    "filename": rd.get("filename") or "legacy_resume",
                    "stored_path": rd.get("filename") or "",
                    "file_size": rd.get("file_size") or 0,
                    "status": "READY",
                    "active": True,
                    "uploaded_at": rd.get("uploaded_at"),
                    "parsed_at": rd.get("parsed_at"),
                    "parse_error": None,
                    "parsed_json": _parse_json_field(rd.get("parsed_json")),
                    "skills_json": _parse_json_field(rd.get("skills_json")),
                    "roles_json": _parse_json_field(rd.get("roles_json")),
                    "health_json": _parse_json_field(rd.get("health_json")),
                    "legacy": True,
                }
        except Exception:
            return None

    def list_all(self) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            if not _has_resumes_table(conn):
                active = self._legacy_fallback(conn)
                return [active] if active else []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, filename, stored_path, file_size, mime_type, status, active, uploaded_at, parsed_at, parse_error FROM resumes ORDER BY active DESC, uploaded_at DESC")
                return [dict(r) for r in cur.fetchall()]
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_by_id(self, rid: int) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            if not _has_resumes_table(conn):
                return None
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resumes WHERE id=%s", (rid,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                for k in ("parsed_json", "skills_json", "roles_json", "health_json"):
                    d[k] = _parse_json_field(d.get(k))
                return d
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def upload(self, file_storage) -> Dict[str, Any]:
        if not file_storage or not getattr(file_storage, "filename", None):
            raise ValueError("No file provided")
        orig = file_storage.filename
        # Reject path traversal in original name
        if ".." in orig or "/" in orig or "\\" in orig:
            # basename strips dirs, but explicit .. is malicious
            if ".." in orig:
                raise ValueError("Invalid filename")
        safe = _safe_filename(orig)
        ext = _ext(safe)
        if ext not in ALLOWED_EXTS:
            raise ValueError(f"Unsupported file type '.{ext or '(none)'}'. Allowed: {', '.join(sorted(ALLOWED_EXTS))}")
        try:
            data = file_storage.read()
        except Exception:
            raise ValueError("Could not read uploaded file")
        if not data:
            raise ValueError("Empty file")
        if len(data) > MAX_SIZE:
            raise ValueError(f"File too large ({len(data)} bytes). Max {MAX_SIZE}")
        mime, _ = mimetypes.guess_type(safe)
        rdir = _resume_dir()
        rdir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}_{safe}"
        stored_path = rdir / stored_name
        try:
            # Ensure stored path stays inside resume dir (no traversal)
            stored_path.resolve().relative_to(rdir.resolve())
        except Exception:
            raise ValueError("Invalid storage path")
        with open(stored_path, "wb") as f:
            f.write(data)
        file_size = len(data)
        uploaded_at = _now()

        conn = _conn()
        try:
            if not _has_resumes_table(conn):
                raise RuntimeError("resumes table missing (run migration 011_master_resume.sql)")
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO resumes (filename, stored_path, file_size, mime_type, status, active, uploaded_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (safe, str(stored_path), file_size, mime or "application/octet-stream", "PROCESSING", False, uploaded_at),
                )
                rid = cur.fetchone()[0]
            conn.commit()

            # Parse with existing parser (do not rewrite architecture)
            parsed_json = None
            skills_json: Any = []
            roles_json: Any = []
            health_json = None
            parse_error = None
            parse_ok = False
            try:
                from agents.resume_parser_agent import ResumeParserAgent
                agent = ResumeParserAgent()
                parsed_obj = agent.parse_file(str(stored_path))
                if parsed_obj:
                    parsed = parsed_obj.model_dump() if hasattr(parsed_obj, "model_dump") else dict(parsed_obj.__dict__)
                    # Minimal validation: must have some content
                    if parsed and (parsed.get("skills") or parsed.get("name") or parsed.get("experience")):
                        parse_ok = True
                        parsed_json = parsed
                        skills_json = parsed.get("skills") or []
                        roles_json = parsed.get("roles") or []
                        health_json = {"resume_parsed": True}
                    else:
                        parse_error = "Parser returned empty result"
                else:
                    parse_error = "Parser returned no result"
            except Exception as e:
                parse_error = str(e)[:2000]
                logger.warning("[master_resume] parse failed for %s: %s", safe, type(e).__name__)

            parsed_at = _now()
            if parse_ok:
                status = "READY"
                # Activate atomically: deactivate previous, activate new
                with conn.cursor() as cur:
                    cur.execute("UPDATE resumes SET active=FALSE WHERE active=TRUE")
                    cur.execute(
                        """UPDATE resumes SET status=%s, parsed_at=%s, parse_error=%s,
                           parsed_json=%s, skills_json=%s, roles_json=%s, health_json=%s, active=TRUE
                           WHERE id=%s""",
                        (status, parsed_at, None,
                         json.dumps(parsed_json) if parsed_json else None,
                         json.dumps(skills_json) if skills_json is not None else None,
                         json.dumps(roles_json) if roles_json is not None else None,
                         json.dumps(health_json) if health_json else None, rid),
                    )
                conn.commit()
                # Sync legacy resume_data for backward-compat consumers + invalidate caches.
                # TEST-aware: write via _conn() so TEST DB stays isolated; also clear get_db caches.
                try:
                    _sync_legacy_resume_data(
                        filename=safe, file_size=file_size, uploaded_at=uploaded_at,
                        parsed_at=parsed_at, parsed_json=parsed_json or {},
                        skills_json=skills_json or [], roles_json=roles_json or [],
                        health_json=health_json or {},
                    )
                except Exception as e:
                    logger.warning("[master_resume] legacy sync failed: %s", type(e).__name__)
                # Mirror to legacy pointer for file-based consumers (orchestrator fallback).
                # Versioned original preserved at stored_path; legacy pointer is a copy.
                # Uses isolated dir when MASTER_RESUME_DIR is set (tests), else production resume/.
                try:
                    legacy_map = {"pdf": "master_resume.pdf", "docx": "master_resume.docx", "doc": "master_resume.docx", "txt": "master_resume.txt"}
                    legacy_name = legacy_map.get(ext)
                    if legacy_name:
                        legacy_path = _resume_dir() / legacy_name
                        shutil.copyfile(stored_path, legacy_path)
                except Exception as e:
                    logger.warning("[master_resume] legacy mirror failed: %s", type(e).__name__)
            else:
                status = "FAILED"
                if not parse_error:
                    parse_error = "Resume parsing failed"
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE resumes SET status=%s, parsed_at=%s, parse_error=%s WHERE id=%s",
                        (status, parsed_at, parse_error, rid),
                    )
                conn.commit()
                # Do NOT activate, previous remains active. Remove orphan file? Keep for debugging but not active.

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resumes WHERE id=%s", (rid,))
                row = dict(cur.fetchone())
                for k in ("parsed_json", "skills_json", "roles_json", "health_json"):
                    row[k] = _parse_json_field(row.get(k))
                return row
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def remove_active(self) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            if not _has_resumes_table(conn):
                raise RuntimeError("resumes table missing (run migration 011_master_resume.sql)")
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM resumes WHERE active=TRUE LIMIT 1")
                row = cur.fetchone()
                if not row:
                    return None
                row = dict(row)
                cur.execute("UPDATE resumes SET active=FALSE, status='INACTIVE' WHERE id=%s", (row["id"],))
            conn.commit()
            # Clear legacy cache and delete legacy resume_data so candidate becomes UNKNOWN.
            try:
                _clear_legacy_resume_data()
                # Remove legacy pointer files (versioned originals retained, isolated dir aware).
                for n in ("master_resume.pdf", "master_resume.docx", "master_resume.txt"):
                    try:
                        p = _resume_dir() / n
                        if p.exists():
                            p.unlink()
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("[master_resume] remove invalidate failed: %s", type(e).__name__)
            for k in ("parsed_json", "skills_json", "roles_json", "health_json"):
                row[k] = _parse_json_field(row.get(k))
            return row
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _sync_legacy_resume_data(filename, file_size, uploaded_at, parsed_at, parsed_json, skills_json, roles_json, health_json) -> None:
    """TEST-aware mirror of active resume into resume_data (no runtime DDL). Clears caches."""
    import json as _json
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resume_data")
            cur.execute(
                """INSERT INTO resume_data
                   (filename, file_size, uploaded_at, parsed_at, parse_status, parsed_json, skills_json, roles_json, health_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (filename, file_size, uploaded_at, parsed_at, "success",
                 _json.dumps(parsed_json) if isinstance(parsed_json, (dict, list)) else parsed_json,
                 _json.dumps(skills_json) if isinstance(skills_json, (dict, list)) else skills_json,
                 _json.dumps(roles_json) if isinstance(roles_json, (dict, list)) else roles_json,
                 _json.dumps(health_json) if isinstance(health_json, (dict, list)) else health_json),
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass
    # Clear singleton caches (production pool) so stale reads do not persist
    try:
        from db.db_client import get_db
        db = get_db()
        db._cache_clear("resume_data")
        db._disk_invalidate("resume_data")
        try:
            db._disk_invalidate("candidate_intelligence")
        except Exception:
            pass
    except Exception:
        pass


def _clear_legacy_resume_data() -> None:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resume_data")
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass
    try:
        from db.db_client import get_db
        db = get_db()
        db._cache_clear("resume_data")
        db._disk_invalidate("resume_data")
        try:
            db._disk_invalidate("candidate_intelligence")
        except Exception:
            pass
    except Exception:
        pass


def get_master_resume_service() -> MasterResumeService:
    return MasterResumeService()
