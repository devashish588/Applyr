"""
AutoApply / Applyr — Flask Dashboard
Single-file app: backend API + self-contained HTML dashboard (no templates folder needed).

Fixes vs original:
  - Removed calls to non-existent orchestrator methods (_step_manual_input, etc.)
  - Removed dependency on missing db_client — now uses db/db_client.py
  - orchestrator.run_full_pipeline() called correctly (matching what we built)
  - Complete dashboard UI embedded — no templates/ folder needed
  - SSE pipeline streaming works with correct orchestrator interface
  - Resume parse uses correct method name (parse_file not parse_resume)

Run:
    python ui/app.py
    # → http://localhost:5000
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
load_dotenv()

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from db.db_client import get_db

app = Flask(__name__)
CORS(app)
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

def _allowed(filename, allowed_set):
    return _ext(filename) in allowed_set


# ── Dashboard HTML (self-contained, no templates/ needed) ─────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Applyr — AI Job Application Agent</title>
<style>
  :root {
    --bg:       #0d0f14;
    --surface:  #161921;
    --border:   #252830;
    --accent:   #6c8fff;
    --accent2:  #a78bfa;
    --green:    #34d399;
    --amber:    #fbbf24;
    --red:      #f87171;
    --text:     #e8eaf0;
    --muted:    #6b7280;
    --radius:   10px;
    --mono:     'JetBrains Mono', 'Fira Code', monospace;
    --sans:     'Inter', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans);
         font-size: 14px; min-height: 100vh; }

  /* ── Layout ── */
  .shell   { display: flex; height: 100vh; overflow: hidden; }
  .sidebar { width: 220px; background: var(--surface); border-right: 1px solid var(--border);
             display: flex; flex-direction: column; flex-shrink: 0; padding: 20px 0; }
  .main    { flex: 1; overflow-y: auto; padding: 28px 32px; }

  /* ── Sidebar ── */
  .logo { padding: 0 20px 24px; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;
          color: var(--text); }
  .logo span { color: var(--accent); }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 20px;
              color: var(--muted); cursor: pointer; border-radius: 0;
              transition: all .15s; font-size: 13px; border: none; background: none;
              width: 100%; text-align: left; }
  .nav-item:hover, .nav-item.active { color: var(--text); background: rgba(108,143,255,.08); }
  .nav-item.active { border-left: 2px solid var(--accent); }
  .nav-icon { font-size: 16px; width: 18px; text-align: center; }
  .sidebar-footer { margin-top: auto; padding: 16px 20px;
                    border-top: 1px solid var(--border); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green);
                display: inline-block; margin-right: 6px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  /* ── Pages ── */
  .page { display: none; }
  .page.active { display: block; }
  .page-title { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
  .page-sub   { color: var(--muted); margin-bottom: 28px; font-size: 13px; }

  /* ── Cards ── */
  .card { background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius); padding: 20px; }
  .card-title { font-size: 12px; font-weight: 600; text-transform: uppercase;
                letter-spacing: .08em; color: var(--muted); margin-bottom: 12px; }

  /* ── Stats row ── */
  .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
  .stat-val   { font-size: 32px; font-weight: 700; letter-spacing: -1px; }
  .stat-label { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .stat-delta { font-size: 11px; color: var(--green); margin-top: 2px; }

  /* ── Trigger buttons ── */
  .actions { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }
  .btn { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px;
         border-radius: 7px; font-size: 13px; font-weight: 500; cursor: pointer;
         border: none; transition: all .15s; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: #7c9fff; }
  .btn-outline { background: transparent; color: var(--text);
                 border: 1px solid var(--border); }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }
  .btn:disabled { opacity: .45; cursor: not-allowed; }

  /* ── Pipeline progress ── */
  .pipeline-wrap { margin-bottom: 24px; }
  .pipeline-steps { display: flex; gap: 0; margin-bottom: 12px; }
  .step { flex: 1; text-align: center; position: relative; }
  .step:not(:last-child)::after { content:''; position:absolute; top:13px; left:60%;
    width:80%; height:2px; background:var(--border); z-index:0; }
  .step-dot { width: 26px; height: 26px; border-radius: 50%; background: var(--border);
              margin: 0 auto 6px; display: flex; align-items: center; justify-content: center;
              font-size: 11px; position: relative; z-index: 1; transition: all .3s; }
  .step.done .step-dot   { background: var(--green); color: #000; }
  .step.active .step-dot { background: var(--accent); color: #fff;
                            box-shadow: 0 0 0 3px rgba(108,143,255,.25); }
  .step.error .step-dot  { background: var(--red); color: #fff; }
  .step-label { font-size: 11px; color: var(--muted); }
  .step.done .step-label   { color: var(--green); }
  .step.active .step-label { color: var(--accent); }
  .progress-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--accent); border-radius: 2px;
                   transition: width .4s ease; }
  .pipeline-log { font-family: var(--mono); font-size: 12px; color: var(--muted);
                  margin-top: 10px; min-height: 18px; }

  /* ── Table ── */
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing:.06em;
       color: var(--muted); padding: 8px 12px; border-bottom: 1px solid var(--border); }
  td { padding: 10px 12px; border-bottom: 1px solid rgba(37,40,48,.6); vertical-align: middle; }
  tr:hover td { background: rgba(255,255,255,.02); }
  .empty-row td { text-align: center; color: var(--muted); padding: 32px; }

  /* ── Badges ── */
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
           font-size: 11px; font-weight: 500; }
  .badge-green  { background: rgba(52,211,153,.15); color: var(--green); }
  .badge-amber  { background: rgba(251,191,36,.12); color: var(--amber); }
  .badge-red    { background: rgba(248,113,113,.12); color: var(--red); }
  .badge-blue   { background: rgba(108,143,255,.15); color: var(--accent); }
  .badge-gray   { background: rgba(107,114,128,.15); color: var(--muted); }

  /* ── Score bar ── */
  .score-bar { display: flex; align-items: center; gap: 8px; }
  .score-track { flex: 1; height: 4px; background: var(--border); border-radius: 2px; }
  .score-fill  { height: 100%; border-radius: 2px; }

  /* ── Upload zone ── */
  .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius);
               padding: 36px; text-align: center; cursor: pointer; transition: all .2s; }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: var(--accent); background: rgba(108,143,255,.04); }
  .drop-zone .icon { font-size: 32px; margin-bottom: 10px; }
  .drop-zone p { color: var(--muted); font-size: 13px; }
  .drop-zone strong { color: var(--text); }

  /* ── Textarea / input ── */
  textarea, input[type=text] {
    width: 100%; background: var(--bg); border: 1px solid var(--border);
    border-radius: 7px; color: var(--text); padding: 10px 14px; font-size: 13px;
    font-family: var(--sans); resize: vertical; outline: none; }
  textarea:focus, input[type=text]:focus { border-color: var(--accent); }

  /* ── Grid ── */
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  @media(max-width:900px) { .stats{grid-template-columns:1fr 1fr;} .grid2,.grid3{grid-template-columns:1fr;} }

  /* ── Toast ── */
  #toast { position: fixed; bottom: 24px; right: 24px; background: var(--surface);
           border: 1px solid var(--border); border-radius: 8px; padding: 12px 18px;
           font-size: 13px; opacity: 0; transform: translateY(8px);
           transition: all .25s; pointer-events: none; z-index: 999; max-width: 300px; }
  #toast.show { opacity: 1; transform: translateY(0); }

  /* ── Env status ── */
  .env-row { display: flex; align-items: center; justify-content: space-between;
             padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
  .env-row:last-child { border: none; }
  .env-key { font-family: var(--mono); font-size: 12px; color: var(--muted); }

  .mt16 { margin-top: 16px; }
  .mt24 { margin-top: 24px; }
  .gap12 { gap: 12px; }
</style>
</head>
<body>

<div class="shell">

  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="logo">App<span>lyr</span></div>

    <button class="nav-item active" onclick="nav('dashboard')">
      <span class="nav-icon">⚡</span> Dashboard
    </button>
    <button class="nav-item" onclick="nav('run')">
      <span class="nav-icon">▶</span> Run Pipeline
    </button>
    <button class="nav-item" onclick="nav('jobs')">
      <span class="nav-icon">💼</span> Jobs
    </button>
    <button class="nav-item" onclick="nav('emails')">
      <span class="nav-icon">✉</span> Drafts
    </button>
    <button class="nav-item" onclick="nav('history')">
      <span class="nav-icon">📋</span> History
    </button>
    <button class="nav-item" onclick="nav('settings')">
      <span class="nav-icon">⚙</span> Settings
    </button>

    <div class="sidebar-footer">
      <span class="status-dot"></span>
      <span style="color:var(--muted);font-size:12px;">Agent online</span>
    </div>
  </aside>

  <!-- Main -->
  <main class="main">

    <!-- ── Dashboard ── -->
    <div id="page-dashboard" class="page active">
      <div class="page-title">Dashboard</div>
      <div class="page-sub">Overview of your job application pipeline</div>

      <div class="stats" id="stat-cards">
        <div class="card"><div class="stat-val" id="s-found">—</div>
          <div class="stat-label">Jobs Found</div></div>
        <div class="card"><div class="stat-val" id="s-filtered">—</div>
          <div class="stat-label">Passed Filter</div></div>
        <div class="card"><div class="stat-val" id="s-applied">—</div>
          <div class="stat-label">Applications</div></div>
        <div class="card"><div class="stat-val" id="s-sent">—</div>
          <div class="stat-label">Emails Sent</div></div>
      </div>

      <div class="grid2">
        <div class="card">
          <div class="card-title">Recent Jobs</div>
          <div class="table-wrap">
            <table id="dash-jobs-table">
              <thead><tr><th>Role</th><th>Company</th><th>Score</th><th>Status</th></tr></thead>
              <tbody><tr class="empty-row"><td colspan="4">Loading...</td></tr></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-title">System Status</div>
          <div id="env-status">Loading...</div>
        </div>
      </div>
    </div>

    <!-- ── Run Pipeline ── -->
    <div id="page-run" class="page">
      <div class="page-title">Run Pipeline</div>
      <div class="page-sub">Trigger automatically or feed a specific job description</div>

      <div class="actions">
        <button class="btn btn-primary" id="btn-run-now" onclick="runNow()">
          ⚡ Run Now (auto-discover)
        </button>
      </div>

      <!-- Pipeline progress -->
      <div class="card pipeline-wrap" id="pipeline-card" style="display:none">
        <div class="card-title">Pipeline Progress</div>
        <div class="pipeline-steps">
          <div class="step" id="ps-discover"><div class="step-dot">1</div><div class="step-label">Discover</div></div>
          <div class="step" id="ps-parse"><div class="step-dot">2</div><div class="step-label">Parse</div></div>
          <div class="step" id="ps-score"><div class="step-dot">3</div><div class="step-label">Score</div></div>
          <div class="step" id="ps-tailor"><div class="step-dot">4</div><div class="step-label">Tailor</div></div>
          <div class="step" id="ps-email"><div class="step-dot">5</div><div class="step-label">Email</div></div>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="prog-fill" style="width:0%"></div></div>
        <div class="pipeline-log" id="pipeline-log">Initializing...</div>
      </div>

      <div class="grid2 mt24">
        <!-- Upload JD -->
        <div class="card">
          <div class="card-title">Upload JD (PDF / Image)</div>
          <div class="drop-zone" id="jd-drop"
               onclick="document.getElementById('jd-file').click()"
               ondragover="event.preventDefault();this.classList.add('drag-over')"
               ondragleave="this.classList.remove('drag-over')"
               ondrop="handleJdDrop(event)">
            <div class="icon">📄</div>
            <p><strong>Click or drag</strong> a JD PDF / screenshot here</p>
            <p style="margin-top:6px;font-size:11px;">PDF, PNG, JPG, TXT supported</p>
          </div>
          <input type="file" id="jd-file" style="display:none"
                 accept=".pdf,.png,.jpg,.jpeg,.txt" onchange="uploadJd(this.files[0])">
        </div>

        <!-- Paste JD -->
        <div class="card">
          <div class="card-title">Paste JD Text</div>
          <textarea id="jd-text" rows="6"
                    placeholder="Paste the full job description here..."></textarea>
          <button class="btn btn-primary mt16" onclick="pasteJd()" style="width:100%">
            ▶ Run on this JD
          </button>
        </div>
      </div>

      <!-- Upload resume -->
      <div class="card mt24">
        <div class="card-title">Master Resume</div>
        <div class="grid2" style="align-items:center">
          <div>
            <div id="resume-status-text" style="color:var(--muted);font-size:13px">Checking...</div>
          </div>
          <div>
            <div class="drop-zone" id="resume-drop"
                 onclick="document.getElementById('resume-file').click()"
                 ondragover="event.preventDefault();this.classList.add('drag-over')"
                 ondragleave="this.classList.remove('drag-over')"
                 ondrop="handleResumeDrop(event)">
              <div class="icon">📝</div>
              <p><strong>Upload</strong> your resume</p>
              <p style="font-size:11px;margin-top:4px">PDF, DOCX, TXT</p>
            </div>
            <input type="file" id="resume-file" style="display:none"
                   accept=".pdf,.docx,.doc,.txt" onchange="uploadResume(this.files[0])">
          </div>
        </div>
      </div>
    </div>

    <!-- ── Jobs ── -->
    <div id="page-jobs" class="page">
      <div class="page-title">Jobs</div>
      <div class="page-sub">All discovered and processed job listings</div>
      <div class="card">
        <div class="table-wrap">
          <table id="jobs-table">
            <thead>
              <tr>
                <th>Role</th><th>Company</th><th>Location</th>
                <th>Fit Score</th><th>Source</th><th>Status</th><th>Date</th>
              </tr>
            </thead>
            <tbody><tr class="empty-row"><td colspan="7">Loading...</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Email Drafts ── -->
    <div id="page-emails" class="page">
      <div class="page-title">Email Drafts</div>
      <div class="page-sub">Ready-to-send application emails</div>
      <div class="card">
        <div class="table-wrap">
          <table id="emails-table">
            <thead>
              <tr><th>To</th><th>Subject</th><th>Company</th><th>Score</th><th>Status</th></tr>
            </thead>
            <tbody><tr class="empty-row"><td colspan="5">Loading...</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── History ── -->
    <div id="page-history" class="page">
      <div class="page-title">Run History</div>
      <div class="page-sub">Every pipeline run logged here</div>
      <div class="card">
        <div class="table-wrap">
          <table id="history-table">
            <thead>
              <tr><th>Run ID</th><th>Trigger</th><th>Started</th><th>Found</th>
                  <th>Applied</th><th>Sent</th><th>Status</th></tr>
            </thead>
            <tbody><tr class="empty-row"><td colspan="7">Loading...</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Settings ── -->
    <div id="page-settings" class="page">
      <div class="page-title">Settings</div>
      <div class="page-sub">Environment configuration and API key status</div>
      <div class="grid2">
        <div class="card">
          <div class="card-title">API Keys</div>
          <div id="settings-env">Loading...</div>
        </div>
        <div class="card">
          <div class="card-title">Pipeline Config</div>
          <div style="font-size:13px;line-height:2;color:var(--muted)">
            Edit <code style="color:var(--accent)">.env</code> to change these values.
          </div>
          <div id="settings-config" style="margin-top:12px;font-family:var(--mono);font-size:12px;line-height:2"></div>
        </div>
      </div>
    </div>

  </main>
</div>

<div id="toast"></div>

<script>
// ── Navigation ────────────────────────────────────────────────────────────────
function nav(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  event.currentTarget.classList.add('active');
  if (page === 'jobs')     loadJobs();
  if (page === 'emails')   loadEmails();
  if (page === 'history')  loadHistory();
  if (page === 'settings') loadSettings();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, color) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.borderColor = color || 'var(--border)';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Status checks ─────────────────────────────────────────────────────────────
async function loadStatus() {
  const r = await fetch('/api/status').then(r => r.json()).catch(() => ({}));

  // Dashboard env card
  const keys = r.env_keys || {};
  document.getElementById('env-status').innerHTML = `
    ${envRow('GROQ_API_KEY',    keys.GROQ_API_KEY)}
    ${envRow('TAVILY_API_KEY',  keys.TAVILY_API_KEY)}
    ${envRow('GEMINI_API_KEY',  keys.GEMINI_API_KEY)}
    ${envRow('Resume uploaded', r.resume_uploaded)}
  `;

  // Resume status on Run page
  document.getElementById('resume-status-text').innerHTML = r.resume_uploaded
    ? '<span style="color:var(--green)">✓ Resume uploaded</span> — ' + r.resume_path
    : '<span style="color:var(--amber)">⚠ No resume found</span> — upload one to the right';
}

function envRow(label, ok) {
  return `<div class="env-row">
    <span class="env-key">${label}</span>
    <span class="badge ${ok ? 'badge-green' : 'badge-red'}">${ok ? '✓ Set' : '✗ Missing'}</span>
  </div>`;
}

// ── Dashboard stats ───────────────────────────────────────────────────────────
async function loadDashStats() {
  const r = await fetch('/api/analytics').then(r => r.json()).catch(() => ({}));
  const a = r.analytics || {};
  document.getElementById('s-found').textContent    = a.total_jobs    ?? '0';
  document.getElementById('s-filtered').textContent = a.tailored      ?? '0';
  document.getElementById('s-applied').textContent  = a.applied       ?? '0';
  document.getElementById('s-sent').textContent     = a.applied       ?? '0';
}

async function loadDashJobs() {
  const r = await fetch('/api/jobs').then(r => r.json()).catch(() => ({}));
  const jobs = (r.jobs || []).slice(0, 8);
  const tbody = document.querySelector('#dash-jobs-table tbody');
  if (!jobs.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No jobs yet — run the pipeline</td></tr>';
    return;
  }
  tbody.innerHTML = jobs.map(j => `
    <tr>
      <td>${j.title || '—'}</td>
      <td>${j.company || '—'}</td>
      <td>${scoreBar(j.fit_score)}</td>
      <td>${statusBadge(j.status)}</td>
    </tr>`).join('');
}

// ── Jobs table ────────────────────────────────────────────────────────────────
async function loadJobs() {
  const r = await fetch('/api/jobs').then(r => r.json()).catch(() => ({}));
  const jobs = r.jobs || [];
  const tbody = document.querySelector('#jobs-table tbody');
  if (!jobs.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No jobs found yet</td></tr>';
    return;
  }
  tbody.innerHTML = jobs.map(j => `
    <tr>
      <td>${j.title || '—'}</td>
      <td>${j.company || '—'}</td>
      <td>${j.location || '—'}</td>
      <td>${scoreBar(j.fit_score)}</td>
      <td><span class="badge badge-gray">${j.source || '—'}</span></td>
      <td>${statusBadge(j.status)}</td>
      <td style="color:var(--muted);font-size:11px">${fmtDate(j.scraped_at)}</td>
    </tr>`).join('');
}

// ── Emails table ──────────────────────────────────────────────────────────────
async function loadEmails() {
  const r = await fetch('/api/emails').then(r => r.json()).catch(() => ({}));
  const emails = r.emails || [];
  const tbody = document.querySelector('#emails-table tbody');
  if (!emails.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No email drafts yet</td></tr>';
    return;
  }
  tbody.innerHTML = emails.map(e => `
    <tr>
      <td style="font-family:var(--mono);font-size:11px">${e.hr_email || '—'}</td>
      <td>${e.email_subject || '—'}</td>
      <td>${e.company || '—'}</td>
      <td>${scoreBar(e.fit_score)}</td>
      <td>${statusBadge(e.status)}</td>
    </tr>`).join('');
}

// ── History table ─────────────────────────────────────────────────────────────
async function loadHistory() {
  const r = await fetch('/api/logs').then(r => r.json()).catch(() => ({}));
  const runs = r.runs || [];
  const tbody = document.querySelector('#history-table tbody');
  if (!runs.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No runs yet</td></tr>';
    return;
  }
  tbody.innerHTML = runs.map(run => `
    <tr>
      <td style="font-family:var(--mono);font-size:11px">${run.run_id || '—'}</td>
      <td><span class="badge badge-blue">${run.triggered_by || '—'}</span></td>
      <td style="color:var(--muted);font-size:11px">${fmtDate(run.started_at)}</td>
      <td>${run.jobs_found ?? '—'}</td>
      <td>${run.jobs_applied ?? '—'}</td>
      <td>${run.emails_sent ?? '—'}</td>
      <td>${statusBadge(run.status)}</td>
    </tr>`).join('');
}

// ── Settings ──────────────────────────────────────────────────────────────────
async function loadSettings() {
  const r = await fetch('/api/status').then(r => r.json()).catch(() => ({}));
  const keys = r.env_keys || {};
  document.getElementById('settings-env').innerHTML =
    Object.entries({
      'GROQ_API_KEY':       keys.GROQ_API_KEY,
      'TAVILY_API_KEY':     keys.TAVILY_API_KEY,
      'GEMINI_API_KEY':     keys.GEMINI_API_KEY,
      'SCRAPINGBEE_API_KEY':keys.SCRAPINGBEE_API_KEY,
    }).map(([k,v]) => envRow(k, v)).join('');

  document.getElementById('settings-config').innerHTML = [
    ['AUTO_APPLY',              'false'],
    ['DRY_RUN',                 'true'],
    ['MIN_FIT_SCORE',           '50'],
    ['MAX_EMAILS_PER_RUN',      '10'],
    ['MAX_APPLICATIONS_PER_DAY','20'],
  ].map(([k,v]) => `<div style="color:var(--muted)">${k} <span style="color:var(--accent)">${v}</span></div>`).join('');
}

// ── Pipeline trigger ──────────────────────────────────────────────────────────
async function runNow() {
  const btn = document.getElementById('btn-run-now');
  btn.disabled = true;
  btn.textContent = '⏳ Running...';
  const r = await fetch('/api/run-now', {method:'POST'}).then(r=>r.json()).catch(e=>({error:e}));
  if (r.run_id) {
    showPipelineCard();
    listenToRun(r.run_id);
  } else {
    toast('Failed to start pipeline: ' + (r.error || 'unknown'), 'var(--red)');
    btn.disabled = false;
    btn.textContent = '⚡ Run Now (auto-discover)';
  }
}

async function uploadJd(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/api/upload-jd', {method:'POST', body:fd}).then(r=>r.json()).catch(e=>({error:e}));
  if (r.run_id) { showPipelineCard(); listenToRun(r.run_id); toast('JD uploaded — pipeline running'); }
  else toast('Upload failed: ' + (r.error || 'unknown'), 'var(--red)');
}

async function pasteJd() {
  const text = document.getElementById('jd-text').value.trim();
  if (text.length < 30) { toast('Paste more JD text first', 'var(--amber)'); return; }
  const r = await fetch('/api/paste-jd', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({jd_text: text})
  }).then(r=>r.json()).catch(e=>({error:e}));
  if (r.run_id) { showPipelineCard(); listenToRun(r.run_id); toast('JD received — pipeline running'); }
  else toast('Failed: ' + (r.error || 'unknown'), 'var(--red)');
}

async function uploadResume(file) {
  if (!file) return;
  toast('Uploading resume...');
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/api/upload-resume', {method:'POST', body:fd}).then(r=>r.json()).catch(e=>({error:e}));
  if (r.success) { toast('Resume uploaded ✓', 'var(--green)'); loadStatus(); }
  else toast('Upload failed: ' + (r.error || 'unknown'), 'var(--red)');
}

// Drag-and-drop helpers
function handleJdDrop(e) {
  e.preventDefault();
  document.getElementById('jd-drop').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadJd(file);
}
function handleResumeDrop(e) {
  e.preventDefault();
  document.getElementById('resume-drop').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadResume(file);
}

// ── SSE pipeline progress ─────────────────────────────────────────────────────
const STEP_MAP = {
  init:'discover', discover:'discover', discover_done:'discover',
  parse:'parse',   parse_done:'parse',
  score:'score',   score_done:'score',
  tailor:'tailor', tailor_done:'tailor',
  email:'email',   email_done:'email',
  done:'email',    error:'error'
};

function showPipelineCard() {
  const card = document.getElementById('pipeline-card');
  card.style.display = 'block';
  card.scrollIntoView({behavior:'smooth'});
  ['discover','parse','score','tailor','email'].forEach(s => {
    const el = document.getElementById('ps-' + s);
    el.classList.remove('done','active','error');
  });
  document.getElementById('prog-fill').style.width = '0%';
  document.getElementById('pipeline-log').textContent = 'Starting...';
}

function listenToRun(runId) {
  const es = new EventSource('/api/pipeline/stream/' + runId);
  const steps = ['discover','parse','score','tailor','email'];
  let lastStep = null;

  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    const pct  = data.pct || 0;
    const step = STEP_MAP[data.step];

    document.getElementById('prog-fill').style.width = pct + '%';
    document.getElementById('pipeline-log').textContent = data.msg || '';

    if (step && step !== 'error') {
      steps.forEach(s => {
        const el = document.getElementById('ps-' + s);
        const idx = steps.indexOf(s);
        const cur = steps.indexOf(step);
        el.classList.remove('done','active','error');
        if (idx < cur) el.classList.add('done');
        else if (idx === cur) el.classList.add('active');
      });
    }

    if (data.step === 'done') {
      steps.forEach(s => document.getElementById('ps-' + s).classList.replace('active','done') || document.getElementById('ps-' + s).classList.add('done'));
      document.getElementById('prog-fill').style.width = '100%';
      toast('Pipeline complete ✓', 'var(--green)');
      document.getElementById('btn-run-now').disabled = false;
      document.getElementById('btn-run-now').textContent = '⚡ Run Now (auto-discover)';
      loadDashStats(); loadDashJobs();
      es.close();
    }
    if (data.step === 'error') {
      toast('Pipeline error: ' + data.msg, 'var(--red)');
      document.getElementById('btn-run-now').disabled = false;
      document.getElementById('btn-run-now').textContent = '⚡ Run Now (auto-discover)';
      es.close();
    }
  };
  es.onerror = () => { es.close(); };
}

// ── Util ──────────────────────────────────────────────────────────────────────
function scoreBar(score) {
  if (score == null) return '—';
  const color = score >= 75 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
  return `<div class="score-bar">
    <div class="score-track"><div class="score-fill" style="width:${score}%;background:${color}"></div></div>
    <span style="font-size:11px;color:${color};width:28px">${score}</span>
  </div>`;
}

function statusBadge(status) {
  const map = {
    sent:'badge-green', draft:'badge-blue', ready:'badge-amber',
    skipped:'badge-gray', found:'badge-gray', failed:'badge-red',
    running:'badge-blue', completed:'badge-green', error:'badge-red'
  };
  return `<span class="badge ${map[status]||'badge-gray'}">${status||'—'}</span>`;
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadStatus();
loadDashStats();
loadDashJobs();
</script>
</body>
</html>"""


