"""
Applyr Flask Web Application - Dashboard, API, and Pipeline Control.

Features:
- Premium dashboard with live pipeline visualization
- Resume upload & management
- JD upload (PDF/image/text/URL)
- Real-time pipeline progress via SSE
- Job feed, email drafts, run history, analytics
"""
import os
import sys
import json
import time
import queue
import logging
import threading
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Flask
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_DIR', os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'uploads'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx'}
RESUME_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}

# Pipeline progress queue for SSE streaming
pipeline_events = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_resume(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in RESUME_EXTENSIONS


# ─── Page Routes ────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─── Pipeline Progress SSE ──────────────────────────────────────

@app.route('/api/pipeline/stream/<run_id>')
def pipeline_stream(run_id):
    """Server-Sent Events stream for pipeline progress."""
    def generate():
        q = pipeline_events.get(run_id)
        if not q:
            yield f"data: {json.dumps({'step': 'error', 'msg': 'Run not found'})}\n\n"
            return
        while True:
            try:
                event = q.get(timeout=120)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get('step') == 'done' or event.get('step') == 'error':
                    break
            except Exception:
                yield f"data: {json.dumps({'step': 'timeout', 'msg': 'Stream timeout'})}\n\n"
                break

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


def run_pipeline_with_progress(run_id, job_text=None, job_file=None):
    """Run pipeline in background thread, pushing progress events."""
    q = queue.Queue()
    pipeline_events[run_id] = q

    def _run():
        try:
            from pipeline.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            orchestrator.run_id = run_id

            q.put({'step': 'init', 'msg': 'Initializing pipeline...', 'pct': 5})
            time.sleep(0.3)

            # Step 1: Discover
            q.put({'step': 'discover', 'msg': 'Searching for jobs...', 'pct': 10})
            if job_text or job_file:
                jobs = orchestrator._step_manual_input(job_text, job_file)
            else:
                jobs = orchestrator._step_discover()
            q.put({'step': 'discover_done', 'msg': f'Found {len(jobs)} jobs', 'pct': 25, 'count': len(jobs)})

            # Step 2: Parse
            q.put({'step': 'parse', 'msg': 'Parsing job descriptions...', 'pct': 30})
            parsed = orchestrator._step_parse_and_match(jobs)
            q.put({'step': 'parse_done', 'msg': f'Parsed {len(parsed)} jobs', 'pct': 40, 'count': len(parsed)})

            # Step 3: Score
            q.put({'step': 'score', 'msg': 'Scoring job matches...', 'pct': 45})
            filtered = orchestrator._step_filter_and_score(parsed)
            q.put({'step': 'score_done', 'msg': f'{len(filtered)} jobs passed threshold', 'pct': 60, 'count': len(filtered)})

            # Step 4: Tailor
            q.put({'step': 'tailor', 'msg': 'Tailoring resumes & cover letters...', 'pct': 65})
            tailored = orchestrator._step_tailor(filtered)
            q.put({'step': 'tailor_done', 'msg': f'Tailored {len(tailored)} applications', 'pct': 80, 'count': len(tailored)})

            # Step 5: Email
            q.put({'step': 'email', 'msg': 'Drafting cold emails...', 'pct': 85})
            applied = orchestrator._step_draft_and_send(tailored)
            q.put({'step': 'email_done', 'msg': f'Drafted {len(applied)} emails', 'pct': 95, 'count': len(applied)})

            orchestrator.results.update({
                'jobs_found': len(jobs),
                'jobs_filtered': len(filtered),
                'jobs_applied': len(applied),
                'emails_sent': len(applied),
                'status': 'completed'
            })

            orchestrator.db.update_run_log(
                run_id,
                jobs_found=len(jobs), jobs_filtered=len(filtered),
                jobs_applied=len(applied), emails_sent=len(applied),
                errors_count=len(orchestrator.results.get('errors', [])),
                summary=orchestrator.results
            )
            orchestrator.save_run_summary()

            q.put({'step': 'done', 'msg': 'Pipeline complete!', 'pct': 100,
                   'results': orchestrator.results})

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            q.put({'step': 'error', 'msg': str(e), 'pct': 0})
        finally:
            if run_id in pipeline_events:
                del pipeline_events[run_id]

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return run_id


# ─── API Routes ─────────────────────────────────────────────────

@app.route('/api/status')
def api_status():
    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    resume_path = os.getenv("MASTER_RESUME_PDF", "./resume/master_resume.pdf")
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "groq_configured": bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx"),
        "tavily_configured": bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx"),
        "resume_uploaded": os.path.exists(resume_path),
        "resume_path": resume_path if os.path.exists(resume_path) else None,
        "env_keys": {
            "GROQ_API_KEY": bool(groq_key and groq_key != "gsk_xxxxxxxxxxxxx"),
            "TAVILY_API_KEY": bool(tavily_key),
            "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY", "")),
            "SCRAPINGBEE_API_KEY": bool(os.getenv("SCRAPINGBEE_API_KEY", "")),
        }
    })


