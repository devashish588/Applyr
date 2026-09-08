"""
Applyr v2.1 — Flask API Server
Pure JSON API backend — no HTML rendering.
The frontend is a separate Next.js app in frontend/.

Run:
    python ui/app.py
    → http://localhost:5000/api/...
"""

import json
import logging
import os
import queue
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from flask import Flask, Response, jsonify, request, stream_with_context, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from db.db_client import get_db

from core.services.match_service import MatchService, get_match_service
from core.models import Profile, Resume, SeniorityLevel, MatchAnalysis
from core.services.gmail_service import GmailService, get_gmail_service
from core.services.startup_service import StartupDiscoveryService

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]}})
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"]      = os.getenv("UPLOAD_DIR", str(ROOT / "uploads"))
app.config["SECRET_KEY"]         = os.getenv("SECRET_KEY", "dev-secret-change-me")

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_JD     = {"pdf", "png", "jpg", "jpeg", "txt"}
ALLOWED_RESUME = {"pdf", "docx", "doc", "txt"}

# SSE event queues keyed by run_id
_pipeline_queues: dict[str, queue.Queue] = {}

# In-memory role inference cache (populated on resume upload)
_inferred_roles: list[str] = []
_search_strategy: dict = {}
_startup_service = StartupDiscoveryService()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

def _allowed(filename, allowed_set):
    return _ext(filename) in allowed_set

def _sanitize_company(company) -> str:
    """Never return None for a company name."""
    if not company or str(company).strip().lower() in ("none", "null", "n/a", ""):
        return "Unknown Company"
    return str(company).strip()

def _infer_roles_from_skills(skills: list[str]) -> list[str]:
    """Infer likely job roles from a skill set."""
    skill_lower = {s.lower() for s in skills}
    roles = []

    ml_keywords = {"machine learning", "scikit-learn", "tensorflow", "pytorch",
                   "keras", "xgboost", "deep learning", "nlp", "computer vision"}
    data_keywords = {"pandas", "numpy", "sql", "power bi", "tableau", "excel",
                     "data analysis", "statistics", "r", "spark"}
    ai_keywords = {"langchain", "llm", "openai", "gpt", "transformers",
                   "huggingface", "rag", "vector database"}
    web_keywords = {"react", "next.js", "node.js", "express", "django", "flask",
                    "fastapi", "html", "css", "javascript", "typescript"}
    backend_keywords = {"python", "java", "go", "rust", "c++", "docker",
                       "kubernetes", "aws", "gcp", "azure", "postgresql", "redis"}
    devops_keywords = {"docker", "kubernetes", "terraform", "ci/cd", "jenkins",
                      "github actions", "aws", "gcp"}

    if skill_lower & ml_keywords:
        roles.extend(["Machine Learning Engineer", "ML Intern"])
    if skill_lower & data_keywords:
        roles.extend(["Data Scientist", "Data Analyst"])
    if skill_lower & ai_keywords:
        roles.extend(["AI Engineer", "GenAI Engineer"])
    if skill_lower & web_keywords:
        roles.extend(["Full Stack Developer", "Frontend Developer"])
    if skill_lower & backend_keywords:
        roles.extend(["Backend Engineer", "Software Engineer"])
    if skill_lower & devops_keywords:
        roles.append("DevOps Engineer")

    # Deduplicate preserving order
    seen = set()
    unique = []
    for r in roles:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique or ["Software Engineer"]


# ── Match helpers ──────────────────────────────────────────────────────────────

def _load_profile_for_match() -> Profile:
    """Load candidate profile from profile.json and resume_data."""
    profile_path = os.getenv("PROFILE_PATH", str(ROOT / "profile.json"))
    profile = Profile()
    if os.path.exists(profile_path):
        try:
            with open(profile_path) as f:
                data = json.load(f)
            profile = Profile(**data)
        except Exception as e:
            logger.warning("Failed to load profile: %s", e)

    # Try to enhance with resume data
    try:
        resume_data = get_db().get_resume_data()
        if resume_data:
            roles = resume_data.get("roles_json", [])
            if roles and not profile.inferred_roles:
                profile.inferred_roles = roles if isinstance(roles, list) else []
            skills = resume_data.get("skills_json", {})
            if isinstance(skills, dict):
                for k, v in skills.items():
                    if k not in profile.skills:
                        profile.skills[k] = v
            elif isinstance(skills, list):
                if "parsed" not in profile.skills:
                    profile.skills["parsed"] = skills
    except Exception as e:
        logger.warning("Failed to load resume data: %s", e)

    return profile


def _build_match_service() -> MatchService:
    """Build a MatchService with profile and resume."""
    profile = _load_profile_for_match()

    # Try to build Resume model from resume_data
    resume = None
    try:
        resume_data = get_db().get_resume_data()
        if resume_data and resume_data.get("parsed_json"):
            parsed = resume_data["parsed_json"]
            if isinstance(parsed, dict):
                resume = Resume(**parsed)
    except Exception as e:
        logger.warning("Failed to build Resume model: %s", e)

    return MatchService(profile=profile, resume=resume)


# ── SSE stream ────────────────────────────────────────────────────────────────
@app.route("/api/pipeline/stream/<run_id>")
def pipeline_stream(run_id):
    def generate():
        q = _pipeline_queues.get(run_id)
        if not q:
            yield f"data: {json.dumps({'step':'error','msg':'Run not found'})}\n\n"
            return
        try:
            while True:
                try:
                    event = q.get(timeout=120)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("step") in ("done", "error"):
                        break
                except queue.Empty:
                    yield f"data: {json.dumps({'step':'timeout','msg':'No activity'})}\n\n"
                    break
        finally:
            _pipeline_queues.pop(run_id, None)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _emit_event(run_id: str, step: str, msg: str, pct: int = 0,
                agent: str = "", status: str = "running", **extra):
    """Push an SSE event AND persist it to DB."""
    ts = datetime.now().isoformat()
    event = {
        "step": step, "msg": msg, "pct": pct,
        "agent": agent, "status": status,
        "timestamp": ts, **extra
    }
    q = _pipeline_queues.get(run_id)
    if q:
        q.put(event)
    # Persist to DB
    try:
        get_db().save_pipeline_event(run_id, {
            "timestamp": ts,
            "agent": agent,
            "step": step,
            "status": status,
            "message": msg,
            "duration_ms": extra.get("duration_ms"),
            "output": extra.get("output"),
            "error": extra.get("error"),
        })
    except Exception as e:
        logger.warning(f"[app] Failed to persist pipeline event: {e}")


def _run_pipeline_thread(run_id: str, job_text: str = None, job_file: str = None):
    """Run orchestrator in background, push SSE events."""
    q = queue.Queue()
    _pipeline_queues[run_id] = q

    def _run():
        try:
            from pipeline.orchestrator import Orchestrator
            orch = Orchestrator(run_id=run_id, event_callback=_emit_event)

            # ── HARD STOP: resume parsing failed or confidence too low ─────────
            if orch.resume_blocked:
                q.put({
                    "step": "blocked",
                    "pct": 0,
                    "msg": orch.resume_block_reason,
                    "blocked": True,
                    "validation": {
                        "name": bool(getattr(orch.parsed_resume, "name", None)) if orch.parsed_resume else False,
                        "skills": bool(getattr(orch.parsed_resume, "skills", [])) if orch.parsed_resume else False,
                        "experience": bool(getattr(orch.parsed_resume, "experience", [])) if orch.parsed_resume else False,
                        "education": bool(getattr(orch.parsed_resume, "education", [])) if orch.parsed_resume else False,
                        "projects": bool(getattr(orch.parsed_resume, "projects", [])) if orch.parsed_resume else False,
                        "confidence": getattr(orch.parsed_resume, "confidence", 0) if orch.parsed_resume else 0,
                    },
                })
                get_db().update_run_log(
                    run_id,
                    status="blocked",
                    errors_count=1,
                    summary={"status": "blocked", "reason": orch.resume_block_reason},
                )
                logger.warning(f"[app] Pipeline BLOCKED: {orch.resume_block_reason}")
                try:
                    _release_pipeline_lock()
                except: pass
                return  # <-- STOP. Do not run pipeline.

            _emit_event(run_id, "init", "Initializing pipeline...", 5, "orchestrator")
            _emit_event(run_id, "discover", "Searching for jobs...", 10, "web_research")

            t0 = time.time()
            results = orch.run_full_pipeline(
                triggered_by="manual" if (job_text or job_file) else "scheduled",
                job_text=job_text,
                job_file=job_file,
            )
            total_ms = int((time.time() - t0) * 1000)

            _emit_event(run_id, "discover_done",
                       f"Found {results.get('jobs_found', 0)} jobs",
                       30, "web_research", "done",
                       count=results.get("jobs_found", 0))
            _emit_event(run_id, "parse_done",
                       f"Filtered to {results.get('jobs_filtered', 0)} new jobs",
                       50, "resume_parser", "done")
            _emit_event(run_id, "score_done",
                       f"Scored and ranked jobs",
                       60, "fit_scorer", "done")
            _emit_event(run_id, "tailor_done",
                       f"Tailored {results.get('jobs_applied', 0)} applications",
                       75, "job_application", "done")
            _emit_event(run_id, "email_done",
                       f"Prepared {results.get('jobs_applied', 0)} draft(s)",
                       90, "email_drafting", "done")

            get_db().update_run_log(
                run_id,
                jobs_found=results.get("jobs_found", 0),
                jobs_filtered=results.get("jobs_filtered", 0),
                jobs_applied=results.get("jobs_applied", 0),
                emails_sent=results.get("emails_sent", 0),
                errors_count=len(results.get("errors", [])),
                status=results.get("status", "completed"),
                summary=results,
            )
            orch.save_run_summary()

            _emit_event(run_id, "done", "Pipeline complete!", 100,
                       "orchestrator", "done", duration_ms=total_ms,
                       results=results)

        except Exception as e:
            logger.error(f"[app] Pipeline thread error: {e}", exc_info=True)
            _emit_event(run_id, "error", str(e), 0, "orchestrator", "error",
                       error=str(e))
        finally:
            try:
                _release_pipeline_lock()
            except: pass

    threading.Thread(target=_run, daemon=True).start()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("index.html")


