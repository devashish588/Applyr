"""
JobSource Service — Multi-Source Job Discovery registry.

Single-user, local, modular monolith. No Redis/Kafka.
Persists to PostgreSQL `job_sources` table; falls back to in-memory + JSON seed
when DB unavailable (tests). Seeds built-in _JOB_SITE_POOL as search sources.

Contract per-source: {source_id,status,adapter,jobs_found/jobs_normalized/jobs_new/jobs_duplicate,failure_category,error,duration_ms}
Failure categories: SUCCESS, NO_RESULTS, TIMEOUT, HTTP_ERROR, BLOCKED, ROBOTS_DISALLOWED,
                    AUTH_REQUIRED, PARSER_ERROR, SCHEMA_CHANGED, RATE_LIMITED, UNSUPPORTED, NETWORK, UNKNOWN
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_BUILTIN_POOL = [
    "linkedin.com/jobs", "wellfound.com", "indeed.com", "ycombinator.com",
    "weworkremotely.com", "remoteok.com", "builtin.com", "dice.com",
    "glassdoor.com", "naukri.com", "remotive.com", "arc.dev",
]

# Map host substring -> (source_type, adapter)
_HOST_MAP = {
    "greenhouse.io": ("ats", "ATSAdapter"),
    "lever.co": ("ats", "ATSAdapter"),
    "myworkdayjobs.com": ("ats", "ATSAdapter"),
    "ashbyhq.com": ("ats", "ATSAdapter"),
    "workable.com": ("ats", "ATSAdapter"),
    "bamboohr.com": ("ats", "ATSAdapter"),
    "rss": ("rss", "RSSAdapter"),
    "feed": ("rss", "RSSAdapter"),
    "api": ("json", "JSONAdapter"),
}

VALID_FAILURE_CATEGORIES = {
    "SUCCESS", "NO_RESULTS", "FILTERED", "TIMEOUT", "HTTP_ERROR", "BLOCKED",
    "ROBOTS_DISALLOWED", "AUTH", "AUTH_REQUIRED", "PARSER_ERROR", "SCHEMA_CHANGED",
    "RATE_LIMITED", "UNSUPPORTED", "UNSUPPORTED_SOURCE", "NETWORK", "NETWORK_ERROR", "PROVIDER_ERROR", "UNKNOWN",
}

# Source policy vocabulary (single enum)
SOURCE_ROLES = {"EMPLOYER","JOB_BOARD","AGGREGATOR","ATS","FEED","SEARCH","CUSTOM","UNKNOWN"}
SOURCE_MODES = {"HTML","RSS","JSON","ATS","SEARCH","PLAYWRIGHT","UNSUPPORTED","AUTO"}

# Minimal built-in host → policy (source_role, primary_mode, direct_fetch_allowed, search_discovery_allowed)
# Wellfound and boards → JOB_BOARD SEARCH direct false (must not direct crawl)
# Aggregators → AGGREGATOR SEARCH direct false
# ATS → ATS ATS direct true
# Company careers (custom) → EMPLOYER HTML direct true (inferred when not in map)
_BUILTIN_POLICY = {
    "wellfound.com": ("JOB_BOARD","SEARCH", False, True),
    "linkedin.com": ("JOB_BOARD","SEARCH", False, True),
    "indeed.com": ("JOB_BOARD","SEARCH", False, True),
    "glassdoor.com": ("JOB_BOARD","SEARCH", False, True),
    "dice.com": ("JOB_BOARD","SEARCH", False, True),
    "naukri.com": ("JOB_BOARD","SEARCH", False, True),
    "ycombinator.com": ("JOB_BOARD","SEARCH", False, True),
    "builtin.com": ("JOB_BOARD","SEARCH", False, True),
    "arc.dev": ("JOB_BOARD","SEARCH", False, True),
    "weworkremotely.com": ("AGGREGATOR","SEARCH", False, True),
    "remoteok.com": ("AGGREGATOR","SEARCH", False, True),
    "remotive.com": ("FEED","RSS", True, True),  # FEED but also supports RSS/JSON
    "greenhouse.io": ("ATS","ATS", True, True),
    "boards.greenhouse.io": ("ATS","ATS", True, True),
    "lever.co": ("ATS","ATS", True, True),
    "jobs.lever.co": ("ATS","ATS", True, True),
    "ashbyhq.com": ("ATS","ATS", True, True),
    "myworkdayjobs.com": ("ATS","ATS", True, True),
    "workable.com": ("ATS","ATS", True, True),
    "bamboohr.com": ("ATS","ATS", True, True),
}

def _policy_for_host(host: str, source_type: str, explicit_role: str | None = None) -> tuple[str, str, bool, bool]:
    h = (host or "").lower()
    # Explicit role overrides
    if explicit_role and explicit_role.upper() in SOURCE_ROLES:
        r = explicit_role.upper()
        # Map role to sensible defaults if not in built-in map
        if r == "EMPLOYER":
            return ("EMPLOYER","HTML", True, True)
        if r == "JOB_BOARD":
            return ("JOB_BOARD","SEARCH", False, True)
        if r == "ATS":
            return ("ATS","ATS", True, True)
        if r == "FEED":
            # FEED could be RSS or JSON, keep original source_type if rss/json else RSS
            mode = "RSS" if source_type == "rss" else ("JSON" if source_type=="json" else "RSS")
            return ("FEED", mode, True, True)
        return (r, "AUTO", True, True)
    for k, v in _BUILTIN_POLICY.items():
        if h == k or h.endswith("."+k) or k in h:
            return v
    # Custom / unknown → infer from source_type
    if source_type == "ats":
        return ("ATS","ATS", True, True)
    if source_type == "rss":
        return ("FEED","RSS", True, True)
    if source_type == "json":
        return ("FEED","JSON", True, True)
    if source_type == "search":
        return ("JOB_BOARD","SEARCH", False, True)
    # Default for company careers and custom
    return ("EMPLOYER","HTML", True, True) if source_type=="html" else ("CUSTOM","AUTO", True, True)

def _now() -> str:
    return datetime.now().isoformat()

def _host_from_url(url: str) -> str:
    try:
        h = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        if h.startswith("www."):
            h = h[4:]
        return h.split(":")[0]
    except Exception:
        return url.lower().split("/")[0]

def _classify_url(url: str, explicit_type: str | None = None) -> tuple[str, str]:
    if explicit_type:
        t = explicit_type.lower()
        if t in ("html", "generic"):
            return "html", "GenericHTMLAdapter"
        if t in ("rss", "feed"):
            return "rss", "RSSAdapter"
        if t in ("json", "api"):
            return "json", "JSONAdapter"
        if t == "ats":
            return "ats", "ATSAdapter"
        if t == "search":
            return "search", "SearchAdapter"
    low = url.lower()
    for k, v in _HOST_MAP.items():
        if k in low:
            return v
    if low.endswith(".rss") or low.endswith(".xml") or "/rss" in low or "/feed" in low:
        return "rss", "RSSAdapter"
    if "/api/" in low or low.endswith(".json"):
        return "json", "JSONAdapter"
    # default: search for pool sites (Tavily), html for arbitrary company URLs
    if any(h in low for h in ("linkedin.com", "indeed.com", "wellfound.com", "ycombinator.com",
                               "weworkremotely.com", "remoteok.com", "builtin.com", "dice.com",
                               "glassdoor.com", "naukri.com", "remotive.com", "arc.dev")):
        return "search", "SearchAdapter"
    return "html", "GenericHTMLAdapter"

def _id_from_url(url: str) -> str:
    host = _host_from_url(url)
    slug = re.sub(r"[^a-z0-9]+", "-", host)[:40].strip("-")
    short = re.sub(r"[^a-z0-9]+", "-", url.lower())[:16].strip("-")
    return f"{slug}-{short}-{str(uuid.uuid4())[:4]}"

@dataclass
class JobSource:
    id: str
    name: str
    url: str
    host: str
    enabled: bool
    source_type: str
    adapter: str
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    last_job_count: int = 0
    last_duration_ms: int = 0
    failure_category: Optional[str] = None
    last_error: Optional[str] = None
    priority: int = 100
    is_builtin: Optional[bool] = None
    last_failure_category: Optional[str] = None
    # Source policy (010)
    source_role: str = "UNKNOWN"
    primary_mode: str = "AUTO"
    direct_fetch_allowed: bool = True
    search_discovery_allowed: bool = True
    observed_mode: Optional[str] = None
    observed_success_count: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        # is_builtin: authoritative is id prefix for built-ins, but allow DB override for custom
        if isinstance(self.is_builtin, bool):
            # If DB has explicit true, honor it; if false but id is builtin, correct to true
            if self.id.startswith("builtin-"):
                d["is_builtin"] = True
            else:
                d["is_builtin"] = self.is_builtin
        else:
            d["is_builtin"] = bool(self.id.startswith("builtin-"))
        d["last_failure_category"] = self.failure_category if self.last_failure_at else None
        if d.get("source_role") not in SOURCE_ROLES:
            d["source_role"] = "UNKNOWN"
        if d.get("primary_mode") not in SOURCE_MODES:
            d["primary_mode"] = "AUTO"
        return d

class JobSourceService:
    """Registry + per-source execution."""

    _instance: Optional["JobSourceService"] = None

    @classmethod
    def get_instance(cls) -> "JobSourceService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._mem: dict[str, JobSource] = {}
        self._seeded = False

    # -- persistence helpers --
    def _db(self):
        try:
            from db.db_client import get_db
            return get_db()
        except Exception:
            return None

    def _ensure_table(self):
        """Check job_sources exists; do NOT create DDL here. Migration 008 is authoritative."""
        db = self._db()
        if not db:
            return False
        conn = None
        try:
            conn = db._conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM job_sources LIMIT 1")
            conn.commit()
            db._put_conn(conn)
            return True
        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    db._put_conn(conn)
            except Exception:
                pass
            logger.warning("[job_source] job_sources table not available (run migration 008_job_sources.sql): %s", e)
            return False

    def _load_all(self) -> dict[str, JobSource]:
        db = self._db()
        if db and self._ensure_table():
            try:
                conn = db._conn()
                try:
                    from psycopg2.extras import RealDictCursor
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT * FROM job_sources ORDER BY created_at ASC")
                        rows = cur.fetchall()
                    if rows:
                        out = {}
                        for r in rows:
                            d = dict(r)
                            d["enabled"] = bool(d.get("enabled"))
                            # Normalize policy defaults if columns missing (pre-010)
                            if d.get("source_role") is None:
                                role, mode, direct, search = _policy_for_host(d.get("host",""), d.get("source_type",""))
                                d.setdefault("source_role", role)
                                d.setdefault("primary_mode", mode)
                                d.setdefault("direct_fetch_allowed", direct)
                                d.setdefault("search_discovery_allowed", search)
                            else:
                                # ensure booleans
                                d["direct_fetch_allowed"] = bool(d.get("direct_fetch_allowed")) if d.get("direct_fetch_allowed") is not None else True
                                d["search_discovery_allowed"] = bool(d.get("search_discovery_allowed")) if d.get("search_discovery_allowed") is not None else True
                            # handle missing priority/is_builtin
                            if d.get("priority") is None:
                                d["priority"] = 100
                            # Build JobSource, only include known fields
                            filtered = {k: d.get(k) for k in JobSource.__dataclass_fields__ if k in d}
                            # Fill missing with defaults via dataclass defaults
                            out[d["id"]] = JobSource(**filtered)
                        self._mem = out
                        self._seeded = True
                        return out
                finally:
                    db._put_conn(conn)
            except Exception as e:
                logger.warning("[job_source] load failed: %s", e)
        # seed built-ins if empty
        if not self._mem and not self._seeded:
            self._seed_builtins()
        return self._mem

    def _seed_builtins(self):
        now = _now()
        for entry in _BUILTIN_POOL:
            url = entry if "://" in entry else f"https://{entry}"
            host = _host_from_url(url)
            sid = f"builtin-{re.sub(r'[^a-z0-9]+','-',host)[:30].strip('-')}"
            if sid in self._mem:
                continue
            st, ad = _classify_url(url)
            role, mode, direct, search = _policy_for_host(host, st)
            self._mem[sid] = JobSource(
                id=sid, name=host.title(), url=url, host=host,
                enabled=True, source_type=st, adapter=ad,
                created_at=now, updated_at=now,
                source_role=role, primary_mode=mode, direct_fetch_allowed=direct, search_discovery_allowed=search,
            )
        self._seeded = True
        # persist seeds if DB available
        db = self._db()
        if db and self._ensure_table():
            try:
                conn = db._conn()
                try:
                    with conn.cursor() as cur:
                        for s in self._mem.values():
                            cur.execute("""
                                INSERT INTO job_sources (id,name,url,host,enabled,source_type,adapter,created_at,updated_at)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                            """, (s.id, s.name, s.url, s.host, s.enabled, s.source_type, s.adapter, s.created_at, s.updated_at))
                    conn.commit()
                finally:
                    db._put_conn(conn)
            except Exception as e:
                logger.warning("[job_source] seed persist failed: %s", e)
                try:
                    conn.rollback()
                except Exception:
                    pass

    # -- public API --
    def list_sources(self) -> list[JobSource]:
        return list(self._load_all().values())

    def list_enabled(self) -> list[JobSource]:
        return [s for s in self.list_sources() if s.enabled]

    def get(self, source_id: str) -> Optional[JobSource]:
        return self._load_all().get(source_id)

    def upsert(self, url: str, name: str | None = None, enabled: bool = True,
               source_type: str | None = None, sid: str | None = None, source_role: str | None = None) -> JobSource:
        url = url.strip()
        if not url:
            raise ValueError("url required")
        if "://" not in url:
            url = f"https://{url}"
        host = _host_from_url(url)
        st, ad = _classify_url(url, source_type)
        role, mode, direct, search = _policy_for_host(host, st, explicit_role=source_role)
        # Allow explicit overrides for legacy callers that pass source_type as role
        now = _now()
        # dedup by host+url
        existing = None
        for s in self._load_all().values():
            if s.host == host and s.url.rstrip("/") == url.rstrip("/"):
                existing = s
                break
        if existing:
            existing.name = name or existing.name
            existing.enabled = enabled
            existing.source_type = st
            existing.adapter = ad
            existing.url = url
            existing.updated_at = now
            existing.host = host
            existing.source_role = role
            existing.primary_mode = mode
            existing.direct_fetch_allowed = direct
            existing.search_discovery_allowed = search
            self._persist(existing)
            return existing
        nid = sid or _id_from_url(url)
        # ensure unique
        base = nid
        i = 1
        while nid in self._mem:
            nid = f"{base}-{i}"
            i += 1
        js = JobSource(id=nid, name=name or host.title(), url=url, host=host,
                       enabled=enabled, source_type=st, adapter=ad,
                       created_at=now, updated_at=now,
                       source_role=role, primary_mode=mode, direct_fetch_allowed=direct, search_discovery_allowed=search)
        self._mem[nid] = js
        self._persist(js)
        return js

    def update(self, source_id: str, **patch) -> Optional[JobSource]:
        s = self.get(source_id)
        if not s:
            return None
        for k in ("name", "url", "enabled", "source_type", "adapter", "priority", "source_role", "primary_mode", "direct_fetch_allowed", "search_discovery_allowed"):
            if k in patch and patch[k] is not None:
                setattr(s, k, patch[k])
        if "url" in patch and patch["url"]:
            s.host = _host_from_url(patch["url"])
            if "source_type" not in patch:
                st, ad = _classify_url(s.url)
                s.source_type = st
                s.adapter = ad
            # Recompute policy if role/mode not explicitly patched
            if "source_role" not in patch or "primary_mode" not in patch:
                role, mode, direct, search = _policy_for_host(s.host, s.source_type, explicit_role=patch.get("source_role") or s.source_role)
                if "source_role" not in patch:
                    s.source_role = role
                if "primary_mode" not in patch:
                    s.primary_mode = mode
                if "direct_fetch_allowed" not in patch:
                    s.direct_fetch_allowed = direct
                if "search_discovery_allowed" not in patch:
                    s.search_discovery_allowed = search
        s.updated_at = _now()
        self._persist(s)
        return s

    def delete(self, source_id: str) -> bool:
        if source_id not in self._load_all():
            return False
        self._mem.pop(source_id, None)
        db = self._db()
        if db and self._ensure_table():
            try:
                conn = db._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM job_sources WHERE id = %s", (source_id,))
                    conn.commit()
                finally:
                    db._put_conn(conn)
            except Exception as e:
                logger.warning("[job_source] delete failed: %s", e)
        return True

    def set_enabled(self, source_id: str, enabled: bool) -> Optional[JobSource]:
        return self.update(source_id, enabled=enabled)

    def _persist(self, s: JobSource):
        self._mem[s.id] = s
        db = self._db()
        if not db or not self._ensure_table():
            return
        # Try with policy columns (010), fallback to legacy if columns missing (pre-migration)
        for attempt in (0,1):
            try:
                conn = db._conn()
                try:
                    with conn.cursor() as cur:
                        if attempt == 0:
                            cur.execute("""
                                INSERT INTO job_sources (id,name,url,host,enabled,source_type,adapter,created_at,updated_at,
                                                         last_run_at,last_success_at,last_failure_at,last_job_count,last_duration_ms,failure_category,last_error,
                                                         source_role,primary_mode,direct_fetch_allowed,search_discovery_allowed,priority,is_builtin,observed_mode,observed_success_count)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT (id) DO UPDATE SET
                                    name=EXCLUDED.name, url=EXCLUDED.url, host=EXCLUDED.host, enabled=EXCLUDED.enabled,
                                    source_type=EXCLUDED.source_type, adapter=EXCLUDED.adapter, updated_at=EXCLUDED.updated_at,
                                    last_run_at=EXCLUDED.last_run_at, last_success_at=EXCLUDED.last_success_at,
                                    last_failure_at=EXCLUDED.last_failure_at, last_job_count=EXCLUDED.last_job_count,
                                    last_duration_ms=EXCLUDED.last_duration_ms, failure_category=EXCLUDED.failure_category,
                                    last_error=EXCLUDED.last_error, source_role=EXCLUDED.source_role, primary_mode=EXCLUDED.primary_mode,
                                    direct_fetch_allowed=EXCLUDED.direct_fetch_allowed, search_discovery_allowed=EXCLUDED.search_discovery_allowed,
                                    priority=EXCLUDED.priority, is_builtin=EXCLUDED.is_builtin, observed_mode=EXCLUDED.observed_mode, observed_success_count=EXCLUDED.observed_success_count
                            """, (s.id, s.name, s.url, s.host, s.enabled, s.source_type, s.adapter, s.created_at, s.updated_at,
                                   s.last_run_at, s.last_success_at, s.last_failure_at, s.last_job_count, s.last_duration_ms,
                                   s.failure_category, s.last_error, s.source_role, s.primary_mode, s.direct_fetch_allowed, s.search_discovery_allowed, s.priority, s.is_builtin, s.observed_mode, s.observed_success_count))
                        else:
                            cur.execute("""
                                INSERT INTO job_sources (id,name,url,host,enabled,source_type,adapter,created_at,updated_at,
                                                         last_run_at,last_success_at,last_failure_at,last_job_count,last_duration_ms,failure_category,last_error)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT (id) DO UPDATE SET
                                    name=EXCLUDED.name, url=EXCLUDED.url, host=EXCLUDED.host, enabled=EXCLUDED.enabled,
                                    source_type=EXCLUDED.source_type, adapter=EXCLUDED.adapter, updated_at=EXCLUDED.updated_at,
                                    last_run_at=EXCLUDED.last_run_at, last_success_at=EXCLUDED.last_success_at,
                                    last_failure_at=EXCLUDED.last_failure_at, last_job_count=EXCLUDED.last_job_count,
                                    last_duration_ms=EXCLUDED.last_duration_ms, failure_category=EXCLUDED.failure_category,
                                    last_error=EXCLUDED.last_error
                            """, (s.id, s.name, s.url, s.host, s.enabled, s.source_type, s.adapter, s.created_at, s.updated_at,
                                   s.last_run_at, s.last_success_at, s.last_failure_at, s.last_job_count, s.last_duration_ms,
                                   s.failure_category, s.last_error))
                    conn.commit()
                finally:
                    db._put_conn(conn)
                break
            except Exception as e:
                try:
                    conn.rollback()
                    db._put_conn(conn)
                except Exception:
                    pass
                if attempt == 0 and ("column" in str(e).lower() or "does not exist" in str(e)):
                    continue
                logger.warning("[job_source] persist failed: %s", e)
                break

    def record_run(self, source_id: str, result: dict):
        """Update last_* fields from per-source result contract."""
        s = self.get(source_id)
        if not s:
            return
        now = _now()
        s.last_run_at = now
        s.last_duration_ms = int(result.get("duration_ms", 0) or 0)
        s.last_job_count = int(result.get("jobs_found", 0) or 0)
        cat = result.get("failure_category") or ("SUCCESS" if result.get("status") == "success" else "UNKNOWN")
        if cat not in VALID_FAILURE_CATEGORIES:
            cat = "UNKNOWN"
        s.failure_category = cat
        if result.get("status") == "success" and cat in ("SUCCESS", "NO_RESULTS"):
            s.last_success_at = now
            s.last_error = None
        else:
            s.last_failure_at = now
            s.last_error = (result.get("error") or "")[:2000]
        s.updated_at = now
        self._persist(s)

    # -- per-source run logs (for Pipeline Status) --
    def start_source_run(self, run_id: str, source_id: str, adapter: str) -> int | None:
        db = self._db()
        if not db or not self._ensure_table():
            return None
        try:
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO job_source_runs (run_id, source_id, started_at, status, adapter)
                        VALUES (%s,%s,%s,'running',%s) RETURNING id
                    """, (run_id, source_id, _now(), adapter))
                    rid = cur.fetchone()[0]
                conn.commit()
                return rid
            finally:
                db._put_conn(conn)
        except Exception as e:
            logger.warning("[job_source] start_source_run failed: %s", e)
            return None

    def finish_source_run(self, run_row_id: int | None, result: dict):
        if not run_row_id:
            return
        db = self._db()
        if not db:
            return
        # Sanitize error for telemetry (no secrets)
        try:
            from core.ai.errors import sanitize_exception_message as _san
            _err = _san(str(result.get("error") or ""))[:2000]
        except Exception:
            _err = (result.get("error") or "")[:2000]
        # Try extended observability columns if migration 013 applied, else fallback
        for attempt in (0, 1):
            try:
                conn = db._conn()
                try:
                    with conn.cursor() as cur:
                        if attempt == 0:
                            cur.execute("""
                                UPDATE job_source_runs SET finished_at=%s, status=%s,
                                    jobs_found=%s, jobs_normalized=%s, jobs_new=%s, jobs_duplicate=%s,
                                    failure_category=%s, error=%s, duration_ms=%s,
                                    provider_raw_count=%s, site_mismatch_count=%s
                                WHERE id=%s
                            """, (_now(), result.get("status", "unknown"),
                                  int(result.get("jobs_found", 0) or 0),
                                  int(result.get("jobs_normalized", 0) or 0),
                                  int(result.get("jobs_new", 0) or 0),
                                  int(result.get("jobs_duplicate", 0) or 0),
                                  result.get("failure_category"), _err,
                                  int(result.get("duration_ms", 0) or 0),
                                  int(result.get("provider_raw_count", 0) or 0),
                                  int(result.get("site_mismatch_count", 0) or 0),
                                  run_row_id))
                        else:
                            cur.execute("""
                                UPDATE job_source_runs SET finished_at=%s, status=%s,
                                    jobs_found=%s, jobs_normalized=%s, jobs_new=%s, jobs_duplicate=%s,
                                    failure_category=%s, error=%s, duration_ms=%s
                                WHERE id=%s
                            """, (_now(), result.get("status", "unknown"),
                                  int(result.get("jobs_found", 0) or 0),
                                  int(result.get("jobs_normalized", 0) or 0),
                                  int(result.get("jobs_new", 0) or 0),
                                  int(result.get("jobs_duplicate", 0) or 0),
                                  result.get("failure_category"), _err,
                                  int(result.get("duration_ms", 0) or 0), run_row_id))
                    conn.commit()
                finally:
                    db._put_conn(conn)
                break
            except Exception as e:
                try:
                    conn.rollback()
                    db._put_conn(conn)
                except Exception:
                    pass
                if attempt == 0 and ("column" in str(e).lower() or "does not exist" in str(e).lower()):
                    continue
                logger.warning("[job_source] finish_source_run failed: %s", e)
                break

    def get_source_runs(self, run_id: str) -> list[dict]:
        db = self._db()
        if not db or not self._ensure_table():
            return []
        try:
            conn = db._conn()
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM job_source_runs WHERE run_id=%s ORDER BY id ASC", (run_id,))
                    return [dict(r) for r in cur.fetchall()]
            finally:
                db._put_conn(conn)
        except Exception:
            return []

    def recent_source_runs(self, limit: int = 50) -> list[dict]:
        db = self._db()
        if not db or not self._ensure_table():
            return []
        try:
            conn = db._conn()
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM job_source_runs ORDER BY started_at DESC LIMIT %s", (limit,))
                    return [dict(r) for r in cur.fetchall()]
            finally:
                db._put_conn(conn)
        except Exception:
            return []

def get_job_source_service() -> JobSourceService:
    return JobSourceService.get_instance()

def reset_job_source_service():
    JobSourceService._instance = None