# ── Page ──────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return DASHBOARD_HTML


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


def _run_pipeline_thread(run_id: str, job_text: str = None, job_file: str = None):
    """Run orchestrator in background, push SSE events."""
    q = queue.Queue()
    _pipeline_queues[run_id] = q

    def _run():
        try:
            from pipeline.orchestrator import Orchestrator
            orch = Orchestrator(run_id=run_id)

            q.put({"step": "init",    "msg": "Initializing...",          "pct": 5})
            q.put({"step": "discover","msg": "Searching for jobs...",     "pct": 10})

            results = orch.run_full_pipeline(
                triggered_by = "manual" if (job_text or job_file) else "scheduled",
                job_text     = job_text,
                job_file     = job_file,
            )

            # Push progress milestones based on results
            q.put({"step": "discover_done", "pct": 30,
                   "msg": f"Found {results.get('jobs_found', 0)} jobs",
                   "count": results.get("jobs_found", 0)})
            q.put({"step": "parse_done",    "pct": 50,
                   "msg": f"Filtered to {results.get('jobs_filtered', 0)} new jobs"})
            q.put({"step": "tailor_done",   "pct": 75,
                   "msg": f"Tailored {results.get('jobs_applied', 0)} applications"})
            q.put({"step": "email_done",    "pct": 90,
                   "msg": f"Prepared {results.get('jobs_applied', 0)} draft(s)"})

            get_db().update_run_log(
                run_id,
                jobs_found    = results.get("jobs_found", 0),
                jobs_filtered = results.get("jobs_filtered", 0),
                jobs_applied  = results.get("jobs_applied", 0),
                emails_sent   = results.get("emails_sent", 0),
                errors_count  = len(results.get("errors", [])),
                status        = results.get("status", "completed"),
                summary       = results,
            )
            orch.save_run_summary()

            q.put({"step": "done", "msg": "Pipeline complete!", "pct": 100, "results": results})

        except Exception as e:
            logger.error(f"[app] Pipeline thread error: {e}", exc_info=True)
            q.put({"step": "error", "msg": str(e), "pct": 0})

    threading.Thread(target=_run, daemon=True).start()


