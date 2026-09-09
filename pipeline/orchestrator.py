"""
Orchestrator — AutoApply AI
Wires all agents into a single pipeline:
  web_research_agent  -> find jobs
  pdf_qa_agent        -> parse uploaded JD PDFs
  resume_parser_agent -> parse resume + score fit
  job_application_agent -> tailor resume + cover letter
  email_drafting_agent  -> draft + send cold email

Two trigger modes:
  - Scheduled: scrapes job boards, processes all listings
  - Manual:    user uploads a JD PDF/text -> runs same pipeline on it
"""

import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Path setup so agents are importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.resume_parser_agent   import ResumeParserAgent
from agents.job_application_agent import JobApplicationAgent
from agents.email_drafting_agent  import EmailDraftingAgent
from agents.recruiter_discovery_agent import RecruiterDiscoveryAgent

# Template-based email builder (primary path, fallback to LLM)
from email_module.email_templates import build_cold_email

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main pipeline orchestrator - coordinates all agents."""

    def __init__(self, run_id=None, event_callback=None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.event_callback = event_callback

        # Config from .env
        self.profile_path      = os.getenv("PROFILE_PATH",        str(ROOT / "profile.json"))
        self.master_resume_pdf = os.getenv("MASTER_RESUME_PDF",   str(ROOT / "resume/master_resume.pdf"))
        self.log_dir           = os.getenv("LOG_DIR",             str(ROOT / "logs"))
        self.auto_apply        = os.getenv("AUTO_APPLY",  "false").lower() == "true"
        self.dry_run           = os.getenv("DRY_RUN",     "true").lower()  == "true"
        self.min_fit_score     = int(os.getenv("MIN_FIT_SCORE",   "50"))
        self.max_per_day       = int(os.getenv("MAX_APPLICATIONS_PER_DAY", "20"))
        self.max_per_run       = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))
        self.min_resume_confidence = int(os.getenv("MIN_RESUME_CONFIDENCE", "70"))

        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # Load profile
        if not os.path.exists(self.profile_path):
            raise FileNotFoundError(
                f"profile.json not found at {self.profile_path}\n"
                "Fill it in before running the pipeline."
            )
        with open(self.profile_path) as f:
            self.profile = json.load(f)

        logger.info(f"[orchestrator] Profile loaded: "
                    f"{self.profile.get('personal', {}).get('name', 'Unknown')}")

        # Resume parsing with blocking logic — DB active is authoritative (011).
        # Legacy master_resume.* existence alone never means active when DB says NONE.
        self.parsed_resume = None
        self.resume_blocked = False
        self.resume_block_reason = None
        self.active_resume_path = None
        try:
            from core.services.master_resume_service import get_master_resume_service
            _active = get_master_resume_service().get_active()
        except Exception:
            _active = None
        # _active is None when no active row (or legacy fallback with no data).
        # When resumes table has never been used, _active may be legacy resume_data fallback;
        # otherwise None means NONE even if stale legacy file exists.
        if _active and _active.get("status") == "READY":
            _sp = _active.get("stored_path")
            # Prefer versioned stored_path (authoritative). Never silently pick stale legacy V1.
            _cand = None
            if _sp:
                try:
                    from pathlib import Path as _P
                    _pp = _P(_sp)
                    if _pp.exists():
                        _cand = str(_pp)
                except Exception:
                    _cand = None
            if not _cand and _active.get("legacy"):
                # Pre-migration legacy row has no versioned file; legacy pointer is compatibility
                if os.path.exists(self.master_resume_pdf):
                    _cand = self.master_resume_pdf
            if _cand:
                self.active_resume_path = _cand
                self.master_resume_pdf = _cand
            else:
                # Active exists but versioned file missing: real storage problem, do not use stale file
                self.active_resume_path = None
                if _sp:
                    self.resume_blocked = True
                    self.resume_block_reason = (
                        f"Active master resume file missing at { _sp }. Re-upload the resume."
                    )
                    logger.error(f"[orchestrator] BLOCKED: {self.resume_block_reason}")
        else:
            self.active_resume_path = None

        if self.active_resume_path is None and _active is None:
            # Check if resumes table exists: if it does (post-011), DB NONE wins over stale file.
            # If table missing (pre-migration), fall back to legacy file check for backward compat.
            _has_table = True
            try:
                from core.services.master_resume_service import _conn as _mconn, _has_resumes_table
                _c = _mconn()
                try:
                    _has_table = _has_resumes_table(_c)
                finally:
                    try:
                        _c.close()
                    except Exception:
                        pass
            except Exception:
                _has_table = False
            if _has_table:
                self.resume_blocked = True
                self.resume_block_reason = (
                    "No active master resume. Upload a resume before running the pipeline."
                )
                logger.error(f"[orchestrator] BLOCKED: {self.resume_block_reason}")

        if self.resume_blocked:
            pass
        elif not os.path.exists(self.master_resume_pdf):
            self.resume_blocked = True
            self.resume_block_reason = (
                f"No resume found at {self.master_resume_pdf}. "
                "Upload a resume before running the pipeline."
            )
            logger.error(f"[orchestrator] BLOCKED: {self.resume_block_reason}")
        else:
            try:
                resume_agent = ResumeParserAgent()
                parsed = resume_agent.parse_file(self.master_resume_pdf)
                self.parsed_resume = parsed

                # Extract key metrics
                confidence = parsed.confidence
                has_name = bool(parsed.name)
                has_skills = bool(parsed.skills and len(parsed.skills) > 0)
                has_experience = bool(parsed.experience and len(parsed.experience) > 0)
                has_projects = bool(parsed.projects and len(parsed.projects) > 0)

                # Check all blocking conditions
                missing_critical = []
                if not has_name:
                    missing_critical.append("name")
                if not has_skills:
                    missing_critical.append("skills")
                if not has_experience:
                    missing_critical.append("experience")
                if not has_projects:
                    missing_critical.append("projects")

                if confidence < self.min_resume_confidence or missing_critical:
                    self.resume_blocked = True
                    self.resume_block_reason = (
                        f"Resume parsing confidence is {confidence}% "
                        f"(minimum required: {self.min_resume_confidence}%). "
                        f"Missing or insufficient: {', '.join(missing_critical) or 'confidence too low'}.\n"
                        "Please upload a DOCX or text-based (not scanned-image) PDF resume with:\n"
                        "  • Your name and contact information\n"
                        "  • At least 5 skills\n"
                        "  • Work experience entries\n"
                        "  • Project examples or achievements"
                    )
                    logger.error(f"[orchestrator] BLOCKED: {self.resume_block_reason}")
                else:
                    logger.info(
                        f"[orchestrator] Resume parsed successfully — "
                        f"confidence {confidence}%, name={parsed.name}, "
                        f"{len(parsed.skills)} skills, {len(parsed.experience)} experience entries, "
                        f"{len(parsed.projects)} projects"
                    )

            except Exception as e:
                self.resume_blocked = True
                self.resume_block_reason = (
                    f"Resume parsing failed: {e}\n"
                    "Please upload a DOCX or ATS-friendly text-based PDF."
                )
                logger.error(f"[orchestrator] BLOCKED: {self.resume_block_reason}", exc_info=True)

        # Init agents (only if resume is OK)
        if not self.resume_blocked:
            self.job_agent   = JobApplicationAgent()
            self.email_agent = EmailDraftingAgent()
            self.recruiter_agent = RecruiterDiscoveryAgent()

        # Runtime counters — authoritative run contract
        self.results = {
            "run_id":               self.run_id,
            "triggered_by":         None,
            "started_at":           None,
            "completed_at":         None,
            "finished_at":          None,  # alias for backward compat
            "jobs_found":           0,
            "jobs_inserted":        0,
            "jobs_duplicate":       0,
            "non_job_filtered":     0,
            "jobs_rejected":        0,
            "jobs_filtered":        0,
            "applications_drafted": 0,
            "jobs_applied":         0,
            "applications_submitted": 0,
            "emails_drafted":       0,
            "emails_sent":          0,
            "skipped":              0,
            "errors":               [],
            "status":               "pending",  # SUCCESS/SUCCESS_EMPTY/SUCCESS_WITH_FALLBACK/FAILED_*
            "applications":         [],
            "fallback_used":        False,
            "failure_category":     None,
            "retryable":            False,
        }

    def _emit(self, step: str, msg: str, agent="orchestrator", status="running", **extra):
        if self.event_callback:
            self.event_callback(self.run_id, step, msg, agent=agent, status=status, **extra)

    # Public: main entry point
    def run_full_pipeline(self, triggered_by="scheduled",
                          job_text=None, job_file=None):
        self.results["triggered_by"] = triggered_by
        self.results["started_at"]   = datetime.now().isoformat()
        self.results["status"]       = "running"

        logger.info(f"\n{'='*60}")
        logger.info(f"[orchestrator] Pipeline START -- trigger: {triggered_by}")
        logger.info(f"[orchestrator] dry_run={self.dry_run}  "
                    f"auto_apply={self.auto_apply}  "
                    f"min_fit_score={self.min_fit_score}")
        logger.info(f"{'='*60}")

        # HARD BLOCK: resume parsing failed or confidence too low
        if self.resume_blocked:
            logger.error(f"[orchestrator] Pipeline BLOCKED — not running. Reason: {self.resume_block_reason}")
            self.results["status"] = "blocked"
            self.results["errors"] = [self.resume_block_reason]
            self.results["finished_at"] = datetime.now().isoformat()
            return self.results

        try:
            # STEP 1: get job listings
            self._emit("discover", "Searching for jobs...", agent="web_research")
            job_listings = self._step_discover(triggered_by, job_text, job_file)
            self.results["jobs_found"] = len(job_listings)

            if not job_listings:
                logger.warning("[orchestrator] No jobs found -- pipeline ending early")
                self._emit("done", "No jobs found", status="done")
                self.results["status"] = "completed_empty"
                self.results["jobs_inserted"] = 0
                self.results["jobs_duplicate"] = 0
                self.results["jobs_rejected"] = len(job_listings)
                return self._finalise()

            # Batch cross-host grouping: same underlying job from different hosts in same run -> one canonical with multiple attributions (host not primary)
            # Preserve distinct requisitions (different levels/locations/stable IDs) as separate
            try:
                from core.services.canonical_identity_service import get_canonical_identity_service
                _batch_resolver = get_canonical_identity_service()
                _grouped: dict[str, dict] = {}
                _batch_extra: dict[str, list[dict]] = {}
                _representatives: list[dict] = []
                for j in job_listings:
                    from core.services.job_canonical_service import _normalize_company, normalize_title, _normalize_location
                    from core.services.canonical_identity_service import _extract_stable_id, _normalize_type
                    company_n = _normalize_company(j.get("company"))
                    title_n = " ".join(normalize_title(j.get("title") or "").lower().split())
                    loc_n = _normalize_location(j.get("location"))
                    type_n = _normalize_type(j.get("type"))
                    stable = _extract_stable_id(j.get("url"), j.get("source")) or ""
                    batch_key = f"{company_n}|{title_n}|{loc_n}|{type_n}|{stable}"
                    if batch_key in _grouped:
                        _batch_extra.setdefault(batch_key, []).append(j)
                    else:
                        # Check via resolver for near-matches that differ only by stable/description? Use resolver for T1/T2 with existing batch cands
                        # For batch, we consider same composite without stable as same, but stable difference already in key, so this is new
                        _grouped[batch_key] = j
                        _representatives.append(j)
                # Replace job_listings with representatives for DB dedup, keep extra for post-insert attribution
                self._batch_extra_attributions = _batch_extra
                self._batch_grouped = _grouped
                job_listings = _representatives
                if _batch_extra:
                    logger.info(f"[orchestrator] Batch grouping: {len(_representatives)} canonical representatives from batch, {sum(len(v) for v in _batch_extra.values())} extra source observations (host not primary)")
            except Exception as e:
                logger.warning(f"[orchestrator] batch grouping failed: {e}")
                self._batch_extra_attributions = {}
                self._batch_grouped = {}

            # STEP 2: deduplicate against DB
            self._emit("dedup", "Deduplicating jobs", agent="orchestrator")
            new_listings = self._deduplicate(job_listings)
            self.results["jobs_filtered"] = len(new_listings)
            self.results["jobs_inserted"] = len(new_listings)
            self.results["jobs_duplicate"] = len(job_listings) - len(new_listings)
            logger.info(f"[orchestrator] {len(new_listings)} new jobs after dedup "
                        f"({len(job_listings) - len(new_listings)} already seen)")
            # 33.1 Additive attribution for duplicates already in DB (no new canonical)
            try:
                from core.services.job_attribution_service import get_attribution_service
                attr = get_attribution_service()
                # Duplicates are those not in new_listings (by url)
                new_urls = {j.get("url") for j in new_listings}
                for j in job_listings:
                    if j.get("url") in new_urls:
                        continue
                    # Already seen URL -> record observation for existing canonical
                    if j.get("_source_id"):
                        try:
                            from core.services.job_canonical_service import compute_canonical_id
                            cid = compute_canonical_id(j.get("title"), j.get("company"), j.get("location"), j.get("url"))
                        except Exception:
                            cid = None
                        attr.record_observation(
                            source_id=j.get("_source_id"), source_name=j.get("_source_name") or j.get("_source_host") or "Unknown",
                            host=j.get("_source_host") or "unknown", mode=j.get("_source_mode") or "SEARCH",
                            adapter=j.get("_source_adapter") or "SearchAdapter", source_url=j.get("url") or "",
                            job_url=j.get("url"), canonical_id=cid, title=j.get("title"), company=j.get("company"), location=j.get("location"),
                        )
            except Exception as e:
                logger.warning(f"[orchestrator] attribution (duplicates) failed: {e}")

            # STEP 3: process each job
            applied_count = 0
            rejected = 0
            for job in new_listings:
                if applied_count >= self.max_per_run:
                    logger.info(f"[orchestrator] Hit MAX_EMAILS_PER_RUN={self.max_per_run}")
                    break
                if self._daily_count() >= self.max_per_day:
                    logger.info(f"[orchestrator] Hit MAX_APPLICATIONS_PER_DAY={self.max_per_day}")
                    break

                result = self._step_process_job(job)
                if result:
                    applied_count += 1
                else:
                    rejected += 1

            self.results["jobs_applied"] = applied_count
            self.results["jobs_rejected"] = rejected
            # Batch extra attributions: same job from different hosts in same run -> one canonical, multiple sources (host not primary)
            try:
                _extra = getattr(self, "_batch_extra_attributions", {}) or {}
                if _extra:
                    from core.services.job_attribution_service import get_attribution_service
                    from core.services.job_canonical_service import compute_canonical_id
                    attr2 = get_attribution_service()
                    for _k, _extras in _extra.items():
                        for _ej in _extras:
                            if not _ej.get("_source_id"):
                                continue
                            try:
                                _cid = compute_canonical_id(_ej.get("title"), _ej.get("company"), _ej.get("location"), _ej.get("url"))
                            except Exception:
                                _cid = None
                            attr2.record_observation(
                                source_id=_ej.get("_source_id"), source_name=_ej.get("_source_name") or _ej.get("_source_host") or "Unknown",
                                host=_ej.get("_source_host") or "unknown", mode=_ej.get("_source_mode") or "SEARCH",
                                adapter=_ej.get("_source_adapter") or "SearchAdapter", source_url=_ej.get("url") or "",
                                job_url=_ej.get("url"), canonical_id=_cid, title=_ej.get("title"), company=_ej.get("company"), location=_ej.get("location"),
                            )
                    logger.info(f"[orchestrator] Batch extra attributions recorded: {sum(len(v) for v in _extra.values())}")
            except Exception as e:
                logger.warning(f"[orchestrator] batch extra attribution failed: {e}")
            # Determine final status with fallback distinction
            if self.results["fallback_used"]:
                self.results["status"] = "completed_with_fallback" if applied_count>0 or len(new_listings)>0 else "completed_empty"
                # Keep empty distinction for UI
                if len(new_listings)==0:
                    self.results["status"] = "completed_empty"
            else:
                self.results["status"] = "completed" if len(new_listings)>0 else "completed_empty"

        except Exception as e:
            logger.error(f"[orchestrator] Pipeline error: {e}", exc_info=True)
            self.results["status"] = "failed"
            self.results["errors"].append(str(e))

        return self._finalise()

    # Step 1: discover jobs
    def _step_discover(self, triggered_by, job_text, job_file):
        # Manual: uploaded PDF
        if job_file and os.path.exists(job_file):
            logger.info(f"[orchestrator] Manual trigger -- PDF: {job_file}")
            try:
                from agents.pdf_qa_agent import extract_jd_info
                job = extract_jd_info(job_file)
                return [job] if job.get("title") else []
            except Exception as e:
                logger.error(f"[orchestrator] PDF extraction failed: {e}")
                self.results["errors"].append(f"PDF extraction: {e}")
                return []

        # Manual: pasted text
        if job_text:
            logger.info("[orchestrator] Manual trigger -- pasted JD text")
            return [self._text_to_job_dict(job_text)]

        # Scheduled: multi-source independent discovery (source-aware policy + truthful mode)
        logger.info("[orchestrator] Scheduled trigger -- independent per-source discovery (policy-aware)")
        try:
            from core.services.job_source_service import get_job_source_service
            from core.services.job_source_adapters import dispatch_with_policy
            from db.db_client import get_db as _get_db
            resume_data = None
            try:
                resume_data = _get_db().get_resume_data()
            except Exception as e:
                logger.warning(f"[orchestrator] Failed to get resume data: {e}")
            if resume_data:
                roles = resume_data.get("roles_json", []) or resume_data.get("roles", [])
                skills = resume_data.get("skills_json", []) or resume_data.get("skills", [])
                logger.info(f"[orchestrator] Resume-driven search — roles: {roles[:4]}, skills: {skills[:8]}")
            else:
                logger.info("[orchestrator] No resume data — using profile.json target_roles")

            svc = get_job_source_service()
            sources = svc.list_enabled()
            # No registry yet (cold DB) -> fallback to single web_research_graph but per-source contract
            if not sources:
                logger.warning("[orchestrator] No enabled job sources — seeding built-ins")
                svc._seed_builtins()
                sources = svc.list_enabled()

            all_listings: list[dict] = []
            per_source: list[dict] = []
            run_id = self.run_id
            for src in sources:
                t0 = time.time()
                # Determine policy actual adapter for run log (fallback to source.adapter if policy not yet loaded)
                _policy_adapter = getattr(src, "adapter", "SearchAdapter")
                try:
                    # Use primary_mode to choose adapter for logging
                    _pm = getattr(src, "primary_mode", None)
                    if _pm:
                        from core.services.job_source_adapters import _mode_to_adapter
                        _policy_adapter = _mode_to_adapter(_pm)
                except Exception:
                    pass
                rid = None
                try:
                    rid = svc.start_source_run(run_id, src.id, _policy_adapter)
                except Exception:
                    rid = None
                try:
                    jobs, cat, err, actual_mode, fallback_used, primary_failure = dispatch_with_policy(src, self.profile, resume_data)
                    duration = int((time.time() - t0) * 1000)
                    # Normalize cat
                    if cat not in ("SUCCESS", "NO_RESULTS", "TIMEOUT", "HTTP_ERROR", "BLOCKED",
                                   "ROBOTS_DISALLOWED", "AUTH_REQUIRED", "PARSER_ERROR",
                                   "SCHEMA_CHANGED", "RATE_LIMITED", "UNSUPPORTED", "UNSUPPORTED_SOURCE", "NETWORK", "NETWORK_ERROR", "UNKNOWN"):
                        cat = "UNKNOWN" if err else ("SUCCESS" if jobs else "NO_RESULTS")
                    status = "success" if cat in ("SUCCESS", "NO_RESULTS") else "failed"
                    if not jobs and cat == "SUCCESS":
                        cat = "NO_RESULTS"
                    # Map actual_mode to adapter truthfully
                    from core.services.job_source_adapters import _mode_to_adapter as _m2a
                    actual_adapter = _m2a(actual_mode)
                    # Pre-storage gate: exclude clear non-job pages (listing indexes,
                    # team/tag/article pages) BEFORE canonical ID / DB insert.
                    # jobs_found = raw adapter output; jobs_normalized = gate
                    # survivors (JOB + UNDETERMINED); non_job_filtered is new.
                    from core.services.job_listing_gate import filter_listings
                    passing, nonjob = filter_listings(jobs)
                    for _nj, _reason in nonjob:
                        logger.info(f"[orchestrator] filtered non-job from {src.host}: {_reason} :: {str(_nj.get('title'))[:60]!r}")
                    res = {
                        "source_id": src.id,
                        "status": status,
                        "adapter": actual_adapter,
                        "mode": actual_mode,
                        "primary_mode": getattr(src, "primary_mode", actual_mode),
                        "source_role": getattr(src, "source_role", "UNKNOWN"),
                        "jobs_found": len(jobs),
                        "jobs_normalized": len(passing),
                        "non_job_filtered": len(nonjob),
                        "jobs_new": 0,
                        "jobs_duplicate": 0,
                        "failure_category": cat,
                        "error": err,
                        "duration_ms": duration,
                        "fallback_used": fallback_used,
                        "primary_failure": primary_failure,
                    }
                    # Record health + observed mode
                    try:
                        # Update observed success tracking
                        if cat == "SUCCESS" and jobs:
                            try:
                                src.observed_mode = actual_mode
                                src.observed_success_count = int(getattr(src, "observed_success_count", 0) or 0) + 1
                            except Exception:
                                pass
                        svc.record_run(src.id, res)
                        svc.finish_source_run(rid, res)
                    except Exception:
                        pass
                    self._emit("source_done", f"Source {src.host}: {len(jobs)} jobs ({cat}) via {actual_mode}{' (fallback)' if fallback_used else ''}",
                               agent="web_research", status="done" if status == "success" else "error",
                               source_id=src.id, host=src.host, adapter=actual_adapter, mode=actual_mode, fallback_used=fallback_used,
                               jobs_found=len(jobs), failure_category=cat, duration_ms=duration)
                    logger.info(f"[orchestrator] source {src.host} role={getattr(src,'source_role','?')} primary={getattr(src,'primary_mode','?')} actual={actual_mode} fallback={fallback_used} found={len(jobs)} normalized={len(passing)} non_job_filtered={len(nonjob)} cat={cat} ms={duration} err={err!r}")
                    per_source.append(res)
                    # Tag jobs with truthful source attribution (host not primary, mode truthful)
                    # Only gate survivors are tagged/extended: NON_JOB creates no
                    # canonical identity, attribution, Match, Priority, or OI.
                    for j in passing:
                        j["_source_id"] = src.id
                        j["_source_name"] = src.name
                        j["_source_host"] = src.host
                        j["_source_mode"] = actual_mode
                        j["_source_adapter"] = actual_adapter
                        j["_source_url"] = j.get("url")
                        j["_fallback_used"] = fallback_used
                        j["_primary_failure"] = primary_failure
                    # Only extend successes; failures contribute 0 jobs but are tracked
                    if passing:
                        all_listings.extend(passing)
                    # Fallback detection: if any search source used broadened query, mark
                    # but do NOT hide per-source failure — per-source contract is authoritative
                except Exception as e:
                    duration = int((time.time() - t0) * 1000)
                    from core.ai.errors import sanitize_exception_message
                    safe = sanitize_exception_message(str(e))
                    # Use policy adapter for exception case as well
                    try:
                        _pm = getattr(src, "primary_mode", "AUTO")
                        from core.services.job_source_adapters import _mode_to_adapter
                        _actual_adapter = _mode_to_adapter(_pm) if _pm and _pm!="AUTO" else getattr(src, "adapter", "SearchAdapter")
                        _actual_mode = _pm if _pm and _pm!="AUTO" else "SEARCH"
                    except Exception:
                        _actual_adapter = getattr(src, "adapter", "SearchAdapter")
                        _actual_mode = "UNKNOWN"
                    res = {"source_id": src.id, "status": "failed", "adapter": _actual_adapter, "mode": _actual_mode,
                           "jobs_found": 0, "jobs_normalized": 0, "non_job_filtered": 0, "jobs_new": 0, "jobs_duplicate": 0,
                           "failure_category": "UNKNOWN", "error": safe, "duration_ms": duration, "fallback_used": False}
                    try:
                        svc.record_run(src.id, res)
                        svc.finish_source_run(rid, res)
                    except Exception:
                        pass
                    per_source.append(res)
                    self.results["errors"].append(f"{src.host}: {safe}")
                    logger.error(f"[orchestrator] source {src.host} failed: {safe}")

            # Attach per-source telemetry to results for UI (Pipeline Status) — truthful, no hidden fallback
            self.results["sources"] = per_source
            self.results["sources_configured"] = len(sources)
            self.results["sources_attempted"] = len(per_source)
            self.results["sources_succeeded"] = sum(1 for r in per_source if r["status"] == "success" and r["failure_category"] == "SUCCESS")
            self.results["sources_failed"] = sum(1 for r in per_source if r["status"] == "failed" or r["failure_category"] not in ("SUCCESS", "NO_RESULTS"))
            # Explicit fallback: true if any source used fallback (primary HTML failed → SEARCH succeeded)
            self.results["fallback_used"] = any(r.get("fallback_used") for r in per_source)
            # Also expose per-source fallback details for UI diagnostics
            self.results["fallback_details"] = [r for r in per_source if r.get("fallback_used")]
            self.results["non_job_filtered"] = sum(int(r.get("non_job_filtered", 0) or 0) for r in per_source)
            logger.info(f"[orchestrator] Multi-source found {len(all_listings)} jobs across {len(sources)} sources "
                        f"({self.results['sources_succeeded']} succeeded, {self.results['sources_failed']} failed) fallback_used={self.results['fallback_used']} "
                        f"non_job_filtered={self.results['non_job_filtered']}")
            return all_listings
        except Exception as e:
            from core.ai.errors import sanitize_exception_message, classify_error
            safe = sanitize_exception_message(str(e))
            logger.error(f"[orchestrator] Web research failed: {safe}")
            meta = classify_error(e)
            self.results["failure_category"] = meta["category"]
            self.results["retryable"] = meta["retryable"]
            self.results["errors"].append(f"Web research: {safe}")
            return []

    def _sanitize_company(self, company) -> str:
        if not company or str(company).strip().lower() in ("none", "null", "n/a", "", "unknown"):
            return "Company Not Extracted"
        return str(company).strip()

    # Step 2: process one job
    def _step_process_job(self, job):
        title   = job.get("title",   "Unknown Role")
        company = self._sanitize_company(job.get("company"))
        logger.info(f"\n[orchestrator] -> Processing: {title} at {company}")
        self._emit("process_job", f"Evaluating {title} at {company}", agent="fit_scorer")

        try:
            # Agent 18: tailor resume + cover letter
            resume_dict = self.parsed_resume.model_dump() if hasattr(self.parsed_resume, 'model_dump') else self.parsed_resume
            app_result = self.job_agent.process(job, self.profile, resume_dict)

            if not app_result.get("should_apply"):
                reason = app_result.get("reason", "below fit threshold")
                logger.info(f"[orchestrator]   x Skip -- {reason}")
                self._emit("skip_job", f"Skipped {company}: {reason}", agent="fit_scorer", status="done")
                self.results["skipped"] += 1
                self._save_to_db(job, app_result, status="skipped")
                return False

            self._emit("tailoring", f"Tailoring resume for {company}", agent="job_application")

            # At this point we are drafting an application (resume + cover letter)
            self.results["applications_drafted"] += 1
            self.results["emails_drafted"] += 1
            # Keep jobs_applied in sync for backward compatibility
            self.results["jobs_applied"] = self.results["applications_drafted"]

            fit_score = app_result.get("fit_score", 0)
            logger.info(f"[orchestrator]   Fit score: {fit_score}/100 -- proceeding")

            # Ensure we have a recruiter email (hr_email) for the job
            if not job.get("hr_email"):
                self._emit("discover_recruiter", f"Finding recruiter for {company}", agent="web_research")
                discovered = self.recruiter_agent.find_email(job)
                if discovered:
                    job["hr_email"] = discovered

            # Agent 05: draft email (template-based primary, LLM fallback)
            self._emit("draft_email", f"Drafting email for {company}", agent="email_drafting")

            try:
                email = build_cold_email(job, self.profile, app_result)
                if not email.get("body") or email.get("missing_placeholders"):
                    logger.warning(
                        f"[orchestrator] Template email incomplete "
                        f"(missing: {email.get('missing_placeholders')}) — falling back to LLM"
                    )
                    email = self.email_agent.draft_email(job, self.profile)
            except FileNotFoundError as e:
                logger.warning(f"[orchestrator] {e} — using LLM email drafting instead")
                email = self.email_agent.draft_email(job, self.profile)

            # Validate email
            warnings = self.email_agent.validate_email(email, self.profile)
            for w in warnings:
                logger.warning(f"[orchestrator]   Email warning: {w}")

            # Send or queue
            sent = False
            if self.auto_apply and not self.dry_run and job.get("hr_email"):
                sent = self._send_email(email, app_result)
                if sent:
                    self.results["applications_submitted"] += 1
                    self.results["emails_sent"] += 1
            else:
                mode = "DRY RUN" if self.dry_run else "AUTO_APPLY=false"
                logger.info(f"[orchestrator]   [{mode}] Email drafted but not sent")

            # Save to DB
            status = "sent" if sent else ("draft" if self.dry_run else "ready")
            self._save_to_db(job, app_result, email, status=status)

            self.results["applications"].append({
                "title":     title,
                "company":   company,
                "fit_score": fit_score,
                "status":    status,
                "email_to":  email.get("to"),
                "subject":   email.get("subject"),
            })

            self._emit("job_done", f"Processed {company}", agent="orchestrator", status="done")
            return True

        except Exception as e:
            logger.error(f"[orchestrator]   Error processing {company}: {e}", exc_info=True)
            self._emit("job_error", f"Error on {company}: {e}", agent="orchestrator", status="error", error=str(e))
            self.results["errors"].append(f"{company} ({title}): {e}")
            return False

    # Email sending
    def _send_email(self, email, app_result):
        try:
            from email_module.sender import GmailSender
            sender = GmailSender()
            attachments = []
            for key in ("tailored_resume_path", "cover_letter_path"):
                path = app_result.get(key)
                if path and os.path.exists(path):
                    attachments.append(path)
            return sender.send(
                to=email["to"], subject=email["subject"],
                body=email["body"], attachments=attachments,
            )
        except Exception as e:
            logger.warning(f"[orchestrator] Email send failed: {e}")
            return False

    # Persistence Model: Model B — incremental per-job transactions
    # Each job is persisted via _save_to_db() in its own transaction (db.insert_job).
    # If process dies after N jobs, first N are committed, rest not. Replay is safe
    # via canonical_id/URL idempotency (db.url_exists + ON CONFLICT) and
    # last_seen_at update, not duplicate insertion. Counters (jobs_inserted etc.)
    # are recomputed from authoritative DB state on replay, not double-incremented.

    # DB helpers — all use get_db() (PostgreSQL via DBClient)
    def _deduplicate(self, jobs):
        from db.db_client import get_db
        db = get_db()
        new = []
        # Batch in-memory grouping for same job from different hosts in same run (host not primary)
        _batch_seen: set[str] = set()
        try:
            from core.services.canonical_identity_service import get_canonical_identity_service, _extract_stable_id, _normalize_type
            from core.services.job_canonical_service import _normalize_company, normalize_title, _normalize_location
        except Exception:
            _batch_seen = set()  # fallback
            _extract_stable_id = lambda u,s: None  # type: ignore
            _normalize_company = lambda x: (x or "").lower().strip()  # type: ignore
            normalize_title = lambda x: x or ""  # type: ignore
            _normalize_location = lambda x: (x or "").lower().strip()  # type: ignore
            _normalize_type = lambda x: (x or "").lower().strip()  # type: ignore
            get_canonical_identity_service = lambda: None  # type: ignore
        # For cross-source resolver, reuse one connection for candidate lookup to avoid O(N^2)
        # Preserve existing url_exists semantics, additive tiered identity for host - not primary
        try:
            from core.services.canonical_identity_service import get_canonical_identity_service
            resolver = get_canonical_identity_service()
        except Exception:
            resolver = None
        conn = None
        try:
            conn = db._conn()
        except Exception:
            conn = None
        for job in jobs:
            url = job.get("url") or f"{job.get('company','')}-{job.get('title','')}"
            # In-batch duplicate check (same underlying job observed via different hosts in same pipeline run)
            try:
                company_n = _normalize_company(job.get("company"))
                title_n = " ".join(normalize_title(job.get("title") or "").lower().split())
                loc_n = _normalize_location(job.get("location"))
                type_n = _normalize_type(job.get("type"))
                stable = _extract_stable_id(job.get("url"), job.get("source")) or ""
                batch_key = f"{company_n}|{title_n}|{loc_n}|{type_n}|{stable}"
                if batch_key and batch_key in _batch_seen and company_n and title_n:
                    # Same job as earlier in this batch (host not primary) -> duplicate, will be attributed via batch extra
                    continue
            except Exception:
                pass
            if db.url_exists(url):
                try:
                    _batch_seen.add(batch_key)  # type: ignore
                except Exception:
                    pass
                continue
            # Cross-host tiered identity vs DB: if same underlying job exists via different host, treat as duplicate
            if resolver and conn:
                try:
                    candidates = resolver.find_candidates(job, conn)
                    hit = resolver.resolve(job, candidates)
                    if hit is not None:
                        try:
                            _batch_seen.add(batch_key)  # type: ignore
                        except Exception:
                            pass
                        continue
                except Exception:
                    pass
            try:
                _batch_seen.add(batch_key)  # type: ignore
            except Exception:
                pass
            new.append(job)
        if conn:
            try:
                db._put_conn(conn)
            except Exception:
                pass
        return new

    def _daily_count(self):
        try:
            from db.db_client import get_db
            return get_db().daily_sent_count()
        except Exception:
            return 0

    def _save_to_db(self, job, app_result, email=None, status="found"):
        from db.db_client import get_db
        db = get_db()
        now = datetime.now().isoformat()
        try:
            db.insert_job(job, app_result, email, status=status)
            # 33.1 Record cross-source attribution for canonical (additive, no duplicate canonical)
            try:
                if job.get("_source_id"):
                    from core.services.job_attribution_service import get_attribution_service
                    from core.services.job_canonical_service import compute_canonical_id
                    cid = None
                    try:
                        cid = compute_canonical_id(job.get("title"), job.get("company"), job.get("location"), job.get("url"))
                    except Exception:
                        pass
                    get_attribution_service().record_observation(
                        source_id=job.get("_source_id"), source_name=job.get("_source_name") or job.get("_source_host") or "Unknown",
                        host=job.get("_source_host") or "unknown", mode=job.get("_source_mode") or "SEARCH",
                        adapter=job.get("_source_adapter") or "SearchAdapter", source_url=job.get("url") or "",
                        job_url=job.get("url"), canonical_id=cid, title=job.get("title"), company=job.get("company"), location=job.get("location"),
                    )
            except Exception as e:
                logger.warning(f"[orchestrator] attribution (new) failed: {e}")

            # Also save email record
            if email:
                conn = db._conn()
                try:
                    with conn.cursor() as cur:
                        url = job.get("url") or f"{job.get('company','')}-{job.get('title','')}"
                        cur.execute("SELECT id FROM jobs WHERE url = %s", (url,))
                        row = cur.fetchone()
                        job_id = row[0] if row else 0
                        cur.execute("""
                            INSERT INTO emails (job_id, hr_email, subject, body_text, status,
                                               resume_path, cover_letter_path, created_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            job_id, email.get("to"), email.get("subject"),
                            email.get("body"), "drafted",
                            app_result.get("tailored_resume_path"),
                            app_result.get("cover_letter_path"), now
                        ))
                    conn.commit()
                except Exception as inner_e:
                    conn.rollback()
                    logger.error(f"[orchestrator] Email record save failed: {inner_e}")
                finally:
                    db._put_conn(conn)
        except Exception as e:
            logger.error(f"[orchestrator] DB save failed: {e}")

    # Helpers
    def _text_to_job_dict(self, text):
        cleaned = " ".join(text.split())
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cleaned)
        hr_email = email_match.group(0).rstrip(".,;:") if email_match else None

        title = "Manual Job"
        company = "Unknown Company"
        at_match = re.search(
            r"(?P<title>[A-Z][A-Za-z0-9 +/#.&-]{2,80})\s+at\s+(?P<company>[A-Z][A-Za-z0-9 .&-]{2,80})",
            cleaned,
        )
        if at_match:
            title = at_match.group("title").strip(" .,-")
            company = at_match.group("company").split(".")[0].strip(" .,-")

        location = "N/A"
        if re.search(r"\bremote\b", cleaned, re.IGNORECASE):
            location = "Remote"

        role_type = "fulltime"
        if re.search(r"\bintern(ship)?\b", cleaned, re.IGNORECASE):
            role_type = "internship"
        elif re.search(r"\bcontract\b", cleaned, re.IGNORECASE):
            role_type = "contract"

        profile_skills = []
        for key in ("languages", "frameworks", "tools"):
            profile_skills.extend(self.profile.get("skills", {}).get(key, []))
        required_skills = []
        lower_text = cleaned.lower()
        for skill in profile_skills:
            pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, lower_text):
                required_skills.append(skill)

        return {
            "title": title, "company": company,
            "location": location, "type": role_type,
            "hr_email": hr_email,
            "url": f"manual-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "source": "manual_text",
            "description_snippet": text[:1200],
            "jd_text": text,
            "required_skills": required_skills,
        }

    def _finalise(self):
        self.results["finished_at"] = datetime.now().isoformat()
        self._save_run_log()
        logger.info(f"\n[orchestrator] Pipeline DONE")
        logger.info(f"  Jobs found:   {self.results['jobs_found']}")
        logger.info(f"  Filtered:     {self.results['jobs_filtered']}")
        logger.info(f"  Applied:      {self.results['jobs_applied']}")
        logger.info(f"  Emails sent:  {self.results['emails_sent']}")
        logger.info(f"  Status:       {self.results['status']}")
        return self.results

    def _save_run_log(self):
        try:
            from db.db_client import get_db
            db = get_db()
            run_id = self.results["run_id"]
            db.start_run_log(run_id, self.results.get("triggered_by", ""))
            db.update_run_log(run_id,
                jobs_found=self.results.get("jobs_found", 0),
                jobs_filtered=self.results.get("jobs_filtered", 0),
                jobs_applied=self.results.get("jobs_applied", 0),
                emails_sent=self.results.get("emails_sent", 0),
                errors_count=len(self.results.get("errors", [])),
                status=self.results["status"],
                summary=self.results,
            )
        except Exception as e:
            logger.warning(f"[orchestrator] Run log save failed: {e}")

    def save_run_summary(self):
        path = os.path.join(
            self.log_dir,
            f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"[orchestrator] Run summary saved: {path}")
        return path