# ── API Routes ────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    groq_key       = os.getenv("GROQ_API_KEY", "")
    tavily_key     = os.getenv("TAVILY_API_KEY", "")
    resume_path    = os.getenv("MASTER_RESUME_PDF", str(ROOT / "resume/master_resume.pdf"))
    apollo_key     = os.getenv("APOLLO_API_KEY", "")
    hunter_key     = os.getenv("HUNTER_API_KEY", "")
    clearbit_key   = os.getenv("CLEARBIT_API_KEY", "")
    scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY", "")
    gemini_key     = os.getenv("GEMINI_API_KEY", "")

    db = get_db()
    conn = None
    try:
        resume_data = db.get_resume_data()
        conn = db._conn()

        # Email status via EmailSender (checks both Resend and Gmail)
        try:
            from email_module.sender import EmailSender
            sender = EmailSender()
            ps = sender.provider_status()
            email_configured = ps.get("can_send", False)
            email_provider = ps.get("active_provider")
            email_account = ps.get("gmail", {}).get("account") or os.getenv("FROM_EMAIL")
            gmail_status = ps.get("gmail", {}).get("authenticated", False)
        except Exception:
            email_configured = False
            email_provider = None
            email_account = None
            gmail_status = False

        return jsonify({
            "status":           "online",
            "timestamp":        datetime.now().isoformat(),
            "resume_uploaded":  os.path.exists(resume_path),
            "resume_parsed":    bool(resume_data and resume_data.get("parse_status") == "success"),
            "resume_path":      resume_path if os.path.exists(resume_path) else None,
            "recruiters_count": len(db.get_all_recruiters(conn=conn)),
            "env_keys": {
                "GROQ_API_KEY":        bool(groq_key   and groq_key   != "gsk_xxxxxxxxxxxxx"),
                "TAVILY_API_KEY":      bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx"),
                "GEMINI_API_KEY":      bool(gemini_key),
                "SCRAPINGBEE_API_KEY": bool(scrapingbee_key),
                "APOLLO_API_KEY":      bool(apollo_key),
                "CLEARBIT_API_KEY":    bool(clearbit_key),
                "HUNTER_API_KEY":      bool(hunter_key),
            },
            "email": {
                "configured": email_configured,
                "from_email": email_account,
                "provider": email_provider,
                "gmail_status": "connected" if gmail_status else "not_authenticated",
                "health": (
                    "healthy" if email_configured else
                    "missing_configuration"
                ),
            },
            "recruiter_discovery": {
                "apollo": bool(apollo_key),
                "hunter": bool(hunter_key),
                "clearbit": bool(clearbit_key),
                "active": bool(apollo_key or hunter_key or clearbit_key),
            },
        })
    finally:
        if conn is not None:
            try:
                db._put_conn(conn)
            except Exception:
                pass


@app.route("/api/config")
def api_config():
    """Return pipeline config flags — for dry run banner, etc."""
    return jsonify({
        "dry_run":          os.getenv("DRY_RUN", "true").lower() == "true",
        "auto_apply":       os.getenv("AUTO_APPLY", "false").lower() == "true",
        "min_fit_score":    int(os.getenv("MIN_FIT_SCORE", "50")),
        "max_emails_per_run": int(os.getenv("MAX_EMAILS_PER_RUN", "10")),
        "max_per_day":      int(os.getenv("MAX_APPLICATIONS_PER_DAY", "20")),
        "scheduler_enabled": os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
        "scheduler_cron":   os.getenv("SCHEDULER_CRON", "0 9,12,15,18 * * *"),
    })


# ── Resume endpoints ─────────────────────────────────────────────────────────

@app.route("/api/upload-resume", methods=["POST"])
def api_upload_resume():
    # Accept either field name: the Flask UI posts "resume", the Next.js client
    # posts "file". Support both so uploads don't silently 400.
    file = request.files.get("file") or request.files.get("resume")
    if file is None:
        logger.warning(
            f"[app] upload-resume 400: no file field. "
            f"files={list(request.files.keys())} form={list(request.form.keys())} "
            f"content_type={request.content_type!r}"
        )
        return jsonify({"error": "No file provided"}), 400
    if not file.filename:
        logger.warning("[app] upload-resume 400: empty filename")
        return jsonify({"error": "No filename — please select a file"}), 400
    if not _allowed(file.filename, ALLOWED_RESUME):
        rejected_ext = _ext(file.filename) or "(none)"
        logger.warning(f"[app] upload-resume 400: disallowed type '{file.filename}' ext={rejected_ext}")
        return jsonify({
            "error": f"Unsupported file type '.{rejected_ext}'. Please upload a PDF, DOCX, or TXT."
        }), 400

    ext        = _ext(file.filename)
    resume_dir = ROOT / "resume"
    resume_dir.mkdir(parents=True, exist_ok=True)
    name_map   = {"pdf": "master_resume.pdf", "docx": "master_resume.docx",
                  "doc": "master_resume.docx", "txt": "master_resume.txt"}
    save_path  = resume_dir / name_map.get(ext, "master_resume.txt")
    file.save(save_path)
    upload_time = datetime.now().isoformat()
    file_size = os.path.getsize(save_path)
    logger.info(f"[app] Resume saved: {save_path}")

    result = {
        "success": True,
        "path": str(save_path),
        "filename": file.filename,
        "size": file_size,
        "uploaded_at": upload_time,
    }

    # Parse resume
    parsed = None
    try:
        from agents.resume_parser_agent import ResumeParserAgent
        parsed = ResumeParserAgent().parse_file(str(save_path))
        result["parsed"] = parsed.model_dump() if parsed else {}
        result["parse_status"] = "success"
    except Exception as e:
        logger.warning(f"[app] Resume parse on upload failed: {e}")
        result["parse_error"] = str(e)
        result["parse_status"] = "failed"

    # Infer roles from parsed skills
    global _inferred_roles, _search_strategy
    skills = parsed.skills if parsed else []
    _inferred_roles = _infer_roles_from_skills(skills)

    # Build search strategy
    _search_strategy = {
        "roles": _inferred_roles,
        "locations": ["India", "Remote"],
        "keywords": skills[:10],
        "query": _build_search_query(_inferred_roles, skills),
    }

    # Persist to DB
    health = {
        "resume_parsed": result.get("parse_status") == "success",
        "profile_generated": len(_inferred_roles) > 0,
        "embedding_created": result.get("parse_status") == "success",
        "ready_for_search": result.get("parse_status") == "success" and len(_inferred_roles) > 0,
    }
    try:
        get_db().save_resume_data({
            "filename": file.filename,
            "file_size": file_size,
            "uploaded_at": upload_time,
            "parsed_at": datetime.now().isoformat(),
            "parse_status": result.get("parse_status", "pending"),
            "parsed_json": parsed.model_dump() if parsed else {},
            "skills_json": skills,
            "roles_json": _inferred_roles,
            "health": health,
        })
    except Exception as e:
        logger.warning(f"[app] Failed to persist resume data: {e}")

    result["inferred_roles"] = _inferred_roles
    result["health"] = health
    return jsonify(result)


def _build_search_query(roles: list[str], skills: list[str]) -> str:
    role_part = " OR ".join(f'"{r}"' for r in roles[:4])
    skill_part = " ".join(skills[:5])
    return f"({role_part}) {skill_part} India OR Remote Entry Level Internship"


@app.route("/api/resume-status")
def api_resume_status():
    resume_dir = ROOT / "resume"
    # Check if resume is parsed in DB
    data = get_db().get_resume_data()
    parsed = data and data.get("parse_status") == "success"
    parsed_info = None
    if parsed:
        pj = data.get("parsed_json") or {}
        # Confidence lives inside parsed_json (the parser writes it there); the
        # top-level DB record has no "confidence" key, which is why this used to
        # read 0. Prefer the nested value, fall back to any top-level value.
        raw_conf = pj.get("confidence", data.get("confidence", data.get("parse_confidence", 0))) or 0
        parsed_info = {
            "name": pj.get("name", pj.get("full_name", "")),
            "email": pj.get("email", ""),
            "confidence": int(round(float(raw_conf))),
            "quality_score": pj.get("quality_score", data.get("quality_score", 0)),
            "skills_count": len(pj.get("skills", []) or []),
            "experience_count": len(pj.get("experience", []) or []),
            "education_count": len(pj.get("education", []) or []),
        }
    for name in ["master_resume.pdf", "master_resume.docx", "master_resume.txt"]:
        path = resume_dir / name
        if path.exists():
            return jsonify({
                "uploaded": True, "parsed": parsed_info if parsed else False,
                "path": str(path), "filename": name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            })
    return jsonify({"uploaded": False, "parsed": False})


@app.route("/api/resume/parsed")
def api_resume_parsed():
    """Return full parsed resume data with consistent structure."""
    data = get_db().get_resume_data()

    # If DB has valid parsed data, return it
    if data and data.get("parse_status") == "success":
        parsed_json = data.get("parsed_json") or {}
        skills_json = data.get("skills_json") or parsed_json.get("skills", [])
        roles_json = data.get("roles_json") or parsed_json.get("roles", [])
        return jsonify({
            "success": True,
            "filename": data.get("filename"),
            "file_size": data.get("file_size"),
            "uploaded_at": data.get("uploaded_at"),
            "parse_status": "success",
            "parsed_json": parsed_json,
            "skills_json": skills_json,
            "roles_json": roles_json,
        })

    # DB data is stale/failed or missing — re-parse from disk
    resume_dir = ROOT / "resume"
    for name in ["master_resume.pdf", "master_resume.docx", "master_resume.txt"]:
        path = resume_dir / name
        if path.exists():
            try:
                from agents.resume_parser_agent import ResumeParserAgent
                parsed = ResumeParserAgent().parse_file(str(path))
                resume_dict = parsed.model_dump() if parsed else {}
                # Persist successful parse to DB
                try:
                    get_db().save_resume_data({
                        "filename": name,
                        "file_size": path.stat().st_size,
                        "uploaded_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                        "parsed_at": datetime.now().isoformat(),
                        "parse_status": "success",
                        "parsed_json": resume_dict,
                        "skills_json": parsed.skills if parsed else [],
                        "roles_json": parsed.roles if parsed else [],
                        "health": {"resume_parsed": True, "profile_generated": True, "embedding_created": True, "ready_for_search": True},
                    })
                except Exception as e:
                    logger.warning(f"[app] Failed to persist re-parsed resume: {e}")
                return jsonify({
                    "success": True,
                    "filename": name,
                    "file_size": path.stat().st_size,
                    "uploaded_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "parse_status": "success",
                    "parsed_json": resume_dict,
                    "skills_json": parsed.skills if parsed else [],
                    "roles_json": parsed.roles if parsed else [],
                })
            except Exception as e:
                logger.error("Resume re-parse failed: %s", e, exc_info=True)
                return jsonify({"error": "Internal server error"}), 500

    return jsonify({"success": False, "error": "No resume uploaded"}), 404


