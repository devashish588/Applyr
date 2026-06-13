"""
Simple Flask UI for Applyr - provides web interface for manual triggering and uploads
"""
import os
import sys
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.manual_trigger import trigger_manual_run

# Configure Flask
app = Flask(__name__, template_folder='./ui/templates')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_FOLDER'] = './uploads'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx'}


def allowed_file(filename):
    """Check if file type is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get current status."""
    return jsonify({
        "status": "online",
        "message": "Applyr Pipeline Ready"
    })


@app.route('/api/run-now', methods=['POST'])
def api_run_now():
    """Trigger manual pipeline run."""
    try:
        logger.info("Manual run triggered via UI")
        results = trigger_manual_run()
        
        return jsonify({
            "success": True,
            "message": "Pipeline run started",
            "results": results
        })
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/upload-jd', methods=['POST'])
def api_upload_jd():
    """Handle JD file upload (PDF/image/text)."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        filename = secure_filename(file.filename)
        
        # Save to uploads folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"JD file uploaded: {filepath}")
        
        # Trigger pipeline with uploaded JD
        results = trigger_manual_run(job_file=filepath)
        
        return jsonify({
            "success": True,
            "message": "File uploaded and pipeline started",
            "filename": filename,
            "results": results
        })
    
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/paste-jd', methods=['POST'])
def api_paste_jd():
    """Handle pasted JD text."""
    try:
        data = request.get_json()
        jd_text = data.get('jd_text', '').strip()
        
        if not jd_text:
            return jsonify({"error": "No JD text provided"}), 400
        
        if len(jd_text) < 50:
            return jsonify({"error": "JD text too short"}), 400
        
        logger.info(f"JD text pasted ({len(jd_text)} characters)")
        
        # Trigger pipeline with pasted JD
        results = trigger_manual_run(job_text=jd_text)
        
        return jsonify({
            "success": True,
            "message": "JD processed and pipeline started",
            "jd_length": len(jd_text),
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Pasted JD processing failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Get recent run logs."""
    try:
        from db.db_client import get_db
        db = get_db()
        
        runs = db.get_recent_run_logs(limit=10)
        
        return jsonify({
            "success": True,
            "runs": runs
        })
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info("Starting Applyr Flask UI...")
    app.run(debug=True, host='0.0.0.0', port=5000)