# ── API Routes ────────────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    groq_key    = os.getenv("GROQ_API_KEY", "")
    tavily_key  = os.getenv("TAVILY_API_KEY", "")
    resume_path = os.getenv("MASTER_RESUME_PDF", str(ROOT / "resume/master_resume.pdf"))
    return jsonify({
        "status":           "online",
        "timestamp":        datetime.now().isoformat(),
        "resume_uploaded":  os.path.exists(resume_path),
        "resume_path":      resume_path if os.path.exists(resume_path) else None,
        "env_keys": {
            "GROQ_API_KEY":        bool(groq_key   and groq_key   != "gsk_xxxxxxxxxxxxx"),
            "TAVILY_API_KEY":      bool(tavily_key and tavily_key != "tvly_xxxxxxxxxxxxx"),
            "GEMINI_API_KEY":      bool(os.getenv("GEMINI_API_KEY")),
            "SCRAPINGBEE_API_KEY": bool(os.getenv("SCRAPINGBEE_API_KEY")),
        },
    })


@app.route("/api/run-now", methods=["POST"])
def api_run_now():
    run_id = str(uuid.uuid4())[:8]
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
    get_db().start_run_log(run_id, "upload")
    _run_pipeline_thread(run_id, job_file=filepath)
    return jsonify({"success": True, "run_id": run_id, "filename": filename})