def _get_parsed_resume():
    """Helper: return (parsed_dict, skills_list, roles_list) or (None, [], [])."""
    data = get_db().get_resume_data()
    if data and data.get("parse_status") == "success":
        parsed_json = data.get("parsed_json") or {}
        skills = data.get("skills_json") or parsed_json.get("skills", [])
        roles = data.get("roles_json") or parsed_json.get("roles", [])
        return parsed_json, skills, roles
    return None, [], []


@app.route("/api/resume/skills")
def api_resume_skills():
    parsed, skills, _ = _get_parsed_resume()
    if parsed is None:
        return jsonify({"success": False, "skills": []})
    # Support both list and categorized dict
    if isinstance(skills, list):
        return jsonify({"success": True, "skills": skills})
    if isinstance(skills, dict):
        all_skills = []
        for cat_skills in skills.values():
            all_skills.extend(cat_skills if isinstance(cat_skills, list) else [])
        return jsonify({"success": True, "skills": all_skills})
    return jsonify({"success": True, "skills": []})


@app.route("/api/resume/roles")
def api_resume_roles():
    parsed, _, roles = _get_parsed_resume()
    if parsed is None:
        return jsonify({"success": False, "roles": []})
    # Support scored_roles [{role, score}] or plain list
    scored = parsed.get("scored_roles") or roles
    if isinstance(scored, list) and len(scored) > 0 and isinstance(scored[0], dict) and "role" in scored[0]:
        return jsonify({"success": True, "roles": scored})
    if isinstance(roles, list):
        return jsonify({"success": True, "roles": roles})
    return jsonify({"success": True, "roles": []})


@app.route("/api/resume/experience")
def api_resume_experience():
    parsed, _, _ = _get_parsed_resume()
    if parsed is None:
        return jsonify({"success": False, "experience": []})
    exp = parsed.get("experience") or parsed.get("work_experience") or []
    if isinstance(exp, list):
        return jsonify({"success": True, "experience": exp})
    return jsonify({"success": True, "experience": []})


@app.route("/api/resume/education")
def api_resume_education():
    parsed, _, _ = _get_parsed_resume()
    if parsed is None:
        return jsonify({"success": False, "education": []})
    edu = parsed.get("education") or []
    if isinstance(edu, list):
        return jsonify({"success": True, "education": edu})
    return jsonify({"success": True, "education": []})


@app.route("/api/resume/health")
def api_resume_health():
    """Return resume health checks."""
    data = get_db().get_resume_data()
    if data and data.get("health_json"):
        return jsonify({"success": True, "health": data["health_json"]})

    # Compute from current state
    resume_path = os.getenv("MASTER_RESUME_PDF", str(ROOT / "resume/master_resume.pdf"))
    uploaded = os.path.exists(resume_path)
    return jsonify({
        "success": True,
        "health": {
            "resume_parsed": uploaded and bool(data),
            "profile_generated": bool(_inferred_roles),
            "embedding_created": uploaded and bool(data),
            "ready_for_search": uploaded and bool(_inferred_roles),
        }
    })


# ── Profile endpoints ─────────────────────────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
def api_profile_get():
    """Return profile.json + inferred roles."""
    profile_path = os.getenv("PROFILE_PATH", str(ROOT / "profile.json"))
    if not os.path.exists(profile_path):
        return jsonify({"error": "profile.json not found"}), 404
    with open(profile_path) as f:
        profile = json.load(f)
    profile["inferred_roles"] = _inferred_roles or profile.get("job_preferences", {}).get("target_roles", [])
    return jsonify({"success": True, "profile": profile})


@app.route("/api/profile", methods=["PUT"])
def api_profile_update():
    """Update profile preferences."""
    data = request.get_json() or {}
    profile_path = os.getenv("PROFILE_PATH", str(ROOT / "profile.json"))
    if not os.path.exists(profile_path):
        return jsonify({"error": "profile.json not found"}), 404

    with open(profile_path) as f:
        profile = json.load(f)

    # Merge updates
    if "target_roles" in data:
        profile.setdefault("job_preferences", {})["target_roles"] = data["target_roles"]
    if "target_locations" in data:
        profile.setdefault("job_preferences", {})["target_locations"] = data["target_locations"]
    if "remote_ok" in data:
        profile.setdefault("job_preferences", {})["remote_ok"] = data["remote_ok"]
    if "personal" in data:
        profile["personal"] = {**profile.get("personal", {}), **data["personal"]}

    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    return jsonify({"success": True, "profile": profile})


# ── Search strategy ───────────────────────────────────────────────────────────

@app.route("/api/search-strategy")
def api_search_strategy():
    """Return current search strategy derived from resume."""
    if _search_strategy:
        return jsonify({"success": True, "strategy": _search_strategy})

    # Fallback to profile.json
    profile_path = os.getenv("PROFILE_PATH", str(ROOT / "profile.json"))
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile = json.load(f)
        prefs = profile.get("job_preferences", {})
        skills = profile.get("skills", {})
        all_skills = (
            skills.get("languages", []) +
            skills.get("frameworks", []) +
            skills.get("tools", [])
        )
        roles = prefs.get("target_roles", ["Software Engineer"])
        return jsonify({
            "success": True,
            "strategy": {
                "roles": roles,
                "locations": prefs.get("target_locations", ["Remote"]),
                "keywords": all_skills[:10],
                "query": _build_search_query(roles, all_skills),
                "source": "profile.json (no resume parsed yet)",
            }
        })

    return jsonify({"success": False, "error": "No strategy available"}), 404


# ── Pipeline concurrency (manual + scheduler share same lock) ───────
PIPELINE_LOCK_KEY = 43  # same as scheduler RUN_LOCK_KEY — manual and scheduler share

def _try_acquire_pipeline_lock(run_id: str) -> bool:
    """Non-blocking try to acquire pipeline run lock. Returns True if acquired, False if busy."""
    import psycopg2
    from core.services.application_service import _resolve_database_url
    conn = psycopg2.connect(_resolve_database_url())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM run_log WHERE status = 'RUNNING' AND run_id != %s LIMIT 1", (run_id,))
            if cur.fetchone():
                return False
            cur.execute("SELECT pg_try_advisory_lock(%s)", (PIPELINE_LOCK_KEY,))
            row = cur.fetchone()
            if row and row[0]:
                return True
            return False
    except Exception:
        try:
            conn.rollback()
        except: pass
        return False
    finally:
        try:
            conn.close()
        except: pass

def _release_pipeline_lock():
    import psycopg2
    from core.services.application_service import _resolve_database_url
    conn = psycopg2.connect(_resolve_database_url())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (PIPELINE_LOCK_KEY,))
        conn.commit()
    except: 
        try: conn.rollback()
        except: pass
    finally:
        try: conn.close()
        except: pass

# ── Pipeline ──────────────────────────────────────────────────────────────────

@app.route("/api/run-now", methods=["POST"])
def api_run_now():
    run_id = str(uuid.uuid4())[:8]
    if not _try_acquire_pipeline_lock(run_id):
        return jsonify({"success": False, "error": "Discovery is already running."}), 409
    get_db().start_run_log(run_id, "scheduled")
    _run_pipeline_thread(run_id)
    return jsonify({"success": True, "run_id": run_id})


@app.route("/api/upload-jd", methods=["POST"])
def api_upload_jd():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename or not _allowed(file.filename, ALLOWED_JD):
        return jsonify({"error": "Invalid file type"}), 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    run_id = str(uuid.uuid4())[:8]
    if not _try_acquire_pipeline_lock(run_id):
        return jsonify({"success": False, "error": "Discovery is already running."}), 409
    get_db().start_run_log(run_id, "upload")
    _run_pipeline_thread(run_id, job_file=filepath)
    return jsonify({"success": True, "run_id": run_id, "filename": filename})


@app.route("/api/paste-jd", methods=["POST"])
def api_paste_jd():
    data    = request.get_json() or {}
    jd_text = data.get("jd_text", "").strip()
    if len(jd_text) < 30:
        return jsonify({"error": "JD text too short (min 30 chars)"}), 400

    run_id = str(uuid.uuid4())[:8]
    if not _try_acquire_pipeline_lock(run_id):
        return jsonify({"success": False, "error": "Discovery is already running."}), 409
    get_db().start_run_log(run_id, "paste")
    _run_pipeline_thread(run_id, job_text=jd_text)
    return jsonify({"success": True, "run_id": run_id})


@app.route("/api/pipeline/logs/<run_id>")
def api_pipeline_logs(run_id):
    """Return all pipeline events for a run."""
    events = get_db().get_pipeline_events(run_id)
    return jsonify({"success": True, "events": events, "total": len(events)})


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.route("/api/jobs")
def api_jobs():
    try:
        jobs = get_db().get_all_jobs(limit=100)
        # Enrich with freshness/quality additive fields (backward compatible)
        try:
            from core.services.job_canonical_service import freshness_state, determine_source_reliability
            for j in jobs:
                j["company"] = _sanitize_company(j.get("company"))
                # Additive fields — do not break existing consumers
                j.setdefault("canonical_id", j.get("canonical_id"))
                j.setdefault("last_seen_at", j.get("last_seen_at") or j.get("scraped_at"))
                # Freshness derived from scraped_at/last_seen_at
                try:
                    j["freshness_state"] = freshness_state(j.get("scraped_at"), j.get("last_seen_at"))
                except Exception:
                    j["freshness_state"] = "UNKNOWN"
                j["source_reliability"] = j.get("source_reliability") or determine_source_reliability(j.get("source"), j.get("url"))
                j["is_duplicate"] = bool(j.get("is_duplicate_of"))
                j["canonical_job_id"] = j.get("is_duplicate_of")
        except Exception:
            for j in jobs:
                j["company"] = _sanitize_company(j.get("company"))
        return jsonify({"success": True, "jobs": jobs, "total": len(jobs)})
    except Exception as e:
        logger.error("List jobs failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/jobs/<int:job_id>/company", methods=["POST"])