@app.route('/api/run-now', methods=['POST'])
def api_run_now():
    import uuid
    run_id = str(uuid.uuid4())[:8]
    from db.db_client import get_db
    db = get_db()
    db.start_run_log(run_id, "manual")
    run_pipeline_with_progress(run_id)
    return jsonify({"success": True, "run_id": run_id})


@app.route('/api/upload-jd', methods=['POST'])
def api_upload_jd():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename(file.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    import uuid
    run_id = str(uuid.uuid4())[:8]
    from db.db_client import get_db
    get_db().start_run_log(run_id, "upload")
    run_pipeline_with_progress(run_id, job_file=filepath)
    return jsonify({"success": True, "run_id": run_id, "filename": filename})


@app.route('/api/paste-jd', methods=['POST'])
def api_paste_jd():
    data = request.get_json()
    jd_text = data.get('jd_text', '').strip()
    if not jd_text or len(jd_text) < 30:
        return jsonify({"error": "JD text too short (min 30 chars)"}), 400

    import uuid
    run_id = str(uuid.uuid4())[:8]
    from db.db_client import get_db
    get_db().start_run_log(run_id, "paste")
    run_pipeline_with_progress(run_id, job_text=jd_text)
    return jsonify({"success": True, "run_id": run_id})


@app.route('/api/upload-resume', methods=['POST'])
def api_upload_resume():
    """Upload master resume."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_resume(file.filename):
        return jsonify({"error": "Invalid file. Allowed: PDF, DOCX, TXT"}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    resume_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resume')
    os.makedirs(resume_dir, exist_ok=True)

    if ext == 'pdf':
        save_path = os.path.join(resume_dir, 'master_resume.pdf')
    elif ext in ('doc', 'docx'):
        save_path = os.path.join(resume_dir, 'master_resume.docx')
    else:
        save_path = os.path.join(resume_dir, 'master_resume.txt')

    file.save(save_path)
    logger.info(f"Resume uploaded: {save_path}")

    # Parse resume to update profile
    result = {"success": True, "path": save_path, "size": os.path.getsize(save_path)}
    try:
        from agents.resume_parser_agent import ResumeParserAgent
        parser = ResumeParserAgent()
        profile = parser.parse_resume(save_path)
        result["parsed"] = profile
    except Exception as e:
        logger.warning(f"Resume parse failed: {e}")
        result["parse_error"] = str(e)

    return jsonify(result)


@app.route('/api/resume-status')
def api_resume_status():
    """Check if resume is uploaded."""
    resume_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resume')
    pdf_path = os.path.join(resume_dir, 'master_resume.pdf')
    docx_path = os.path.join(resume_dir, 'master_resume.docx')
    txt_path = os.path.join(resume_dir, 'master_resume.txt')

    for path in [pdf_path, docx_path, txt_path]:
        if os.path.exists(path):
            return jsonify({
                "uploaded": True,
                "path": path,
                "filename": os.path.basename(path),
                "size": os.path.getsize(path),
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })

    return jsonify({"uploaded": False})


@app.route('/api/jobs')
def api_jobs():
    try:
        from db.db_client import get_db
        jobs = get_db().get_all_jobs(limit=100)
        return jsonify({"success": True, "jobs": jobs, "total": len(jobs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/emails')
def api_emails():
    try:
        from db.db_client import get_db
        emails = get_db().get_unsent_emails()
        return jsonify({"success": True, "emails": emails, "total": len(emails)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs')
def api_logs():
    try:
        from db.db_client import get_db
        runs = get_db().get_recent_run_logs(limit=20)
        return jsonify({"success": True, "runs": runs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics')
def api_analytics():
    try:
        from db.db_client import get_db
        db = get_db()
        all_jobs = db.get_all_jobs(limit=1000)
        runs = db.get_recent_run_logs(limit=50)

        total = len(all_jobs)
        applied = len([j for j in all_jobs if j.get('status') == 'applied'])
        tailored = len([j for j in all_jobs if j.get('status') == 'tailored'])
        avg = sum(j.get('fit_score', 0) for j in all_jobs) / max(total, 1)

        scores = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
        for j in all_jobs:
            s = j.get("fit_score", 0)
            if s <= 25: scores["0-25"] += 1
            elif s <= 50: scores["26-50"] += 1
            elif s <= 75: scores["51-75"] += 1
            else: scores["76-100"] += 1

        sources = {}
        for j in all_jobs:
            src = j.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        return jsonify({
            "success": True,
            "analytics": {
                "total_jobs": total, "applied": applied, "tailored": tailored,
                "avg_score": round(avg, 1), "total_runs": len(runs),
                "score_distribution": scores, "source_distribution": sources,
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Applyr Dashboard on http://localhost:5000")
    # use_reloader=False prevents watchdog from killing background pipeline threads
    app.run(debug=True, use_reloader=False, host='0.0.0.0',
            port=int(os.getenv('FLASK_PORT', 5000)))
