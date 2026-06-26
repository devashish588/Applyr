"""
API layer for Applyr AI job application platform.

This module provides the REST API endpoints for the Applyr platform,
using the new core architecture with typed models and event-driven services.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from core.models import (
    Resume, Profile, Job, Recruiter, Email, Application,
    PipelineRun, SearchStrategy, Company, PipelineEvent, SystemHealth
)
from core.services import get_orchestrator, get_event_bus

logger = logging.getLogger(__name__)


class ApplyrAPI:
    """API layer for Applyr platform."""

    def __init__(self, app: Flask):
        self.app = app
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup API routes."""
        # Profile endpoints
        self.app.route("/api/profile", methods=["GET"])(self.get_profile)
        self.app.route("/api/profile", methods=["PUT"])(self.update_profile)

        # Resume endpoints
        self.app.route("/api/resume", methods=["GET"])(self.get_resume_status)
        self.app.route("/api/resume/upload", methods=["POST"])(self.upload_resume)
        self.app.route("/api/resume/parsed", methods=["GET"])(self.get_parsed_resume)

        # Job endpoints
        self.app.route("/api/jobs", methods=["GET"])(self.get_jobs)
        self.app.route("/api/jobs/<int:job_id>", methods=["GET"])(self.get_job)
        self.app.route("/api/jobs/<int:job_id>/match", methods=["GET"])(self.get_job_match)

        # Application endpoints
        self.app.route("/api/applications", methods=["GET"])(self.get_applications)

        # Recruiter endpoints
        self.app.route("/api/recruiters", methods=["GET"])(self.get_recruiters)

        # Email endpoints
        self.app.route("/api/emails", methods=["GET"])(self.get_emails)
        self.app.route("/api/email/status", methods=["GET"])(self.get_email_status)
        self.app.route("/api/email/test", methods=["POST"])(self.send_test_email)

        # Pipeline endpoints
        self.app.route("/api/run", methods=["POST"])(self.run_pipeline)
        self.app.route("/api/pipeline/logs/<run_id>", methods=["GET"])(self.get_pipeline_logs)

        # Analytics endpoints
        self.app.route("/api/analytics", methods=["GET"])(self.get_analytics)

        # System health endpoints
        self.app.route("/api/status", methods=["GET"])(self.get_system_status)
        self.app.route("/api/health", methods=["GET"])(self.get_system_health)

        # Setup endpoints
        self.app.route("/api/setup/status", methods=["GET"])(self.get_setup_status)

        # Configuration endpoints
        self.app.route("/api/config", methods=["GET"])(self.get_config)

    def get_profile(self) -> Response:
        """Get user profile."""
        try:
            from db.db_client import get_db
            db = get_db()

            # Get resume data
            resume_data = db.get_resume_data()
            if not resume_data:
                return jsonify({"error": "No resume uploaded"}), 404

            # Parse resume JSON
            parsed_resume = resume_data.get("parsed_json", {})
            resume = Resume(**parsed_resume)

            # Create profile from resume
            from core.services import get_profile_service
            profile_service = get_profile_service()
            profile = profile_service.create_profile_from_resume(resume)

            return jsonify({
                "success": True,
                "profile": profile.dict(),
                "resume": resume.dict(),
            })

        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return jsonify({"error": str(e)}), 500

    def update_profile(self) -> Response:
        """Update user profile."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # TODO: Implement profile update logic
            # This would involve updating the profile.json file

            return jsonify({
                "success": True,
                "profile": data,
            })

        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return jsonify({"error": str(e)}), 500

    def get_resume_status(self) -> Response:
        """Get resume upload status."""
        try:
            from db.db_client import get_db
            db = get_db()

            # Get resume data
            resume_data = db.get_resume_data()
            if not resume_data:
                return jsonify({"uploaded": False})

            # Parse resume JSON
            parsed_resume = resume_data.get("parsed_json", {})
            resume = Resume(**parsed_resume)

            return jsonify({
                "uploaded": True,
                "filename": resume_data.get("filename"),
                "file_size": resume_data.get("file_size"),
                "uploaded_at": resume_data.get("uploaded_at"),
                "parsed_at": resume_data.get("parsed_at"),
                "parse_status": resume_data.get("parse_status"),
                "name": resume.name,
                "skills_count": len(resume.skills),
                "experience_count": len(resume.experience),
                "education_count": len(resume.education),
                "confidence": resume.confidence,
                "sections_detected": resume.sections_detected,
                "sections_missing": resume.sections_missing,
            })

        except Exception as e:
            logger.error(f"Error getting resume status: {e}")
            return jsonify({"error": str(e)}), 500

    def upload_resume(self) -> Response:
        """Upload resume file."""
        try:
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files["file"]
            if not file.filename:
                return jsonify({"error": "No file selected"}), 400

            # Save file
            upload_dir = Path("resume")
            upload_dir.mkdir(parents=True, exist_ok=True)

            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            filename = f"master_resume.{ext}"
            filepath = upload_dir / filename

            file.save(filepath)

            # Parse resume
            from agents.resume_parser_agent import ResumeParserAgent
            parser = ResumeParserAgent()
            parsed = parser.parse_file(str(filepath))

            # Save to database
            from db.db_client import get_db
            db = get_db()

            db.save_resume_data({
                "filename": file.filename,
                "file_size": filepath.stat().st_size,
                "uploaded_at": datetime.now().isoformat(),
                "parsed_at": datetime.now().isoformat(),
                "parse_status": "success",
                "parsed": parsed,
                "skills": parsed.get("skills", []),
                "roles": parsed.get("roles", []),
                "health": {
                    "resume_parsed": True,
                    "profile_generated": True,
                    "embedding_created": True,
                    "ready_for_search": True,
                },
            })

            return jsonify({
                "success": True,
                "filename": file.filename,
                "file_size": filepath.stat().st_size,
                "parsed": parsed,
            })

        except Exception as e:
            logger.error(f"Error uploading resume: {e}")
            return jsonify({"error": str(e)}), 500

    def get_parsed_resume(self) -> Response:
        """Get parsed resume data."""
        try:
            from db.db_client import get_db
            db = get_db()

            # Get resume data
            resume_data = db.get_resume_data()
            if not resume_data:
                return jsonify({"success": False, "error": "No resume uploaded"}), 404

            # Parse resume JSON
            parsed_resume = resume_data.get("parsed_json", {})
            resume = Resume(**parsed_resume)

            return jsonify({
                "success": True,
                "filename": resume_data.get("filename"),
                "file_size": resume_data.get("file_size"),
                "uploaded_at": resume_data.get("uploaded_at"),
                "parse_status": resume_data.get("parse_status"),
                "parsed_json": resume.dict(),
                "skills_json": resume.skills,
                "roles_json": resume.roles,
            })

        except Exception as e:
            logger.error(f"Error getting parsed resume: {e}")
            return jsonify({"error": str(e)}), 500

    def get_jobs(self) -> Response:
        """Get jobs."""
        try:
            from db.db_client import get_db
            db = get_db()

            jobs = db.get_all_jobs(limit=100)
            return jsonify({
                "success": True,
                "jobs": jobs,
                "total": len(jobs),
            })

        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return jsonify({"error": str(e)}), 500

    def get_job(self, job_id: int) -> Response:
        """Get job by ID."""
        try:
            from db.db_client import get_db
            db = get_db()

            job = db.get_job_by_id(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            return jsonify({
                "success": True,
                "job": job,
            })

        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return jsonify({"error": str(e)}), 500

    def get_job_match(self, job_id: int) -> Response:
        """Get job match information."""
        try:
            from db.db_client import get_db
            db = get_db()

            job = db.get_job_by_id(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            # Calculate match
            profile_path = os.getenv("PROFILE_PATH", "profile.json")
            if os.path.exists(profile_path):
                with open(profile_path) as f:
                    profile = json.load(f)

                skills = profile.get("skills", {})
                all_skills = (
                    skills.get("languages", []) +
                    skills.get("frameworks", []) +
                    skills.get("tools", [])
                )

                jd_text = (job.get("jd_text") or "").lower()
                matched = [s for s in all_skills if s.lower() in jd_text]
                missing = [s for s in all_skills if s.lower() not in jd_text][:5]

                score = job.get("fit_score", 0) or 0
                recommendation = "Apply" if score >= 70 else ("Consider" if score >= 50 else "Skip")
                explanation = []
                if matched:
                    explanation.append(f"Strong alignment with {', '.join(matched[:3])} requirements.")
                if missing:
                    explanation.append(f"Missing experience in {', '.join(missing[:3])}.")

                match = {
                    "fit_score": score,
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "explanation": " ".join(explanation),
                    "recommendation": recommendation,
                }
            else:
                match = {"fit_score": job.get("fit_score", 0)}

            return jsonify({
                "success": True,
                "match": match,
            })

        except Exception as e:
            logger.error(f"Error getting job match: {e}")
            return jsonify({"error": str(e)}), 500

    def get_applications(self) -> Response:
        """Get applications."""
        try:
            from db.db_client import get_db
            db = get_db()

            jobs = db.get_all_jobs(limit=100)
            return jsonify({
                "success": True,
                "applications": jobs,
                "total": len(jobs),
            })

        except Exception as e:
            logger.error(f"Error getting applications: {e}")
            return jsonify({"error": str(e)}), 500

    def get_recruiters(self) -> Response:
        """Get recruiters."""
        try:
            from db.db_client import get_db
            db = get_db()

            recruiters = db.get_all_recruiters(limit=50)
            return jsonify({
                "success": True,
                "recruiters": recruiters,
                "total": len(recruiters),
            })

        except Exception as e:
            logger.error(f"Error getting recruiters: {e}")
            return jsonify({"error": str(e)}), 500

    def get_emails(self) -> Response:
        """Get emails."""
        try:
            from db.db_client import get_db
            db = get_db()

            emails = db.get_unsent_emails()
            return jsonify({
                "success": True,
                "emails": emails,
                "total": len(emails),
            })

        except Exception as e:
            logger.error(f"Error getting emails: {e}")
            return jsonify({"error": str(e)}), 500

    def get_email_status(self) -> Response:
        """Get email status."""
        try:
            resend_key = os.getenv("RESEND_API_KEY", "")
            from_email = os.getenv("FROM_EMAIL", "")
            gmail_creds = os.path.exists(os.getenv("GMAIL_CREDENTIALS_PATH", "./email/credentials.json"))

            configured = bool(resend_key and from_email) or gmail_creds
            provider = "resend" if (resend_key and from_email) else ("gmail" if gmail_creds else None)

            return jsonify({
                "success": True,
                "resend_configured": bool(resend_key and from_email),
                "gmail_configured": gmail_creds,
                "from_email": from_email or None,
                "configured": configured,
                "provider": provider,
            })

        except Exception as e:
            logger.error(f"Error getting email status: {e}")
            return jsonify({"error": str(e)}), 500

    def send_test_email(self) -> Response:
        """Send test email."""
        try:
            from email_module.sender import EmailSender
            sender = EmailSender()
            result = sender.send_test()
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def run_pipeline(self) -> Response:
        """Run pipeline."""
        try:
            # Get orchestrator
            orchestrator = get_orchestrator()

            # Run pipeline
            run = orchestrator.run_pipeline(triggered_by="manual")

            return jsonify({
                "success": True,
                "run_id": run.run_id,
                "status": run.status,
            })

        except Exception as e:
            logger.error(f"Error running pipeline: {e}")
            return jsonify({"error": str(e)}), 500

    def get_pipeline_logs(self, run_id: str) -> Response:
        """Get pipeline logs."""
        try:
            from db.db_client import get_db
            db = get_db()

            events = db.get_pipeline_events(run_id)
            return jsonify({
                "success": True,
                "events": events,
                "total": len(events),
            })

        except Exception as e:
            logger.error(f"Error getting pipeline logs: {e}")
            return jsonify({"error": str(e)}), 500

    def get_analytics(self) -> Response:
        """Get analytics."""
        try:
            from db.db_client import get_db
            db = get_db()

            all_jobs = db.get_all_jobs(limit=1000)
            runs = db.get_recent_run_logs(limit=50)

            total = len(all_jobs)
            drafted = sum(1 for j in all_jobs if j.get("status") in ("sent", "draft", "ready"))
            submitted = sum(1 for j in all_jobs if j.get("status") == "sent")
            emails_drafted = drafted
            emails_sent = submitted

            avg = sum(j.get("fit_score") or 0 for j in all_jobs) / max(total, 1)
            sources = {}
            for j in all_jobs:
                src = j.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1

            dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

            return jsonify({
                "success": True,
                "analytics": {
                    "total_jobs": total,
                    "applications_drafted": drafted,
                    "applications_submitted": submitted,
                    "emails_drafted": emails_drafted,
                    "emails_sent": emails_sent,
                    "avg_score": round(avg, 1),
                    "total_runs": len(runs),
                    "source_distribution": sources,
                    "dry_run": dry_run,
                }
            })

        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return jsonify({"error": str(e)}), 500

    def get_system_status(self) -> Response:
        """Get system status."""
        try:
            from db.db_client import get_db
            db = get_db()

            groq_key = os.getenv("GROQ_API_KEY", "")
            tavily_key = os.getenv("TAVILY_API_KEY", "")
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY", "")
            hunter_key = os.getenv("HUNTER_API_KEY", "")
            clearbit_key = os.getenv("CLEARBIT_API_KEY", "")

            resume_data = None
            try:
                resume_data = db.get_resume_data()
            except Exception:
                pass

            resume_path = os.getenv("MASTER_RESUME_PDF", "resume/master_resume.pdf")

            return jsonify({
                "status": "online",
                "timestamp": datetime.now().isoformat(),
                "resume_uploaded": os.path.exists(resume_path),
                "resume_parsed": bool(resume_data and resume_data.get("parse_status") == "success"),
                "resume_path": resume_path if os.path.exists(resume_path) else None,
                "recruiters_count": len(db.get_all_recruiters()),
                "env_keys": {
                    "GROQ_API_KEY": bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx"),
                    "TAVILY_API_KEY": bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx"),
                    "GEMINI_API_KEY": bool(gemini_key),
                    "SCRAPINGBEE_API_KEY": bool(scrapingbee_key),
                    "HUNTER_API_KEY": bool(hunter_key),
                    "CLEARBIT_API_KEY": bool(clearbit_key),
                },
                "email": {
                    "configured": bool(os.getenv("RESEND_API_KEY") and os.getenv("FROM_EMAIL")),
                    "from_email": os.getenv("FROM_EMAIL") or None,
                    "provider": "resend" if (os.getenv("RESEND_API_KEY") and os.getenv("FROM_EMAIL")) else ("gmail" if os.path.exists(os.getenv("GMAIL_CREDENTIALS_PATH", "./email/credentials.json")) else None),
                },
                "recruiter_discovery": {
                    "hunter": bool(hunter_key),
                    "clearbit": bool(clearbit_key),
                    "active": bool(hunter_key or clearbit_key),
                },
            })

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return jsonify({"error": str(e)}), 500

    def get_system_health(self) -> Response:
        """Get system health."""
        try:
            groq_key = os.getenv("GROQ_API_KEY", "")
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            tavily_key = os.getenv("TAVILY_API_KEY", "")
            scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY", "")
            hunter_key = os.getenv("HUNTER_API_KEY", "")
            clearbit_key = os.getenv("CLEARBIT_API_KEY", "")

            from db.db_client import get_db
            db = get_db()

            resume_data = db.get_resume_data()
            resume_path = os.getenv("MASTER_RESUME_PDF", "resume/master_resume.pdf")
            uploaded = os.path.exists(resume_path)

            services = [
                {"n": "Groq", "ok": bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx"), "d": "LLM Provider"},
                {"n": "Gemini", "ok": bool(gemini_key), "d": "Backup LLM"},
                {"n": "Tavily", "ok": bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx"), "d": "Job Search"},
                {"n": "ScrapingBee", "ok": bool(scrapingbee_key), "d": "Web Scraping"},
                {"n": "Hunter", "ok": bool(hunter_key), "d": "Recruiter Email"},
                {"n": "Clearbit", "ok": bool(clearbit_key), "d": "Company Data"},
                {"n": "Resume Parser", "ok": uploaded and bool(resume_data), "d": "PDF Extraction"},
                {"n": "Email", "ok": bool(os.getenv("RESEND_API_KEY") and os.getenv("FROM_EMAIL")), "d": "Delivery"},
            ]

            return jsonify({
                "success": True,
                "services": services,
            })

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return jsonify({"error": str(e)}), 500

    def get_setup_status(self) -> Response:
        """Get setup status."""
        try:
            resume_dir = Path("resume")
            resume_uploaded = any(
                (resume_dir / name).exists()
                for name in ["master_resume.pdf", "master_resume.docx", "master_resume.txt"]
            )

            from db.db_client import get_db
            db = get_db()

            resume_data = None
            try:
                resume_data = db.get_resume_data()
            except Exception:
                pass

            resume_parsed = bool(resume_data and resume_data.get("parse_status") == "success")

            groq_key = os.getenv("GROQ_API_KEY", "")
            groq_ok = bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx")

            tavily_key = os.getenv("TAVILY_API_KEY", "")
            tavily_ok = bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx")

            gemini_key = os.getenv("GEMINI_API_KEY", "")
            gemini_ok = bool(gemini_key)

            resend_key = os.getenv("RESEND_API_KEY", "")
            from_email = os.getenv("FROM_EMAIL", "")
            email_ok = bool(resend_key and from_email)

            hunter_key = os.getenv("HUNTER_API_KEY", "")
            clearbit_key = os.getenv("CLEARBIT_API_KEY", "")
            recruiter_ok = bool(hunter_key or clearbit_key)

            steps = [
                {"id": "resume_uploaded", "label": "Resume Uploaded", "ok": resume_uploaded,
                 "message": "Resume uploaded" if resume_uploaded else "No resume uploaded"},
                {"id": "resume_parsed", "label": "Resume Parsed", "ok": resume_parsed,
                 "message": "Resume parsed successfully" if resume_parsed else "Resume not yet parsed"},
                {"id": "groq", "label": "Groq Connected", "ok": groq_ok,
                 "message": "Groq API connected" if groq_ok else "Groq API key missing"},
                {"id": "tavily", "label": "Tavily Connected", "ok": tavily_ok,
                 "message": "Tavily API connected" if tavily_ok else "Tavily API key missing"},
                {"id": "gemini", "label": "Gemini Backup", "ok": gemini_ok,
                 "message": "Gemini configured" if gemini_ok else "Gemini key missing (optional)"},
                {"id": "email", "label": "Email Configured", "ok": email_ok,
                 "message": f"Email ready ({from_email})" if email_ok else "Email not configured — set RESEND_API_KEY"},
                {"id": "recruiter", "label": "Recruiter Discovery", "ok": recruiter_ok,
                 "message": "Recruiter discovery active" if recruiter_ok else "Limited — no Hunter or Clearbit key"},
            ]

            completed = sum(1 for s in steps if s["ok"])
            total = len(steps)
            percent = round(completed / total * 100) if total > 0 else 0

            return jsonify({
                "success": True,
                "steps": steps,
                "completed": completed,
                "total": total,
                "percent": percent,
                "ready": percent >= 60,
            })

        except Exception as e:
            logger.error(f"Error getting setup status: {e}")
            return jsonify({"error": str(e)}), 500

    def get_config(self) -> Response:
        """Get configuration."""
        try:
            return jsonify({
                "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
                "auto_apply": os.getenv("AUTO_APPLY", "false").lower() == "true",
                "min_fit_score": int(os.getenv("MIN_FIT_SCORE", "50")),
                "max_emails_per_run": int(os.getenv("MAX_EMAILS_PER_RUN", "10")),
                "max_per_day": int(os.getenv("MAX_APPLICATIONS_PER_DAY", "20")),
                "scheduler_enabled": os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
                "scheduler_cron": os.getenv("SCHEDULER_CRON", "0 9,12,15,18 * * *"),
            })

        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return jsonify({"error": str(e)}), 500


# Create Flask app and API instance
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Initialize API
api = ApplyrAPI(app)


@app.route("/")
def dashboard():
    """Serve dashboard."""
    return app.send_from_directory("ui/templates", "index.html")


if __name__ == "__main__":
    logger.info("Starting Applyr API on http://localhost:5000")
    app.run(
        debug=os.getenv("DEBUG", "true").lower() == "true",
        use_reloader=False,
        host="0.0.0.0",
        port=int(os.getenv("FLASK_PORT", 5000)),
    )