def api_update_job_company(job_id):
    """Set a corrected company name on a flagged job and clear needs_review (Bug 2)."""
    data = request.get_json(silent=True) or {}
    company = (data.get("company") or "").strip()
    if not company or company.lower() in ("company not found", "unknown", "unknown company"):
        return jsonify({"success": False, "error": "Please enter a valid company name"}), 400
    ok = get_db().update_job_company(job_id, company)
    if not ok:
        return jsonify({"success": False, "error": "Update failed"}), 500
    return jsonify({"success": True, "company": company})


@app.route("/api/jobs/<int:job_id>")
def api_job_detail(job_id):
    """Return full job details — triggers match analysis if not cached."""
    job = get_db().get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    job["company"] = _sanitize_company(job.get("company"))

    # Parse match details if stored
    match_details = None
    if job.get("match_details_json"):
        try:
            match_details = json.loads(job["match_details_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    # If no match details yet, compute on the fly
    if not match_details or "final_score" not in match_details:
        try:
            service = _build_match_service()
            required_skills_raw = job.get("required_skills", [])
            if isinstance(required_skills_raw, str):
                try:
                    required_skills = json.loads(required_skills_raw)
                except (json.JSONDecodeError, TypeError):
                    required_skills = [s.strip() for s in required_skills_raw.split(",") if s.strip()]
            elif isinstance(required_skills_raw, list):
                required_skills = required_skills_raw
            else:
                required_skills = []

            analysis = service.analyze(
                job_id=job_id,
                job_title=job.get("title", ""),
                job_location=job.get("location", ""),
                jd_text=job.get("jd_text", ""),
                required_skills=required_skills,
            )

            match_json = service.to_json(analysis)
            get_db().update_job_match(job_id, match_json, fit_score=int(analysis.final_score))
            match_details = json.loads(match_json)
        except Exception as e:
            logger.warning("Background match failed for job %s: %s", job_id, e)

    return jsonify({
        "success": True,
        "job": job,
        "match": match_details,
    })


# Serve job-specific assets (resume / cover letter) safely from server-side paths
@app.route("/api/jobs/<int:job_id>/asset/<kind>")
def api_job_asset(job_id: int, kind: str):
    """Return an asset for a job: kind in ('resume', 'cover').
    Looks up the job record for stored filesystem path and streams the file.
    """
    job = get_db().get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Common job fields that may contain asset paths
    candidates = [
        job.get("tailored_resume_path"),
        job.get("cover_letter_path"),
        job.get("cover_letter_asset"),
        job.get("resume_path"),
    ]

    chosen = None
    if kind == "resume":
        # prefer tailored resume, fall back to any resume_path
        chosen = job.get("tailored_resume_path") or job.get("resume_path")
    elif kind == "cover":
        chosen = job.get("cover_letter_path") or job.get("cover_letter_asset")
    else:
        return jsonify({"error": "Unsupported asset kind"}), 400

    if not chosen:
        return jsonify({"error": "No asset available for this job/kind"}), 404

    # Normalize and resolve to canonical path, then verify inside approved ROOT/resume or ROOT/uploads
    try:
        raw = Path(chosen)
        if not raw.is_absolute():
            # Resolve relative to project ROOT
            candidate = (ROOT / raw).resolve()
        else:
            candidate = raw.resolve()
        # Also handle legacy "./" prefix via ROOT join
        if chosen.startswith("./") or chosen.startswith("../"):
            candidate = (ROOT / Path(chosen)).resolve()
        # Approved roots
        approved_resume = (ROOT / "resume").resolve()
        approved_uploads = (ROOT / "uploads").resolve()
        # Must be inside approved_resume or approved_uploads
        try:
            is_inside = candidate.is_relative_to(approved_resume) or candidate.is_relative_to(approved_uploads)
        except AttributeError:
            # Python <3.9 fallback
            is_inside = str(candidate).startswith(str(approved_resume)) or str(candidate).startswith(str(approved_uploads))
        if not is_inside:
            return jsonify({"error": "Asset file not found"}), 404
        chosen_path = str(candidate)
    except Exception:
        return jsonify({"error": "Asset file not found"}), 404

    if not os.path.exists(chosen_path):
        return jsonify({"error": "Asset file not found"}), 404

    directory, filename = os.path.split(chosen_path)
    if not os.path.isdir(directory):
        return jsonify({"error": "Asset directory not found"}), 404

    # Serve the file; let browser decide inline vs download based on content-type
    try:
        return send_from_directory(directory, filename, as_attachment=False)
    except Exception as e:
        logger.error(f"[app] Failed to send asset {chosen_path}: {e}")
        return jsonify({"error": "Failed to serve asset"}), 500


@app.route("/api/jobs/<int:job_id>/match")
def api_job_match(job_id):
    """Return unified MatchAnalysis + additive MatchEngine2 MatchResult."""
    job = get_db().get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Try stored match details (from pipeline) for baseline
    baseline = None
    if job.get("match_details_json"):
        try:
            details = json.loads(job["match_details_json"])
            if "final_score" in details or "skill_match" in details:
                baseline = details
        except (json.JSONDecodeError, TypeError):
            pass

    # Compute baseline on the fly if needed
    if baseline is None:
        try:
            service = _build_match_service()
            required_skills_raw = job.get("required_skills", [])
            if isinstance(required_skills_raw, str):
                try:
                    required_skills = json.loads(required_skills_raw)
                except (json.JSONDecodeError, TypeError):
                    required_skills = [s.strip() for s in required_skills_raw.split(",") if s.strip()]
            elif isinstance(required_skills_raw, list):
                required_skills = required_skills_raw
            else:
                required_skills = []

            analysis = service.analyze(
                job_id=job_id,
                job_title=job.get("title", ""),
                job_location=job.get("location", ""),
                jd_text=job.get("jd_text", ""),
                required_skills=required_skills,
            )
            match_json = service.to_json(analysis)
            try:
                get_db().update_job_match(job_id, match_json, fit_score=int(analysis.final_score))
            except Exception:
                pass
            baseline = json.loads(match_json)
        except Exception as e:
            logger.warning("Baseline match failed for job %s: %s", job_id, e)
            baseline = {
                "final_score": job.get("fit_score", 0) or 0,
                "recommendation": "Apply" if (job.get("fit_score", 0) or 0) >= 70 else ("Consider" if (job.get("fit_score", 0) or 0) >= 50 else "Skip"),
                "explanation": "Match analysis temporarily unavailable",
            }

    # Additive MatchEngine2 result (deterministic, no scoring mutation)
    match_result = None
    try:
        from core.services.match_engine_adapters import CandidateAdapter, JobAdapter
        from core.services.match_engine2 import MatchEngine2
        from core.services.job_intelligence_service import get_job_intelligence_service

        cand_input = CandidateAdapter().adapt_safe()
        # Build job intelligence with provenance
        try:
            j_service = get_job_intelligence_service()
            job_profile = j_service.build_job_intelligence(job)
        except Exception:
            job_profile = None
        if job_profile is not None:
            job_input = JobAdapter().adapt(job_profile)
        else:
            # Fallback to legacy raw
            job_input = JobAdapter().adapt_from_legacy(
                job_id=job_id,
                job_title=job.get("title", ""),
                job_location=job.get("location", ""),
                jd_text=job.get("jd_text", ""),
                required_skills=baseline.get("all_required_skills") if isinstance(baseline, dict) else [],
            )
        engine = MatchEngine2()
        # Need baseline MatchAnalysis object for MatchResult baseline_analysis
        try:
            from core.models import MatchAnalysis as _MA
            baseline_obj = _MA.model_validate(baseline) if isinstance(baseline, dict) and "final_score" in baseline else None
        except Exception:
            baseline_obj = None
        mr = engine.analyze(cand_input, job_input, baseline_analysis=baseline_obj)
        # Minimal evidence — do not expose full resume/JD
        match_result = {
            "inventory_status": mr.inventory_status.value if hasattr(mr.inventory_status, "value") else str(mr.inventory_status),
            "analysis_completeness": mr.analysis_completeness,
            "data_completeness": mr.data_completeness,
            "match_confidence": mr.match_confidence,
            "engine_version": mr.engine_version,
            "requirement_evaluations": [e.model_dump() for e in mr.requirement_evaluations],
            "experience_evaluations": [e.model_dump() for e in mr.experience_evaluations],
            "role_evaluations": [e.model_dump() for e in mr.role_evaluations],
            "location_evaluations": [e.model_dump() for e in mr.location_evaluations],
            "seniority_evaluations": [e.model_dump() for e in mr.seniority_evaluations],
        }
        # Analysis completeness deterministic: fraction of DETERMINED dimensions
        try:
            from core.models.match_engine import ExperienceAvailability, RoleAvailability, LocationAvailability, SeniorityAvailability

            dims = [
                cand_input.skill_inventory_status.value == "determined",
                cand_input.experience_availability.value == "determined",
                cand_input.role_availability.value == "determined",
                cand_input.location_availability.value == "determined",
                cand_input.seniority_availability.value == "determined",
            ]
            match_result["analysis_completeness"] = round(sum(1 for d in dims if d) / len(dims), 2)
        except Exception:
            pass
    except Exception as e:
        logger.warning("MatchEngine2 evaluation failed for job %s: %s", job_id, e)

    resp = {"success": True, "match": baseline, "baseline_analysis": baseline}
    if match_result is not None:
        resp["match_result"] = match_result
    return jsonify(resp)


@app.route("/api/jobs/prioritized")
def api_jobs_prioritized():
    """Return jobs sorted by Application Priority (HOT→WARM→COLD→REVIEW)."""
    try:
        from core.services.application_priority_service import get_priority_service
        from core.services.match_engine_adapters import CandidateAdapter, JobAdapter
        from core.services.match_engine2 import MatchEngine2
        from core.services.job_intelligence_service import get_job_intelligence_service
        from core.models import MatchAnalysis as _MA

        jobs = get_db().get_all_jobs(limit=100)
        # Phase 9: do not surface duplicates as independent recommendations
        try:
            jobs = [j for j in jobs if not j.get("is_duplicate_of")]
        except Exception:
            pass
        # Preload recruiters for tie-breaker
        try:
            recruiters = get_db().get_all_recruiters()
            recruiter_job_ids = {r.get("job_id") for r in recruiters if r.get("job_id") and r.get("email")}
        except Exception:
            recruiter_job_ids = set()

        cand_input = CandidateAdapter().adapt_safe()
        j_service = get_job_intelligence_service()
        engine = MatchEngine2()
        pri_service = get_priority_service()

        # Try baseline once for candidate
        items = []
        for job in jobs:
            job_id = job.get("id")
            # Baseline
            baseline = None
            if job.get("match_details_json"):
                try:
                    d = json.loads(job["match_details_json"])
                    if "final_score" in d:
                        baseline = d
                except Exception:
                    pass
            if baseline is None:
                try:
                    svc = _build_match_service()
                    rs = job.get("required_skills", [])
                    if isinstance(rs, str):
                        try:
                            rs = json.loads(rs)
                        except Exception:
                            rs = [s.strip() for s in rs.split(",") if s.strip()]
                    elif not isinstance(rs, list):
                        rs = []
                    analysis = svc.analyze(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""), jd_text=job.get("jd_text",""), required_skills=rs)
                    baseline = json.loads(svc.to_json(analysis))
                except Exception:
                    baseline = {"final_score": job.get("fit_score",0) or 0}

            # MatchResult
            try:
                job_profile = j_service.build_job_intelligence(job)
                job_input = JobAdapter().adapt(job_profile)
            except Exception:
                job_input = JobAdapter().adapt_from_legacy(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""))

            try:
                baseline_obj = _MA.model_validate(baseline) if isinstance(baseline, dict) and "final_score" in baseline else None
            except Exception:
                baseline_obj = None
            try:
                mr = engine.analyze(cand_input, job_input, baseline_analysis=baseline_obj)
            except Exception:
                continue

            has_desc = bool(job.get("jd_text") and job.get("jd_text","").strip())
            # Phase 6 contract: freshness age from original discovery (scraped_at), NOT last_seen_at
            disc = job.get("scraped_at") or job.get("discovered_date") or job.get("discovered_at")
            pri = pri_service.evaluate(
                job_id=job_id,
                match_result=mr,
                discovered_date=disc,
                has_description=has_desc,
                source=job.get("source"),
                application_url=job.get("url") or job.get("application_url"),
                recruiter_email_exists=(job_id in recruiter_job_ids),
            )
            items.append((job_id, pri, job, baseline, mr))

        # Sort via service rank (tier order + recruiter + timestamp). For tie-break timestamp we may use last_seen_at for "recently observed" ordering, but tier (freshness) already decided via scraped_at.
        # Reuse service rank for ordering
        # Build tuples for rank
        rank_input = []
        for job_id, pri, job, baseline, mr in items:
            disc = job.get("scraped_at") or job.get("discovered_date") or job.get("scraped_at")
            rank_input.append((job_id, mr, disc, bool(job.get("jd_text")), job.get("source"), job.get("url"), job_id in recruiter_job_ids))
        ranked = pri_service.rank(rank_input)
        # Map ranked order to jobs
        order = {job_id: idx for idx, (job_id, _) in enumerate(ranked)}
        items_sorted = sorted(items, key=lambda x: order.get(x[0], 999))

        out = []
        for job_id, pri, job, baseline, mr in items_sorted:
            # Enrich job with Phase 9 additive fields
            try:
                from core.services.job_canonical_service import freshness_state, determine_source_reliability
                job["freshness_state"] = freshness_state(job.get("scraped_at"), job.get("last_seen_at"))
                job["source_reliability"] = job.get("source_reliability") or determine_source_reliability(job.get("source"), job.get("url"))
                job["is_duplicate"] = bool(job.get("is_duplicate_of"))
                job["canonical_job_id"] = job.get("is_duplicate_of")
                job["canonical_id"] = job.get("canonical_id")
                job["last_seen_at"] = job.get("last_seen_at") or job.get("scraped_at")
            except Exception:
                pass
            out.append({
                "job": job,
                "baseline_analysis": baseline,
                "match_result": {
                    "requirement_evaluations": [e.model_dump() for e in mr.requirement_evaluations],
                    "experience_evaluations": [e.model_dump() for e in mr.experience_evaluations],
                    "role_evaluations": [e.model_dump() for e in mr.role_evaluations],
                    "location_evaluations": [e.model_dump() for e in mr.location_evaluations],
                    "seniority_evaluations": [e.model_dump() for e in mr.seniority_evaluations],
                    "analysis_completeness": mr.analysis_completeness,
                },
                "priority": pri.model_dump(),
            })
        return jsonify({"success": True, "jobs": out, "total": len(out)})
    except Exception as e:
        logger.error("Prioritized failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/jobs/<int:job_id>/priority")
