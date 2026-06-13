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
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Path setup so agents are importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.web_research_agent    import build_graph as build_research_graph
from agents.pdf_qa_agent          import extract_jd_info
from agents.resume_parser_agent   import ResumeParserAgent
from agents.job_application_agent import JobApplicationAgent
from agents.email_drafting_agent  import EmailDraftingAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main pipeline orchestrator - coordinates all agents."""

    def __init__(self):
        # Config from .env
        self.profile_path      = os.getenv("PROFILE_PATH",        str(ROOT / "profile.json"))
        self.master_resume_pdf = os.getenv("MASTER_RESUME_PDF",   str(ROOT / "resume/master_resume.pdf"))
        self.db_path           = os.getenv("DB_PATH",             str(ROOT / "db/applications.db"))
        self.log_dir           = os.getenv("LOG_DIR",             str(ROOT / "logs"))
        self.auto_apply        = os.getenv("AUTO_APPLY",  "false").lower() == "true"
        self.dry_run           = os.getenv("DRY_RUN",     "true").lower()  == "true"
        self.min_fit_score     = int(os.getenv("MIN_FIT_SCORE",   "50"))
        self.max_per_day       = int(os.getenv("MAX_APPLICATIONS_PER_DAY", "20"))
        self.max_per_run       = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))

        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

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

        # Parse master resume once (reused for all jobs)
        self.parsed_resume = None
        if os.path.exists(self.master_resume_pdf):
            try:
                resume_agent       = ResumeParserAgent()
                self.parsed_resume = resume_agent.parse_file(self.master_resume_pdf)
                logger.info("[orchestrator] Master resume parsed")
            except Exception as e:
                logger.warning(f"[orchestrator] Resume parse failed: {e} -- continuing without it")

        # Init agents
        self.job_agent   = JobApplicationAgent()
        self.email_agent = EmailDraftingAgent()

        # Runtime counters
        self.results = {
            "triggered_by":  None,
            "started_at":    None,
            "finished_at":   None,
            "jobs_found":    0,
            "jobs_filtered": 0,
            "jobs_applied":  0,
            "emails_sent":   0,
            "skipped":       0,
            "errors":        [],
            "status":        "pending",
            "applications":  [],
        }

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

        try:
            # STEP 1: get job listings
            job_listings = self._step_discover(triggered_by, job_text, job_file)
            self.results["jobs_found"] = len(job_listings)

            if not job_listings:
                logger.warning("[orchestrator] No jobs found -- pipeline ending early")
                self.results["status"] = "completed_empty"
                return self._finalise()

            # STEP 2: deduplicate against DB
            new_listings = self._deduplicate(job_listings)
            self.results["jobs_filtered"] = len(new_listings)
            logger.info(f"[orchestrator] {len(new_listings)} new jobs after dedup "
                        f"({len(job_listings) - len(new_listings)} already seen)")

            # STEP 3: process each job
            applied_count = 0
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

            self.results["jobs_applied"] = applied_count
            self.results["status"]       = "completed"

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
            graph  = build_research_graph()
            result = graph.invoke({
                "query":          "",
                "profile":        self.profile,
                "messages":       [],
                "search_results": [],
                "job_listings":   [],
                "report":         "",
            })
            listings = result.get("job_listings", [])
            logger.info(f"[orchestrator] Web research found {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"[orchestrator] Web research failed: {e}")
            self.results["errors"].append(f"Web research: {e}")
            return []

    # Step 2: process one job
    def _step_process_job(self, job):
        title   = job.get("title",   "Unknown Role")
        company = job.get("company", "Unknown Company")
        logger.info(f"\n[orchestrator] -> Processing: {title} at {company}")

        try:
            # Agent 18: tailor resume + cover letter
            app_result = self.job_agent.process(job, self.profile, self.parsed_resume)

            if not app_result.get("should_apply"):
                reason = app_result.get("reason", "below fit threshold")
                logger.info(f"[orchestrator]   x Skip -- {reason}")
                self.results["skipped"] += 1
                self._save_to_db(job, app_result, status="skipped")
                return False

            fit_score = app_result.get("fit_score", 0)
            logger.info(f"[orchestrator]   Fit score: {fit_score}/100 -- proceeding")

            # Agent 05: draft email
            email = self.email_agent.draft_email(job, self.profile)

            # Validate email
            warnings = self.email_agent.validate_email(email, self.profile)
            for w in warnings:
                logger.warning(f"[orchestrator]   Email warning: {w}")

            # Send or queue
            sent = False
            if self.auto_apply and not self.dry_run and job.get("hr_email"):
                sent = self._send_email(email, app_result)
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

            if sent:
                self.results["emails_sent"] += 1

            return True

        except Exception as e:
            logger.error(f"[orchestrator]   Error processing {company}: {e}", exc_info=True)
            self.results["errors"].append(f"{company} ({title}): {e}")
            return False

    # Email sending
    def _send_email(self, email, app_result):
        try:
            from email.sender import GmailSender
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

    # DB helpers
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, company TEXT, url TEXT UNIQUE,
                source TEXT, location TEXT, type TEXT, hr_email TEXT,
                fit_score INTEGER, status TEXT DEFAULT 'found',
                jd_text TEXT,
                scraped_at TEXT, applied_at TEXT,
                cover_letter_path TEXT, tailored_resume_path TEXT,
                email_subject TEXT, email_body TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, triggered_by TEXT,
                started_at TEXT, finished_at TEXT,
                jobs_found INTEGER, jobs_filtered INTEGER,
                jobs_applied INTEGER, emails_sent INTEGER,
                errors_count INTEGER, status TEXT, summary_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER, hr_email TEXT,
                subject TEXT, body_text TEXT, status TEXT,
                resume_path TEXT, cover_letter_path TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        return conn

    def _deduplicate(self, jobs):
        conn = self._init_db()
        new = []
        for job in jobs:
            url = job.get("url") or f"{job.get('company','')}-{job.get('title','')}"
            row = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
            if not row:
                new.append(job)
        conn.close()
        return new

    def _daily_count(self):
        try:
            conn = self._init_db()
            today = datetime.now().strftime("%Y-%m-%d")
            count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE applied_at LIKE ? AND status='sent'",
                (f"{today}%",)
            ).fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def _save_to_db(self, job, app_result, email=None, status="found"):
        conn = self._init_db()
        now = datetime.now().isoformat()
        try:
            url = job.get("url") or f"{job.get('company','')}-{job.get('title','')}"
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, company, url, source, location, type, hr_email,
                 fit_score, status, jd_text, scraped_at, applied_at,
                 cover_letter_path, tailored_resume_path,
                 email_subject, email_body)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job.get("title"), job.get("company"), url,
                job.get("source"), job.get("location"), job.get("type"),
                job.get("hr_email"),
                app_result.get("fit_score"), status,
                job.get("description_snippet", job.get("jd_text", ""))[:2000],
                now, now if status == "sent" else None,
                app_result.get("cover_letter_path"),
                app_result.get("tailored_resume_path"),
                email.get("subject") if email else None,
                email.get("body") if email else None,
            ))

            # Also save email record
            if email:
                job_row = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
                job_id = job_row[0] if job_row else 0
                conn.execute("""
                    INSERT INTO emails (job_id, hr_email, subject, body_text, status,
                                       resume_path, cover_letter_path, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    job_id, email.get("to"), email.get("subject"),
                    email.get("body"), "drafted", 
                    app_result.get("tailored_resume_path"),
                    app_result.get("cover_letter_path"), now
                ))

            conn.commit()
        except Exception as e:
            logger.error(f"[orchestrator] DB save failed: {e}")
        finally:
            conn.close()

    # Helpers
    def _text_to_job_dict(self, text):
        return {
            "title": "Unknown Role", "company": "Unknown Company",
            "location": "N/A", "type": "fulltime", "hr_email": None,
            "url": f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "source": "manual_text",
            "description_snippet": text[:800],
            "required_skills": [],
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
            conn = self._init_db()
            conn.execute("""
                INSERT INTO run_log
                (triggered_by, started_at, finished_at,
                 jobs_found, jobs_filtered, jobs_applied,
                 emails_sent, errors_count, status, summary_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                self.results["triggered_by"],
                self.results["started_at"],
                self.results["finished_at"],
                self.results["jobs_found"],
                self.results["jobs_filtered"],
                self.results["jobs_applied"],
                self.results["emails_sent"],
                len(self.results.get("errors", [])),
                self.results["status"],
                json.dumps(self.results),
            ))
            conn.commit()
            conn.close()
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
