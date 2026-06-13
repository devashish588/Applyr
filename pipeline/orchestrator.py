"""
Orchestrator - main pipeline that coordinates all 6 agents.
Runs the 5-step process: discover → parse & match → filter & score → tailor → draft & send
"""
import os
import sys
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_client import get_db
from utils.profile_loader import get_profile
from utils.fit_scorer import FitScorer
from utils.deduplicator import Deduplicator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Main pipeline orchestrator."""
    
    def __init__(self):
        self.db = get_db()
        self.profile = get_profile()
        self.scorer = FitScorer()
        self.deduplicator = Deduplicator()
        self.run_id = str(uuid.uuid4())
        self.results = {
            "run_id": self.run_id,
            "jobs_found": 0,
            "jobs_filtered": 0,
            "jobs_applied": 0,
            "emails_sent": 0,
            "errors": []
        }
    
    def run_full_pipeline(self, triggered_by: str = "scheduler") -> Dict[str, Any]:
        """
        Run the complete 5-step pipeline.
        
        Steps:
        1. Discover - Web research agent scrapes jobs
        2. Parse & Match - Resume parser + PDF QA process JDs
        3. Filter & Score - Job application agent ranks by fit
        4. Tailor - Documentation writer rewrites resume + cover letter
        5. Draft & Send - Email drafting agent composes and sends cold email
        """
        logger.info(f"Starting pipeline (run_id: {self.run_id})")
        
        # Start run log
        run_log_id = self.db.start_run_log(self.run_id, triggered_by)
        logger.info(f"Created run log: {run_log_id}")
        
        try:
            # Step 1: Discover
            logger.info("Step 1: Discovering jobs...")
            discovered_jobs = self._step_discover()
            self.results["jobs_found"] = len(discovered_jobs)
            logger.info(f"Discovered {len(discovered_jobs)} jobs")
            
            # Step 2: Parse & Match
            logger.info("Step 2: Parsing and matching...")
            parsed_jobs = self._step_parse_and_match(discovered_jobs)
            logger.info(f"Parsed {len(parsed_jobs)} jobs")
            
            # Step 3: Filter & Score
            logger.info("Step 3: Filtering and scoring...")
            filtered_jobs = self._step_filter_and_score(parsed_jobs)
            self.results["jobs_filtered"] = len(filtered_jobs)
            logger.info(f"Filtered to {len(filtered_jobs)} jobs (min score: 50)")
            
            # Step 4: Tailor
            logger.info("Step 4: Tailoring applications...")
            tailored_jobs = self._step_tailor(filtered_jobs)
            logger.info(f"Tailored {len(tailored_jobs)} applications")
            
            # Step 5: Draft & Send
            logger.info("Step 5: Drafting and sending emails...")
            applied_jobs = self._step_draft_and_send(tailored_jobs)
            self.results["jobs_applied"] = len(applied_jobs)
            self.results["emails_sent"] = self._count_emails_sent()
            logger.info(f"Completed applications: {len(applied_jobs)}")
            
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
            logger.info(f"Pipeline completed successfully: {self.results}")
            
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
        """
        Step 1: Web research agent discovers jobs.
        
        TODO: Call your 01_web_research_agent.py
        For now, return empty list (you'll plug in your agent here)
        """
        logger.info("Calling Web Research Agent (01_web_research_agent)...")
        
        # TODO: Import and call your web research agent
        # from agents.web_research_agent import WebResearchAgent
        # agent = WebResearchAgent()
        # jobs = agent.scrape_jobs()
        
        # Placeholder: return empty list
        return []
    
    def _step_parse_and_match(self, discovered_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 2: Resume parser + PDF QA agents process jobs.
        
        TODO: Call your 09_resume_parser_agent.py and 03_pdf_qa_agent.py
        For now, return input jobs
        """
        logger.info("Calling Resume Parser (09) and PDF QA (03) agents...")
        
        # TODO: Import and call your agents
        # from agents.resume_parser_agent import ResumeParserAgent
        # from agents.pdf_qa_agent import PDFQAAgent
        # parser = ResumeParserAgent()
        # pdf_qa = PDFQAAgent()
        
        parsed_jobs = []
        for job in discovered_jobs:
            # Parse JD text
            # Extract skills, experience, etc.
            parsed_jobs.append(job)
        
        return parsed_jobs
    
    def _step_filter_and_score(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3: Job application agent filters and scores by fit.
        
        TODO: Call your 18_job_application_agent.py
        """
        logger.info("Calling Job Application Agent (18)...")
        
        filtered_jobs = []
        
        for job in jobs:
            # Check deduplication
            should_skip, reason = self.deduplicator.should_skip_job(job)
            if should_skip:
                logger.debug(f"Skipping job: {reason}")
                continue
            
            # Score job
            score = self.scorer.score_job(job)
            job["fit_score"] = score
            
            # Keep jobs above threshold (50)
            if score >= 50:
                filtered_jobs.append(job)
                
                # Store in database
                job_id = self.db.add_job(
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    url=job.get("url", ""),
                    source=job.get("source", "unknown"),
                    jd_text=job.get("jd_text", ""),
                    fit_score=score
                )
                job["job_id"] = job_id
                logger.info(f"Added job: {job.get('title')} at {job.get('company')} (score: {score})")
        
        return filtered_jobs
    
    def _step_tailor(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 4: Documentation writer tailors resume and cover letter.
        
        TODO: Call your 16_doc_writer_agent.py
        """
        logger.info("Calling Documentation Writer Agent (16)...")
        
        # TODO: Import and call your agent
        # from agents.doc_writer_agent import DocWriterAgent
        # writer = DocWriterAgent()
        
        tailored_jobs = []
        
        for job in jobs:
            try:
                # Generate tailored resume
                resume_path = f"./resume/tailored/{job.get('company')}_{job.get('job_id')}_resume.pdf"
                
                # Generate cover letter
                cover_letter_path = f"./resume/cover_letters/{job.get('company')}_{job.get('job_id')}_cover_letter.txt"
                
                job["resume_path"] = resume_path
                job["cover_letter_path"] = cover_letter_path
                
                # Mark as tailored
                self.db.update_job_status(job.get("job_id"), "tailored")
                tailored_jobs.append(job)
                
                logger.info(f"Tailored application for {job.get('company')}")
            
            except Exception as e:
                logger.error(f"Error tailoring job {job.get('job_id')}: {e}")
                self.results["errors"].append(f"Tailor error: {e}")
        
        return tailored_jobs
    
    def _step_draft_and_send(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 5: Email drafting agent composes and sends cold email.
        
        TODO: Call your 05_email_drafting_agent.py
        """
        logger.info("Calling Email Drafting Agent (05)...")
        
        # TODO: Import and call your agent
        # from agents.email_drafting_agent import EmailDraftingAgent
        # mailer = EmailDraftingAgent()
        
        applied_jobs = []
        
        for job in jobs:
            try:
                # Generate email subject and body
                company = job.get("company", "Unknown")
                role = job.get("title", "Unknown")
                
                subject = f"Application: {role} at {company}"
                body = f"Dear Hiring Team,\n\nI'm interested in the {role} position at {company}.\n\nBest regards"
                
                # Log email
                email_id = self.db.add_email_log(
                    job_id=job.get("job_id"),
                    hr_email=job.get("hr_email", ""),
                    subject=subject,
                    body_text=body,
                    resume_path=job.get("resume_path", ""),
                    cover_letter_path=job.get("cover_letter_path", "")
                )
                
                # TODO: Actually send email via Gmail API
                # status = mailer.send_email(...)
                
                # For now, mark as pending
                self.db.update_email_status(email_id, "pending")
                self.db.update_job_status(job.get("job_id"), "applied")
                
                applied_jobs.append(job)
                logger.info(f"Prepared email for {company}")
            
            except Exception as e:
                logger.error(f"Error preparing email for job {job.get('job_id')}: {e}")
                self.results["errors"].append(f"Email error: {e}")
        
        return applied_jobs
    
    def _count_emails_sent(self) -> int:
        """Count emails successfully sent in this run."""
        # This would be updated when email agent actually sends
        return 0
    
    def save_run_summary(self) -> str:
        """Save run summary to logs."""
        summary_path = f"./logs/run_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        
        import json
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        
        with open(summary_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Run summary saved to {summary_path}")
        return summary_path


def main():
    """Run the pipeline."""
    orchestrator = Orchestrator()
    results = orchestrator.run_full_pipeline(triggered_by="manual")
    orchestrator.save_run_summary()
    
    print("\n" + "="*50)
    print("PIPELINE SUMMARY")
    print("="*50)
    print(f"Jobs Found:     {results['jobs_found']}")
    print(f"Jobs Filtered:  {results['jobs_filtered']}")
    print(f"Jobs Applied:   {results['jobs_applied']}")
    print(f"Emails Sent:    {results['emails_sent']}")
    print(f"Errors:         {len(results['errors'])}")
    print(f"Status:         {results['status']}")
    print("="*50)


if __name__ == "__main__":
    main()