@app.route("/api/paste-jd", methods=["POST"])
def api_paste_jd():
    data     = request.get_json() or {}
    jd_text  = data.get("jd_text", "").strip()
    if len(jd_text) < 30:
        return jsonify({"error": "JD text too short (min 30 chars)"}), 400

    run_id = str(uuid.uuid4())[:8]
    get_db().start_run_log(run_id, "paste")
    _run_pipeline_thread(run_id, job_text=jd_text)
    return jsonify({"success": True, "run_id": run_id})


@app.route("/api/upload-resume", methods=["POST"])
def api_upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename or not _allowed(file.filename, ALLOWED_RESUME):
        return jsonify({"error": "Allowed: PDF, DOCX, TXT"}), 400

    ext        = _ext(file.filename)
    resume_dir = ROOT / "resume"
    resume_dir.mkdir(parents=True, exist_ok=True)
    name_map   = {"pdf": "master_resume.pdf", "docx": "master_resume.docx",
                  "doc": "master_resume.docx", "txt": "master_resume.txt"}
    save_path  = resume_dir / name_map.get(ext, "master_resume.txt")
    file.save(save_path)
    logger.info(f"[app] Resume saved: {save_path}")

    result = {"success": True, "path": str(save_path), "size": os.path.getsize(save_path)}
    try:
        from agents.resume_parser_agent import ResumeParserAgent
        parsed         = ResumeParserAgent().parse_file(str(save_path))
        result["parsed"] = parsed
    except Exception as e:
        logger.warning(f"[app] Resume parse on upload failed: {e}")
        result["parse_error"] = str(e)

    return jsonify(result)


