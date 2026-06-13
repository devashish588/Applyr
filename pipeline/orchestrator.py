"""
Orchestrator - main pipeline that coordinates all 6 agents.
Runs the 5-step process: discover → parse & match → filter & score → tailor → draft & send

All agents are now fully implemented and wired in.
"""
import os
import sys
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_client import get_db
from utils.profile_loader import get_profile
from utils.fit_scorer import FitScorer
from utils.deduplicator import Deduplicator

# Import all agents
from agents.web_research_agent import WebResearchAgent
from agents.pdf_qa_agent import PDFQAAgent
from agents.resume_parser_agent import ResumeParserAgent
from agents.doc_writer_agent import DocWriterAgent
from agents.email_drafting_agent import EmailDraftingAgent
from agents.job_application_agent import JobApplicationAgent

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'orchestrator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Main pipeline orchestrator - coordinates all agents."""

    def __init__(self):
        self.db = get_db()
        self.profile = get_profile()
        self.scorer = FitScorer()
        self.deduplicator = Deduplicator()
        self.run_id = str(uuid.uuid4())

        # Initialize agents
        self.web_agent = WebResearchAgent()
        self.pdf_agent = PDFQAAgent()
        self.resume_agent = ResumeParserAgent()
        self.doc_agent = DocWriterAgent()
        self.email_agent = EmailDraftingAgent()
        self.job_agent = JobApplicationAgent()

        self.results = {
            "run_id": self.run_id,
            "jobs_found": 0,
            "jobs_filtered": 0,
            "jobs_applied": 0,
            "emails_sent": 0,
            "errors": []
        }

    def run_full_pipeline(self, triggered_by: str = "scheduler",
                           job_text: str = None,
                           job_file: str = None) -> Dict[str, Any]:
        """Run the complete 5-step pipeline.

        Args:
            triggered_by: "scheduler", "manual", or "upload"
            job_text: Optional JD text pasted by user
            job_file: Optional path to uploaded JD file

        Steps:
        1. Discover - Web research agent scrapes jobs OR process manual input
        2. Parse & Match - Resume parser + PDF QA process JDs
        3. Filter & Score - Job application agent ranks by fit
        4. Tailor - Documentation writer rewrites resume + cover letter
        5. Draft & Send - Email drafting agent composes cold emails
        """
        logger.info(f"{'='*60}")
        logger.info(f"Starting pipeline (run_id: {self.run_id}, triggered_by: {triggered_by})")
        logger.info(f"{'='*60}")

        # Start run log
        run_log_id = self.db.start_run_log(self.run_id, triggered_by)

        try:
            # Step 1: Discover
            if job_text or job_file:
                logger.info("Step 1: Processing manual input...")
                discovered_jobs = self._step_manual_input(job_text, job_file)
            else:
                logger.info("Step 1: Discovering jobs from web...")
                discovered_jobs = self._step_discover()

            self.results["jobs_found"] = len(discovered_jobs)
            logger.info(f"[OK] Step 1 complete: {len(discovered_jobs)} jobs discovered")

            # Step 2: Parse & Match
            logger.info("Step 2: Parsing and analyzing...")
            parsed_jobs = self._step_parse_and_match(discovered_jobs)
            logger.info(f"[OK] Step 2 complete: {len(parsed_jobs)} jobs parsed")

            # Step 3: Filter & Score
            logger.info("Step 3: Filtering and scoring...")
            filtered_jobs = self._step_filter_and_score(parsed_jobs)
            self.results["jobs_filtered"] = len(filtered_jobs)
            logger.info(f"[OK] Step 3 complete: {len(filtered_jobs)} jobs passed threshold")

            # Step 4: Tailor
            logger.info("Step 4: Tailoring applications...")
            tailored_jobs = self._step_tailor(filtered_jobs)
            logger.info(f"[OK] Step 4 complete: {len(tailored_jobs)} applications tailored")

            # Step 5: Draft & Send
            logger.info("Step 5: Drafting emails...")
            applied_jobs = self._step_draft_and_send(tailored_jobs)
            self.results["jobs_applied"] = len(applied_jobs)
            self.results["emails_sent"] = len(applied_jobs)
            logger.info(f"[OK] Step 5 complete: {len(applied_jobs)} emails drafted")

            # Update run log
            self.db.update_run_log(
                self.run_id,
                jobs_found=self.results["jobs_found"],
                jobs_filtered=self.results["jobs_filtered"],
                jobs_applied=self.results["jobs_applied"],
                emails_sent=self.results["emails_sent"],
                errors_count=len(self.results["errors"]),
                summary=self.results
            )

            self.results["status"] = "completed"
            logger.info("Pipeline completed successfully!")
            logger.info(f"   Jobs: {self.results['jobs_found']} found -> "
                        f"{self.results['jobs_filtered']} filtered -> "
                        f"{self.results['jobs_applied']} applied")

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.results["status"] = "failed"
            self.results["errors"].append(str(e))
            self.db.update_run_log(
                self.run_id,
                errors_count=len(self.results["errors"]),
                summary=self.results
            )

        return self.results

    def _step_discover(self) -> List[Dict[str, Any]]:
        """Step 1: Web research agent discovers jobs."""
        # Build profile text for search query generation
        profile_data = self.profile.to_dict()
        target_roles = ", ".join(self.profile.get_target_roles())
        skills_text = self.profile.get_skills_text()
        locations = ", ".join(self.profile.get_job_preferences().get("target_locations", []))
        profile_text = f"Looking for: {target_roles}. Skills: {skills_text}. Locations: {locations}"

        try:
            jobs = self.web_agent.scrape_jobs(profile_text=profile_text)
            return jobs
        except Exception as e:
            logger.error(f"Web research failed: {e}")
            self.results["errors"].append(f"Discovery: {e}")
            return []

    def _step_manual_input(self, job_text: str = None,
                            job_file: str = None) -> List[Dict[str, Any]]:
        """Step 1 (manual): Process uploaded JD file or pasted text."""
        jd_text = ""
        jobs = []

        if job_file and os.path.exists(job_file):
            ext = os.path.splitext(job_file)[1].lower()
            if ext == ".pdf":
                jd_text = self.pdf_agent.extract_jd_from_pdf(job_file)
            elif ext in (".png", ".jpg", ".jpeg"):
                jd_text = self.pdf_agent.extract_jd_from_image(job_file)
            elif ext in (".txt", ".doc", ".docx"):
                with open(job_file, "r", encoding="utf-8", errors="ignore") as f:
                    jd_text = f.read()
            logger.info(f"Extracted {len(jd_text)} chars from {job_file}")

        elif job_text:
            jd_text = job_text

        if jd_text:
            # Use LLM to analyze the JD
            analysis = self.pdf_agent.analyze_jd(jd_text)
            contact = self.pdf_agent.extract_hr_contact_info(jd_text)

            job = {
                "title": analysis.get("title", "Unknown Position"),
                "company": analysis.get("company", "Unknown Company"),
                "url": contact.get("apply_url", ""),
                "source": "manual_upload",
                "jd_text": jd_text[:2000],
                "location": analysis.get("location", ""),
                "salary": analysis.get("salary", ""),
                "hr_email": contact.get("hr_email", analysis.get("hr_email", ""))
            }
            jobs.append(job)
            logger.info(f"Manual JD: {job['title']} at {job['company']}")

        return jobs

    def _step_parse_and_match(self, discovered_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 2: Enhance jobs with parsed details."""
        parsed_jobs = []

        for job in discovered_jobs:
            try:
                # If JD text is available but sparse, enrich it
                if job.get("jd_text") and len(job["jd_text"]) > 50:
                    # Extract contact info if not already present
                    if not job.get("hr_email"):
                        contact = self.pdf_agent.extract_hr_contact_info(job["jd_text"])
                        job["hr_email"] = contact.get("hr_email", "")
                        if not job.get("url"):
                            job["url"] = contact.get("apply_url", "")

                parsed_jobs.append(job)

            except Exception as e:
                logger.warning(f"Parse error for {job.get('title', 'unknown')}: {e}")
                parsed_jobs.append(job)  # Keep job even if parsing fails

        return parsed_jobs

    def _step_filter_and_score(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 3: Score and filter jobs by fit."""
        filtered_jobs = []

        for job in jobs:
            # Check deduplication
            should_skip, reason = self.deduplicator.should_skip_job(job)
            if should_skip:
                logger.debug(f"Skipping job: {reason}")
                continue

            # Score job using profile-based scorer
            score = self.scorer.score_job(job)
            job["fit_score"] = score

            # Keep jobs above threshold
            min_score = int(os.getenv("MIN_FIT_SCORE", "50"))
            if score >= min_score:
                # Store in database
                try:
                    job_id = self.db.add_job(
                        title=job.get("title", ""),
                        company=job.get("company", ""),
                        url=job.get("url", ""),
                        source=job.get("source", "unknown"),
                        jd_text=job.get("jd_text", ""),
                        fit_score=score
                    )
                    job["job_id"] = job_id
                except Exception as e:
                    logger.warning(f"DB insert failed: {e}")
                    job["job_id"] = 0

                filtered_jobs.append(job)
                logger.info(f"  [+] {job.get('title')} at {job.get('company')} "
                            f"(score: {score}/100)")
            else:
                logger.debug(f"  [-] {job.get('title')} at {job.get('company')} "
                             f"(score: {score}/100, below threshold)")

        # Sort by score
        filtered_jobs.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
        return filtered_jobs

    def _step_tailor(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 4: Generate tailored resume + cover letter for each job."""
        tailored_jobs = []
        profile_data = self.profile.to_dict()
        master_resume = os.path.join("resume", "master_resume.pdf")

        for job in jobs:
            try:
                # Add current job context to profile for file naming
                profile_data["_current_company"] = job.get("company", "company")
                profile_data["_current_job_id"] = str(job.get("job_id", "0"))

                # Generate tailored resume
                resume_path = self.doc_agent.generate_tailored_resume(
                    job_jd=job.get("jd_text", ""),
                    profile=profile_data,
                    master_resume_path=master_resume if os.path.exists(master_resume) else ""
                )
                job["resume_path"] = resume_path

                # Generate cover letter
                cover_letter_path = self.doc_agent.generate_cover_letter(
                    job_data=job,
                    profile=profile_data
                )
                job["cover_letter_path"] = cover_letter_path

                # Update DB status
                if job.get("job_id"):
                    self.db.update_job_status(job["job_id"], "tailored")

                tailored_jobs.append(job)
                logger.info(f"  [TAILORED] {job.get('company', 'Unknown')}")

            except Exception as e:
                logger.error(f"Tailor error for {job.get('company', 'Unknown')}: {e}")
                self.results["errors"].append(f"Tailor: {e}")
                tailored_jobs.append(job)  # Keep job even if tailoring fails

        return tailored_jobs

    def _step_draft_and_send(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 5: Draft emails for each job."""
        applied_jobs = []
        profile_data = self.profile.to_dict()

        for job in jobs:
            try:
                # Draft email using LLM
                email_data = self.email_agent.draft_email(
                    job_data=job,
                    profile=profile_data
                )

                subject = email_data.get("subject", f"Application: {job.get('title', '')}")
                body = email_data.get("body", "")

                # Log email to database
                email_id = self.db.add_email_log(
                    job_id=job.get("job_id", 0),
                    hr_email=job.get("hr_email", ""),
                    subject=subject,
                    body_text=body,
                    resume_path=job.get("resume_path", ""),
                    cover_letter_path=job.get("cover_letter_path", "")
                )

                # Check if we should auto-send
                if self.job_agent.should_auto_apply(job) and job.get("hr_email"):
                    # Send email via Gmail API
                    try:
                        from email.sender import EmailSender
                        sender = EmailSender()
                        sent = sender.send_email(
                            to_email=job["hr_email"],
                            subject=subject,
                            body=body,
                            resume_path=job.get("resume_path"),
                            cover_letter_path=job.get("cover_letter_path")
                        )
                        if sent:
                            self.db.update_email_status(email_id, "sent")
                            logger.info(f"  [SENT] Email to {job['hr_email']}")
                        else:
                            self.db.update_email_status(email_id, "failed")
                    except Exception as e:
                        logger.warning(f"Email send failed: {e}")
                        self.db.update_email_status(email_id, "pending")
                else:
                    # Mark as drafted (pending manual review)
                    self.db.update_email_status(email_id, "drafted")
                    logger.info(f"  [DRAFTED] Email for {job.get('company', 'Unknown')} "
                                f"(pending review)")

                # Update job status
                if job.get("job_id"):
                    self.db.update_job_status(job["job_id"], "applied")

                applied_jobs.append(job)

            except Exception as e:
                logger.error(f"Email error for {job.get('company', 'Unknown')}: {e}")
                self.results["errors"].append(f"Email: {e}")

        return applied_jobs

    def save_run_summary(self) -> str:
        """Save run summary to logs."""
        summary_path = os.path.join(
            log_dir,
            f"run_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        )

        with open(summary_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Run summary saved: {summary_path}")
        return summary_path


def main():
    """Run the pipeline."""
    orchestrator = Orchestrator()
    results = orchestrator.run_full_pipeline(triggered_by="manual")
    orchestrator.save_run_summary()

    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"Jobs Found:     {results['jobs_found']}")
    print(f"Jobs Filtered:  {results['jobs_filtered']}")
    print(f"Jobs Applied:   {results['jobs_applied']}")
    print(f"Emails Sent:    {results['emails_sent']}")
    print(f"Errors:         {len(results['errors'])}")
    print(f"Status:         {results['status']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
