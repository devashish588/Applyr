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

        # Resume parsing with blocking logic
        self.parsed_resume = None
        self.resume_blocked = False
        self.resume_block_reason = None

        if not os.path.exists(self.master_resume_pdf):
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

            # STEP 2: deduplicate against DB
            self._emit("dedup", "Deduplicating jobs", agent="orchestrator")
            new_listings = self._deduplicate(job_listings)
            self.results["jobs_filtered"] = len(new_listings)
            self.results["jobs_inserted"] = len(new_listings)
            self.results["jobs_duplicate"] = len(job_listings) - len(new_listings)
            logger.info(f"[orchestrator] {len(new_listings)} new jobs after dedup "
                        f"({len(job_listings) - len(new_listings)} already seen)")

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

        # Scheduled: web search
        logger.info("[orchestrator] Scheduled trigger -- running web research agent")
        try:
            from agents.web_research_agent import build_graph as build_research_graph
            
            # Fetch inferred roles and skills from parsed resume in DB
            resume_data = None
            try:
                from db.db_client import get_db
                resume_data = get_db().get_resume_data()
            except Exception as e:
                logger.warning(f"[orchestrator] Failed to get resume data: {e}")

            # Log the search strategy for transparency
            if resume_data:
                roles = resume_data.get("roles_json", []) or resume_data.get("roles", [])
                skills = resume_data.get("skills_json", []) or resume_data.get("skills", [])
                logger.info(f"[orchestrator] Resume-driven search — roles: {roles[:4]}, skills: {skills[:8]}")
            else:
                logger.info("[orchestrator] No resume data — using profile.json target_roles")

            graph  = build_research_graph()
            result = graph.invoke({
                "query":          "",
                "profile":        self.profile,
                "resume_data":    resume_data or {},
                "messages":       [],
                "search_results": [],
                "job_listings":   [],
                "report":         "",
            })
            listings = result.get("job_listings", [])
            logger.info(f"[orchestrator] Web research found {len(listings)} jobs")
            # Explicit fallback detection: web_research_agent retry without site: filter sets fallback
            if result.get("fallback_used"):
                self.results["fallback_used"] = True
            try:
                if "site:" in state.get("query","") and len(listings)==0 and not self.results["fallback_used"]:
                    # Heuristic fallback for older agent without explicit flag
                    self.results["fallback_used"] = True
            except: pass
            return listings
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
        for job in jobs:
            url = job.get("url") or f"{job.get('company','')}-{job.get('title','')}"
            if not db.url_exists(url):
                new.append(job)
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