@app.route("/api/resume-status")
def api_resume_status():
    resume_dir = ROOT / "resume"
    for name in ["master_resume.pdf", "master_resume.docx", "master_resume.txt"]:
        path = resume_dir / name
        if path.exists():
            return jsonify({
                "uploaded": True, "path": str(path), "filename": name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            })
    return jsonify({"uploaded": False})


@app.route("/api/jobs")
def api_jobs():
    try:
        jobs = get_db().get_all_jobs(limit=100)
        return jsonify({"success": True, "jobs": jobs, "total": len(jobs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/emails")
def api_emails():
    try:
        emails = get_db().get_unsent_emails()
        return jsonify({"success": True, "emails": emails, "total": len(emails)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/logs")
def api_logs():
    try:
        runs = get_db().get_recent_run_logs(limit=20)
        return jsonify({"success": True, "runs": runs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics")
def api_analytics():
    try:
        db       = get_db()
        all_jobs = db.get_all_jobs(limit=1000)
        runs     = db.get_recent_run_logs(limit=50)
        total    = len(all_jobs)
        applied  = sum(1 for j in all_jobs if j.get("status") == "sent")
        tailored = sum(1 for j in all_jobs if j.get("status") in ("sent", "draft", "ready"))
        avg      = sum(j.get("fit_score") or 0 for j in all_jobs) / max(total, 1)
        sources  = {}
        for j in all_jobs:
            src = j.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        return jsonify({"success": True, "analytics": {
            "total_jobs": total, "applied": applied, "tailored": tailored,
            "avg_score": round(avg, 1), "total_runs": len(runs),
            "source_distribution": sources,
        }})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Applyr on http://localhost:5000")
    app.run(
        debug      = os.getenv("DEBUG", "true").lower() == "true",
        use_reloader = False,   # prevents killing background pipeline threads
        host       = "0.0.0.0",
        port       = int(os.getenv("FLASK_PORT", 5000)),
    )