def api_job_priority(job_id):
    """Return ApplicationPriority for a single job."""
    job = get_db().get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    try:
        from core.services.application_priority_service import get_priority_service
        from core.services.match_engine_adapters import CandidateAdapter, JobAdapter
        from core.services.match_engine2 import MatchEngine2
        from core.services.job_intelligence_service import get_job_intelligence_service
        from core.models import MatchAnalysis as _MA

        cand_input = CandidateAdapter().adapt_safe()
        j_service = get_job_intelligence_service()
        try:
            job_profile = j_service.build_job_intelligence(job)
            job_input = JobAdapter().adapt(job_profile)
        except Exception:
            job_input = JobAdapter().adapt_from_legacy(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""))

        # Baseline
        baseline = None
        if job.get("match_details_json"):
            try:
                d = json.loads(job["match_details_json"])
                if "final_score" in d:
                    baseline = d
            except Exception:
                pass
        if baseline is None:
            svc = _build_match_service()
            rs = job.get("required_skills", [])
            if isinstance(rs, str):
                try:
                    rs = json.loads(rs)
                except Exception:
                    rs = []
            analysis = svc.analyze(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""), jd_text=job.get("jd_text",""), required_skills=rs if isinstance(rs, list) else [])
            baseline = json.loads(svc.to_json(analysis))

        try:
            baseline_obj = _MA.model_validate(baseline) if isinstance(baseline, dict) and "final_score" in baseline else None
        except Exception:
            baseline_obj = None
        mr = MatchEngine2().analyze(cand_input, job_input, baseline_analysis=baseline_obj)
        disc = job.get("discovered_date") or job.get("scraped_at")
        has_desc = bool(job.get("jd_text") and job.get("jd_text","").strip())
        try:
            recruiters = get_db().get_all_recruiters()
            rec_exists = any(r.get("job_id")==job_id and r.get("email") for r in recruiters)
        except Exception:
            rec_exists = False
        pri = get_priority_service().evaluate(job_id, mr, disc, has_desc, job.get("source"), job.get("url"), rec_exists)
        return jsonify({"success": True, "priority": pri.model_dump(), "match_result": {
            "requirement_evaluations": [e.model_dump() for e in mr.requirement_evaluations],
            "experience_evaluations": [e.model_dump() for e in mr.experience_evaluations],
            "role_evaluations": [e.model_dump() for e in mr.role_evaluations],
            "location_evaluations": [e.model_dump() for e in mr.location_evaluations],
            "seniority_evaluations": [e.model_dump() for e in mr.seniority_evaluations],
        }})
    except Exception as e:
        logger.error("Priority failed for %s: %s", job_id, e, exc_info=True)
        return jsonify({"error": str(e)}), 500


# ── Applications (Phase 7 P0) ────────────────────────────────────────────────

@app.route("/api/applications", methods=["GET"])
def api_applications():
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        apps = svc.list_applications(limit=50)
        return jsonify({"success": True, "applications": apps})
    except Exception as e:
        logger.error("List applications failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications", methods=["POST"])
def api_applications_create():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400
    try:
        int(job_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id must be a valid integer"}), 400
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        app_row = svc.create_application(job_id=int(job_id), application_method=data.get("application_method", "MANUAL"))
        return jsonify({"success": True, "application": app_row}), 201
    except ValueError as e:
        msg = str(e)
        code = 409 if "already exists" in msg else 400
        return jsonify({"error": msg}), code
    except Exception as e:
        logger.error("Create application failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>", methods=["GET"])
def api_application_get(app_id):
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        app_row = svc.get_application(app_id)
        if not app_row:
            return jsonify({"error": "Application not found"}), 404
        timeline = svc.get_timeline(app_id)
        return jsonify({"success": True, "application": app_row, "timeline": timeline})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Get application failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>", methods=["PATCH"])
def api_application_patch(app_id):
    data = request.get_json(silent=True) or {}
    state = data.get("state")
    if not state:
        return jsonify({"error": "state required"}), 400
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        app_row = svc.patch_state(app_id, state)
        return jsonify({"success": True, "application": app_row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Patch failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/apply", methods=["POST"])
def api_application_apply(app_id):
    data = request.get_json(silent=True) or {}
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        # Capture snapshots if available (match/priority) — optional
        app_row = svc.apply_application(app_id, application_method=data.get("application_method", "MANUAL"))
        return jsonify({"success": True, "application": app_row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Apply failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/outcome", methods=["POST"])
def api_application_outcome(app_id):
    data = request.get_json(silent=True) or {}
    outcome = data.get("outcome")
    if not outcome:
        return jsonify({"error": "outcome required"}), 400
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        app_row = svc.set_outcome(app_id, outcome, reason=data.get("reason"))
        return jsonify({"success": True, "application": app_row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Outcome failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/events", methods=["POST"])
def api_application_events(app_id):
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type") or data.get("type")
    if not event_type:
        return jsonify({"error": "event_type required"}), 400
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        ev = svc.add_event(app_id, event_type, actor=data.get("actor", "user"), payload=json.dumps(data.get("payload", {})) if data.get("payload") else None)
        return jsonify({"success": True, "event": ev}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Add event failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/timeline", methods=["GET"])
def api_application_timeline(app_id):
    try:
        from core.services.application_service import get_application_service
        svc = get_application_service()
        timeline = svc.get_timeline(app_id)
        return jsonify({"success": True, "timeline": timeline})
    except Exception as e:
        logger.error("Get timeline failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/studio/<int:job_id>", methods=["POST", "GET"])
def api_application_studio(job_id):
    """Application Studio — per-job preparation workspace (Phase 10). POST generates, GET returns latest."""
    if request.method == "GET":
        # Return latest studio run for this job if exists
        try:
            from core.services.studio_service import _safe_conn
            conn = _safe_conn()
            try:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM studio_runs WHERE job_id=%s ORDER BY created_at DESC LIMIT 1", (job_id,))
                    row = cur.fetchone()
                    if row:
                        return jsonify({"success": True, "studio": dict(row)})
                    return jsonify({"success": False, "error": "No studio run found"}), 404
            finally:
                conn.close()
        except Exception as e:
            logger.error("Studio GET failed: %s", e, exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    # POST — orchestrate
    try:
        from core.services.studio_service import get_studio_service
        svc = get_studio_service()
        ctx = svc.build(job_id)
        # Persist (bounded snapshots)
        try:
            sid = svc.persist(ctx)
            ctx["studio_run_id"] = sid
        except Exception as e:
            logger.warning("Studio persist failed (non-fatal): %s", e)
        return jsonify({"success": True, "studio": ctx})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Studio failed for %s: %s", job_id, e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# ── Interviews & Follow-ups (Phase 11) ────────────────────────────────────────

@app.route("/api/applications/<int:app_id>/interviews", methods=["GET", "POST"])
def api_application_interviews(app_id):
    if request.method == "GET":
        try:
            from core.services.interview_store_service import get_interview_store_service
            svc = get_interview_store_service()
            items = svc.list_for_application(app_id)
            return jsonify({"success": True, "interviews": items})
        except Exception as e:
            logger.error("List interviews failed: %s", e, exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    # POST
    data = request.get_json(silent=True) or {}
    stage = (data.get("stage") or "OTHER").strip().upper()
    scheduled_at = data.get("scheduled_at")
    notes = data.get("notes")
    if notes and len(notes) > 2000:
        return jsonify({"error": "Notes too long"}), 400
    try:
        from core.services.interview_store_service import get_interview_store_service
        svc = get_interview_store_service()
        row = svc.create(app_id, stage=stage, scheduled_at=scheduled_at, notes=notes)
        return jsonify({"success": True, "interview": row}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Create interview failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/interviews/<int:interview_id>/complete", methods=["POST"])
def api_interview_complete(interview_id):
    data = request.get_json(silent=True) or {}
    notes = data.get("notes")
    try:
        from core.services.interview_store_service import get_interview_store_service
        svc = get_interview_store_service()
        row = svc.complete(interview_id, notes=notes)
        return jsonify({"success": True, "interview": row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Complete interview failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/interviews/<int:interview_id>/cancel", methods=["POST"])
def api_interview_cancel(interview_id):
    try:
        from core.services.interview_store_service import get_interview_store_service
        svc = get_interview_store_service()
        row = svc.cancel(interview_id)
        return jsonify({"success": True, "interview": row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Cancel interview failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/interview-prep", methods=["GET", "POST"])
def api_application_interview_prep(app_id):
    try:
        from core.services.interview_prep_service import get_interview_prep_service
        svc = get_interview_prep_service()
        kit = svc.generate_for_application(app_id)
        return jsonify({"success": True, "prep": kit})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Interview prep failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/applications/<int:app_id>/follow-ups", methods=["GET", "POST"])
def api_application_followups(app_id):
    if request.method == "GET":
        try:
            from core.services.follow_up_service import get_follow_up_service
            svc = get_follow_up_service()
            items = svc.list_for_application(app_id)
            return jsonify({"success": True, "follow_ups": items})
        except Exception as e:
            logger.error("List follow-ups failed: %s", e, exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    data = request.get_json(silent=True) or {}
    ftype = (data.get("follow_up_type") or data.get("type") or "POST_APPLICATION").strip().upper()
    channel = (data.get("channel") or "EMAIL").strip().upper()
    scheduled_at = data.get("scheduled_at")
    subject = data.get("subject")
    preview = data.get("message_preview") or data.get("preview")
    try:
        from core.services.follow_up_service import get_follow_up_service
        svc = get_follow_up_service()
        row = svc.create(app_id, follow_up_type=ftype, channel=channel, scheduled_at=scheduled_at, subject=subject, message_preview=preview)
        return jsonify({"success": True, "follow_up": row}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Create follow-up failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/follow-ups/<int:follow_up_id>/review", methods=["POST"])
def api_followup_review(follow_up_id):
    try:
        from core.services.follow_up_service import get_follow_up_service
        svc = get_follow_up_service()
        row = svc.review(follow_up_id)
        return jsonify({"success": True, "follow_up": row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Review follow-up failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/follow-ups/<int:follow_up_id>/approve", methods=["POST"])
def api_followup_approve(follow_up_id):
    try:
        from core.services.follow_up_service import get_follow_up_service
        svc = get_follow_up_service()
        row = svc.approve(follow_up_id)
        return jsonify({"success": True, "follow_up": row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Approve follow-up failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/follow-ups/<int:follow_up_id>/send", methods=["POST"])
def api_followup_send(follow_up_id):
    # Only allowed after APPROVED — never auto-send
    try:
        from core.services.follow_up_service import get_follow_up_service
        svc = get_follow_up_service()
        row = svc.mark_sent(follow_up_id)
        return jsonify({"success": True, "follow_up": row})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Send follow-up failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# ── Emails ────────────────────────────────────────────────────────────────────

@app.route("/api/emails")
def api_emails():
    try:
        emails = get_db().get_unsent_emails()
        for e in emails:
            e["company"] = _sanitize_company(e.get("company"))
        return jsonify({"success": True, "emails": emails, "total": len(emails)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails/send", methods=["POST"])
def api_emails_send():
    """Bug 3 — manually send approved draft emails via EmailSender.

    Works regardless of DRY_RUN (DRY_RUN only governs auto-send at the end of a
    pipeline run, not explicit user sends from the review page). Each approved
    item may carry an edited subject/body; on success the job is marked 'sent'.
    """
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"success": False, "error": "No emails approved to send"}), 400

    try:
        from email_module.sender import EmailSender
        sender = EmailSender()
    except Exception as e:
        return jsonify({"success": False, "error": f"Email sender unavailable: {e}"}), 500

    if not sender.configured:
        return jsonify({"success": False,
                        "error": "Email not configured — connect Gmail in Settings first."}), 400

    db = get_db()
    sent = 0
    failed = []
    for it in items:
        jid = it.get("id")
        job = db.get_job_by_id(jid) if jid is not None else None
        if not job:
            failed.append({"id": jid, "reason": "Job not found"})
            continue
        recipient = (job.get("hr_email") or "").strip()
        if not recipient:
            failed.append({"id": jid, "company": _sanitize_company(job.get("company")),
                           "reason": "No recruiter email — find a contact first"})
            continue
        subject = (it.get("subject") or job.get("email_subject") or "").strip()
        body = (it.get("body") or job.get("email_body") or "").strip()
        if not body:
            failed.append({"id": jid, "company": _sanitize_company(job.get("company")),
                           "reason": "Empty email body"})
            continue
        attachments = [p for p in (job.get("tailored_resume_path"), job.get("cover_letter_path"))
                       if p and os.path.exists(p)]
        try:
            ok = sender.send(to=recipient, subject=subject, body=body, attachments=attachments)
        except Exception as e:
            ok = False
            logger.error(f"[app] send failed for job {jid}: {e}")
        if ok:
            db.mark_job_applied(jid, subject=subject, body=body)
            sent += 1
        else:
            failed.append({"id": jid, "company": _sanitize_company(job.get("company")),
                           "reason": "Send failed (check provider/logs)"})

    return jsonify({"success": True, "sent": sent, "failed": failed, "total": len(items)})


# ── History ───────────────────────────────────────────────────────────────────

@app.route("/api/logs")
def api_logs():
    try:
        runs = get_db().get_recent_run_logs(limit=20)
        return jsonify({"success": True, "runs": runs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Recruiters ────────────────────────────────────────────────────────────────

@app.route("/api/recruiters")
def api_recruiters():
    """Return discovered recruiters with confidence and API status."""
    try:
        recruiters = get_db().get_all_recruiters()
        api_status = {
            "clearbit": bool(os.getenv("CLEARBIT_API_KEY")),
            "hunter": bool(os.getenv("HUNTER_API_KEY")),
        }
        warnings = []
        if not api_status["clearbit"]:
            warnings.append("Clearbit API Missing — Limited company discovery")
        if not api_status["hunter"]:
            warnings.append("Hunter API Missing — Limited email discovery")
        if not api_status["clearbit"] and not api_status["hunter"]:
            warnings.append("Running in Limited Discovery Mode")

        return jsonify({
            "success": True,
            "recruiters": recruiters,
            "total": len(recruiters),
            "api_status": api_status,
            "warnings": warnings,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route("/api/analytics")
def api_analytics():
    conn = None
    try:
        db       = get_db()
        conn     = db._conn()
        all_jobs = db.get_all_jobs(limit=100, conn=conn)
        runs     = db.get_recent_run_logs(limit=50, conn=conn)
        startups = db.get_startup_companies(limit=100, conn=conn)
        tracker  = db.get_application_tracker(limit=100, conn=conn)

        # FIX 1: headline stats come from LIVE COUNT queries against the tables
        # (not the 100-row cached slice, not a run-scoped value) so the Home
        # dashboard always reflects what's actually in the DB. Every value is a
        # plain int (never None) — see FIX 2.
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM jobs")
            total = cur.fetchone()[0] or 0
            cur.execute("SELECT count(*) FROM jobs WHERE COALESCE(fit_score, 0) >= 70")
            strong_matches = cur.fetchone()[0] or 0
            cur.execute("SELECT count(*) FROM jobs WHERE status IN ('sent','draft','ready')")
            drafted = cur.fetchone()[0] or 0
            cur.execute("SELECT count(*) FROM jobs WHERE status = 'sent'")
            submitted = cur.fetchone()[0] or 0
            cur.execute("SELECT count(*) FROM recruiters")
            recruiters_found = cur.fetchone()[0] or 0
            cur.execute("SELECT COALESCE(AVG(COALESCE(fit_score, 0)), 0) FROM jobs")
            avg = float(cur.fetchone()[0] or 0)

        emails_drafted = drafted
        emails_sent = submitted

        sources = {}
        for j in all_jobs:
            # FIX 1: never a None key — a None source made jsonify(sort_keys) raise
            # "'<' not supported between NoneType and str" and 500'd the whole endpoint.
            src = j.get("source") or "unknown"
            sources[src] = sources.get(src, 0) + 1

        tracker_sources = {}
        status_counts = {}
        followups_due = 0
        interview_count = 0
        offer_count = 0
        response_count = 0
        for item in tracker:
            source = item.get("source") or "unknown"   # FIX 1: never a None key
            tracker_sources[source] = tracker_sources.get(source, 0) + 1
            status = (item.get("application_status") or "saved").lower()
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "follow_up_due":
                followups_due += 1
            if status == "interview":
                interview_count += 1
            if status == "offer":
                offer_count += 1
            if status in ("interview", "offer", "rejected"):
                response_count += 1

        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        referral_contacts = len(db.get_company_contacts(limit=100, conn=conn))

        return jsonify({"success": True, "analytics": {
            "total_jobs": total,
            "strong_matches": strong_matches,
            "recruiters_found": recruiters_found,
            "applications_drafted": drafted,
            "applications_submitted": submitted,
            # FIX 2: explicit integer stat-card counts (never null)
            "responses": int(response_count or 0),
            "interviews": int(interview_count or 0),
            "offers": int(offer_count or 0),
            "emails_drafted": emails_drafted,
            "emails_sent": emails_sent,
            "avg_score": round(avg, 1),
            "total_runs": len(runs),
            "source_distribution": sources,
            "startup_matches": len(startups),
            "referral_opportunities": referral_contacts,
            "official_careers_applications": sum(1 for j in all_jobs if (j.get("source") or "").lower() in ("company_careers", "greenhouse", "lever", "ashby", "workday")),
            "followups_due": followups_due,
            "interviews_scheduled": interview_count,
            "offers_received": offer_count,
            "applications_by_source": tracker_sources,
            "application_status_breakdown": status_counts,
            "referral_success_rate": round((interview_count / max(referral_contacts, 1)) * 100, 1),
            "interview_conversion_rate": round((interview_count / max(len(tracker), 1)) * 100, 1),
            "company_response_rate": round((response_count / max(len(tracker), 1)) * 100, 1),
            "average_time_to_first_response_days": 0,
            "dry_run": dry_run,
        }})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn is not None:
            try:
                db._put_conn(conn)
            except Exception:
                pass


# ── Outcome Analytics (Phase 12) ────────────────────────────────────────────

@app.route("/api/analytics/overview", methods=["GET"])
def api_analytics_overview():
    try:
        from core.services.outcome_analytics_service import get_outcome_analytics_service
        svc = get_outcome_analytics_service()
        return jsonify({"success": True, "funnel": svc.funnel(), "time": svc.time_metrics()})
    except Exception as e:
        logger.error("Analytics overview failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/analytics/funnel", methods=["GET"])
def api_analytics_funnel():
    try:
        from core.services.outcome_analytics_service import get_outcome_analytics_service
        return jsonify({"success": True, "funnel": get_outcome_analytics_service().funnel()})
    except Exception as e:
        logger.error("Funnel failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/analytics/sources", methods=["GET"])
def api_analytics_sources():
    try:
        from core.services.outcome_analytics_service import get_outcome_analytics_service
        return jsonify({"success": True, "sources": get_outcome_analytics_service().source_performance()})
    except Exception as e:
        logger.error("Sources failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/analytics/priority", methods=["GET"])
def api_analytics_priority():
    try:
        from core.services.outcome_analytics_service import get_outcome_analytics_service
        return jsonify({"success": True, "priority": get_outcome_analytics_service().priority_insights()})
    except Exception as e:
        logger.error("Priority analytics failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/analytics/insights", methods=["GET"])
def api_analytics_insights():
    try:
        from core.services.outcome_analytics_service import get_outcome_analytics_service
        return jsonify({"success": True, "insights": get_outcome_analytics_service().insights()})
    except Exception as e:
        logger.error("Insights failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/feedback", methods=["GET", "POST"])
def api_feedback():
    if request.method == "GET":
        try:
            from core.services.feedback_service import get_feedback_service
            app_id = request.args.get("application_id", type=int)
            items = get_feedback_service().list(application_id=app_id)
            return jsonify({"success": True, "feedback": items})
        except Exception as e:
            logger.error("List feedback failed: %s", e, exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    data = request.get_json(silent=True) or {}
    try:
        from core.services.feedback_service import get_feedback_service
        row = get_feedback_service().create(application_id=data.get("application_id"), job_id=data.get("job_id"), signal_type=data.get("signal_type"), value=data.get("value"))
        return jsonify({"success": True, "feedback": row}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Create feedback failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# ── Scheduler / Automation (Phase 13) ───────────────────────────────────────

@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    try:
        from core.services.scheduler_service import get_scheduler_service
        return jsonify({"success": True, **get_scheduler_service().get_status()})
    except Exception as e:
        logger.error("Scheduler status failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/scheduler/runs", methods=["GET"])
def api_scheduler_runs():
    try:
        from core.services.scheduler_service import get_scheduler_service
        limit = min(int(request.args.get("limit", 20)), 50)
        runs = get_scheduler_service().get_run_history(limit=limit)
        return jsonify({"success": True, "runs": runs, "total": len(runs)})
    except Exception as e:
        logger.error("Scheduler runs failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/scheduler/trigger", methods=["POST"])
def api_scheduler_trigger():
    try:
        from core.services.scheduler_service import get_scheduler_service
        run_id = get_scheduler_service().trigger_run(triggered_by="manual")
        if not run_id:
            return jsonify({"success": False, "error": "Another run is already active"}), 409
        return jsonify({"success": True, "run_id": run_id, "message": "Pipeline run started"})
    except Exception as e:
        logger.error("Scheduler trigger failed: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# ── Startup Discovery ────────────────────────────────────────────────────────

@app.route("/api/startups", methods=["GET"])
def api_startups_list():
    try:
        limit = int(request.args.get("limit", 20))
        startups = get_db().get_startup_companies(limit=limit)
        return jsonify({"success": True, "startups": startups, "total": len(startups)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/startups/discover", methods=["POST"])
def api_startups_discover():
    try:
        limit = int((request.get_json(silent=True) or {}).get("limit", 20))
        startups = _startup_service.discover(limit=limit)
        for startup in startups:
            get_db().save_pipeline_event(startup.get("discovered_at", datetime.now().isoformat())[:19].replace("T", "-"), {
                "timestamp": startup.get("discovered_at", datetime.now().isoformat()),
                "agent": "startup_discovery",
                "step": "startup_discovered",
                "status": "done",
                "message": f"Startup discovered: {startup.get('company')}",
                "output": startup,
            })
        return jsonify({"success": True, "startups": startups, "total": len(startups)})
    except Exception as e:
        logger.error("[app] Startup discovery failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/startups/<company>/contacts", methods=["GET"])
def api_startup_contacts(company: str):
    try:
        limit = int(request.args.get("limit", 6))
        contacts = _startup_service.discover_contacts(company, limit=limit)
        for contact in contacts:
            get_db().save_pipeline_event(datetime.now().isoformat(), {
                "timestamp": datetime.now().isoformat(),
                "agent": "apollo",
                "step": "recruiter_found",
                "status": "done",
                "message": f"Recruiter found: {contact.get('name')} at {company}",
                "output": contact,
            })
        return jsonify({"success": True, "company": company, "contacts": contacts, "total": len(contacts)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/startups/<company>/message", methods=["POST"])
def api_startup_message(company: str):
    try:
        data = request.get_json(silent=True) or {}
        contact_name = data.get("contact_name") or company
        message = _startup_service.generate_linkedin_message(company, contact_name, data.get("project_hint"))
        get_db().save_pipeline_event(datetime.now().isoformat(), {
            "timestamp": datetime.now().isoformat(),
            "agent": "outreach",
            "step": "linkedin_message_generated",
            "status": "done",
            "message": f"LinkedIn message generated for {contact_name} at {company}",
            "output": {"company": company, "contact_name": contact_name, "message": message},
        })
        return jsonify({"success": True, "company": company, "contact_name": contact_name, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tracker", methods=["GET", "POST"])
def api_application_tracker():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            tracker = _startup_service.create_application_tracker_entry(data)
            get_db().save_pipeline_event(datetime.now().isoformat(), {
                "timestamp": datetime.now().isoformat(),
                "agent": "application_tracker",
                "step": "application_tracked",
                "status": "done",
                "message": f"Application tracked for {tracker.get('company')} - {tracker.get('role')}",
                "output": tracker,
            })
            return jsonify({"success": True, "application": tracker})

        items = _startup_service.get_tracker()
        return jsonify({"success": True, "applications": items, "total": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tracker/followups", methods=["GET"])
def api_tracker_followups():
    try:
        items = _startup_service.get_followups_due()
        return jsonify({"success": True, "applications": items, "total": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/candidate/intelligence", methods=["GET"])
def api_candidate_intelligence():
    """Return canonical Candidate Intelligence profile."""
    try:
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        svc = get_candidate_intelligence_service()
        canonical_profile = svc.build_candidate_intelligence()
        return jsonify({"success": True, "intelligence": canonical_profile.dict()})
    except Exception as e:
        logger.error(f"[app] Candidate Intelligence error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500



# ── Career Copilot & Interview Prep ───────────────────────────────────────────


@app.route("/api/copilot/chat", methods=["POST"])
def api_copilot_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()
        history = data.get("history", [])
        job_id = data.get("job_id")

        # Load profile context
        profile_path = os.getenv("PROFILE_PATH", str(ROOT / "profile.json"))
        profile = {}
        if os.path.exists(profile_path):
            with open(profile_path) as f:
                profile = json.load(f)

        # Enhance with resume data
        resume_data = get_db().get_resume_data()
        if resume_data and resume_data.get("parsed_json"):
            pj = resume_data["parsed_json"]
            profile["inferred_roles"] = resume_data.get("roles_json") or pj.get("roles", [])
            profile["skills"] = resume_data.get("skills_json") or pj.get("skills", [])

        # Load job context if job_id provided
        job_context = None
        if job_id:
            job_context = get_db().get_job_by_id(job_id)

        from core.services.copilot_service import get_copilot_service
        service = get_copilot_service()
        result = service.ask_copilot(
            user_message=user_message,
            history=history,
            candidate_profile=profile,
            job_context=job_context,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error(f"[app] Copilot error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/interview/prep", methods=["POST"])
def api_interview_prep():
    try:
        data = request.get_json(silent=True) or {}
        job_id = data.get("job_id")
        title = data.get("title", "")
        company = data.get("company", "")
        jd_text = data.get("jd_text", "")

        if job_id:
            job = get_db().get_job_by_id(job_id)
            if job:
                title = title or job.get("title", "")
                company = company or job.get("company", "")
                jd_text = jd_text or job.get("jd_text", "")

        if not title:
            title = "Software Engineer"
        if not company:
            company = "Target Company"

        # Load candidate skills
        candidate_skills = []
        resume_data = get_db().get_resume_data()
        if resume_data:
            candidate_skills = resume_data.get("skills_json") or []
            if isinstance(candidate_skills, dict):
                all_s = []
                for v in candidate_skills.values():
                    if isinstance(v, list):
                        all_s.extend(v)
                candidate_skills = all_s

        from core.services.interview_service import get_interview_service
        service = get_interview_service()
        prep_kit = service.generate_prep_kit(
            job_title=title,
            company=company,
            jd_text=jd_text,
            candidate_skills=candidate_skills if isinstance(candidate_skills, list) else [],
        )
        return jsonify({"success": True, "prep": prep_kit})
    except Exception as e:
        logger.error(f"[app] Interview prep error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/interview/evaluate", methods=["POST"])
def api_interview_evaluate():
    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()
        user_answer = data.get("user_answer", "").strip()
        expected_topic = data.get("expected_topic", "").strip()

        from core.services.interview_service import get_interview_service
        service = get_interview_service()
        evaluation = service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            expected_topic=expected_topic,
        )
        return jsonify({"success": True, "evaluation": evaluation})
    except Exception as e:
        logger.error(f"[app] Interview evaluation error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ── Email Status & Test ──────────────────────────────────────────────────────


@app.route("/api/email/status")
def api_email_status():
    """Return email provider configuration status using EmailSender."""
    try:
        from email_module.sender import EmailSender
        sender = EmailSender()
        ps = sender.provider_status()
        resend_configured = ps.get("resend", {}).get("configured", False)
        gs = ps.get("gmail", {})
        gmail_configured = gs.get("authenticated", False)
        gmail_account = gs.get("account") or os.getenv("FROM_EMAIL")
        gmail_status = "connected" if gmail_configured else "not_authenticated"
        configured = ps.get("can_send", False)
        provider = ps.get("active_provider")
    except Exception as e:
        logger.warning(f"[app] EmailSender error: {e}")
        resend_configured = False
        gs = {}
        gmail_configured = bool(os.path.exists(os.getenv("GMAIL_CREDENTIALS_PATH", "./email_module/credentials.json")))
        gmail_account = None
        gmail_status = "error"
        configured = gmail_configured
        provider = "gmail" if gmail_configured else None

    return jsonify({
        "success": True,
        "configured": configured,
        "provider": provider,
        "from_email": gmail_account or os.getenv("FROM_EMAIL"),
        "resend_configured": resend_configured,
        "gmail": {
            "configured": gmail_configured,
            "account": gmail_account,
            "status": gmail_status,
            "has_credentials": gs.get("credentials", False) if isinstance(gs, dict) else False,
            "has_token": gs.get("token", False) if isinstance(gs, dict) else False,
            "token_expired": False,
        },
    })


@app.route("/api/email/test", methods=["POST"])
def api_email_test():
    """Send a test email to verify provider configuration."""
    try:
        body = request.get_json(silent=True) or {}
        to = body.get("to") or os.getenv("FROM_EMAIL")

        # Try Gmail first
        gmail = get_gmail_service()
        if gmail.is_ready():
            result = gmail.send_test(to=to)
            return jsonify(result)

        # Fallback to Resend
        from email_module.sender import EmailSender
        sender = EmailSender()
        result = sender.send_test(to=to)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Granular Email Health (for Settings page diagnostics) ─────────────────────

@app.route("/api/email-status")
def api_email_diagnostics():
    """Granular email health check for Settings page."""
    try:
        from email_module.sender import EmailSender
        sender = EmailSender()
        return jsonify({"success": True, **sender.provider_status()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/email-test", methods=["POST"])
def api_email_diagnostics_test():
    """'Send Test Email' button on Settings page."""
    try:
        from email_module.sender import EmailSender
        data = request.get_json(silent=True) or {}
        to   = data.get("to")
        sender = EmailSender()
        result = sender.send_test(to=to)
        return jsonify({"success": result["success"], **result})
    except Exception as e:
        logger.error(f"[app] Email test failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ── Gmail OAuth ───────────────────────────────────────────────────────────────

@app.route("/api/gmail/auth-url", methods=["GET"])
def api_gmail_auth_url():
    """Generate Google OAuth authorization URL."""
    gmail = get_gmail_service()
    if not gmail.has_credentials_file:
        return jsonify({
            "success": False,
            "error": "Gmail credentials not found. Set GMAIL_CREDENTIALS_PATH.",
        }), 400

    redirect_uri = request.host_url.rstrip("/") + "/api/gmail/callback"
    auth_url, error = gmail.get_auth_url(redirect_uri)
    if error:
        return jsonify({"success": False, "error": error}), 500

    return jsonify({"success": True, "auth_url": auth_url})


@app.route("/api/gmail/callback", methods=["GET"])
def api_gmail_callback():
    """Handle Gmail OAuth callback — exchange code for token."""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return jsonify({"success": False, "error": f"Google returned error: {error}"})

    if not code:
        return jsonify({"success": False, "error": "No authorization code received"}), 400

    redirect_uri = request.host_url.rstrip("/") + "/api/gmail/callback"
    gmail = get_gmail_service()
    success, message = gmail.handle_callback(code, state or "", redirect_uri)

    if success:
        # Return a small HTML page that closes itself or shows success
        return (
            "<html><body style='background:#0a0a0f;color:#e4e4e7;display:flex;align-items:center;"
            "justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;gap:8px;'>"
            "<div style='font-size:40px'>✅</div>"
            "<div style='font-size:16px;font-weight:600'>Gmail Connected</div>"
            f"<div style='font-size:12px;color:#a1a1aa'>{message}</div>"
            "<div style='font-size:11px;color:#71717a;margin-top:12px'>"
            "You can close this tab and return to Applyr</div>"
            "<script>window.close()</script>"
            "</body></html>"
        ), 200, {"Content-Type": "text/html; charset=utf-8"}
    else:
        return jsonify({"success": False, "error": message}), 500


@app.route("/api/gmail/status", methods=["GET"])
def api_gmail_status():
    """Return Gmail connection status — never exposes tokens."""
    gmail = get_gmail_service()
    try:
        status = gmail.get_status()
        return jsonify({"success": True, **status})
    except Exception as e:
        return jsonify({"success": False, "status": "error", "error": str(e)})


@app.route("/api/gmail/disconnect", methods=["POST"])
def api_gmail_disconnect():
    """Revoke Gmail token and disconnect."""
    gmail = get_gmail_service()
    gmail.revoke_token()
    return jsonify({"success": True, "status": "disconnected"})


# ── Setup Wizard Status ──────────────────────────────────────────────────────

@app.route("/api/setup/status")
def api_setup_status():
    """Return setup completion status for onboarding wizard."""
    resume_dir = ROOT / "resume"
    resume_uploaded = any(
        (resume_dir / name).exists()
        for name in ["master_resume.pdf", "master_resume.docx", "master_resume.txt"]
    )

    resume_data = None
    try:
        resume_data = get_db().get_resume_data()
    except Exception:
        pass

    resume_parsed = bool(resume_data and resume_data.get("parse_status") == "success")

    groq_key = os.getenv("GROQ_API_KEY", "")
    groq_ok = bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    tavily_ok = bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_ok = bool(gemini_key)

    try:
        from email_module.sender import EmailSender
        sender = EmailSender()
        ps = sender.provider_status()
        email_ok = ps.get("can_send", False)
        from_email = ps.get("gmail", {}).get("account") or os.getenv("FROM_EMAIL", "")
    except Exception:
        email_ok = False

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
        "ready": percent >= 60,  # Ready to run if most critical steps are done
    })


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Startup validation
    logger.info("=" * 50)
    logger.info("Applyr API — Starting up")

    # Gmail check
    gmail = get_gmail_service()
    if gmail.has_credentials_file:
        status = gmail.get_status()
        if status.get("status") == "connected":
            account = status.get("account") or "unknown"
            logger.info("[Gmail] Connected — account: %s", account)
        elif status.get("status") == "expired_token":
            logger.warning("[Gmail] Token expired — will auto-refresh on send")
        elif status.get("status") == "not_authenticated":
            logger.warning("[Gmail] Credentials found but not authenticated — use Settings > Connect Gmail")
        else:
            logger.warning("[Gmail] Not configured — status: %s", status.get("status"))
    else:
        logger.info("[Gmail] Not configured — set GMAIL_CREDENTIALS_PATH")

    # Resend check
    resend_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("FROM_EMAIL", "")
    if resend_key and from_email:
        logger.info("[Resend] Configured — from: %s", from_email)
    else:
        logger.info("[Resend] Not configured")

    # Phase 13: Start scheduler singleton
    try:
        from core.services.scheduler_service import init_scheduler
        scheduler_started = init_scheduler()
        if scheduler_started:
            logger.info("[Scheduler] Started — runs at 09:00, 12:00, 15:00, 18:00 IST")
        else:
            logger.info("[Scheduler] Not started — SCHEDULER_ENABLED=false or APScheduler missing")
    except Exception as e:
        logger.warning("[Scheduler] Init failed (non-fatal): %s", e)

    port = int(os.getenv("FLASK_PORT", 5000))
    logger.info("Starting server on http://localhost:%d", port)
    logger.info("=" * 50)

    app.run(
        debug=os.getenv("DEBUG", "true").lower() == "true",
        use_reloader=False,
        host="0.0.0.0",
        port=port,
        threaded=True,  # serve the SSE stream + UI polls + background run concurrently
    )
